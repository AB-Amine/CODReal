"""Campaign CRUD (manual entry until Meta/TikTok OAuth)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser
from app.core.supabase_client import SupabaseNotConfiguredError
from app.services import persistence as db

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    platform: str = "manual"
    platform_campaign_id: str | None = None
    spend: float = 0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    status: str = "active"


class CampaignBulk(BaseModel):
    campaigns: list[CampaignCreate] = Field(default_factory=list)


@router.get("")
def list_my_campaigns(user: CurrentUser) -> dict:
    try:
        rows = db.list_campaigns(user.id)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"campaigns": rows, "count": len(rows)}


@router.post("")
def create_campaign(body: CampaignCreate, user: CurrentUser) -> dict:
    try:
        db.ensure_profile(user.id, email=user.email)
        row = db.upsert_campaign(
            user.id,
            platform_campaign_id=body.platform_campaign_id
            or f"manual-{body.name.strip().lower().replace(' ', '-')[:60]}",
            name=body.name,
            platform=body.platform,
            spend=body.spend,
            impressions=body.impressions,
            clicks=body.clicks,
            leads=body.leads,
            status=body.status,
        )
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"campaign": row}


@router.post("/bulk")
def bulk_upsert(body: CampaignBulk, user: CurrentUser) -> dict:
    try:
        db.ensure_profile(user.id, email=user.email)
        rows = db.upsert_campaigns_bulk(
            user.id,
            [c.model_dump() | {"campaign_id": c.platform_campaign_id} for c in body.campaigns],
        )
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"campaigns": rows, "count": len(rows)}
