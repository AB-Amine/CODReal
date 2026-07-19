"""Cron / background jobs (protected by CRON_SECRET)."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.config import get_settings
from app.core.supabase_client import SupabaseNotConfiguredError, is_supabase_configured
from app.services.sync_jobs import sync_all_accounts

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _assert_cron(authorization: str | None) -> None:
    settings = get_settings()
    expected = settings.cron_secret
    if not expected:
        raise HTTPException(status_code=503, detail="CRON_SECRET non configuré")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization Bearer requis")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="CRON_SECRET invalide")


@router.post("/sync-ads")
def job_sync_ads(
    authorization: str | None = Header(default=None),
    platform: str | None = Query(None, description="meta | tiktok | omit for all"),
) -> dict:
    """
    Sync all connected ad accounts.

    Call every 4–6h from Render Cron / GitHub Actions / Task Scheduler:

      curl -X POST http://127.0.0.1:8000/api/v1/jobs/sync-ads \\
        -H "Authorization: Bearer YOUR_CRON_SECRET"
    """
    _assert_cron(authorization)
    if not is_supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    if platform and platform not in ("meta", "tiktok"):
        raise HTTPException(status_code=400, detail="platform doit être meta ou tiktok")
    try:
        return sync_all_accounts(platform=platform)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def jobs_health() -> dict:
    settings = get_settings()
    return {
        "cron_configured": bool(settings.cron_secret),
        "supabase_configured": is_supabase_configured(),
        "meta_configured": settings.meta_configured,
        "tiktok_configured": settings.tiktok_configured,
    }
