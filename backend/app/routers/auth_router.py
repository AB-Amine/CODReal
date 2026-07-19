"""Auth / profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentUser
from app.core.supabase_client import (
    SupabaseNotConfiguredError,
    is_supabase_configured,
)
from app.services import persistence as db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status() -> dict:
    return {
        "supabase_configured": is_supabase_configured(),
        "message": (
            "Prêt pour JWT Supabase"
            if is_supabase_configured()
            else "Configurez SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET"
        ),
    }


@router.get("/me")
def me(user: CurrentUser) -> dict:
    try:
        profile = db.ensure_profile(user.id, email=user.email)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "id": user.id,
        "email": user.email or profile.get("email"),
        "profile": profile,
    }
