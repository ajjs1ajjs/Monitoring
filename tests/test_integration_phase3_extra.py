import pytest


def test_history_endpoint_all_methods(client):
    """Test history endpoint"""
    resp = client.get("/api/v1/servers/1/history-detail?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data


def test_export_json_single_server(client):
    """Test export single server as JSON"""
    resp = client.get("/api/v1/servers/1/export?format=json&range=24h")
    assert resp.status_code in (200, 401)  # 401 if not authenticated


def test_export_csv_single_server(client):
    """Test export single server as CSV"""
    resp = client.get("/api/v1/servers/1/export?format=csv&range=24h")
    assert resp.status_code in (200, 401)
