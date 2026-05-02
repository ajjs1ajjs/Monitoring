import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
import statistics

# Assuming the processor class and utility types are accessible via relative imports in the test environment.
from pymon.processors.disk_processor import DiskProcessor


@pytest.fixture(scope="module")
def disk_processor():
    """Fixture to provide a fresh instance of the DiskProcessor for testing."""
    # Initialize with minimal configuration since it's not strictly needed for core logic tests
    return DiskProcessor(metric_name="disk", config={"unit": "bytes"})


class TestDiskProcessor:
    """
    Comprehensive unit tests suite for validating the DiskProcessor module.
    Focuses on transformation correctness and derived metric accuracy.
    """

    def test_processor_identification(self, disk_processor):
        """Tests that the processor correctly identifies its supported metric type."""
        assert disk_processor.get_supported_metric_types() == "disk"

    @pytest.mark.parametrize("config", [{}, {"unit": "gb"}])
    def test_initialization(self, disk_processor, config):
        """Tests that the processor can be initialized with various configurations."""
        # Re-initialize to ensure configuration parameter handling is correct
        processor = DiskProcessor(metric_name="disk", config=config)
        assert processor.metric_name == "Disk Usage"

    def test_process_batch_success(self, disk_processor):
        """
        Tests the successful transformation of a batch of valid raw metrics.
        Verifies that percentages are calculated correctly and output is standardized.
        """
        # Simulate 3 clean data points from different servers/targets
        raw_metrics: List[Dict] = [
            {
                "timestamp": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                "total_bytes": 1000.0 * 1024**3,  # 1 TB total
                "used_bytes": 750.0 * 1024**3,    # 750 GB used
                "source": "server-web-01"
            },
            {
                "timestamp": datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
                "total_bytes": 500 * 1024**3,      # 500 GB total
                "used_bytes": 50.0 * 1024**3,     # 50 GB used (10% usage)
                "source": "server-db-02"
            },
        ]

        processed = disk_processor.process_batch(raw_metrics)

        assert len(processed) == 2

        # Check the first record's calculation: (750/1000) * 100 = 75.0%
        first_record = processed[0]
        assert abs(first_record["usage_percent"] - 75.0) < 1e-6
        assert first_record["source"] == "server-web-01"
        # Check the second record's calculation: (50/500) * 100 = 10.0%
        second_record = processed[1]
        assert abs(second_record["usage_percent"] - 10.0) < 1e-6
        assert second_record["source"] == "server-db-02"

    def test_process_batch_edge_cases(self, disk_processor):
        """Tests batch processing with invalid or incomplete data points."""
        raw_metrics: List[Dict] = [
            # 1. Valid record
            {"timestamp": datetime.now(timezone.utc), "total_bytes": 200 * 1024**3, "used_bytes": 50 * 1024**3, "source": "valid"},
            # 2. Invalid: Missing total bytes (should skip)
            {"timestamp": datetime.now(timezone.utc), "total_bytes": None, "used_bytes": 10 * 1024**3, "source":
