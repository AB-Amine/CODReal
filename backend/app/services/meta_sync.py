"""Persist Meta OAuth tokens and sync campaign insights into CODReal DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.supabase_client import get_supabase_admin
from app.services import persistence as db
from app.services.meta_api import (
    MetaAPIError,
    MetaMarketingClient,
    mock_meta_campaigns,
)


def create_oauth_state(user_id: str) -> str:
    settings = get_settings()
    secret = settings.supabase_jwt_secret or settings.token_encryption_key or "codreal-dev"
    return jwt.encode(
        {
            "sub": user_id,
            "purpose": "meta_oauth",
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
        raise MetaAPIError("State OAuth invalide ou expiré") from exc
    if payload.get("purpose") != "meta_oauth" or not payload.get("sub"):
        raise MetaAPIError("State OAuth incorrect")
    return str(payload["sub"])


def list_meta_accounts(user_id: str) -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("ad_accounts")
        .select("id,platform,account_id,account_name,last_sync,token_expires_at,created_at")
        .eq("user_id", user_id)
        .eq("platform", "meta")
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
        .eq("platform", "meta")
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )
    payload = {
        "user_id": user_id,
        "platform": "meta",
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
        .eq("platform", "meta")
    )
    if account_row_id:
        q = q.eq("id", account_row_id)
    res = q.order("created_at", desc=True).limit(1).execute()
    if not res.data:
        raise MetaAPIError("Aucun compte Meta connecté")
    row = res.data[0]
    token = decrypt_token(row.get("access_token") or "")
    if not token:
        raise MetaAPIError("Token Meta manquant — reconnectez le compte")
    return row, token


def complete_oauth(user_id: str, code: str) -> dict[str, Any]:
    """Exchange code, store long-lived token for each ad account found."""
    client = MetaMarketingClient()
    short = client.exchange_code(code)
    short_token = short.get("access_token")
    if not short_token:
        raise MetaAPIError("Pas d'access_token dans la réponse Meta")

    long_lived = client.exchange_long_lived(short_token)
    token = long_lived.get("access_token") or short_token
    expires_in = long_lived.get("expires_in") or short.get("expires_in")

    me = client.get_me(token)
    accounts = client.list_ad_accounts(token)
    if not accounts:
        # Store a placeholder account so user can still retry sync
        row = upsert_ad_account(
            user_id,
            account_id=f"user-{me.get('id', 'unknown')}",
            account_name=f"Meta user {me.get('name') or me.get('id')}",
            access_token=token,
            expires_in=int(expires_in) if expires_in else None,
        )
        return {
            "user": me,
            "accounts": [row],
            "warning": "Aucun ad account trouvé — vérifiez les permissions Business Manager",
        }

    saved = []
    for acc in accounts:
        saved.append(
            upsert_ad_account(
                user_id,
                account_id=acc.account_id,
                account_name=acc.name,
                access_token=token,
                expires_in=int(expires_in) if expires_in else None,
            )
        )
    return {"user": me, "accounts": saved, "count": len(saved)}


def sync_meta_account(
    user_id: str,
    *,
    ad_account_row_id: str | None = None,
    date_preset: str | None = None,
) -> dict[str, Any]:
    """Pull campaigns + insights and upsert into campaigns table."""
    db.ensure_profile(user_id)
    row, token = get_decrypted_token(user_id, ad_account_row_id)
    client = MetaMarketingClient()
    account_id = str(row["account_id"])

    # Skip live API if mock account
    if account_id.startswith("mock-"):
        insights = mock_meta_campaigns()
    else:
        try:
            insights = client.list_campaigns_with_insights(
                token, account_id, date_preset=date_preset
            )
        except MetaAPIError:
            raise

    upserted = []
    for item in insights:
        camp = db.upsert_campaign(
            user_id,
            platform_campaign_id=item.platform_campaign_id,
            name=item.name,
            platform="meta",
            spend=item.spend,
            impressions=item.impressions,
            clicks=item.clicks,
            leads=item.leads,
            status=item.status.lower() if item.status else "active",
        )
        # Link ad_account_id
        try:
            sb = get_supabase_admin()
            sb.table("campaigns").update({"ad_account_id": row["id"]}).eq(
                "id", camp["id"]
            ).execute()
            camp["ad_account_id"] = row["id"]
        except Exception:
            pass
        upserted.append(camp)

    # Update last_sync
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
        "date_preset": date_preset or get_settings().meta_insights_date_preset,
    }


def connect_mock_meta(user_id: str) -> dict[str, Any]:
    """Dev/onboarding: connect a fake Meta account and sync sample campaigns."""
    db.ensure_profile(user_id)
    row = upsert_ad_account(
        user_id,
        account_id="mock-meta-001",
        account_name="[MOCK] Meta Business — CODReal Demo",
        access_token="mock-token-not-for-production",
        expires_in=60 * 60 * 24 * 60,
    )
    sync_result = sync_meta_account(user_id, ad_account_row_id=row["id"])
    return {"account": row, "sync": sync_result, "mode": "mock"}


def disconnect_meta_account(user_id: str, ad_account_row_id: str) -> dict[str, Any]:
    sb = get_supabase_admin()
    # Clear token first
    sb.table("ad_accounts").update(
        {"access_token": None, "token_expires_at": None}
    ).eq("user_id", user_id).eq("id", ad_account_row_id).eq("platform", "meta").execute()
    deleted = (
        sb.table("ad_accounts")
        .delete()
        .eq("user_id", user_id)
        .eq("id", ad_account_row_id)
        .eq("platform", "meta")
        .execute()
    )
    return {"deleted": True, "id": ad_account_row_id, "rows": deleted.data}
