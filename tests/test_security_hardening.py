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
