"""Matching Engine — core of CODReal.

Matches ad leads/campaigns to delivery orders primarily by phone,
secondarily by order_ref. Tracks confidence and match type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.phone import normalize_phone


class MatchType(str, Enum):
    PHONE = "phone"
    ORDER_REF = "order_ref"
    FUZZY = "fuzzy"


@dataclass
class LeadCandidate:
    """A lead or conversion attributed to a campaign (from ads or CSV)."""

    id: str
    campaign_id: str
    phone: str | None = None
    order_ref: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRecord:
    """A delivery order from CSV upload."""

    id: str
    phone: str | None = None
    order_ref: str | None = None
    status: str = "pending"
    amount_collected: float = 0.0
    delivery_date: str | None = None
    carrier: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    campaign_id: str
    order_id: str
    lead_id: str | None
    match_type: MatchType
    confidence_score: float
    normalized_phone: str | None = None
    order_ref: str | None = None


@dataclass
class MatchingReport:
    matches: list[MatchResult] = field(default_factory=list)
    unmatched_orders: list[str] = field(default_factory=list)
    unmatched_leads: list[str] = field(default_factory=list)
    duplicate_phones: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class MatchingEngine:
    """Intelligent matching: phone (primary) + order_ref (secondary)."""

    def __init__(
        self,
        phone_confidence: float = 0.95,
        order_ref_confidence: float = 0.99,
        keep_most_recent: bool = True,
    ):
        self.phone_confidence = phone_confidence
        self.order_ref_confidence = order_ref_confidence
        self.keep_most_recent = keep_most_recent

    def match(
        self,
        leads: list[LeadCandidate],
        orders: list[OrderRecord],
        *,
        # When no leads yet (MVP: match orders to campaigns via phone on campaign leads later),
        # allow direct campaign_id on orders via a phone→campaign map.
        phone_to_campaign: dict[str, str] | None = None,
    ) -> MatchingReport:
        report = MatchingReport()
        used_order_ids: set[str] = set()
        used_lead_ids: set[str] = set()

        # Index leads by normalized phone and order_ref
        leads_by_phone: dict[str, list[LeadCandidate]] = {}
        leads_by_ref: dict[str, list[LeadCandidate]] = {}

        for lead in leads:
            nphone = normalize_phone(lead.phone)
            if nphone:
                leads_by_phone.setdefault(nphone, []).append(lead)
            if lead.order_ref:
                ref = lead.order_ref.strip().upper()
                leads_by_ref.setdefault(ref, []).append(lead)

        phone_campaign_map = phone_to_campaign or {}

        # Track duplicate phones among orders
        phone_counts: dict[str, int] = {}
        for order in orders:
            nphone = normalize_phone(order.phone)
            if nphone:
                phone_counts[nphone] = phone_counts.get(nphone, 0) + 1
        report.duplicate_phones = [p for p, c in phone_counts.items() if c > 1]

        # Pass 1: order_ref matching (highest confidence)
        for order in orders:
            if order.id in used_order_ids:
                continue
            if not order.order_ref:
                continue
            ref = order.order_ref.strip().upper()
            candidates = [
                l for l in leads_by_ref.get(ref, []) if l.id not in used_lead_ids
            ]
            if not candidates:
                continue
            lead = candidates[0]
            report.matches.append(
                MatchResult(
                    campaign_id=lead.campaign_id,
                    order_id=order.id,
                    lead_id=lead.id,
                    match_type=MatchType.ORDER_REF,
                    confidence_score=self.order_ref_confidence,
                    normalized_phone=normalize_phone(order.phone),
                    order_ref=ref,
                )
            )
            used_order_ids.add(order.id)
            used_lead_ids.add(lead.id)

        # Pass 2: phone matching
        for order in orders:
            if order.id in used_order_ids:
                continue
            nphone = normalize_phone(order.phone)
            if not nphone:
                report.unmatched_orders.append(order.id)
                continue

            candidates = [
                l for l in leads_by_phone.get(nphone, []) if l.id not in used_lead_ids
            ]

            if candidates:
                # Prefer most recent lead if extra has timestamp; else first
                lead = self._pick_best_lead(candidates)
                report.matches.append(
                    MatchResult(
                        campaign_id=lead.campaign_id,
                        order_id=order.id,
                        lead_id=lead.id,
                        match_type=MatchType.PHONE,
                        confidence_score=self.phone_confidence,
                        normalized_phone=nphone,
                        order_ref=order.order_ref,
                    )
                )
                used_order_ids.add(order.id)
                used_lead_ids.add(lead.id)
                continue

            # Fallback: direct phone → campaign map (manual attribution / ads sync)
            campaign_id = phone_campaign_map.get(nphone)
            if campaign_id:
                report.matches.append(
                    MatchResult(
                        campaign_id=campaign_id,
                        order_id=order.id,
                        lead_id=None,
                        match_type=MatchType.PHONE,
                        confidence_score=self.phone_confidence * 0.9,
                        normalized_phone=nphone,
                        order_ref=order.order_ref,
                    )
                )
                used_order_ids.add(order.id)
                continue

            report.unmatched_orders.append(order.id)

        report.unmatched_leads = [l.id for l in leads if l.id not in used_lead_ids]
        report.stats = {
            "total_orders": len(orders),
            "total_leads": len(leads),
            "matched": len(report.matches),
            "unmatched_orders": len(report.unmatched_orders),
            "unmatched_leads": len(report.unmatched_leads),
            "match_rate": (
                round(len(report.matches) / len(orders), 4) if orders else 0.0
            ),
            "by_type": {
                "phone": sum(
                    1 for m in report.matches if m.match_type == MatchType.PHONE
                ),
                "order_ref": sum(
                    1 for m in report.matches if m.match_type == MatchType.ORDER_REF
                ),
                "fuzzy": sum(
                    1 for m in report.matches if m.match_type == MatchType.FUZZY
                ),
            },
        }
        return report

    def _pick_best_lead(self, candidates: list[LeadCandidate]) -> LeadCandidate:
        if len(candidates) == 1:
            return candidates[0]
        if self.keep_most_recent:

            def sort_key(lead: LeadCandidate) -> str:
                return str(lead.extra.get("created_at") or lead.extra.get("date") or "")

            return sorted(candidates, key=sort_key, reverse=True)[0]
        return candidates[0]


def match_orders_to_campaigns(
    orders: list[dict[str, Any]],
    phone_to_campaign: dict[str, str],
    leads: list[dict[str, Any]] | None = None,
) -> MatchingReport:
    """Convenience wrapper from plain dicts (API / CSV path)."""
    engine = MatchingEngine()
    order_records = [
        OrderRecord(
            id=str(o.get("id") or o.get("order_ref") or idx),
            phone=o.get("phone"),
            order_ref=o.get("order_ref"),
            status=str(o.get("status") or "pending"),
            amount_collected=float(o.get("amount_collected") or 0),
            delivery_date=o.get("delivery_date"),
            carrier=o.get("carrier"),
        )
        for idx, o in enumerate(orders)
    ]
    lead_records = [
        LeadCandidate(
            id=str(l.get("id") or idx),
            campaign_id=str(l["campaign_id"]),
            phone=l.get("phone"),
            order_ref=l.get("order_ref"),
            extra={k: v for k, v in l.items() if k not in ("id", "campaign_id", "phone", "order_ref")},
        )
        for idx, l in enumerate(leads or [])
        if l.get("campaign_id")
    ]
    return engine.match(lead_records, order_records, phone_to_campaign=phone_to_campaign)
