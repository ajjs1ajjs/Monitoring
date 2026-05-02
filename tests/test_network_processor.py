import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
import statistics

# Assuming the processor class is available from the local structure
from pymon.processors.network_processor import NetworkProcessor


@pytest.fixture(scope="module")
def network_processor():
    """Fixture to provide a fresh instance of the NetworkProcessor for testing."""
    return NetworkProcessor(metric_name="network", config={"interval": "1s"})


class TestNetworkProcessor:
    """
    Comprehensive unit tests suite for validating the NetworkProcessor module.
    Focuses on transformation correctness (bytes->rate) and derived metric accuracy.
    """

    def test_processor_identification(self, network_processor):
        """Tests that the processor correctly identifies its supported metric type."""
        assert network_processor.get_supported_metric_types() == "network"

    @pytest.mark.parametrize("config", [{}, {"interval": "30s"}])
    def test_initialization(self, network_processor, config):
        """Tests that the processor can be initialized with various configurations."""
        # Re-initialize to ensure configuration parameter handling is correct
        processor = NetworkProcessor(metric_name="network", config=config)
        assert processor.metric_name == "Network Throughput"

    def test_process_batch_success(self, network_processor):
        """
        Tests the successful transformation of a batch of valid raw metrics.
        Verifies that throughput rates are calculated correctly and output is standardized.
        """
        # Simulate 3 data points showing increasing byte counts (cumulative) over time
        raw_metrics: List[Dict] = [
            {
                "timestamp": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                "bytes_in": 5000.0,  # Starting cumulative bytes in (B)
                "bytes_out": 3000.0, # Starting cumulative bytes out (B)
                "target": "server-web-01"
            },
            {
                "timestamp": datetime(2024, 1, 1, 10, 5
