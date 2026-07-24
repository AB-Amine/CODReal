"""Persist and load CODReal domain data in Supabase."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.core.phone import normalize_phone
from app.core.supabase_client import get_supabase_admin
from app.services.calculations import (
    CalculationEngine,
    CampaignInput,
    OrderForCalc,
    kpis_to_dict,
)
from app.services.matching import LeadCandidate, MatchingEngine, OrderRecord


def ensure_profile(user_id: str, email: str | None = None, full_name: str | None = None) -> dict:
    """Create profile row if missing (trigger may already have done it)."""
    sb = get_supabase_admin()
    existing = (
        sb.table("profiles").select("*").eq("id", user_id).limit(1).execute()
    )
    if existing.data:
        return existing.data[0]

    row = {
        "id": user_id,
        "email": email or f"{user_id}@unknown.local",
        "full_name": full_name or "",
    }
    inserted = sb.table("profiles").insert(row).execute()
    return inserted.data[0] if inserted.data else row


def list_campaigns(user_id: str) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("campaigns")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def upsert_campaign(
    user_id: str,
    *,
    platform_campaign_id: str,
    name: str,
    platform: str = "manual",
    spend: float = 0.0,
    impressions: int = 0,
    clicks: int = 0,
    leads: int = 0,
    status: str = "active",
) -> dict:
    sb = get_supabase_admin()
    platform = platform if platform in ("meta", "tiktok", "manual") else "manual"
    payload = {
        "user_id": user_id,
        "platform_campaign_id": platform_campaign_id,
        "name": name,
        "platform": platform,
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "leads": leads,
        "status": status,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    # Prefer update if exists
    found = (
        sb.table("campaigns")
        .select("*")
        .eq("user_id", user_id)
        .eq("platform", platform)
        .eq("platform_campaign_id", platform_campaign_id)
        .limit(1)
        .execute()
    )
    if found.data:
        updated = (
            sb.table("campaigns")
            .update(payload)
            .eq("id", found.data[0]["id"])
            .execute()
        )
        return updated.data[0] if updated.data else {**found.data[0], **payload}

    inserted = sb.table("campaigns").insert(payload).execute()
    return inserted.data[0]


def upsert_campaigns_bulk(user_id: str, campaigns: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in campaigns:
        row = upsert_campaign(
            user_id,
            platform_campaign_id=str(
                c.get("platform_campaign_id") or c.get("campaign_id") or c.get("name")
            ),
            name=str(c.get("name") or c.get("campaign_id") or "Campagne"),
            platform=str(c.get("platform") or "manual"),
            spend=float(c.get("spend") or 0),
            impressions=int(c.get("impressions") or 0),
            clicks=int(c.get("clicks") or 0),
            leads=int(c.get("leads") or 0),
            status=str(c.get("status") or "active"),
        )
        out.append(row)
    return out


def create_upload_batch(
    user_id: str,
    *,
    filename: str,
    total_rows: int,
    valid_rows: int,
    error_rows: int,
    storage_path: str | None = None,
) -> dict:
    sb = get_supabase_admin()
    row = {
        "user_id": user_id,
        "filename": filename,
        "storage_path": storage_path,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "error_rows": error_rows,
    }
    res = sb.table("upload_batches").insert(row).execute()
    return res.data[0]


def insert_orders(
    user_id: str,
    orders: list[dict],
    *,
    upload_batch_id: str | None = None,
) -> list[dict]:
    if not orders:
        return []
    sb = get_supabase_admin()
    rows = []
    for o in orders:
        phone = o.get("phone") or ""
        rows.append(
            {
                "user_id": user_id,
                "order_ref": o.get("order_ref"),
                "phone": phone,
                "phone_normalized": o.get("phone_normalized")
                or normalize_phone(phone),
                "status": o.get("status") or "pending",
                "amount_collected": float(o.get("amount_collected") or 0),
                "delivery_date": o.get("delivery_date"),
                "carrier": o.get("carrier"),
                "upload_batch_id": upload_batch_id,
            }
        )
    res = sb.table("orders").insert(rows).execute()
    return res.data or []


def insert_leads(user_id: str, leads: list[dict], campaign_id_map: dict[str, str]) -> list[dict]:
    """campaign_id_map: external/platform id or name → uuid campaign id."""
    if not leads:
        return []
    sb = get_supabase_admin()
    rows = []
    for lead in leads:
        ext = str(lead.get("campaign_id") or "")
        camp_uuid = campaign_id_map.get(ext)
        if not camp_uuid and lead.get("campaign_name"):
            camp_uuid = campaign_id_map.get(str(lead["campaign_name"]))
        phone = lead.get("phone")
        rows.append(
            {
                "user_id": user_id,
                "campaign_id": camp_uuid,
                "phone": phone,
                "phone_normalized": normalize_phone(phone) if phone else None,
                "order_ref": lead.get("order_ref"),
                "source": lead.get("source") or "manual",
            }
        )
    res = sb.table("leads").insert(rows).execute()
    return res.data or []


def replace_matches(user_id: str, matches: list[dict]) -> list[dict]:
    """Insert match rows (skip duplicates via ignore or delete+insert for batch)."""
    if not matches:
        return []
    sb = get_supabase_admin()
    # Upsert-like: delete existing pairs for these order_ids then insert
    order_ids = [m["order_id"] for m in matches if m.get("order_id")]
    if order_ids:
        sb.table("matches").delete().eq("user_id", user_id).in_(
            "order_id", order_ids
        ).execute()
    res = sb.table("matches").insert(matches).execute()
    return res.data or []


def save_campaign_stats(user_id: str, stats_rows: list[dict]) -> None:
    if not stats_rows:
        return
    sb = get_supabase_admin()
    # Replace latest snapshot per campaign (simple MVP: insert only)
    for row in stats_rows:
        row["user_id"] = user_id
        row["calculated_at"] = datetime.now(timezone.utc).isoformat()
    sb.table("campaign_stats").insert(stats_rows).execute()


def save_alerts(user_id: str, alerts: list[dict]) -> None:
    if not alerts:
        return
    sb = get_supabase_admin()
    rows = [
        {
            "user_id": user_id,
            "campaign_id": a.get("campaign_id"),
            "severity": a.get("severity"),
            "code": a.get("code"),
            "message": a.get("message"),
            "is_read": False,
        }
        for a in alerts
    ]
    sb.table("alerts").insert(rows).execute()


def list_orders(user_id: str, limit: int = 500) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("orders")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def list_leads(user_id: str, limit: int = 1000) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("leads")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def list_matches(user_id: str) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("matches")
        .select("*, orders(*), campaigns(*)")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []


def list_alerts(user_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    sb = get_supabase_admin()
    q = sb.table("alerts").select("*").eq("user_id", user_id)
    if unread_only:
        q = q.eq("is_read", False)
    res = q.order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def build_campaign_id_map(campaigns: list[dict]) -> dict[str, str]:
    """Map platform_campaign_id, name, and uuid → uuid."""
    m: dict[str, str] = {}
    for c in campaigns:
        cid = c["id"]
        m[cid] = cid
        if c.get("platform_campaign_id"):
            m[str(c["platform_campaign_id"])] = cid
        if c.get("name"):
            m[str(c["name"])] = cid
    return m


def process_and_persist_upload(
    user_id: str,
    *,
    filename: str,
    valid_rows: list[dict],
    total_rows: int,
    error_count: int,
    return_fee: float = 25.0,
) -> dict[str, Any]:
    """
    Full ingestion path:
    upload_batch → orders → ensure campaigns from CSV names → match → stats.
    """
    ensure_profile(user_id)

    batch = create_upload_batch(
        user_id,
        filename=filename,
        total_rows=total_rows,
        valid_rows=len(valid_rows),
        error_rows=error_count,
    )

    # Ensure campaigns referenced by CSV
    campaigns = list_campaigns(user_id)
    cmap = build_campaign_id_map(campaigns)

    for row in valid_rows:
        cname = row.get("campaign_name")
        cid_ext = row.get("campaign_id")
        if cid_ext and str(cid_ext) not in cmap:
            camp = upsert_campaign(
                user_id,
                platform_campaign_id=str(cid_ext),
                name=str(cname or cid_ext),
                platform="manual",
            )
            campaigns.append(camp)
            cmap = build_campaign_id_map(campaigns)
        elif cname and str(cname) not in cmap:
            slug = str(cname).strip().lower().replace(" ", "-")[:80]
            camp = upsert_campaign(
                user_id,
                platform_campaign_id=f"manual-{slug}",
                name=str(cname),
                platform="manual",
            )
            campaigns.append(camp)
            cmap = build_campaign_id_map(campaigns)

    saved_orders = insert_orders(
        user_id, valid_rows, upload_batch_id=batch["id"]
    )

    # Run matching against all user leads + phone map from campaign names on orders
    db_leads = list_leads(user_id)
    engine_leads = [
        LeadCandidate(
            id=str(l["id"]),
            campaign_id=str(l["campaign_id"]) if l.get("campaign_id") else "",
            phone=l.get("phone"),
            order_ref=l.get("order_ref"),
        )
        for l in db_leads
        if l.get("campaign_id")
    ]

    phone_to_campaign: dict[str, str] = {}
    for row, saved in zip(valid_rows, saved_orders):
        nphone = saved.get("phone_normalized") or normalize_phone(row.get("phone"))
        if not nphone:
            continue
        key = row.get("campaign_id") or row.get("campaign_name")
        if key and str(key) in cmap:
            phone_to_campaign[nphone] = cmap[str(key)]

    # Also map from existing leads
    for lead in engine_leads:
        n = normalize_phone(lead.phone)
        if n and lead.campaign_id:
            phone_to_campaign.setdefault(n, lead.campaign_id)

    order_records = [
        OrderRecord(
            id=str(o["id"]),
            phone=o.get("phone"),
            order_ref=o.get("order_ref"),
            status=o.get("status") or "pending",
            amount_collected=float(o.get("amount_collected") or 0),
            delivery_date=str(o.get("delivery_date") or "") or None,
            carrier=o.get("carrier"),
        )
        for o in saved_orders
    ]

    report = MatchingEngine().match(
        engine_leads, order_records, phone_to_campaign=phone_to_campaign or None
    )

    match_rows = []
    for m in report.matches:
        # campaign_id from engine may be platform id — resolve to uuid
        camp_uuid = cmap.get(m.campaign_id, m.campaign_id)
        match_rows.append(
            {
                "user_id": user_id,
                "campaign_id": camp_uuid,
                "order_id": m.order_id,
                "lead_id": m.lead_id,
                "match_type": m.match_type.value,
                "confidence_score": m.confidence_score,
            }
        )
    saved_matches = replace_matches(user_id, match_rows)

    # Compute KPIs across all user data
    pipeline = compute_user_dashboard(user_id, return_fee=return_fee)

    return {
        "batch": batch,
        "orders_saved": len(saved_orders),
        "matches_saved": len(saved_matches),
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
        **pipeline,
    }


def compute_user_dashboard(
    user_id: str,
    return_fee: float = 25.0,
    days: int | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    """Load campaigns + matched orders from DB and compute KPIs with optional filters."""
    campaigns = list_campaigns(user_id)
    matches = list_matches(user_id)
    all_orders = {o["id"]: o for o in list_orders(user_id)}

    # Apply platform filter
    if platform and platform.lower() != "all":
        plat_lower = platform.lower()
        campaigns = [c for c in campaigns if c.get("platform") == plat_lower]
        campaign_ids = {c["id"] for c in campaigns}
        matches = [m for m in matches if m.get("campaign_id") in campaign_ids]

    # Apply date range filter (days)
    if days is not None:
        from datetime import timedelta
        today = date.today()
        filtered_orders = {}
        for oid, o in all_orders.items():
            d_str = o.get("delivery_date")
            if not d_str:
                continue
            try:
                o_date = date.fromisoformat(str(d_str))
            except ValueError:
                continue
            
            if days == 1:
                if o_date == today:
                    filtered_orders[oid] = o
            elif days == 2:
                if o_date == today - timedelta(days=1):
                    filtered_orders[oid] = o
            elif days in (7, 30):
                if today - timedelta(days=days) <= o_date <= today:
                    filtered_orders[oid] = o
            else:
                filtered_orders[oid] = o
        all_orders = filtered_orders
        matches = [m for m in matches if m.get("order_id") in all_orders]

    camp_inputs = [
        CampaignInput(
            campaign_id=c["id"],
            name=c.get("name") or "",
            platform=c.get("platform") or "manual",
            spend=float(c.get("spend") or 0),
            impressions=int(c.get("impressions") or 0),
            clicks=int(c.get("clicks") or 0),
            leads=int(c.get("leads") or 0),
        )
        for c in campaigns
    ]

    order_calcs: list[OrderForCalc] = []
    for m in matches:
        oid = m.get("order_id")
        order = m.get("orders") if isinstance(m.get("orders"), dict) else all_orders.get(oid)
        if not order:
            order = all_orders.get(oid)
        if not order:
            continue
        order_calcs.append(
            OrderForCalc(
                order_id=str(order["id"]),
                campaign_id=str(m["campaign_id"]),
                status=str(order.get("status") or "pending"),
                amount_collected=float(order.get("amount_collected") or 0),
            )
        )

    # Load custom threshold settings
    user_settings = get_user_settings(user_id)
    fee = float(user_settings.get("return_fee_mad", return_fee))
    t_roas = float(user_settings.get("target_roas", 2.00))
    crit_rate = float(user_settings.get("critical_return_rate", 0.30))

    engine = CalculationEngine(default_return_fee=fee)
    kpis = engine.compute_dashboard(
        camp_inputs,
        order_calcs,
        target_roas=t_roas,
        critical_return_rate=crit_rate,
    )
    kpis_dict = kpis_to_dict(kpis)

    # Persist stats snapshot
    stats_rows = []
    today = date.today().isoformat()
    for c in kpis.campaigns:
        stats_rows.append(
            {
                "campaign_id": c.campaign_id,
                "period_start": today,
                "period_end": today,
                "total_spend": c.total_spend,
                "delivered_orders": c.delivered_orders,
                "returned_orders": c.returned_orders + c.refused_orders,
                "net_revenue": c.net_revenue,
                "net_profit": c.net_profit,
                "real_cpa": c.real_cpa,
                "real_roas": c.real_roas,
                "return_rate": c.return_rate,
                "performance_score": c.performance_score,
            }
        )
    try:
        save_campaign_stats(user_id, stats_rows)
    except Exception:
        pass  # non-fatal if stats table insert fails

    from app.services.alerts import build_alerts, AlertRule as ServiceAlertRule

    rules = ServiceAlertRule(
        min_roas=t_roas,
        max_return_rate=crit_rate,
        min_net_profit=0.0,
    )
    alerts = build_alerts(kpis.campaigns, rules)
    alert_dicts = [a.to_dict() for a in alerts]

    return {
        "kpis": kpis_dict,
        "alerts": alert_dicts,
        "campaigns_count": len(campaigns),
        "orders_count": len(all_orders),
        "matches_count": len(matches),
    }


def seed_demo_for_user(user_id: str, email: str | None = None) -> dict[str, Any]:
    """Seed demo campaigns, leads, orders for a logged-in user."""
    ensure_profile(user_id, email=email)

    demo_campaigns = [
        {
            "campaign_id": "meta-summer",
            "name": "Summer Meta Lookalike",
            "platform": "meta",
            "spend": 1200,
            "impressions": 45000,
            "clicks": 890,
            "leads": 40,
        },
        {
            "campaign_id": "tiktok-broad",
            "name": "TikTok Broad COD",
            "platform": "tiktok",
            "spend": 800,
            "impressions": 60000,
            "clicks": 1200,
            "leads": 35,
        },
        {
            "campaign_id": "meta-retarget",
            "name": "Retargeting Meta",
            "platform": "meta",
            "spend": 400,
            "impressions": 12000,
            "clicks": 400,
            "leads": 20,
        },
    ]
    camps = upsert_campaigns_bulk(user_id, demo_campaigns)
    cmap = build_campaign_id_map(camps)

    demo_leads = [
        {"campaign_id": "meta-summer", "phone": "0612345678", "order_ref": "CMD-2026-0001"},
        {"campaign_id": "meta-summer", "phone": "+212698765432", "order_ref": "CMD-2026-0002"},
        {"campaign_id": "meta-summer", "phone": "0611223344", "order_ref": "CMD-2026-0003"},
        {"campaign_id": "tiktok-broad", "phone": "0700112233", "order_ref": "CMD-2026-0004"},
        {"campaign_id": "tiktok-broad", "phone": "0655554444", "order_ref": "CMD-2026-0005"},
        {"campaign_id": "tiktok-broad", "phone": "0655554444", "order_ref": "CMD-2026-0006"},
        {"campaign_id": "meta-retarget", "phone": "0611223344", "order_ref": "CMD-2026-0007"},
        {"campaign_id": "meta-retarget", "phone": "0699887766", "order_ref": "CMD-2026-0008"},
    ]
    insert_leads(user_id, demo_leads, cmap)

    demo_orders = [
        {
            "order_ref": "CMD-2026-0001",
            "phone": "0612345678",
            "phone_normalized": "612345678",
            "status": "delivered",
            "amount_collected": 449,
            "delivery_date": "2026-07-10",
            "carrier": "Amana",
            "campaign_name": "Summer Meta Lookalike",
        },
        {
            "order_ref": "CMD-2026-0002",
            "phone": "+212698765432",
            "phone_normalized": "698765432",
            "status": "delivered",
            "amount_collected": 349,
            "delivery_date": "2026-07-11",
            "carrier": "Amana",
            "campaign_name": "Summer Meta Lookalike",
        },
        {
            "order_ref": "CMD-2026-0003",
            "phone": "06 11 22 33 44",
            "phone_normalized": "611223344",
            "status": "returned",
            "amount_collected": 0,
            "delivery_date": "2026-07-12",
            "carrier": "Chronopost",
            "campaign_name": "Summer Meta Lookalike",
        },
        {
            "order_ref": "CMD-2026-0004",
            "phone": "0700112233",
            "phone_normalized": "700112233",
            "status": "refused",
            "amount_collected": 0,
            "delivery_date": "2026-07-12",
            "carrier": "Amana",
            "campaign_name": "TikTok Broad COD",
        },
        {
            "order_ref": "CMD-2026-0005",
            "phone": "00212655554444",
            "phone_normalized": "655554444",
            "status": "delivered",
            "amount_collected": 499,
            "delivery_date": "2026-07-13",
            "carrier": "Amana",
            "campaign_name": "TikTok Broad COD",
        },
        {
            "order_ref": "CMD-2026-0006",
            "phone": "0655554444",
            "phone_normalized": "655554444",
            "status": "pending",
            "amount_collected": 0,
            "delivery_date": "2026-07-14",
            "carrier": "Amana",
            "campaign_name": "TikTok Broad COD",
        },
        {
            "order_ref": "CMD-2026-0007",
            "phone": "0611223344",
            "phone_normalized": "611223344",
            "status": "delivered",
            "amount_collected": 299,
            "delivery_date": "2026-07-14",
            "carrier": "Chronopost",
            "campaign_name": "Retargeting Meta",
        },
        {
            "order_ref": "CMD-2026-0008",
            "phone": "0699887766",
            "phone_normalized": "699887766",
            "status": "delivered",
            "amount_collected": 399,
            "delivery_date": "2026-07-15",
            "carrier": "Amana",
            "campaign_name": "Retargeting Meta",
        },
    ]

    return process_and_persist_upload(
        user_id,
        filename="demo_seed.csv",
        valid_rows=demo_orders,
        total_rows=len(demo_orders),
        error_count=0,
        return_fee=25.0,
    )


def get_user_settings(user_id: str) -> dict:
    """Load settings for a user. Bypasses if Supabase is not configured (pytest fallback)."""
    from app.core.supabase_client import is_supabase_configured
    if not is_supabase_configured():
        return {
            "user_id": user_id,
            "return_fee_mad": 25.00,
            "critical_return_rate": 0.30,
            "target_roas": 2.00,
        }
    sb = get_supabase_admin()
    try:
        res = sb.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {
        "user_id": user_id,
        "return_fee_mad": 25.00,
        "critical_return_rate": 0.30,
        "target_roas": 2.00,
    }


def save_user_settings(
    user_id: str,
    return_fee_mad: float,
    critical_return_rate: float,
    target_roas: float,
) -> dict:
    """Save/update user configuration settings."""
    from app.core.supabase_client import is_supabase_configured
    payload = {
        "user_id": user_id,
        "return_fee_mad": return_fee_mad,
        "critical_return_rate": critical_return_rate,
        "target_roas": target_roas,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not is_supabase_configured():
        return payload

    sb = get_supabase_admin()
    found = sb.table("user_settings").select("user_id").eq("user_id", user_id).limit(1).execute()
    if found.data:
        res = sb.table("user_settings").update(payload).eq("user_id", user_id).execute()
    else:
        res = sb.table("user_settings").insert(payload).execute()
    return res.data[0] if res.data else payload

