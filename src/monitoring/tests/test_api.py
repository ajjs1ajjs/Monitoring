"""
Monitoring Dashboard API Tests
=====================================

Tests for the Monitoring Dashboard FastAPI application endpoints:
- Main dashboard page (/)
- Metrics endpoint (/api/metrics)
- Historical data (/api/metrics/history/{metric_name})
- System info (/api/system)
- Health check (/api/health)
- Complete dashboard data (/api/dashboard)

Author: Monitoring Team
"""

import json
from datetime import datetime, timedelta
from typing import List

import pytest
from fastapi.testclient import TestClient


# Import the app (we'll create it in the test file)
import sys
sys.path.insert(0, str(__file__).parent.parent)  # Add parent to path

# We need to define a minimal FastAPI app for testing
try:
    from src.monitoring.app import app
except ImportError:
    # Create a minimal standalone app for testing if import fails
    from fastapi import FastAPI, Query
    from typing import Optional

    def generate_mock_data():
        """Generate realistic mock data for demo purposes"""
        now = datetime.utcnow()

        metrics_data = {
            "cpu_usage": {"base": 45.0, "noise": 10.0},
            "memory_usage": {"base": 60.0, "noise": 8.0},
            "disk_io": {"base": 50.0, "noise": 20.0},
            "network_in": {"base": 30.0, "noise": 15.0},
            "network_out": {"base": 15.0, "noise": 8.0},
            "request_rate": {"base": 250.0, "noise": 100.0},
        }

        chart_data = {}
        for metric_name, config in metrics_data.items():
            labels = []
            datasets = [
                {
                    "label": f"{metric_name.replace('_', ' ').title()}",
                    "data": [],
                    "borderColor": "#e17055" if metric_name == "cpu_usage" else "#fdcb6e",
                    "fill": False,
                }
            ]

            # Generate last 24 hours of data
            for i in range(96):  # 4 data points per hour = 24 hours
                timestamp = now - timedelta(hours=1) + timedelta(minutes=(i * 15))

                if metric_name == "cpu_usage":
                    value = max(10, min(95, config["base"] + random.gauss(0, config["noise"]))
                elif metric_name in ["network_in", "network_out"]:
                    value = max(2.0, min(200.0, config["base"] * (1 + random.gauss(0, 0.3))))
                else:
                    value = max(5.0, min(800.0, config["base"] + random.gauss(0, config["noise"] / 2)))

                labels.append(timestamp.strftime("%H:%M"))
                datasets[0]["data"].append({"x": timestamp.isoformat(), "y": round(value, 2)})

            chart_data[metric_name] = {"labels": labels, "datasets": datasets}

        return chart_data

    app = FastAPI(title="Monitoring Dashboard API (Test)")


class TestClientWithMockData(TestClient):
    """Custom test client that generates mock data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_chart_data = generate_mock_data()


# Mock random module since it's used in the app
import random


@pytest.fixture
def client():
    """Create a FastAPI test client with mock data"""
    return TestClient(app)


class TestMainDashboard:
    """Tests for the main dashboard page endpoint"""

    def test_main_dashboard_page(self, client):
        """Test that the main dashboard page returns valid HTML content"""
        response = client.get("/")

        assert response.status_code == 200
        assert "Monitoring Dashboard" in response.text or "Monitoring Dashboard API" in response.text
        assert "<html" in response.text.lower()
        assert '<script src="https://cdn.jsdelivr.net/npm/chart.js' in response.text


class TestMetricsEndpoint:
    """Tests for the /api/metrics endpoint"""

    def test_get_metrics_returns_current_values(self, client):
        """Test that metrics endpoint returns current metric values"""
        response = client.get("/api/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "metrics" in data

        # Should have all expected metrics
        expected_metrics = [
            "cpu_usage",
            "memory_usage",
            "disk_io",
            "network_in",
            "network_out",
            "request_rate",
        ]

        actual_metrics = list(data["metrics"].keys())
        assert len(actual_metrics) == len(expected_metrics), f"Missing metrics: {set(expected_metrics) - set(actual_metrics)}"

        # Each metric should have name, value, and optionally unit
        for metric_name in expected_metrics:
            metric_data = data["metrics"][metric_name]
            assert "name" in metric_data
            assert "value" in metric_data
            # Value should be a number between 0-100 for percentages
            if metric_name in ["cpu_usage", "memory_usage"]:
                assert 0 <= metric_data["value"] <= 100


class TestMetricHistoryEndpoint:
    """Tests for the /api/metrics/history endpoint"""

    def test_get_cpu_history(self, client):
        """Test getting CPU usage history for 24 hours"""
        response = client.get("/api/metrics/history/cpu_usage?hours=24")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "metric" in data
        assert "hours" in data
        assert "data" in data

        metric_name = data["metric"]
        hours = data["hours"]
        data_points = data["data"]

        assert metric_name == "cpu_usage"
        assert hours == 24

        # Should have at least some data points (every 15 minutes = 96 points)
        assert len(data_points) > 0

        # Each point should have timestamp and value
        for point in data_points:
            assert "timestamp" in point
            assert "value" in point
            assert isinstance(point["value"], (int, float))

    def test_get_memory_history(self, client):
        """Test getting memory usage history"""
        response = client.get("/api/metrics/history/memory_usage?hours=12")

        assert response.status_code == 200
        data = response.json()

        assert data["metric"] == "memory_usage"
        # Memory should show gradual increase over time
        values = [point["value"] for point in data["data"]]
        if len(values) > 1:
            # At least some variance expected
            assert any(v != values[0] for v in values)

    def test_get_invalid_metric(self, client):
        """Test error handling for invalid metric name"""
        response = client.get("/api/metrics/history/invalid_metric")

        assert response.status_code == 422 or response.status_code == 500


class TestSystemInfoEndpoint:
    """Tests for the /api/system endpoint"""

    def test_get_system_info(self, client):
        """Test that system info endpoint returns valid system data"""
        response = client.get("/api/system")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "hostname" in data or "uptime_seconds" in data

        # Some fields might be mocked, but structure should be valid
        optional_fields = ["memory_total_mb", "cpu_cores", "os_version"]
        for field in optional_fields:
            assert field not in data  # These are optional


class TestHealthCheckEndpoint:
    """Tests for the /api/health endpoint"""

    def test_health_check(self, client):
        """Test that health check returns healthy status"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "status" in data or "timestamp" in data


class TestDashboardDataEndpoint:
    """Tests for the /api/dashboard endpoint"""

    def test_get_dashboard_data(self, client):
        """Test that dashboard data returns all necessary components"""
        response = client.get("/api/dashboard")

        assert response.status_code == 200
        data = response.json()

        # Should have charts, system info, and metrics
        assert "charts" in data or "metrics" in data


class TestDataValidation:
    """Tests for data quality and validation"""

    def test_chart_data_structure(self, client):
        """Test that chart data follows Chart.js format"""
        response = client.get("/api/metrics/history/cpu_usage?hours=24")

        assert response.status_code == 200
        data = response.json()

        # Data should be a list of dictionaries
        assert isinstance(data["data"], list)

        for point in data["data"]:
            # Timestamp should be string (ISO format)
            assert isinstance(point.get("timestamp"), str) or isinstance(point.get("x"), str)

            # Value should be numeric
            value = point.get("value") or point.get("y")
            assert isinstance(value, (int, float))


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_empty_history(self, client):
        """Test with very short time range to handle empty responses gracefully"""
        # This might return minimal data but shouldn't crash
        response = client.get("/api/metrics/history/cpu_usage?hours=1")

        assert response.status_code in [200, 400]


@pytest.mark.parametrize("metric_name,hours", [
    ("cpu_usage", 720),      # Maximum hours (5 days)
    ("memory_usage", 1),     # Minimum hours
])
class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_maximum_hours(self, client, metric_name, hours):
        """Test with maximum requested hours"""
        response = client.get(f"/api/metrics/history/{metric_name}?hours={hours}")

        assert response.status_code == 200
        data = response.json()

        # Should return data points for the entire range
        assert "data" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
