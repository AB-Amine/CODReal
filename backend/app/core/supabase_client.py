"""Supabase clients (service role for backend persistence)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings


class SupabaseNotConfiguredError(RuntimeError):
    """Raised when Supabase env vars are missing."""


def is_supabase_configured() -> bool:
    """Not cached so .env changes after restart are always reflected."""
    settings = get_settings()
    if hasattr(settings, "supabase_ready"):
        return bool(settings.supabase_ready)
    return bool(settings.supabase_url and settings.supabase_key)


@lru_cache
def get_supabase_admin() -> Any:
    """Service-role client — bypasses RLS; always scope queries by user_id."""
    if not is_supabase_configured():
        raise SupabaseNotConfiguredError(
            "Supabase non configuré. Définissez SUPABASE_URL et SUPABASE_KEY "
            "dans backend/.env (service_role key)."
        )
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.supabase_url.strip(), settings.supabase_key.strip())


def clear_supabase_cache() -> None:
    """Call after env changes in the same process (tests / hot reload helpers)."""
    from app.core.config import clear_settings_cache

    clear_settings_cache()
    get_supabase_admin.cache_clear()

