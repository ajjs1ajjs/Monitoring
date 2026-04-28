import pytest


def test_history_endpoint(client):
    """Test history endpoint"""
    resp = client.get("/api/v1/servers/1/history-detail?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert isinstance(data["history"], list)
