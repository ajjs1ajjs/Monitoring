def test_history_endpoint_all_methods(auth_client):
    """Test history endpoint"""
    resp = auth_client.get("/api/v1/servers/1/history-detail?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data


def test_export_json_single_server(auth_client):
    """Test export single server as JSON"""
    resp = auth_client.get("/api/v1/servers/1/export?format=json&range=24h")
    assert resp.status_code == 200


def test_export_csv_single_server(auth_client):
    """Test export single server as CSV"""
    resp = auth_client.get("/api/v1/servers/1/export?format=csv&range=24h")
    assert resp.status_code == 200
