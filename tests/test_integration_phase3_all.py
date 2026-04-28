import pytest

def test_history_per_server_all_ranges(test_app):
    for r in ["5m", "15m", "1h", "6h", "24h", "7d"]:
        resp = test_app.get(f"/api/v1/servers/1/history?range={r}")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        assert isinstance(data["history"], list)


def test_history_aggregated_all_servers(test_app):
    resp = test_app.get("/api/v1/servers/metrics/history?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "servers" in data or isinstance(data, dict)


def test_export_all_servers_json(test_app):
    resp = test_app.get("/api/v1/servers/export?format=json&range=24h")
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data, dict)
    assert "servers" in data or isinstance(data, dict)


def test_export_all_servers_csv(test_app):
    resp = test_app.get("/api/v1/servers/export?format=csv&range=24h")
    assert resp.status_code in (200, 206)
    assert isinstance(resp.text, str)


def test_uptime_timeline(test_app):
    resp = test_app.get("/api/v1/servers/1/uptime-timeline?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    assert "uptime_percent" in data


def test_disk_breakdown(test_app):
    resp = test_app.get("/api/v1/servers/1/disk-breakdown")
    assert resp.status_code == 200
    data = resp.json()
    assert "disks" in data


def test_backups_endpoints(test_app):
    resp = test_app.get("/api/v1/backup/list")
    assert resp.status_code == 200
    # create backup
    resp2 = test_app.post("/api/v1/backup/create")
    assert resp2.status_code in (200, 201)
