from fastapi import APIRouter

from app.core.config import get_settings
from app.core.supabase_client import is_supabase_configured
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    base = HealthResponse(app=settings.app_name, version=settings.app_version)
    ready = is_supabase_configured()
    return {
        **base.model_dump(),
        "supabase_configured": ready,
        "supabase_url_set": bool((settings.supabase_url or "").strip()),
        "supabase_key_set": bool((settings.supabase_key or "").strip()),
        "supabase_jwt_set": bool((settings.supabase_jwt_secret or "").strip()),
        "meta_configured": settings.meta_configured,
        "tiktok_configured": settings.tiktok_configured,
    }
