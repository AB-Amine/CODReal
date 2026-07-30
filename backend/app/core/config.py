"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve backend/.env even if uvicorn is started from repo root
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CODReal API"
    app_version: str = "0.1.0"
    debug: bool = True
    api_prefix: str = "/api/v1"
    # Comma-separated. Production: set CORS_ORIGINS to your Vercel URL(s)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Supabase (Legacy support)
    supabase_url: str = ""
    supabase_key: str = ""  # service role for backend
    supabase_jwt_secret: str = ""

    # Firebase (Auth + Cloud Firestore)
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_credentials_json: str = ""

    # Token encryption (Fernet key material)
    token_encryption_key: str = ""

    # Meta Marketing API (read-only OAuth)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://127.0.0.1:8000/api/v1/integrations/meta/callback"
    meta_graph_version: str = "v21.0"
    meta_oauth_scopes: str = "ads_read,business_management"
    frontend_url: str = "http://localhost:3000"

    # TikTok Marketing API (read-only OAuth)
    tiktok_app_id: str = ""
    tiktok_app_secret: str = ""
    tiktok_redirect_uri: str = "http://127.0.0.1:8000/api/v1/integrations/tiktok/callback"
    tiktok_api_base: str = "https://business-api.tiktok.com/open_api/v1.3"

    # Sync
    default_return_fee: float = 25.0  # MAD estimated return fee
    meta_insights_date_preset: str = "last_30d"
    # Protect cron endpoint: Authorization: Bearer <CRON_SECRET>
    cron_secret: str = "codreal-dev-cron-secret"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def meta_configured(self) -> bool:
        return bool(self.meta_app_id and self.meta_app_secret)

    @property
    def tiktok_configured(self) -> bool:
        return bool(self.tiktok_app_id and self.tiktok_app_secret)

    @property
    def firebase_ready(self) -> bool:
        return bool(
            self.firebase_project_id
            or self.firebase_credentials_json
            or (self.firebase_client_email and self.firebase_private_key)
        )

    @property
    def supabase_ready(self) -> bool:
        url = (self.supabase_url or "").strip()
        key = (self.supabase_key or "").strip()
        if not url or not key:
            return False
        if "YOUR_PROJECT" in url:
            return False
        if key in ("your-service-role-key", "your-anon-key", "changeme"):
            return False
        return url.startswith("http")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
