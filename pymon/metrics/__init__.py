"""
NOTE: This module is DEPRECATED. The actual metric processing pipeline
uses pymon/metrics/collector.py (MetricsRegistry + prometheus_client format).
METRIC_REGISTRY here is not integrated into the scrape/API flow.
"""

from typing import Any, Dict, List

from ..services.metric_processor import MetricProcessor


class MetricRegistry:
    """
    A singleton-like registry holding all active and available metric processors.

    It acts as a central hub to manage data flow from raw metrics (scraped)
    to processed, standardized formats.
    """

    def __init__(self):
        # Dictionary mapping metric type names to their corresponding processor instance
        self._processors: Dict[str, MetricProcessor] = {}

    @property
    def processors(self) -> List[MetricProcessor]:
        """Returns all registered metric processor instances."""
        return list(self._processors.values())

    def register_processor(self, processor: MetricProcessor):
        """Registers a new concrete MetricProcessor instance."""
        metric_type = processor.get_supported_metric_types()
        if metric_type in self._processors:
            print(f"[WARNING] Overwriting existing processor for type: {metric_type}")
        self._processors[metric_type] = processor

    def process_all_metrics(self, raw_data_batch: List[Dict]) -> Dict[str, Any]:
        """
        Iterates over all registered processors and runs the batch processing logic.

        Args:
            raw_data_batch: A list of dictionaries containing raw metric points
                            scraped from exporters (e.g., [{"metric": "cpu", "value": 0.5, "timestamp": T}, ...]).

        Returns:
            A dictionary containing the results from all processors, keyed by metric type.
        """
        processed_results: Dict[str, Any] = {}

        print("\n[Metrics Processor] Starting batch processing for metrics...")

        # Group raw data by a key field (e.g., 'metric' name) to pass it efficiently
        grouped_raw_data: Dict[str, List[Dict]] = {}
        for item in raw_data_batch:
            metric_key = item.get("metric")  # Assuming 'metric' identifies the type
            if metric_key:
                if metric_key not in grouped_raw_data:
                    grouped_raw_data[metric_key] = []
                grouped_raw_data[metric_key].append(item)

        # Process each registered processor using the relevant subset of raw data
        for processor in self.processors:
            metric_type = processor.get_supported_metric_types()
            if metric_type not in grouped_raw_data:
                print(f"  [SKIP] No raw data found for '{metric_type}'.")
                continue

            raw_metrics_for_processor = grouped_raw_data[metric_type]

            # 1. Process Batch (Clean/Transform)
            try:
                processed_batch = processor.process_batch(raw_metrics_for_processor)

                # 2. Calculate Derived Metrics (Advanced Analysis)
                # We pass the raw data as a source for historical analysis
                derived_data = processor.calculate_derived_metrics(historical_data=raw_metrics_for_processor)  # type: ignore

                processed_results[metric_type] = {
                    "processed": processed_batch,
                    "derived": derived_data,
                    "status": "SUCCESS",
                }
            except Exception as e:
                # Handle exceptions gracefully for a single processor failure
                print(f"  [ERROR] Failed to process '{metric_type}' metrics. Error: {e}")
                processed_results[metric_type] = {"error": str(e), "status": "FAILED"}

        print("[Metrics Processor] Batch processing complete.")
        return processed_results


# Global registry instance
METRIC_REGISTRY = MetricRegistry()


def register_cpu_processor():
    """Utility function to instantiate and register the CPU processor."""
    from pymon.processors.cpu_processor import CpuProcessor

    cpu_proc = CpuProcessor(metric_name="cpu", config={"aggregation": "percent"})
    METRIC_REGISTRY.register_processor(cpu_proc)


def register_memory_processor():
    """Utility function to instantiate and register the Memory processor."""
    from pymon.processors.memory_processor import MemoryProcessor

    mem_proc = MemoryProcessor(metric_name="memory", config={"aggregation": "bytes"})
    METRIC_REGISTRY.register_processor(mem_proc)


# Expose the global registry instance and utility functions for external use in other modules
__all__ = ["METRIC_REGISTRY"]
