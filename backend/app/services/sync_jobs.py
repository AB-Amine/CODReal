"""Background / cron sync for all connected ad accounts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.supabase_client import get_supabase_admin
from app.services import meta_sync, tiktok_sync


def list_all_ad_accounts() -> list[dict]:
    sb = get_supabase_admin()
    res = (
        sb.table("ad_accounts")
        .select("id,user_id,platform,account_id,account_name,last_sync")
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def sync_all_accounts(*, platform: str | None = None) -> dict[str, Any]:
    """Sync every connected account (Meta + TikTok). Safe for cron every 4–6h."""
    accounts = list_all_ad_accounts()
    if platform:
        accounts = [a for a in accounts if a.get("platform") == platform]

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

    for acc in accounts:
        user_id = acc["user_id"]
        row_id = acc["id"]
        plat = acc.get("platform")
        try:
            if plat == "meta":
                out = meta_sync.sync_meta_account(user_id, ad_account_row_id=row_id)
            elif plat == "tiktok":
                out = tiktok_sync.sync_tiktok_account(user_id, ad_account_row_id=row_id)
            else:
                continue
            results.append(
                {
                    "id": row_id,
                    "platform": plat,
                    "account_id": acc.get("account_id"),
                    "campaigns_synced": out.get("campaigns_synced", 0),
                    "ok": True,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "id": row_id,
                    "platform": plat,
                    "account_id": acc.get("account_id"),
                    "ok": False,
                    "error": str(exc)[:300],
                }
            )

    return {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "accounts_total": len(accounts),
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
