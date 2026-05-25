#!/usr/bin/env python3
"""
Tests for Enhanced Dashboard API Endpoints

Tests for:
- GET /api/v1/servers/history
- GET /api/v1/servers/{id}/disk-breakdown
- GET /api/v1/servers/{id}/uptime-timeline
- GET /api/v1/servers/{id}/export
- GET /api/v1/servers/compare

Run with:
    python -m pytest tests/test_enhanced_api.py -v
"""




class TestMetricsHistory:
    """Tests for /api/v1/servers/history endpoint"""

    def test_get_metrics_history_all_metrics(self, auth_client):
        """Test getting all metrics"""
        response = auth_client.get("/api/v1/servers/history?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_cpu_only(self, auth_client):
        """Test getting only CPU metric"""
        response = auth_client.get("/api/v1/servers/history?range=1h&metric=cpu")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_memory_only(self, auth_client):
        """Test getting only memory metric"""
        response = auth_client.get("/api/v1/servers/history?range=1h&metric=memory")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_single_server(self, auth_client):
        """Test getting metrics for single server"""
        response = auth_client.get("/api/v1/servers/1/history-detail?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_get_metrics_history_invalid_range(self, auth_client):
        """Test with invalid range - should return 422"""
        response = auth_client.get("/api/v1/servers/history?range=invalid")
        assert response.status_code == 422  # Validation error


class TestServersApi:
    """Tests for server collection endpoints used by the dashboard."""

    def test_list_servers_endpoint_allows_get(self, auth_client):
        response = auth_client.get("/api/v1/servers")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert isinstance(data["servers"], list)

    def test_delete_server_requires_authentication(self, client):
        response = client.delete("/api/v1/servers/1")

        assert response.status_code == 401

    def test_create_server_endpoint_allows_post(self, auth_client):
        payload = {
            "name": "Test Server",
            "host": "localhost",
            "os_type": "linux",
            "agent_port": 9100,
            "enabled": True,
            "server_group": "Testing"
        }
        response = auth_client.post("/api/v1/servers", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "id" in data

    def test_force_scrape_server_endpoint_allows_post(self, auth_client):
        response = auth_client.post("/api/v1/servers/1/scrape")
        assert response.status_code in (200, 500, 503)


class TestDiskBreakdown:
    """Tests for /api/v1/servers/{id}/disk-breakdown endpoint"""

    def test_get_disk_breakdown(self, auth_client):
        """Test getting disk breakdown"""
        response = auth_client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data
        assert len(data["disks"]) == 2

    def test_get_disk_breakdown_multiple_volumes(self, auth_client):
        """Test multiple volumes"""
        response = auth_client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        volumes = [d["volume"] for d in data["disks"]]
        assert "C:" in volumes
        assert "D:" in volumes

    def test_get_disk_breakdown_nonexistent_server(self, auth_client):
        """Test with non-existent server"""
        response = auth_client.get("/api/v1/servers/999/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["disks"] == []


class TestUptimeTimeline:
    """Tests for /api/v1/servers/{id}/uptime-timeline endpoint"""

    def test_get_uptime_timeline_default_days(self, auth_client):
        """Test default 7 days"""
        response = auth_client.get("/api/v1/servers/1/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert "uptime_percent" in data

    def test_get_uptime_timeline_custom_days(self, auth_client):
        """Test custom days parameter"""
        response = auth_client.get("/api/v1/servers/1/uptime-timeline?days=14")
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data

    def test_get_uptime_timeline_nonexistent_server(self, auth_client):
        """Test with non-existent server"""
        response = auth_client.get("/api/v1/servers/999/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert data["timeline"] == []
        assert data["uptime_percent"] == 0


class TestExport:
    """Tests for /api/v1/servers/{id}/export endpoint"""

    def test_export_json(self, auth_client):
        """Test JSON export"""
        response = auth_client.get("/api/v1/servers/1/export?format=json&range=24h")
        assert response.status_code == 200

    def test_export_csv(self, auth_client):
        """Test CSV export"""
        response = auth_client.get("/api/v1/servers/1/export?format=csv&range=24h")
        assert response.status_code == 200

    def test_export_nonexistent_server(self, auth_client):
        """Test export for non-existent server"""
        response = auth_client.get("/api/v1/servers/999/export?format=json")
        assert response.status_code == 404


class TestCompare:
    """Tests for compare endpoint"""

    def test_compare_cpu(self, auth_client):
        """Test CPU comparison"""
        response = auth_client.get("/api/v1/servers/compare?metric=cpu&range=1h")
        assert response.status_code == 200

    def test_compare_memory(self, auth_client):
        """Test memory comparison"""
        response = auth_client.get("/api/v1/servers/compare?metric=memory")
        assert response.status_code == 200

    def test_compare_disk(self, auth_client):
        """Test disk comparison"""
        response = auth_client.get("/api/v1/servers/compare?metric=disk")
        assert response.status_code == 200


class TestDataValidation:
    """Test data types and validation"""

    def test_metrics_history_data_types(self, auth_client):
        """Test that data types are correct"""
        response = auth_client.get("/api/v1/servers/history?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_disk_breakdown_data_types(self, auth_client):
        """Test disk breakdown data types"""
        response = auth_client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        if data["disks"]:
            disk = data["disks"][0]
            assert "volume" in disk
            assert "size_gb" in disk
            assert "free_gb" in disk
            assert "used_gb" in disk
            assert "percent" in disk

    def test_uptime_percent_range(self, auth_client):
        """Test uptime percent is between 0 and 100"""
        response = auth_client.get("/api/v1/servers/1/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["uptime_percent"] <= 100
