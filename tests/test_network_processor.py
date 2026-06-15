from datetime import datetime, timezone

import pytest

from pymon.processors.network_processor import NetworkProcessor


@pytest.fixture
def network_processor():
    return NetworkProcessor(metric_name="network", config={"interval": "1s"})


def test_processor_identification(network_processor):
    assert network_processor.get_supported_metric_types() == "network"
    assert network_processor.metric_name == "Network Throughput"


def test_process_batch_success(network_processor):
    raw_metrics = [
        {
            "timestamp": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            "bytes_in": 5000,
            "bytes_out": 3000,
            "target": "server-web-01",
        },
        {
            "timestamp": datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
            "bytes_in": 10000,
            "bytes_out": 6000,
            "target": "server-db-02",
        },
    ]

    processed = network_processor.process_batch(raw_metrics)

    assert len(processed) == 2
    assert processed[0]["ingress_rate_bps"] == 5000.0
    assert processed[0]["egress_rate_bps"] == 3000.0
    assert processed[0]["source"] == "server-web-01"
    assert processed[1]["ingress_rate_bps"] == 10000.0
    assert processed[1]["egress_rate_bps"] == 6000.0
    assert processed[1]["source"] == "server-db-02"


def test_process_batch_skips_invalid_points(network_processor):
    raw_metrics = [
        {
            "timestamp": datetime.now(timezone.utc),
            "bytes_in": 5000,
            "bytes_out": 3000,
            "target": "valid",
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "bytes_in": None,
            "bytes_out": 3000,
            "target": "missing-ingress",
        },
    ]

    processed = network_processor.process_batch(raw_metrics)

    assert len(processed) == 1
    assert processed[0]["source"] == "valid"


def test_calculate_derived_metrics(network_processor):
    result = network_processor.calculate_derived_metrics(
        [
            {"ingress_rate_bps": 10, "egress_rate_bps": 5},
            {"ingress_rate_bps": 20, "egress_rate_bps": 10},
            {"ingress_rate_bps": 30, "egress_rate_bps": 15},
        ]
    )

    assert result["moving_average_bps"] == 30.0
    assert result["total_data_points_analyzed"] == 3
