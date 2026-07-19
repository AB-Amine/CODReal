"""Meta (Facebook) Marketing API client — read-only.

Docs:
- OAuth: https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow
- Marketing API: https://developers.facebook.com/docs/marketing-apis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings, get_settings


class MetaAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass
class MetaAdAccount:
    id: str  # act_123 or 123
    account_id: str  # numeric without act_
    name: str
    currency: str | None = None
    account_status: int | None = None


@dataclass
class MetaCampaignInsight:
    platform_campaign_id: str
    name: str
    status: str = "ACTIVE"
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class MetaMarketingClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.version = self.settings.meta_graph_version
        self.base = f"https://graph.facebook.com/{self.version}"

    def is_configured(self) -> bool:
        return self.settings.meta_configured

    def build_oauth_url(self, state: str) -> str:
        if not self.is_configured():
            raise MetaAPIError("Meta App non configurée (META_APP_ID / META_APP_SECRET)")
        params = {
            "client_id": self.settings.meta_app_id,
            "redirect_uri": self.settings.meta_redirect_uri,
            "state": state,
            "scope": self.settings.meta_oauth_scopes,
            "response_type": "code",
        }
        return f"https://www.facebook.com/{self.version}/dialog/oauth?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange OAuth code for short-lived user access token."""
        return self._get(
            f"{self.base}/oauth/access_token",
            params={
                "client_id": self.settings.meta_app_id,
                "client_secret": self.settings.meta_app_secret,
                "redirect_uri": self.settings.meta_redirect_uri,
                "code": code,
            },
            auth=False,
        )

    def exchange_long_lived(self, short_token: str) -> dict[str, Any]:
        """Exchange short-lived token for long-lived (~60 days)."""
        return self._get(
            f"{self.base}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.settings.meta_app_id,
                "client_secret": self.settings.meta_app_secret,
                "fb_exchange_token": short_token,
            },
            auth=False,
        )

    def get_me(self, access_token: str) -> dict[str, Any]:
        return self._get(
            f"{self.base}/me",
            params={"fields": "id,name", "access_token": access_token},
            auth=False,
        )

    def list_ad_accounts(self, access_token: str) -> list[MetaAdAccount]:
        data = self._get(
            f"{self.base}/me/adaccounts",
            params={
                "fields": "id,account_id,name,currency,account_status",
                "limit": 100,
                "access_token": access_token,
            },
            auth=False,
        )
        accounts: list[MetaAdAccount] = []
        for row in data.get("data") or []:
            raw_id = str(row.get("id") or "")
            account_id = str(row.get("account_id") or raw_id.replace("act_", ""))
            accounts.append(
                MetaAdAccount(
                    id=raw_id if raw_id.startswith("act_") else f"act_{account_id}",
                    account_id=account_id,
                    name=str(row.get("name") or f"Ad Account {account_id}"),
                    currency=row.get("currency"),
                    account_status=row.get("account_status"),
                )
            )
        return accounts

    def list_campaigns_with_insights(
        self,
        access_token: str,
        ad_account_id: str,
        date_preset: str | None = None,
    ) -> list[MetaCampaignInsight]:
        """Fetch campaigns + spend insights for an ad account (read-only)."""
        act = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        preset = date_preset or self.settings.meta_insights_date_preset

        # Campaign metadata
        camps = self._paginate(
            f"{self.base}/{act}/campaigns",
            params={
                "fields": "id,name,status,effective_status,objective",
                "limit": 100,
                "access_token": access_token,
            },
        )
        by_id: dict[str, MetaCampaignInsight] = {}
        for c in camps:
            cid = str(c["id"])
            by_id[cid] = MetaCampaignInsight(
                platform_campaign_id=cid,
                name=str(c.get("name") or cid),
                status=str(c.get("effective_status") or c.get("status") or "UNKNOWN"),
            )

        # Insights at campaign level
        insights = self._paginate(
            f"{self.base}/{act}/insights",
            params={
                "level": "campaign",
                "fields": "campaign_id,campaign_name,spend,impressions,clicks,actions",
                "date_preset": preset,
                "limit": 100,
                "access_token": access_token,
            },
        )
        for row in insights:
            cid = str(row.get("campaign_id") or "")
            if not cid:
                continue
            if cid not in by_id:
                by_id[cid] = MetaCampaignInsight(
                    platform_campaign_id=cid,
                    name=str(row.get("campaign_name") or cid),
                )
            item = by_id[cid]
            item.spend = float(row.get("spend") or 0)
            item.impressions = int(float(row.get("impressions") or 0))
            item.clicks = int(float(row.get("clicks") or 0))
            item.leads = _extract_leads(row.get("actions"))
            if row.get("campaign_name"):
                item.name = str(row["campaign_name"])

        return list(by_id.values())

    def _paginate(self, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = params
        with httpx.Client(timeout=45.0) as client:
            while next_url:
                if next_params is not None:
                    resp = client.get(next_url, params=next_params)
                else:
                    resp = client.get(next_url)
                data = self._parse_response(resp)
                rows.extend(data.get("data") or [])
                next_url = (data.get("paging") or {}).get("next")
                next_params = None  # next URL already contains query
                if len(rows) > 2000:
                    break
        return rows

    def _get(self, url: str, params: dict[str, Any], auth: bool = True) -> dict[str, Any]:
        with httpx.Client(timeout=45.0) as client:
            resp = client.get(url, params=params)
        return self._parse_response(resp)

    def _parse_response(self, resp: httpx.Response) -> dict[str, Any]:
        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text}
        if resp.status_code >= 400:
            err = payload.get("error") if isinstance(payload, dict) else None
            msg = (
                err.get("message")
                if isinstance(err, dict)
                else f"Meta API HTTP {resp.status_code}"
            )
            raise MetaAPIError(str(msg), status_code=resp.status_code, payload=payload)
        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise MetaAPIError(str(msg), payload=payload)
        return payload if isinstance(payload, dict) else {"data": payload}


def _extract_leads(actions: Any) -> int:
    if not isinstance(actions, list):
        return 0
    total = 0
    lead_types = {
        "lead",
        "onsite_conversion.lead_grouped",
        "onsite_conversion.messaging_conversation_started_7d",
        "complete_registration",
    }
    for a in actions:
        if not isinstance(a, dict):
            continue
        atype = str(a.get("action_type") or "")
        if atype in lead_types or "lead" in atype:
            try:
                total += int(float(a.get("value") or 0))
            except (TypeError, ValueError):
                continue
    return total


def mock_meta_campaigns() -> list[MetaCampaignInsight]:
    """Realistic Moroccan COD demo campaigns (no live API)."""
    return [
        MetaCampaignInsight(
            platform_campaign_id="meta_mock_summer",
            name="Summer Meta Lookalike",
            status="ACTIVE",
            spend=1200.0,
            impressions=45000,
            clicks=890,
            leads=40,
        ),
        MetaCampaignInsight(
            platform_campaign_id="meta_mock_retarget",
            name="Retargeting Meta",
            status="ACTIVE",
            spend=400.0,
            impressions=12000,
            clicks=400,
            leads=20,
        ),
        MetaCampaignInsight(
            platform_campaign_id="meta_mock_broad",
            name="Meta Broad COD Casablanca",
            status="PAUSED",
            spend=650.0,
            impressions=28000,
            clicks=520,
            leads=18,
        ),
    ]
