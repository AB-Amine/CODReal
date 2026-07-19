"""TikTok Marketing API client — read-only.

Docs: https://business-api.tiktok.com/portal/docs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings, get_settings


class TikTokAPIError(RuntimeError):
    def __init__(self, message: str, payload: Any = None):
        super().__init__(message)
        self.payload = payload


@dataclass
class TikTokAdvertiser:
    advertiser_id: str
    advertiser_name: str


@dataclass
class TikTokCampaignInsight:
    platform_campaign_id: str
    name: str
    status: str = "ENABLE"
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class TikTokMarketingClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base = self.settings.tiktok_api_base.rstrip("/")

    def is_configured(self) -> bool:
        return self.settings.tiktok_configured

    def build_oauth_url(self, state: str) -> str:
        if not self.is_configured():
            raise TikTokAPIError("TikTok App non configurée (TIKTOK_APP_ID / TIKTOK_APP_SECRET)")
        params = {
            "app_id": self.settings.tiktok_app_id,
            "state": state,
            "redirect_uri": self.settings.tiktok_redirect_uri,
        }
        return f"https://business-api.tiktok.com/portal/auth?{urlencode(params)}"

    def exchange_code(self, auth_code: str) -> dict[str, Any]:
        """Exchange auth_code for access_token + advertiser_ids."""
        return self._post(
            f"{self.base}/oauth2/access_token/",
            json_body={
                "app_id": self.settings.tiktok_app_id,
                "secret": self.settings.tiktok_app_secret,
                "auth_code": auth_code,
            },
        )

    def list_advertisers(self, access_token: str) -> list[TikTokAdvertiser]:
        data = self._get(
            f"{self.base}/oauth2/advertiser/get/",
            params={
                "app_id": self.settings.tiktok_app_id,
                "secret": self.settings.tiktok_app_secret,
            },
            access_token=access_token,
        )
        list_data = data.get("list") or data.get("advertiser_ids") or []
        out: list[TikTokAdvertiser] = []
        if list_data and isinstance(list_data[0], dict):
            for row in list_data:
                aid = str(row.get("advertiser_id") or row.get("id") or "")
                if not aid:
                    continue
                out.append(
                    TikTokAdvertiser(
                        advertiser_id=aid,
                        advertiser_name=str(
                            row.get("advertiser_name") or row.get("name") or f"Advertiser {aid}"
                        ),
                    )
                )
        elif list_data:
            for aid in list_data:
                out.append(
                    TikTokAdvertiser(
                        advertiser_id=str(aid),
                        advertiser_name=f"Advertiser {aid}",
                    )
                )
        return out

    def list_campaigns_with_insights(
        self,
        access_token: str,
        advertiser_id: str,
    ) -> list[TikTokCampaignInsight]:
        """Fetch campaigns + basic metrics for last 30 days."""
        camps_data = self._get(
            f"{self.base}/campaign/get/",
            params={
                "advertiser_id": advertiser_id,
                "page_size": 100,
                "fields": '["campaign_id","campaign_name","operation_status","secondary_status"]',
            },
            access_token=access_token,
        )
        list_rows = camps_data.get("list") or []
        by_id: dict[str, TikTokCampaignInsight] = {}
        for c in list_rows:
            cid = str(c.get("campaign_id") or "")
            if not cid:
                continue
            by_id[cid] = TikTokCampaignInsight(
                platform_campaign_id=cid,
                name=str(c.get("campaign_name") or cid),
                status=str(c.get("operation_status") or c.get("secondary_status") or "UNKNOWN"),
            )

        # Integrated report at campaign level
        try:
            report = self._get(
                f"{self.base}/report/integrated/get/",
                params={
                    "advertiser_id": advertiser_id,
                    "report_type": "BASIC",
                    "data_level": "AUCTION_CAMPAIGN",
                    "dimensions": '["campaign_id"]',
                    "metrics": '["spend","impressions","clicks","conversion"]',
                    "page_size": 100,
                    "start_date": _days_ago(30),
                    "end_date": _days_ago(0),
                },
                access_token=access_token,
            )
            for row in report.get("list") or []:
                dims = row.get("dimensions") or {}
                metrics = row.get("metrics") or {}
                cid = str(dims.get("campaign_id") or row.get("campaign_id") or "")
                if not cid:
                    continue
                if cid not in by_id:
                    by_id[cid] = TikTokCampaignInsight(
                        platform_campaign_id=cid,
                        name=str(dims.get("campaign_name") or cid),
                    )
                item = by_id[cid]
                item.spend = float(metrics.get("spend") or 0)
                item.impressions = int(float(metrics.get("impressions") or 0))
                item.clicks = int(float(metrics.get("clicks") or 0))
                item.leads = int(float(metrics.get("conversion") or 0))
        except TikTokAPIError:
            # Campaign list alone is still useful
            pass

        return list(by_id.values())

    def _get(
        self,
        url: str,
        *,
        params: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if access_token:
            headers["Access-Token"] = access_token
        with httpx.Client(timeout=45.0) as client:
            resp = client.get(url, params=params, headers=headers)
        return self._parse(resp)

    def _post(self, url: str, json_body: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=json_body)
        return self._parse(resp)

    def _parse(self, resp: httpx.Response) -> dict[str, Any]:
        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text}
        if resp.status_code >= 400:
            raise TikTokAPIError(
                f"TikTok HTTP {resp.status_code}: {payload}",
                payload=payload,
            )
        # TikTok wraps business errors in code != 0
        if isinstance(payload, dict) and "code" in payload and payload.get("code") not in (0, "0", None):
            msg = payload.get("message") or payload.get("msg") or str(payload)
            raise TikTokAPIError(str(msg), payload=payload)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else (payload if isinstance(payload, dict) else {})


def _days_ago(n: int) -> str:
    from datetime import date, timedelta

    return (date.today() - timedelta(days=n)).isoformat()


def mock_tiktok_campaigns() -> list[TikTokCampaignInsight]:
    return [
        TikTokCampaignInsight(
            platform_campaign_id="tt_mock_broad",
            name="TikTok Broad COD",
            status="ENABLE",
            spend=800.0,
            impressions=60000,
            clicks=1200,
            leads=35,
        ),
        TikTokCampaignInsight(
            platform_campaign_id="tt_mock_spark",
            name="TikTok Spark Ads COD",
            status="ENABLE",
            spend=350.0,
            impressions=22000,
            clicks=480,
            leads=14,
        ),
        TikTokCampaignInsight(
            platform_campaign_id="tt_mock_interest",
            name="TikTok Interest Beauty MA",
            status="DISABLE",
            spend=220.0,
            impressions=15000,
            clicks=310,
            leads=9,
        ),
    ]
