def test_history_per_server_all_ranges(auth_client):
    """Test history endpoint with all range values"""
    for r in ["5m", "15m", "1h", "6h", "24h", "7d"]:
        resp = auth_client.get(f"/api/v1/servers/1/history-detail?range={r}")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data


def test_history_aggregated_all_servers(auth_client):
    """Test aggregated history endpoint"""
    resp = auth_client.get("/api/v1/servers/history?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "servers" in data


def test_export_all_servers_json(auth_client):
    """Test export all servers as JSON"""
    resp = auth_client.get("/api/v1/servers/export?format=json&range=24h")
    assert resp.status_code == 200


def test_export_all_servers_csv(auth_client):
    """Test export all servers as CSV"""
    resp = auth_client.get("/api/v1/servers/export?format=csv&range=24h")
    assert resp.status_code == 200


def test_uptime_timeline(auth_client):
    """Test uptime timeline endpoint"""
    resp = auth_client.get("/api/v1/servers/1/uptime-timeline?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    assert "uptime_percent" in data


def test_disk_breakdown(auth_client):
    """Test disk breakdown endpoint"""
    resp = auth_client.get("/api/v1/servers/1/disk-breakdown")
    assert resp.status_code == 200
    data = resp.json()
    assert "disks" in data


def test_backups_endpoints(auth_client):
    """Test backup endpoints"""
    resp = auth_client.get("/api/v1/backup/list")
    assert resp.status_code == 200
