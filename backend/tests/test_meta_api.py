from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.services.meta_api import MetaMarketingClient, _extract_leads, mock_meta_campaigns
from app.services.meta_sync import create_oauth_state, parse_oauth_state


def test_build_oauth_url():
    settings = Settings(
        meta_app_id="123456",
        meta_app_secret="secret",
        meta_redirect_uri="http://127.0.0.1:8000/api/v1/integrations/meta/callback",
        meta_graph_version="v21.0",
        meta_oauth_scopes="ads_read",
    )
    client = MetaMarketingClient(settings)
    url = client.build_oauth_url("state-token")
    parsed = urlparse(url)
    assert "facebook.com" in parsed.netloc
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["123456"]
    assert qs["state"] == ["state-token"]
    assert qs["scope"] == ["ads_read"]


def test_oauth_state_roundtrip():
    state = create_oauth_state("user-abc-123")
    assert parse_oauth_state(state) == "user-abc-123"


def test_extract_leads():
    actions = [
        {"action_type": "link_click", "value": "10"},
        {"action_type": "lead", "value": "5"},
        {"action_type": "onsite_conversion.lead_grouped", "value": "2"},
    ]
    assert _extract_leads(actions) == 7


def test_mock_campaigns_non_empty():
    camps = mock_meta_campaigns()
    assert len(camps) >= 2
    assert all(c.spend >= 0 for c in camps)
    assert sum(c.spend for c in camps) > 0
