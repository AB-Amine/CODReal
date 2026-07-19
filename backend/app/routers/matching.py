"""Matching API."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import MatchRequest, MatchResponse
from app.services.matching import (
    LeadCandidate,
    MatchingEngine,
    OrderRecord,
)

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/run", response_model=MatchResponse)
def run_matching(body: MatchRequest) -> MatchResponse:
    engine = MatchingEngine()
    leads = [
        LeadCandidate(
            id=l.id or f"lead-{i}",
            campaign_id=l.campaign_id,
            phone=l.phone,
            order_ref=l.order_ref,
        )
        for i, l in enumerate(body.leads)
    ]
    orders = [
        OrderRecord(
            id=o.id or o.order_ref or f"order-{i}",
            phone=o.phone,
            order_ref=o.order_ref,
            status=o.status,
            amount_collected=o.amount_collected,
            delivery_date=o.delivery_date,
            carrier=o.carrier,
        )
        for i, o in enumerate(body.orders)
    ]
    report = engine.match(
        leads, orders, phone_to_campaign=body.phone_to_campaign or None
    )
    return MatchResponse(
        matches=[
            {
                "campaign_id": m.campaign_id,
                "order_id": m.order_id,
                "lead_id": m.lead_id,
                "match_type": m.match_type.value,
                "confidence_score": m.confidence_score,
                "normalized_phone": m.normalized_phone,
                "order_ref": m.order_ref,
            }
            for m in report.matches
        ],
        unmatched_orders=report.unmatched_orders,
        unmatched_leads=report.unmatched_leads,
        duplicate_phones=report.duplicate_phones,
        stats=report.stats,
    )
