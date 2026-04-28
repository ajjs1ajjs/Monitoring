#!/usr/bin/env python3
"""
Tests for Enhanced Dashboard API Endpoints

Tests for:
- GET /api/servers/metrics-history
- GET /api/servers/{id}/disk-breakdown
- GET /api/servers/{id}/uptime-timeline
- GET /api/servers/{id}/export
- GET /api/servers/compare

Run with:
    python -m pytest tests/test_enhanced_api.py -v
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

# Test database path
TEST_DB_PATH = ":memory:"


@pytest.fixture
def db():
    """Create in-memory database for testing"""
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row

    # Create tables
    conn.execute("""
        CREATE TABLE servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            os_type TEXT DEFAULT 'linux',
            agent_port INTEGER DEFAULT 9100,
            last_status TEXT DEFAULT 'unknown',
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            disk_info TEXT,
            last_check TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_rx REAL,
            network_tx REAL,
            timestamp TEXT NOT NULL
        )
    """)

    # Insert test data
    conn.execute(
        """
        INSERT INTO servers (name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, disk_info, last_check)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "Test Server 1",
            "192.168.1.100",
            "linux",
            9100,
            "up",
            45.5,
            62.3,
            78.1,
            json.dumps(
                [
                    {"volume": "C:", "size": 500000000000, "free": 250000000000},
                    {"volume": "D:", "size": 1000000000000, "free": 600000000000},
                ]
            ),
            datetime.now().isoformat(),
        ),
    )

    # Insert metrics history
    now = datetime.now()
    for i in range(10):
        ts = (now - timedelta(minutes=i * 5)).isoformat()
        conn.execute(
            """
            INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (1, 40 + i, 60 + i, 75 + i, 1000000 + i * 100000, 500000 + i * 50000, ts),
        )

    conn.commit()
    yield conn
    conn.close()


class TestMetricsHistory:
    """Tests for /api/servers/metrics-history endpoint"""

    async def test_get_metrics_history_all_metrics(self, db):
        """Test getting all metrics"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        result = await get_servers_metrics_history(range="1h")

        assert "labels" in result
        assert "datasets" in result
        assert len(result["labels"]) > 0
        assert len(result["datasets"]) > 0

    async def test_get_metrics_history_cpu_only(self, db):
        """Test getting only CPU metric"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        result = await get_servers_metrics_history(range="1h", metric="cpu")

        assert "labels" in result
        assert "datasets" in result
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["label"] == "CPU"

    async def test_get_metrics_history_memory_only(self, db):
        """Test getting only Memory metric"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        result = await get_servers_metrics_history(range="1h", metric="memory")

        assert "labels" in result
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["label"] == "Memory"

    async def test_get_metrics_history_single_server(self, db):
        """Test getting metrics for specific server"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        result = await get_servers_metrics_history(server_id=1, range="1h")

        assert "labels" in result
        assert "datasets" in result

    async def test_get_metrics_history_invalid_range(self, db):
        """Test with invalid time range"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        # Should default to 1h or handle gracefully
        result = await get_servers_metrics_history(range="invalid")

        assert isinstance(result, dict)


class TestDiskBreakdown:
    """Tests for /api/servers/{id}/disk-breakdown endpoint"""

    async def test_get_disk_breakdown(self, db):
        """Test getting disk breakdown"""
        from pymon.web_dashboard_enhanced import get_server_disk_breakdown

        result = await get_server_disk_breakdown(1)

        assert "disks" in result
        assert len(result["disks"]) > 0

        disk = result["disks"][0]
        assert "volume" in disk
        assert "size_gb" in disk
        assert "free_gb" in disk
        assert "percent" in disk

    async def test_get_disk_breakdown_multiple_volumes(self, db):
        """Test disk breakdown with multiple volumes"""
        from pymon.web_dashboard_enhanced import get_server_disk_breakdown

        result = await get_server_disk_breakdown(1)

        # Should have C: and D:
        assert len(result["disks"]) >= 1

        volumes = [d["volume"] for d in result["disks"]]
        assert "C:" in volumes

    async def test_get_disk_breakdown_nonexistent_server(self, db):
        """Test disk breakdown for non-existent server"""
        from pymon.web_dashboard_enhanced import get_server_disk_breakdown

        result = await get_server_disk_breakdown(999)

        assert "disks" in result
        assert len(result["disks"]) == 0

    async def test_get_disk_breakdown_no_disk_info(self, db):
        """Test server without disk info"""
        # Insert server without disk_info
        db.execute(
            """
            INSERT INTO servers (name, host, os_type, agent_port, last_status)
            VALUES (?, ?, ?, ?, ?)
        """,
            ("No Disk Server", "192.168.1.200", "linux", 9100, "up"),
        )
        db.commit()

        from pymon.web_dashboard_enhanced import get_server_disk_breakdown

        result = await get_server_disk_breakdown(2)

        assert "disks" in result
        assert len(result["disks"]) == 0


class TestUptimeTimeline:
    """Tests for /api/servers/{id}/uptime-timeline endpoint"""

    async def test_get_uptime_timeline_default_days(self, db):
        """Test getting uptime timeline with default days"""
        from pymon.web_dashboard_enhanced import get_server_uptime_timeline

        result = await get_server_uptime_timeline(1)

        assert "timeline" in result
        assert "uptime_percent" in result
        assert isinstance(result["uptime_percent"], (int, float))

    async def test_get_uptime_timeline_custom_days(self, db):
        """Test getting uptime timeline with custom days"""
        from pymon.web_dashboard_enhanced import get_server_uptime_timeline

        result = await get_server_uptime_timeline(1, days=14)

        assert "timeline" in result
        assert "uptime_percent" in result

    async def test_get_uptime_timeline_nonexistent_server(self, db):
        """Test uptime for non-existent server"""
        from pymon.web_dashboard_enhanced import get_server_uptime_timeline

        result = await get_server_uptime_timeline(999)

        assert "timeline" in result
        assert "uptime_percent" in result


class TestExport:
    """Tests for /api/servers/{id}/export endpoint"""

    async def test_export_json(self, db):
        """Test JSON export"""
        from pymon.web_dashboard_enhanced import export_server_data

        result = await export_server_data(1, format="json", range="24h")

        assert "server_id" in result
        assert "range" in result
        assert "data" in result
        assert isinstance(result["data"], list)

    async def test_export_csv(self, db):
        """Test CSV export"""
        from pymon.web_dashboard_enhanced import export_server_data

        result = await export_server_data(1, format="csv", range="24h")

        # Should return CSV string
        assert isinstance(result, str)
        assert "Timestamp" in result
        assert "CPU" in result

    async def test_export_nonexistent_server(self, db):
        """Test export for non-existent server"""
        from pymon.web_dashboard_enhanced import export_server_data

        result = await export_server_data(999, format="json", range="24h")

        assert "server_id" in result
        assert "data" in result
        assert len(result["data"]) == 0


class TestCompare:
    """Tests for /api/servers/compare endpoint"""

    async def test_compare_cpu(self, db):
        """Test CPU comparison"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(metric="cpu", range="1h")

        assert "current" in result
        assert "previous" in result
        assert "delta" in result
        assert "delta_percent" in result
        assert "trend" in result
        assert result["trend"] in ["up", "down", "stable"]

    async def test_compare_memory(self, db):
        """Test Memory comparison"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(metric="memory", range="1h")

        assert "current" in result
        assert "trend" in result

    async def test_compare_disk(self, db):
        """Test Disk comparison"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(metric="disk", range="1h")

        assert "current" in result
        assert "trend" in result

    async def test_compare_network(self, db):
        """Test Network comparison"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(metric="network", range="1h")

        assert "current" in result
        assert "trend" in result

    async def test_compare_single_server(self, db):
        """Test comparison for specific server"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(server_id=1, metric="cpu", range="1h")

        assert "current" in result
        assert "previous" in result


class TestDataValidation:
    """Data validation tests"""

    async def test_metrics_history_data_types(self, db):
        """Test that metrics history returns correct data types"""
        from pymon.web_dashboard_enhanced import get_servers_metrics_history

        result = await get_servers_metrics_history(range="1h")

        assert isinstance(result["labels"], list)
        assert isinstance(result["datasets"], list)

        if result["datasets"]:
            ds = result["datasets"][0]
            assert isinstance(ds["label"], str)
            assert isinstance(ds["data"], list)
            assert isinstance(ds["borderColor"], str)
            assert isinstance(ds["backgroundColor"], str)

    async def test_disk_breakdown_data_types(self, db):
        """Test that disk breakdown returns correct data types"""
        from pymon.web_dashboard_enhanced import get_server_disk_breakdown

        result = await get_server_disk_breakdown(1)

        for disk in result["disks"]:
            assert isinstance(disk["volume"], str)
            assert isinstance(disk["percent"], (int, float))
            assert isinstance(disk["size_gb"], (int, float))

    async def test_uptime_percent_range(self, db):
        """Test that uptime percent is in valid range"""
        from pymon.web_dashboard_enhanced import get_server_uptime_timeline

        result = await get_server_uptime_timeline(1, days=7)

        uptime = result["uptime_percent"]
        assert 0 <= uptime <= 100

    async def test_compare_trend_values(self, db):
        """Test that trend is one of expected values"""
        from pymon.web_dashboard_enhanced import compare_time_ranges

        result = await compare_time_ranges(metric="cpu", range="1h")

        assert result["trend"] in ["up", "down", "stable"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
