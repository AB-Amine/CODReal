"""Pydantic schemas for API request/response."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str


class CampaignIn(BaseModel):
    campaign_id: str
    name: str = ""
    platform: str = "meta"
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0


class OrderIn(BaseModel):
    id: str | None = None
    order_ref: str | None = None
    phone: str
    status: Literal["delivered", "returned", "refused", "pending"]
    amount_collected: float = 0.0
    delivery_date: str | None = None
    carrier: str | None = None
    campaign_id: str | None = None


class LeadIn(BaseModel):
    id: str | None = None
    campaign_id: str
    phone: str | None = None
    order_ref: str | None = None


class MatchRequest(BaseModel):
    orders: list[OrderIn]
    leads: list[LeadIn] = Field(default_factory=list)
    phone_to_campaign: dict[str, str] = Field(
        default_factory=dict,
        description="Map normalized phone → campaign_id",
    )


class MatchResponse(BaseModel):
    matches: list[dict[str, Any]]
    unmatched_orders: list[str]
    unmatched_leads: list[str]
    duplicate_phones: list[str]
    stats: dict[str, Any]


class CalculateRequest(BaseModel):
    campaigns: list[CampaignIn]
    orders: list[OrderIn]
    return_fee: float | None = None
    # optional pre-computed matches: order_id → campaign_id
    order_campaign_map: dict[str, str] = Field(default_factory=dict)


class PipelineRequest(BaseModel):
    """Full pipeline: match orders to campaigns then compute KPIs."""

    campaigns: list[CampaignIn]
    orders: list[OrderIn]
    leads: list[LeadIn] = Field(default_factory=list)
    phone_to_campaign: dict[str, str] = Field(default_factory=dict)
    return_fee: float | None = 25.0


class AlertRule(BaseModel):
    min_roas: float = 1.0
    max_return_rate: float = 0.30
    min_net_profit: float = 0.0


class AlertItem(BaseModel):
    campaign_id: str
    name: str
    severity: Literal["info", "warning", "critical"]
    code: str
    message: str
