"""Dashboard KPIs and calculation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.phone import normalize_phone
from app.core.supabase_client import SupabaseNotConfiguredError
from app.models.schemas import AlertRule, CalculateRequest, PipelineRequest
from app.services.alerts import AlertRule as ServiceAlertRule
from app.services.alerts import build_alerts
from app.services.calculations import (
    CalculationEngine,
    CampaignInput,
    CampaignMetrics,
    OrderForCalc,
    kpis_to_dict,
)
from app.services.matching import LeadCandidate, MatchingEngine, OrderRecord
from app.services import persistence as db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.post("/calculate")
def calculate(body: CalculateRequest) -> dict:
    """Compute real KPIs from campaigns + orders (already attributed or mapped)."""
    settings = get_settings()
    engine = CalculationEngine(
        default_return_fee=body.return_fee
        if body.return_fee is not None
        else settings.default_return_fee
    )

    campaigns = [
        CampaignInput(
            campaign_id=c.campaign_id,
            name=c.name,
            platform=c.platform,
            spend=c.spend,
            impressions=c.impressions,
            clicks=c.clicks,
            leads=c.leads,
        )
        for c in body.campaigns
    ]

    order_calcs: list[OrderForCalc] = []
    for i, o in enumerate(body.orders):
        oid = o.id or o.order_ref or f"order-{i}"
        campaign_id = (
            o.campaign_id
            or body.order_campaign_map.get(oid)
            or body.order_campaign_map.get(o.order_ref or "")
        )
        if not campaign_id:
            continue
        order_calcs.append(
            OrderForCalc(
                order_id=oid,
                campaign_id=campaign_id,
                status=o.status,
                amount_collected=o.amount_collected,
            )
        )

    kpis = engine.compute_dashboard(campaigns, order_calcs)
    return kpis_to_dict(kpis)


@router.post("/pipeline")
def full_pipeline(body: PipelineRequest) -> dict:
    """Match + calculate in one call (demo / MVP without DB)."""
    settings = get_settings()
    matcher = MatchingEngine()
    calculator = CalculationEngine(
        default_return_fee=body.return_fee
        if body.return_fee is not None
        else settings.default_return_fee
    )

    phone_map = dict(body.phone_to_campaign)
    for o in body.orders:
        if o.campaign_id and o.phone:
            n = normalize_phone(o.phone)
            if n:
                phone_map.setdefault(n, o.campaign_id)

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

    report = matcher.match(leads, orders, phone_to_campaign=phone_map or None)

    order_by_id = {o.id: o for o in orders}
    amount_by_id = {
        (o.id or o.order_ref or f"order-{i}"): o.amount_collected
        for i, o in enumerate(body.orders)
    }
    status_by_id = {
        (o.id or o.order_ref or f"order-{i}"): o.status
        for i, o in enumerate(body.orders)
    }

    matched_orders = [
        OrderForCalc(
            order_id=m.order_id,
            campaign_id=m.campaign_id,
            status=status_by_id.get(m.order_id, order_by_id[m.order_id].status),
            amount_collected=amount_by_id.get(
                m.order_id, order_by_id[m.order_id].amount_collected
            ),
        )
        for m in report.matches
        if m.order_id in order_by_id
    ]

    campaigns = [
        CampaignInput(
            campaign_id=c.campaign_id,
            name=c.name,
            platform=c.platform,
            spend=c.spend,
            impressions=c.impressions,
            clicks=c.clicks,
            leads=c.leads,
        )
        for c in body.campaigns
    ]

    kpis = calculator.compute_dashboard(campaigns, matched_orders)
    alerts = build_alerts(kpis.campaigns)

    return {
        "matching": {
            "matches": [
                {
                    "campaign_id": m.campaign_id,
                    "order_id": m.order_id,
                    "match_type": m.match_type.value,
                    "confidence_score": m.confidence_score,
                    "normalized_phone": m.normalized_phone,
                }
                for m in report.matches
            ],
            "stats": report.stats,
            "unmatched_orders": report.unmatched_orders,
        },
        "kpis": kpis_to_dict(kpis),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/me")
def dashboard_from_db(user: CurrentUser) -> dict:
    """Load KPIs for the authenticated user from Supabase."""
    settings = get_settings()
    try:
        result = db.compute_user_dashboard(
            user.id, return_fee=settings.default_return_fee
        )
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erreur lecture dashboard: {exc}"
        ) from exc
    return result


@router.post("/seed-demo")
def seed_demo(user: CurrentUser) -> dict:
    """Seed demo campaigns/orders/matches for the current user (dev / onboarding)."""
    try:
        return db.seed_demo_for_user(user.id, email=user.email)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erreur seed demo: {exc}"
        ) from exc


@router.post("/alerts/evaluate")
def evaluate_alerts(body: CalculateRequest, rules: AlertRule | None = None) -> dict:
    """Re-run calculate and apply alert rules."""
    kpis = calculate(body)
    rule = rules or AlertRule()
    service_rule = ServiceAlertRule(
        min_roas=rule.min_roas,
        max_return_rate=rule.max_return_rate,
        min_net_profit=rule.min_net_profit,
    )
    campaigns = [
        CampaignMetrics(
            campaign_id=c["campaign_id"],
            name=c["name"],
            platform=c.get("platform", ""),
            total_spend=c["total_spend"],
            delivered_orders=c["delivered_orders"],
            returned_orders=c["returned_orders"],
            refused_orders=c.get("refused_orders", 0),
            pending_orders=c.get("pending_orders", 0),
            total_matched_orders=c.get("total_matched_orders", 0),
            net_revenue=c["net_revenue"],
            return_fees=c.get("return_fees", 0),
            net_profit=c["net_profit"],
            real_cpa=c.get("real_cpa"),
            real_roas=c.get("real_roas"),
            return_rate=c.get("return_rate"),
            performance_score=c.get("performance_score", "warning"),
            performance_label=c.get("performance_label", ""),
        )
        for c in kpis["campaigns"]
    ]
    alerts = build_alerts(campaigns, service_rule)
    return {"alerts": [a.to_dict() for a in alerts], "kpis": kpis}
