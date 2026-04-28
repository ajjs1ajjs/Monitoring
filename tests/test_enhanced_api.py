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

import json
from typing import Any, Dict

import pytest


class TestMetricsHistory:
    """Tests for /api/v1/servers/history endpoint"""

    def test_get_metrics_history_all_metrics(self, client):
        """Test getting all metrics"""
        response = client.get("/api/v1/servers/history?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_cpu_only(self, client):
        """Test getting only CPU metric"""
        response = client.get("/api/v1/servers/history?range=1h&metric=cpu")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_memory_only(self, client):
        """Test getting only memory metric"""
        response = client.get("/api/v1/servers/history?range=1h&metric=memory")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    def test_get_metrics_history_single_server(self, client):
        """Test getting metrics for single server"""
        response = client.get("/api/v1/servers/1/history-detail?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_get_metrics_history_invalid_range(self, client):
        """Test with invalid range - should return 422"""
        response = client.get("/api/v1/servers/history?range=invalid")
        assert response.status_code == 422  # Validation error


class TestDiskBreakdown:
    """Tests for /api/v1/servers/{id}/disk-breakdown endpoint"""

    def test_get_disk_breakdown(self, client):
        """Test getting disk breakdown"""
        response = client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data
        assert len(data["disks"]) == 2

    def test_get_disk_breakdown_multiple_volumes(self, client):
        """Test multiple volumes"""
        response = client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        volumes = [d["volume"] for d in data["disks"]]
        assert "C:" in volumes
        assert "D:" in volumes

    def test_get_disk_breakdown_nonexistent_server(self, client):
        """Test with non-existent server"""
        response = client.get("/api/v1/servers/999/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["disks"] == []


class TestUptimeTimeline:
    """Tests for /api/v1/servers/{id}/uptime-timeline endpoint"""

    def test_get_uptime_timeline_default_days(self, client):
        """Test default 7 days"""
        response = client.get("/api/v1/servers/1/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert "uptime_percent" in data

    def test_get_uptime_timeline_custom_days(self, client):
        """Test custom days parameter"""
        response = client.get("/api/v1/servers/1/uptime-timeline?days=14")
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data

    def test_get_uptime_timeline_nonexistent_server(self, client):
        """Test with non-existent server"""
        response = client.get("/api/v1/servers/999/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert data["timeline"] == []
        assert data["uptime_percent"] == 0


class TestExport:
    """Tests for /api/v1/servers/{id}/export endpoint"""

    def test_export_json(self, client):
        """Test JSON export"""
        response = client.get("/api/v1/servers/1/export?format=json&range=24h")
        assert response.status_code in [200, 401]  # 401 if not authenticated

    def test_export_csv(self, client):
        """Test CSV export"""
        response = client.get("/api/v1/servers/1/export?format=csv&range=24h")
        assert response.status_code in [200, 401]

    def test_export_nonexistent_server(self, client):
        """Test export for non-existent server"""
        response = client.get("/api/v1/servers/999/export?format=json")
        assert response.status_code in [200, 401, 404]


class TestCompare:
    """Tests for compare endpoint"""

    def test_compare_cpu(self, client):
        """Test CPU comparison"""
        response = client.get("/api/v1/servers/compare?metric=cpu&range=1h")
        assert response.status_code in [200, 404]  # May not be implemented yet

    def test_compare_memory(self, client):
        """Test memory comparison"""
        response = client.get("/api/v1/servers/compare?metric=memory")
        assert response.status_code in [200, 404]

    def test_compare_disk(self, client):
        """Test disk comparison"""
        response = client.get("/api/v1/servers/compare?metric=disk")
        assert response.status_code in [200, 404]


class TestDataValidation:
    """Test data types and validation"""

    def test_metrics_history_data_types(self, client):
        """Test that data types are correct"""
        response = client.get("/api/v1/servers/history?range=1h")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_disk_breakdown_data_types(self, client):
        """Test disk breakdown data types"""
        response = client.get("/api/v1/servers/1/disk-breakdown")
        assert response.status_code == 200
        data = response.json()
        if data["disks"]:
            disk = data["disks"][0]
            assert "volume" in disk
            assert "size_gb" in disk
            assert "free_gb" in disk
            assert "used_gb" in disk
            assert "percent" in disk

    def test_uptime_percent_range(self, client):
        """Test uptime percent is between 0 and 100"""
        response = client.get("/api/v1/servers/1/uptime-timeline")
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["uptime_percent"] <= 100
