"""Users / settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser
from app.services import persistence as db

router = APIRouter(prefix="/users", tags=["users"])


class UserSettingsSchema(BaseModel):
    return_fee_mad: float = Field(25.0, description="Frais de retour par défaut (MAD)")
    critical_return_rate: float = Field(0.30, description="Taux de retour critique (%)")
    target_roas: float = Field(2.00, description="Objectif ROAS minimum")


@router.get("/settings")
def get_settings(user: CurrentUser) -> dict:
    """Fetch user settings."""
    try:
        return db.get_user_settings(user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erreur lecture settings: {exc}"
        ) from exc


@router.post("/settings")
def save_settings(body: UserSettingsSchema, user: CurrentUser) -> dict:
    """Create or update user settings."""
    try:
        return db.save_user_settings(
            user.id,
            return_fee_mad=body.return_fee_mad,
            critical_return_rate=body.critical_return_rate,
            target_roas=body.target_roas,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erreur enregistrement settings: {exc}"
        ) from exc
