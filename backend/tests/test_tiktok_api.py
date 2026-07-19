from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.services.tiktok_api import TikTokMarketingClient, mock_tiktok_campaigns
from app.services.tiktok_sync import create_oauth_state, parse_oauth_state


def test_build_tiktok_oauth_url():
    settings = Settings(
        tiktok_app_id="tt-app",
        tiktok_app_secret="tt-secret",
        tiktok_redirect_uri="http://127.0.0.1:8000/api/v1/integrations/tiktok/callback",
    )
    client = TikTokMarketingClient(settings)
    url = client.build_oauth_url("state-xyz")
    parsed = urlparse(url)
    assert "tiktok.com" in parsed.netloc
    qs = parse_qs(parsed.query)
    assert qs["app_id"] == ["tt-app"]
    assert qs["state"] == ["state-xyz"]


def test_tiktok_oauth_state_roundtrip():
    state = create_oauth_state("user-tt-1")
    assert parse_oauth_state(state) == "user-tt-1"


def test_mock_tiktok_campaigns():
    camps = mock_tiktok_campaigns()
    assert len(camps) >= 2
    assert sum(c.spend for c in camps) > 0
