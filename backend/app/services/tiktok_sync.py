"""Persist TikTok OAuth tokens and sync campaigns into CODReal DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.supabase_client import get_supabase_admin
from app.services import persistence as db
from app.services.tiktok_api import (
    TikTokAPIError,
    TikTokAdvertiser,
    TikTokMarketingClient,
    mock_tiktok_campaigns,
)


def create_oauth_state(user_id: str) -> str:
    settings = get_settings()
    secret = settings.supabase_jwt_secret or settings.token_encryption_key or "codreal-dev"
    return jwt.encode(
        {
            "sub": user_id,
            "purpose": "tiktok_oauth",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        secret,
        algorithm="HS256",
    )


def parse_oauth_state(state: str) -> str:
    settings = get_settings()
    secret = settings.supabase_jwt_secret or settings.token_encryption_key or "codreal-dev"
    try:
        payload = jwt.decode(state, secret, algorithms=["HS256"])
    except JWTError as exc:
        raise TikTokAPIError("State OAuth invalide ou expiré") from exc
    if payload.get("purpose") != "tiktok_oauth" or not payload.get("sub"):
        raise TikTokAPIError("State OAuth incorrect")
    return str(payload["sub"])


def list_tiktok_accounts(user_id: str) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("ad_accounts")
        .select("id,platform,account_id,account_name,last_sync,token_expires_at,created_at")
        .eq("user_id", user_id)
        .eq("platform", "tiktok")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def upsert_ad_account(
    user_id: str,
    *,
    account_id: str,
    account_name: str,
    access_token: str,
    expires_in: int | None = None,
) -> dict:
    sb = get_supabase_admin()
    expires_at = None
    if expires_in:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        ).isoformat()

    encrypted = encrypt_token(access_token)
    found = (
        sb.table("ad_accounts")
        .select("*")
        .eq("user_id", user_id)
        .eq("platform", "tiktok")
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )
    payload = {
        "user_id": user_id,
        "platform": "tiktok",
        "account_id": account_id,
        "account_name": account_name,
        "access_token": encrypted,
        "token_expires_at": expires_at,
    }
    if found.data:
        updated = (
            sb.table("ad_accounts")
            .update(payload)
            .eq("id", found.data[0]["id"])
            .execute()
        )
        return updated.data[0] if updated.data else {**found.data[0], **payload}
    inserted = sb.table("ad_accounts").insert(payload).execute()
    return inserted.data[0]


def get_decrypted_token(user_id: str, account_row_id: str | None = None) -> tuple[dict, str]:
    sb = get_supabase_admin()
    q = (
        sb.table("ad_accounts")
        .select("*")
        .eq("user_id", user_id)
        .eq("platform", "tiktok")
    )
    if account_row_id:
        q = q.eq("id", account_row_id)
    res = q.order("created_at", desc=True).limit(1).execute()
    if not res.data:
        raise TikTokAPIError("Aucun compte TikTok connecté")
    row = res.data[0]
    token = decrypt_token(row.get("access_token") or "")
    if not token:
        raise TikTokAPIError("Token TikTok manquant — reconnectez le compte")
    return row, token


def complete_oauth(user_id: str, auth_code: str) -> dict[str, Any]:
    client = TikTokMarketingClient()
    token_data = client.exchange_code(auth_code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise TikTokAPIError("Pas d'access_token dans la réponse TikTok")
    expires_in = token_data.get("expires_in")

    advertisers = client.list_advertisers(access_token)
    # Some responses include advertiser_ids on the token payload
    if not advertisers:
        for aid in token_data.get("advertiser_ids") or []:
            advertisers.append(
                TikTokAdvertiser(
                    advertiser_id=str(aid),
                    advertiser_name=f"Advertiser {aid}",
                )
            )

    if not advertisers:
        row = upsert_ad_account(
            user_id,
            account_id="tiktok-unknown",
            account_name="TikTok (no advertiser listed)",
            access_token=access_token,
            expires_in=int(expires_in) if expires_in else None,
        )
        return {
            "accounts": [row],
            "count": 1,
            "warning": "Aucun advertiser trouvé",
        }

    saved = []
    for adv in advertisers:
        saved.append(
            upsert_ad_account(
                user_id,
                account_id=str(adv.advertiser_id),
                account_name=str(adv.advertiser_name),
                access_token=access_token,
                expires_in=int(expires_in) if expires_in else None,
            )
        )
    return {"accounts": saved, "count": len(saved)}


def sync_tiktok_account(
    user_id: str,
    *,
    ad_account_row_id: str | None = None,
) -> dict[str, Any]:
    db.ensure_profile(user_id)
    row, token = get_decrypted_token(user_id, ad_account_row_id)
    account_id = str(row["account_id"])

    if account_id.startswith("mock-"):
        insights = mock_tiktok_campaigns()
    else:
        insights = TikTokMarketingClient().list_campaigns_with_insights(token, account_id)

    upserted = []
    for item in insights:
        camp = db.upsert_campaign(
            user_id,
            platform_campaign_id=item.platform_campaign_id,
            name=item.name,
            platform="tiktok",
            spend=item.spend,
            impressions=item.impressions,
            clicks=item.clicks,
            leads=item.leads,
            status=(item.status or "active").lower(),
        )
        try:
            sb = get_supabase_admin()
            sb.table("campaigns").update({"ad_account_id": row["id"]}).eq(
                "id", camp["id"]
            ).execute()
            camp["ad_account_id"] = row["id"]
        except Exception:
            pass
        upserted.append(camp)

    sb = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()
    sb.table("ad_accounts").update({"last_sync": now}).eq("id", row["id"]).execute()

    return {
        "ad_account": {
            "id": row["id"],
            "account_id": account_id,
            "account_name": row.get("account_name"),
            "last_sync": now,
        },
        "campaigns_synced": len(upserted),
        "campaigns": upserted,
    }


def connect_mock_tiktok(user_id: str) -> dict[str, Any]:
    db.ensure_profile(user_id)
    row = upsert_ad_account(
        user_id,
        account_id="mock-tiktok-001",
        account_name="[MOCK] TikTok Ads — CODReal Demo",
        access_token="mock-tiktok-token",
        expires_in=60 * 60 * 24 * 60,
    )
    sync_result = sync_tiktok_account(user_id, ad_account_row_id=row["id"])
    return {"account": row, "sync": sync_result, "mode": "mock"}


def disconnect_tiktok_account(user_id: str, ad_account_row_id: str) -> dict[str, Any]:
    sb = get_supabase_admin()
    sb.table("ad_accounts").delete().eq("user_id", user_id).eq(
        "id", ad_account_row_id
    ).eq("platform", "tiktok").execute()
    return {"deleted": True, "id": ad_account_row_id}
