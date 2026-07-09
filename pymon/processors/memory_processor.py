from typing import Dict, List, Optional

from ..services.metric_processor import MetricProcessor, RawMetricPoint


class MemoryProcessor(MetricProcessor):
    """
    Concrete processor for memory utilization metrics (RAM).

    Handles raw physical/virtual memory usage data and calculates derived metrics
    like average utilization percentage and trend analysis.
    """

    def __init__(self, metric_name: str = "memory", config: Optional[Dict] = None):
        """
        Initializes the Memory processor.

        Args:
            metric_name: The identifier for this processor.
            config: Configuration dictionary, expected to contain 'unit' (e.g., 'bytes') or aggregation settings.
        """
        super().__init__(metric_name, config)
        self.metric_name = "Memory Usage"  # Human-readable name for logs/dashboard

    def get_supported_metric_types(self) -> str:
        """Returns the unique type identifier for Memory metrics."""
        return "memory"

    def process_batch(self, raw_metrics: List[RawMetricPoint]) -> List[Dict]:
        """
        Processes a batch of incoming raw metric data points.

        Standardizes memory usage by calculating percentage and ensuring consistent output structure.
        Assumes that the raw metrics provide enough context (e.g., total bytes and used bytes)
        or a direct utilization value.
        """
        processed_results = []
        for point in raw_metrics:
            # Assuming raw metrics might contain 'total_bytes' and 'used_bytes' fields,
            # which is common for OS exporters.
            raw_total: Optional[float] = point.get("total_bytes")
            raw_used: Optional[float] = point.get("used_bytes")

            usage_percent: Optional[float] = None

            if raw_total is not None and raw_used is not None and raw_total > 0:
                # Calculate percentage from absolute bytes (most reliable method)
                usage_percent = (raw_used / raw_total) * 100.0
            elif isinstance(point.get("value"), (int, float)) and 0 <= point["value"] <= 100:
                # Fallback if exporter provides a pre-calculated percentage
                usage_percent = point["value"]
            else:
                print(f"[WARNING] Skipped invalid memory reading at {point.get('timestamp')}. Missing bytes data.")

            if usage_percent is not None:
                processed_results.append(
                    {
                        "timestamp": point["timestamp"],
                        "usage_percent": float(usage_percent),  # Standardize output as percentage
                        "total_bytes": raw_total,
                        "used_bytes": raw_used,
                        "source": point.get("target"),
                    }
                )

        return processed_results

    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:
        """
        Calculates derived metrics (e.g., Moving Average and Standard Deviation).

        Args:
            historical_data: A list of raw points representing memory history.

        Returns:
            A dictionary containing the calculated statistics, or None if insufficient data.
        """
        if len(historical_data) < 2:
            return {"message": "Insufficient historical data to calculate derived metrics."}

        values = []
        for point in historical_data:
            raw_value = None
            if "usage_percent" in point and isinstance(point["usage_percent"], (float, int)):
                raw_value = float(point["usage_percent"])
            elif "value" in point and isinstance(point["value"], (float, int)):
                raw_value = float(point["value"])
            if raw_value is not None:
                values.append(raw_value)

        stats = self._compute_stats(values)
        return {
            "moving_average_5min": stats["moving_average"],
            "standard_deviation": stats["standard_deviation"],
            "total_data_points_analyzed": stats["total_data_points_analyzed"],
        }

