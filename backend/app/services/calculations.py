"""Calculation Engine — Real CPA, Real ROAS, Net Profit for COD campaigns.

Formulas (CDC §3.2):
- Bénéfice net = (Montant collecté livré) – Dépense pub – Frais de retour estimés
- CPA réel = Dépense / Nombre de commandes livrées
- ROAS réel = Revenu livré / Dépense
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderForCalc:
    order_id: str
    campaign_id: str
    status: str  # delivered | returned | refused | pending
    amount_collected: float = 0.0


@dataclass
class CampaignInput:
    campaign_id: str
    name: str = ""
    platform: str = ""
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0


@dataclass
class CampaignMetrics:
    campaign_id: str
    name: str
    platform: str
    total_spend: float
    delivered_orders: int
    returned_orders: int
    refused_orders: int
    pending_orders: int
    total_matched_orders: int
    net_revenue: float  # sum of amount_collected on delivered
    return_fees: float
    net_profit: float
    real_cpa: float | None  # None if no delivered
    real_roas: float | None  # None if spend == 0
    return_rate: float | None  # returned / (delivered + returned + refused)
    performance_score: str  # excellent | good | warning | critical
    performance_label: str


@dataclass
class DashboardKPIs:
    total_ad_spend: float
    delivered_revenue: float
    net_profit: float
    real_roas: float | None
    global_return_rate: float | None
    total_delivered: int
    total_returned: int
    total_campaigns: int
    campaigns: list[CampaignMetrics] = field(default_factory=list)


# Performance thresholds (user-configurable later)
ROAS_EXCELLENT = 2.5
ROAS_GOOD = 1.5
ROAS_WARNING = 1.0


class CalculationEngine:
    def __init__(self, default_return_fee: float = 25.0):
        """
        default_return_fee: estimated logistics cost per returned/refused order (MAD).
        """
        self.default_return_fee = default_return_fee

    def compute_campaign(
        self,
        campaign: CampaignInput,
        orders: list[OrderForCalc],
        return_fee: float | None = None,
    ) -> CampaignMetrics:
        fee = return_fee if return_fee is not None else self.default_return_fee

        delivered = [o for o in orders if o.status == "delivered"]
        returned = [o for o in orders if o.status == "returned"]
        refused = [o for o in orders if o.status == "refused"]
        pending = [o for o in orders if o.status == "pending"]

        net_revenue = sum(o.amount_collected for o in delivered)
        return_fees = fee * (len(returned) + len(refused))
        spend = float(campaign.spend or 0)
        net_profit = net_revenue - spend - return_fees

        real_cpa = (spend / len(delivered)) if delivered else None
        real_roas = (net_revenue / spend) if spend > 0 else None

        closed = len(delivered) + len(returned) + len(refused)
        return_rate = (
            (len(returned) + len(refused)) / closed if closed > 0 else None
        )

        score, label = self._score(real_roas, net_profit, return_rate)

        return CampaignMetrics(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            platform=campaign.platform,
            total_spend=round(spend, 2),
            delivered_orders=len(delivered),
            returned_orders=len(returned),
            refused_orders=len(refused),
            pending_orders=len(pending),
            total_matched_orders=len(orders),
            net_revenue=round(net_revenue, 2),
            return_fees=round(return_fees, 2),
            net_profit=round(net_profit, 2),
            real_cpa=round(real_cpa, 2) if real_cpa is not None else None,
            real_roas=round(real_roas, 2) if real_roas is not None else None,
            return_rate=round(return_rate, 4) if return_rate is not None else None,
            performance_score=score,
            performance_label=label,
        )

    def compute_dashboard(
        self,
        campaigns: list[CampaignInput],
        matched_orders: list[OrderForCalc],
        return_fee: float | None = None,
    ) -> DashboardKPIs:
        by_campaign: dict[str, list[OrderForCalc]] = {}
        for o in matched_orders:
            by_campaign.setdefault(o.campaign_id, []).append(o)

        metrics: list[CampaignMetrics] = []
        for c in campaigns:
            m = self.compute_campaign(
                c, by_campaign.get(c.campaign_id, []), return_fee=return_fee
            )
            metrics.append(m)

        # Sort by net profit ascending so losers surface first (actionable)
        metrics.sort(key=lambda m: m.net_profit)

        total_spend = sum(m.total_spend for m in metrics)
        delivered_revenue = sum(m.net_revenue for m in metrics)
        net_profit = sum(m.net_profit for m in metrics)
        total_delivered = sum(m.delivered_orders for m in metrics)
        total_returned = sum(m.returned_orders + m.refused_orders for m in metrics)
        closed = total_delivered + total_returned

        real_roas = (delivered_revenue / total_spend) if total_spend > 0 else None
        global_return_rate = (total_returned / closed) if closed > 0 else None

        return DashboardKPIs(
            total_ad_spend=round(total_spend, 2),
            delivered_revenue=round(delivered_revenue, 2),
            net_profit=round(net_profit, 2),
            real_roas=round(real_roas, 2) if real_roas is not None else None,
            global_return_rate=(
                round(global_return_rate, 4) if global_return_rate is not None else None
            ),
            total_delivered=total_delivered,
            total_returned=total_returned,
            total_campaigns=len(metrics),
            campaigns=metrics,
        )

    def _score(
        self,
        real_roas: float | None,
        net_profit: float,
        return_rate: float | None,
    ) -> tuple[str, str]:
        """Basic rule-based performance score (Phase 1 alerts foundation)."""
        if real_roas is None:
            if net_profit < 0:
                return "critical", "Perte — données ROAS insuffisantes"
            return "warning", "Données insuffisantes"

        if real_roas >= ROAS_EXCELLENT and net_profit > 0:
            return "excellent", "Très rentable"
        if real_roas >= ROAS_GOOD and net_profit > 0:
            return "good", "Rentable"
        if real_roas >= ROAS_WARNING:
            high_returns = return_rate is not None and return_rate > 0.25
            if high_returns:
                return "warning", "ROAS limite — retours élevés"
            return "warning", "ROAS limite — à surveiller"
        return "critical", "Campagne perdante"


def metrics_to_dict(m: CampaignMetrics) -> dict[str, Any]:
    return {
        "campaign_id": m.campaign_id,
        "name": m.name,
        "platform": m.platform,
        "total_spend": m.total_spend,
        "delivered_orders": m.delivered_orders,
        "returned_orders": m.returned_orders,
        "refused_orders": m.refused_orders,
        "pending_orders": m.pending_orders,
        "total_matched_orders": m.total_matched_orders,
        "net_revenue": m.net_revenue,
        "return_fees": m.return_fees,
        "net_profit": m.net_profit,
        "real_cpa": m.real_cpa,
        "real_roas": m.real_roas,
        "return_rate": m.return_rate,
        "performance_score": m.performance_score,
        "performance_label": m.performance_label,
    }


def kpis_to_dict(k: DashboardKPIs) -> dict[str, Any]:
    return {
        "total_ad_spend": k.total_ad_spend,
        "delivered_revenue": k.delivered_revenue,
        "net_profit": k.net_profit,
        "real_roas": k.real_roas,
        "global_return_rate": k.global_return_rate,
        "total_delivered": k.total_delivered,
        "total_returned": k.total_returned,
        "total_campaigns": k.total_campaigns,
        "campaigns": [metrics_to_dict(c) for c in k.campaigns],
    }
