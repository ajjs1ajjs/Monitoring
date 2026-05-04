import statistics
from typing import Any, Dict, List, Optional

# Assuming this relative import path is correct based on previous actions
from ..services.metric_processor import MetricProcessor, RawMetricPoint


class DiskProcessor(MetricProcessor):
    """
    Concrete processor for disk usage metrics.

    Handles raw data about total size, used space, and free space (or partition breakdowns)
    and calculates derived metrics like overall utilization percentage and trend analysis.
    """

    def __init__(self, metric_name: str = "disk", config: Optional[Dict] = None):
        """
        Initializes the Disk processor.

        Args:
            metric_name: The identifier for this processor.
            config: Configuration dictionary, expected to contain 'unit' (e.g., 'gb') or aggregation settings.
        """
        super().__init__(metric_name, config)
        self.metric_name = "Disk Usage"  # Human-readable name for logs/dashboard

    def get_supported_metric_types(self) -> str:
        """Returns the unique type identifier for Disk metrics."""
        return "disk"

    def process_batch(self, raw_metrics: List[RawMetricPoint]) -> List[Dict]:
        """
        Processes a batch of incoming raw metric data points.

        Standardizes disk usage by calculating overall utilization percentage
        and structure the data to include partition breakdowns if available.
        """
        processed_results = []
        for point in raw_metrics:
            raw_total: Optional[float] = point.get("total_bytes")
            raw_used: Optional[float] = point.get("used_bytes")

            usage_percent: Optional[float] = None

            if raw_total and raw_used and raw_total > 0:
                # Calculate overall utilization percentage based on total/used
                usage_percent = (raw_used / raw_total) * 100.0
            else:
                print(f"[WARNING] Skipped invalid disk reading at {point.get('timestamp')}. Missing bytes data.")

            if usage_percent is not None:
                processed_results.append(
                    {
                        "timestamp": point["timestamp"],
                        "usage_percent": float(usage_percent),  # Standardize output as percentage
                        "total_bytes": raw_total,
                        "used_bytes": raw_used,
                        "source": point.get("target"),
                        # In a real system, we might add a 'partitions' list here for detailed breakdown
                    }
                )

        return processed_results

    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:  # type: ignore
        """
        Calculates derived metrics (Moving Average and Standard Deviation) based on disk utilization history.

        Args:
            historical_data: A list of raw points representing disk usage history.

        Returns:
            A dictionary containing the calculated statistics, or None if insufficient data.
        """
        if len(historical_data) < 2:
            return {"message": "Insufficient historical data to calculate derived metrics."}

        # 1. Extract all valid percentage readings from the history
        values = []
        for point in historical_data:
            raw_value = None
            # Attempt to extract percentage regardless of the raw data structure used during scraping
            if "usage_percent" in point and isinstance(point["usage_percent"], (float, int)):
                raw_value = float(point["usage_percent"])
            elif "value" in point and isinstance(point["value"], (float, int)):
                raw_value = float(point["value"])

            if raw_value is not None:
                values.append(raw_value)

        # 2. Calculate Moving Average and Standard Deviation
        num_points_for_stats = min(len(values), 5)

        if num_points_for_stats >= 2:
            avg = sum(values[-num_points_for_stats:]) / num_points_for_stats
            moving_average = round(avg, 2)
        else:
            moving_average = None

        try:
            stdev = statistics.stdev(values[:num_points_for_stats])
        except statistics.StatisticsError:
            stdev = 0.0  # Happens if all values are the same or list is too short

        return {
            "moving_average_5min": moving_average,
            "standard_deviation": round(stdev, 2),
            "total_data_points_analyzed": len(values),
        }

    def get_supported_metric_types(self) -> str:  # type: ignore
        """Returns the unique type identifier for Disk metrics."""
        return "disk"
