"""Third-party ad platform integrations (Meta + TikTok, read-only)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.supabase_client import SupabaseNotConfiguredError, is_supabase_configured
from app.services import meta_sync, tiktok_sync
from app.services.meta_api import MetaAPIError, MetaMarketingClient
from app.services.tiktok_api import TikTokAPIError, TikTokMarketingClient

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ───────────────────────────── Meta ─────────────────────────────


@router.get("/meta/status")
def meta_status() -> dict:
    settings = get_settings()
    return {
        "platform": "meta",
        "configured": settings.meta_configured,
        "graph_version": settings.meta_graph_version,
        "scopes": settings.meta_oauth_scopes,
        "redirect_uri": settings.meta_redirect_uri,
        "supabase_configured": is_supabase_configured(),
        "mock_available": True,
        "read_only": True,
    }


@router.get("/meta/accounts")
def meta_accounts(user: CurrentUser) -> dict:
    try:
        accounts = meta_sync.list_meta_accounts(user.id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"accounts": accounts, "count": len(accounts)}


@router.get("/meta/connect")
def meta_connect(user: CurrentUser) -> dict:
    settings = get_settings()
    if not settings.meta_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Meta App non configurée. Définissez META_APP_ID et META_APP_SECRET, "
                "ou utilisez POST /integrations/meta/mock-connect pour la démo."
            ),
        )
    if not is_supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase requis pour stocker les tokens Meta")
    state = meta_sync.create_oauth_state(user.id)
    url = MetaMarketingClient().build_oauth_url(state)
    return {
        "authorize_url": url,
        "state": state,
        "scopes": settings.meta_oauth_scopes,
        "redirect_uri": settings.meta_redirect_uri,
    }


@router.get("/meta/callback")
def meta_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    settings = get_settings()
    front = settings.frontend_url.rstrip("/")
    fail = f"{front}/integrations?meta=error"

    if error:
        return RedirectResponse(
            url=f"{fail}&message={quote(error_description or error)}",
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(url=f"{fail}&message=missing_code_or_state", status_code=302)

    try:
        user_id = meta_sync.parse_oauth_state(state)
        result = meta_sync.complete_oauth(user_id, code)
        if result.get("accounts"):
            try:
                meta_sync.sync_meta_account(
                    user_id, ad_account_row_id=result["accounts"][0]["id"]
                )
            except Exception:
                pass
        return RedirectResponse(
            url=f"{front}/integrations?meta=connected&accounts={result.get('count', 1)}",
            status_code=302,
        )
    except (MetaAPIError, SupabaseNotConfiguredError, ValueError) as exc:
        return RedirectResponse(
            url=f"{fail}&message={quote(str(exc)[:200])}",
            status_code=302,
        )


@router.post("/meta/sync")
def meta_sync_endpoint(
    user: CurrentUser,
    ad_account_id: str | None = Query(None),
    date_preset: str | None = Query(None),
) -> dict:
    try:
        return meta_sync.sync_meta_account(
            user.id,
            ad_account_row_id=ad_account_id,
            date_preset=date_preset,
        )
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except MetaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync Meta échouée: {exc}") from exc


@router.post("/meta/mock-connect")
def meta_mock_connect(user: CurrentUser) -> dict:
    try:
        return meta_sync.connect_mock_meta(user.id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/meta/accounts/{ad_account_row_id}")
def meta_disconnect(ad_account_row_id: str, user: CurrentUser) -> dict:
    try:
        return meta_sync.disconnect_meta_account(user.id, ad_account_row_id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ───────────────────────────── TikTok ─────────────────────────────


@router.get("/tiktok/status")
def tiktok_status() -> dict:
    settings = get_settings()
    return {
        "platform": "tiktok",
        "configured": settings.tiktok_configured,
        "redirect_uri": settings.tiktok_redirect_uri,
        "api_base": settings.tiktok_api_base,
        "supabase_configured": is_supabase_configured(),
        "mock_available": True,
        "read_only": True,
    }


@router.get("/tiktok/accounts")
def tiktok_accounts(user: CurrentUser) -> dict:
    try:
        accounts = tiktok_sync.list_tiktok_accounts(user.id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"accounts": accounts, "count": len(accounts)}


@router.get("/tiktok/connect")
def tiktok_connect(user: CurrentUser) -> dict:
    settings = get_settings()
    if not settings.tiktok_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "TikTok App non configurée. Définissez TIKTOK_APP_ID et TIKTOK_APP_SECRET, "
                "ou utilisez POST /integrations/tiktok/mock-connect."
            ),
        )
    if not is_supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase requis pour stocker les tokens TikTok")
    state = tiktok_sync.create_oauth_state(user.id)
    url = TikTokMarketingClient().build_oauth_url(state)
    return {
        "authorize_url": url,
        "state": state,
        "redirect_uri": settings.tiktok_redirect_uri,
    }


@router.get("/tiktok/callback")
def tiktok_callback(
    auth_code: str | None = None,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """TikTok may send auth_code (or code) + state."""
    settings = get_settings()
    front = settings.frontend_url.rstrip("/")
    fail = f"{front}/integrations?tiktok=error"
    token_code = auth_code or code

    if error:
        return RedirectResponse(
            url=f"{fail}&message={quote(error_description or error)}",
            status_code=302,
        )
    if not token_code or not state:
        return RedirectResponse(url=f"{fail}&message=missing_code_or_state", status_code=302)

    try:
        user_id = tiktok_sync.parse_oauth_state(state)
        result = tiktok_sync.complete_oauth(user_id, token_code)
        if result.get("accounts"):
            try:
                tiktok_sync.sync_tiktok_account(
                    user_id, ad_account_row_id=result["accounts"][0]["id"]
                )
            except Exception:
                pass
        return RedirectResponse(
            url=f"{front}/integrations?tiktok=connected&accounts={result.get('count', 1)}",
            status_code=302,
        )
    except (TikTokAPIError, SupabaseNotConfiguredError, ValueError) as exc:
        return RedirectResponse(
            url=f"{fail}&message={quote(str(exc)[:200])}",
            status_code=302,
        )


@router.post("/tiktok/sync")
def tiktok_sync_endpoint(
    user: CurrentUser,
    ad_account_id: str | None = Query(None),
) -> dict:
    try:
        return tiktok_sync.sync_tiktok_account(user.id, ad_account_row_id=ad_account_id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TikTokAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync TikTok échouée: {exc}") from exc


@router.post("/tiktok/mock-connect")
def tiktok_mock_connect(user: CurrentUser) -> dict:
    try:
        return tiktok_sync.connect_mock_tiktok(user.id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/tiktok/accounts/{ad_account_row_id}")
def tiktok_disconnect(ad_account_row_id: str, user: CurrentUser) -> dict:
    try:
        return tiktok_sync.disconnect_tiktok_account(user.id, ad_account_row_id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
