"""Tests for the security-hardening changes (host whitelist, admin gating)."""

import pytest

from pymon import auth
from pymon.notifications import build_channels
from pymon.validation import ValidationError, validate_server_host


def test_validate_server_host_strips_scheme_and_path():
    assert validate_server_host("http://example.com/metrics?x=1") == "example.com"
    assert validate_server_host("10.0.0.5") == "10.0.0.5"


@pytest.mark.parametrize("payload", [
    '<img src=x onerror=alert(1)>',
    'host";<script>',
    "a b",            # space
    "host<>",
])
def test_validate_server_host_rejects_xss_payloads(payload):
    with pytest.raises(ValidationError):
        validate_server_host(payload)


def test_build_channels_only_includes_configured():
    cfg = {
        "telegram_bot_token": "t", "telegram_chat_id": "c",
        "discord_webhook_url": "",   # disabled
        "smtp_server": "smtp", "email_to": "a@b.c",
    }
    channels = build_channels(cfg)
    assert set(channels) == {"telegram", "email"}
    assert channels["telegram"] == {"bot_token": "t", "chat_id": "c"}


def _non_admin_token(client, db_path):
    """Create a real non-admin user and return a bearer token for it."""
    import os
    os.environ["DB_PATH"] = db_path
    user = auth.create_user(username="viewer", password="ViewerPass123", is_admin=False)
    return auth.create_token(user.id, user.username, is_admin=False, must_change=False)


def test_destructive_endpoints_require_admin(client, db_path):
    token = _non_admin_token(client, db_path)
    headers = {"Authorization": f"Bearer {token}"}

    # Non-admin is authenticated but must be forbidden from destructive actions.
    assert client.delete("/api/v1/servers/1", headers=headers).status_code == 403
    assert client.post("/api/v1/backup/restore", json={"filename": "x.db"}, headers=headers).status_code == 403
    assert client.delete("/api/v1/metrics/history", headers=headers).status_code == 403


def test_admin_can_delete_server(auth_client):
    # Admin (auth_client) is allowed through the same gate.
    resp = auth_client.delete("/api/v1/servers/999")
    assert resp.status_code == 200


def test_api_key_cannot_perform_admin_actions(client, db_path):
    import os
    os.environ["DB_PATH"] = db_path
    key = auth.create_api_key(user_id=1, name="ci-key")  # user 1 is the admin
    # API key is rejected for admin actions even though the owner is an admin...
    assert client.delete("/api/v1/servers/999", headers={"X-API-Key": key}).status_code == 403
    # ...but read access still works.
    assert client.get("/api/v1/servers", headers={"X-API-Key": key}).status_code == 200


def test_parse_cron_field_handles_steps_lists_ranges():
    from pymon.scrape import _parse_cron_field
    assert _parse_cron_field("*", 59) is None
    assert _parse_cron_field("*/15", 59) == {0, 15, 30, 45}
    assert _parse_cron_field("2,14", 23) == {2, 14}
    assert _parse_cron_field("1-3", 23) == {1, 2, 3}
    assert _parse_cron_field("bogus", 23) == set()  # no crash


def test_metadata_host_blocked_by_default(monkeypatch):
    from pymon.validation import is_blocked_outbound_host
    monkeypatch.delenv("PYMON_ALLOW_METADATA", raising=False)
    assert is_blocked_outbound_host("169.254.169.254") is True
    assert is_blocked_outbound_host("192.168.1.10") is False  # LAN target allowed
    monkeypatch.setenv("PYMON_ALLOW_METADATA", "true")
    assert is_blocked_outbound_host("169.254.169.254") is False


def test_alert_service_mutations_require_admin(client, db_path):
    """Audit fix: alert/service config mutations must be admin-only (API keys & non-admins rejected)."""
    import os
    os.environ["DB_PATH"] = db_path
    # Unique username — db_path is session-scoped and shared across tests.
    user = auth.create_user(username="viewer_alerts", password="ViewerPass123", is_admin=False)
    token = auth.create_token(user.id, user.username, is_admin=False, must_change=False)
    h = {"Authorization": f"Bearer {token}"}
    assert client.delete("/api/v1/alerts/1", headers=h).status_code == 403
    assert client.delete("/api/v1/services/1", headers=h).status_code == 403
    key = auth.create_api_key(user_id=1, name="k2")  # owner is admin
    assert client.delete("/api/v1/alerts/1", headers={"X-API-Key": key}).status_code == 403
    assert client.delete("/api/v1/services/1", headers={"X-API-Key": key}).status_code == 403


def test_ssrf_blocks_encoded_metadata(monkeypatch):
    """Audit fix: SSRF guard resolves/normalises hosts (not a literal-string blocklist)."""
    from pymon.validation import is_blocked_outbound_host
    monkeypatch.delenv("PYMON_ALLOW_METADATA", raising=False)
    assert is_blocked_outbound_host("2852039166") is True   # decimal-int form of 169.254.169.254
    assert is_blocked_outbound_host("0xA9FEA9FE") is True    # hex form
    assert is_blocked_outbound_host("127.0.0.1") is True     # loopback
    assert is_blocked_outbound_host("[::1]") is True          # ipv6 loopback
    assert is_blocked_outbound_host("10.1.2.3") is False     # private LAN remains allowed


def test_redact_config_masks_secrets():
    """Audit fix: export_config must not echo plaintext secrets."""
    from pymon.api.routers.settings import _redact_config
    cfg = {
        "auth": {"admin_password": "secret123"},
        "notifications": {
            "telegram": {"bot_token": "abc"},
            "webhook": {"headers": {"Authorization": "Bearer x"}},
        },
        "port": 8000,
    }
    r = _redact_config(cfg)
    assert r["auth"]["admin_password"] == "***REDACTED***"
    assert r["notifications"]["telegram"]["bot_token"] == "***REDACTED***"
    assert r["notifications"]["webhook"]["headers"] == "***REDACTED***"
    assert r["port"] == 8000  # non-secret untouched


def test_import_prometheus_invalid_yaml_returns_400(auth_client):
    """Audit fix: non-mapping YAML is a clean 400, not a 500 AttributeError."""
    resp = auth_client.post(
        "/api/v1/settings/config/import-prometheus", json={"yaml_content": "just-a-scalar-string"}
    )
    assert resp.status_code == 400


def test_security_headers_present(client):
    """Audit fix: baseline security headers on every response."""
    resp = client.get("/api/v1/servers")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in resp.headers
