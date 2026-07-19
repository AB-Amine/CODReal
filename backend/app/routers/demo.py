"""Demo helpers — no ads app keys required."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.supabase_client import is_supabase_configured
from app.services.calculations import CalculationEngine, CampaignInput, OrderForCalc, kpis_to_dict
from app.services.matching import LeadCandidate, MatchingEngine, OrderRecord

router = APIRouter(prefix="/demo", tags=["demo"])

# Same sample set as samples/demo_pipeline.json / frontend DEMO_PIPELINE
_DEMO_CAMPAIGNS = [
    CampaignInput("meta-summer", "Summer Meta Lookalike", "meta", 1200, 45000, 890, 40),
    CampaignInput("tiktok-broad", "TikTok Broad COD", "tiktok", 800, 60000, 1200, 35),
    CampaignInput("meta-retarget", "Retargeting Meta", "meta", 400, 12000, 400, 20),
]

_DEMO_LEADS = [
    LeadCandidate("l1", "meta-summer", "0612345678", "CMD-2026-0001"),
    LeadCandidate("l2", "meta-summer", "+212698765432", "CMD-2026-0002"),
    LeadCandidate("l3", "meta-summer", "0611223344", "CMD-2026-0003"),
    LeadCandidate("l4", "tiktok-broad", "0700112233", "CMD-2026-0004"),
    LeadCandidate("l5", "tiktok-broad", "0655554444", "CMD-2026-0005"),
    LeadCandidate("l6", "tiktok-broad", "0655554444", "CMD-2026-0006"),
    LeadCandidate("l7", "meta-retarget", "0611223344", "CMD-2026-0007"),
    LeadCandidate("l8", "meta-retarget", "0699887766", "CMD-2026-0008"),
]

_DEMO_ORDERS = [
    OrderRecord("o1", "0612345678", "CMD-2026-0001", "delivered", 449, "2026-07-10"),
    OrderRecord("o2", "+212698765432", "CMD-2026-0002", "delivered", 349, "2026-07-11"),
    OrderRecord("o3", "06 11 22 33 44", "CMD-2026-0003", "returned", 0, "2026-07-12"),
    OrderRecord("o4", "0700112233", "CMD-2026-0004", "refused", 0, "2026-07-12"),
    OrderRecord("o5", "00212655554444", "CMD-2026-0005", "delivered", 499, "2026-07-13"),
    OrderRecord("o6", "0655554444", "CMD-2026-0006", "pending", 0, "2026-07-14"),
    OrderRecord("o7", "0611223344", "CMD-2026-0007", "delivered", 299, "2026-07-14"),
    OrderRecord("o8", "0699887766", "CMD-2026-0008", "delivered", 399, "2026-07-15"),
]


@router.get("/ready")
def demo_ready() -> dict:
    """What works for local demo right now (no secrets required for core path)."""
    settings = get_settings()
    supabase = is_supabase_configured()
    meta = settings.meta_configured
    tiktok = settings.tiktok_configured

    return {
        "ok": True,
        "message": "Local demo is ready without Meta/TikTok App IDs (use pipeline + mock).",
        "paths": {
            "instant_demo_no_login": {
                "ready": True,
                "how": "POST /api/v1/demo/run or Dashboard → Démo locale",
                "needs": [],
            },
            "full_demo_with_account": {
                "ready": supabase,
                "how": "Signup → seed-demo or mock Meta/TikTok → CSV upload persist",
                "needs": [] if supabase else ["SUPABASE_* in backend/.env"],
            },
            "real_meta_oauth": {
                "ready": meta and supabase,
                "needs": (["META_APP_ID", "META_APP_SECRET"] if not meta else [])
                + ([] if supabase else ["Supabase"]),
            },
            "real_tiktok_oauth": {
                "ready": tiktok and supabase,
                "needs": (["TIKTOK_APP_ID", "TIKTOK_APP_SECRET"] if not tiktok else [])
                + ([] if supabase else ["Supabase"])
                + ["TikTok app verification approved"],
            },
        },
        "supabase_configured": supabase,
        "meta_app_configured": meta,
        "tiktok_app_configured": tiktok,
        "csv_template": "samples/codreal_delivery_template.csv",
        "docs": "http://127.0.0.1:8000/docs",
    }


@router.post("/run")
def demo_run() -> dict:
    """
    Full in-memory demo: match sample leads/orders → KPIs + alerts.
    No auth, no Supabase, no Meta/TikTok keys.
    """
    settings = get_settings()
    report = MatchingEngine().match(_DEMO_LEADS, _DEMO_ORDERS)

    amounts = {o.id: o.amount_collected for o in _DEMO_ORDERS}
    statuses = {o.id: o.status for o in _DEMO_ORDERS}
    matched = [
        OrderForCalc(
            order_id=m.order_id,
            campaign_id=m.campaign_id,
            status=statuses[m.order_id],
            amount_collected=amounts[m.order_id],
        )
        for m in report.matches
        if m.order_id in statuses
    ]

    kpis = CalculationEngine(
        default_return_fee=settings.default_return_fee
    ).compute_dashboard(_DEMO_CAMPAIGNS, matched)

    from app.services.alerts import build_alerts

    alerts = build_alerts(kpis.campaigns)

    return {
        "mode": "local_memory",
        "matching": {
            "stats": report.stats,
            "matches": [
                {
                    "campaign_id": m.campaign_id,
                    "order_id": m.order_id,
                    "match_type": m.match_type.value,
                    "confidence_score": m.confidence_score,
                }
                for m in report.matches
            ],
            "unmatched_orders": report.unmatched_orders,
        },
        "kpis": kpis_to_dict(kpis),
        "alerts": [a.to_dict() for a in alerts],
        "hint": "Open frontend /dashboard and click 'Démo locale' for the same data in the UI.",
    }


@router.get("/sample-csv")
def sample_csv_info() -> dict:
    root = Path(__file__).resolve().parents[3]  # CODREAL/
    path = root / "samples" / "codreal_delivery_template.csv"
    exists = path.exists()
    preview = path.read_text(encoding="utf-8")[:500] if exists else None
    return {
        "path": str(path) if exists else "samples/codreal_delivery_template.csv",
        "exists": exists,
        "preview": preview,
        "upload_url": "/api/v1/orders/upload",
    }
