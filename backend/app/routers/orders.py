"""CSV upload and order parsing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core.auth import CurrentUser, OptionalUser
from app.core.config import get_settings
from app.core.supabase_client import SupabaseNotConfiguredError
from app.services import persistence as db
from app.services.csv_parser import parse_delivery_file, parse_result_to_dict

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/upload")
async def upload_delivery_file(
    file: UploadFile = File(...),
    *,
    user: OptionalUser,
    persist: bool = Query(
        False,
        description="Si true et utilisateur authentifié, enregistre en base + matching",
    ),
) -> dict:
    """Parse and validate a CSV/Excel delivery export.

    Without auth: validation only.
    With auth + persist=true: save orders, match, compute KPIs.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    allowed = (".csv", ".xlsx", ".xls")
    lower = file.filename.lower()
    if not any(lower.endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Utilisez: {', '.join(allowed)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo)")

    result = parse_delivery_file(content, file.filename)
    payload = parse_result_to_dict(result)
    payload["filename"] = file.filename
    payload["persisted"] = False

    if persist:
        if user is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Authentification requise pour persister. "
                    "Connectez-vous sur /login (Supabase), puis réessayez l'upload. "
                    "Le frontend doit envoyer: Authorization: Bearer <session.access_token>."
                ),
            )
        if not result.valid_rows:
            raise HTTPException(
                status_code=400,
                detail="Aucune ligne valide à enregistrer",
            )
        settings = get_settings()
        try:
            saved = db.process_and_persist_upload(
                user.id,
                filename=file.filename,
                valid_rows=result.valid_rows,
                total_rows=result.total_rows,
                error_count=result.error_count,
                return_fee=settings.default_return_fee,
            )
        except SupabaseNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Erreur persistance: {exc}"
            ) from exc
        payload["persisted"] = True
        payload["persistence"] = {
            "batch": saved.get("batch"),
            "orders_saved": saved.get("orders_saved"),
            "matches_saved": saved.get("matches_saved"),
            "matching": saved.get("matching"),
            "kpis": saved.get("kpis"),
            "alerts": saved.get("alerts"),
        }

    return payload


@router.get("")
def list_orders(user: CurrentUser, limit: int = Query(100, ge=1, le=1000)) -> dict:
    try:
        rows = db.list_orders(user.id, limit=limit)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"orders": rows, "count": len(rows)}


@router.get("/template/info")
def template_info() -> dict:
    """Document expected CSV columns for the frontend."""
    return {
        "required": ["phone", "status", "amount_collected", "delivery_date"],
        "optional": ["order_ref", "carrier", "campaign_name", "campaign_id"],
        "status_values": ["delivered", "returned", "refused", "pending"],
        "status_aliases_fr": {
            "livré": "delivered",
            "retour": "returned",
            "refusé": "refused",
            "en_cours": "pending",
        },
        "example_filename": "codreal_delivery_template.csv",
        "notes": [
            "Numéros marocains: 0612345678, +212612345678, 612345678 acceptés",
            "Montants en MAD (point ou virgule)",
            "Dates: YYYY-MM-DD ou formats Excel standards",
            "Avec auth: POST /orders/upload?persist=true pour enregistrer",
        ],
    }
