"""Tests for PyMon"""

import pytest

from pymon.metrics.collector import Counter, Gauge, Histogram, registry
from pymon.metrics.models import Label, MetricType


@pytest.fixture(autouse=True)
def clear_registry():
    registry._metrics.clear()
    registry._series.clear()
    yield


def test_counter():
    counter = Counter("test_counter", "Test counter")
    counter.inc()
    counter.inc(5)

    metric = registry.get_metric("test_counter")
    assert metric is not None
    assert metric.value == 6


def test_gauge():
    gauge = Gauge("test_gauge", "Test gauge")
    gauge.set(100)
    assert registry.get_metric("test_gauge").value == 100

    gauge.inc(10)
    assert registry.get_metric("test_gauge").value == 110

    gauge.dec(20)
    assert registry.get_metric("test_gauge").value == 90


def test_labels():
    gauge = Gauge("http_requests", "HTTP requests", labels=[Label("method", "GET")])
    gauge.set(100, [Label("path", "/api")])

    metric = registry.get_metric("http_requests", [Label("method", "GET"), Label("path", "/api")])
    assert metric is not None
    assert metric.value == 100


def test_histogram():
    hist = Histogram("request_duration", "Request duration")
    hist.observe(0.1)
    hist.observe(0.2)

    metric = registry.get_metric("request_duration")
    assert metric is not None


def test_prometheus_export():
    counter = Counter("requests_total", "Total requests")
    counter.inc(10)

    gauge = Gauge("memory_bytes", "Memory usage")
    gauge.set(1024)

    output = registry.export_prometheus()
    assert "requests_total" in output
    assert "memory_bytes" in output
    assert "10" in output
    assert "1024" in output
