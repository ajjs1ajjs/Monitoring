from datetime import datetime, timezone

import pytest

from pymon.processors.disk_processor import DiskProcessor


@pytest.fixture
def disk_processor():
    return DiskProcessor(metric_name="disk", config={"unit": "bytes"})


def test_processor_identification(disk_processor):
    assert disk_processor.get_supported_metric_types() == "disk"
    assert disk_processor.metric_name == "Disk Usage"


def test_process_batch_success(disk_processor):
    raw_metrics = [
        {
            "timestamp": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            "total_bytes": 1000 * 1024**3,
            "used_bytes": 750 * 1024**3,
            "target": "server-web-01",
        },
        {
            "timestamp": datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
            "total_bytes": 500 * 1024**3,
            "used_bytes": 50 * 1024**3,
            "target": "server-db-02",
        },
    ]

    processed = disk_processor.process_batch(raw_metrics)

    assert len(processed) == 2
    assert processed[0]["usage_percent"] == 75.0
    assert processed[0]["source"] == "server-web-01"
    assert processed[1]["usage_percent"] == 10.0
    assert processed[1]["source"] == "server-db-02"


def test_process_batch_skips_invalid_points(disk_processor):
    raw_metrics = [
        {
            "timestamp": datetime.now(timezone.utc),
            "total_bytes": 200 * 1024**3,
            "used_bytes": 50 * 1024**3,
            "target": "valid",
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "total_bytes": None,
            "used_bytes": 10 * 1024**3,
            "target": "missing-total",
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "total_bytes": 0,
            "used_bytes": 0,
            "target": "zero-total",
        },
    ]

    processed = disk_processor.process_batch(raw_metrics)

    assert len(processed) == 1
    assert processed[0]["source"] == "valid"
    assert processed[0]["usage_percent"] == 25.0


def test_calculate_derived_metrics(disk_processor):
    result = disk_processor.calculate_derived_metrics(
        [
            {"usage_percent": 10},
            {"usage_percent": 20},
            {"usage_percent": 30},
            {"usage_percent": 40},
            {"usage_percent": 50},
        ]
    )

    assert result["moving_average_5min"] == 30.0
    assert result["total_data_points_analyzed"] == 5
