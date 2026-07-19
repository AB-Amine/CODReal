"""Basic rule-based alerts (Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.calculations import CampaignMetrics


@dataclass
class AlertRule:
    min_roas: float = 1.0
    max_return_rate: float = 0.30
    min_net_profit: float = 0.0


@dataclass
class AlertItem:
    campaign_id: str
    name: str
    severity: str  # info | warning | critical
    code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


def build_alerts(
    campaigns: list[CampaignMetrics],
    rules: AlertRule | None = None,
) -> list[AlertItem]:
    rules = rules or AlertRule()
    alerts: list[AlertItem] = []
    for c in campaigns:
        if c.real_roas is not None and c.real_roas < rules.min_roas:
            alerts.append(
                AlertItem(
                    campaign_id=c.campaign_id,
                    name=c.name,
                    severity="critical" if c.real_roas < 1 else "warning",
                    code="LOW_ROAS",
                    message=f"ROAS réel {c.real_roas}x sous le seuil {rules.min_roas}x",
                )
            )
        if c.net_profit < rules.min_net_profit:
            alerts.append(
                AlertItem(
                    campaign_id=c.campaign_id,
                    name=c.name,
                    severity="critical",
                    code="NEGATIVE_PROFIT",
                    message=f"Bénéfice net négatif: {c.net_profit} MAD",
                )
            )
        if c.return_rate is not None and c.return_rate > rules.max_return_rate:
            alerts.append(
                AlertItem(
                    campaign_id=c.campaign_id,
                    name=c.name,
                    severity="warning",
                    code="HIGH_RETURN_RATE",
                    message=(
                        f"Taux de retour {c.return_rate:.0%} "
                        f"> seuil {rules.max_return_rate:.0%}"
                    ),
                )
            )
    return alerts
