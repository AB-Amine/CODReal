"""Auth / profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentUser
from app.core.firebase_client import is_firebase_configured
from app.core.supabase_client import is_supabase_configured
from app.services import persistence as db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status() -> dict:
    fb_configured = is_firebase_configured()
    sb_configured = is_supabase_configured()
    configured = fb_configured or sb_configured
    provider = "firebase" if fb_configured else ("supabase" if sb_configured else "none")

    return {
        "configured": configured,
        "provider": provider,
        "firebase_configured": fb_configured,
        "supabase_configured": sb_configured,
        "message": (
            f"Prêt pour Authentification {provider.title()}"
            if configured
            else "Configurez Firebase ou Supabase dans l'environnement"
        ),
    }


@router.get("/me")
def me(user: CurrentUser) -> dict:
    try:
        profile = db.ensure_profile(user.id, email=user.email)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "id": user.id,
        "email": user.email or profile.get("email"),
        "profile": profile,
    }
