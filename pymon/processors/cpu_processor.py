import statistics
from typing import Dict, List, Optional

# Assuming this relative import path is correct based on previous actions
from ..services.metric_processor import MetricProcessor, RawMetricPoint


class CpuProcessor(MetricProcessor):
    """
    Concrete processor for CPU utilization metrics.

    Handles raw CPU usage percentages and calculates derived metrics like
    Moving Average (MA) over a specified time window.
    """

    def __init__(self, metric_name: str = "cpu", config: Optional[Dict] = None):
        """
        Initializes the CPU processor.

        Args:
            metric_name: The identifier for this processor.
            config: Configuration dictionary, expected to contain 'ma_window' (moving average window).
        """
        super().__init__(metric_name, config)
        self.metric_name = "CPU Utilization"  # Human-readable name for logs/dashboard

    def get_supported_metric_types(self) -> str:
        """Returns the unique type identifier for CPU metrics."""
        return "cpu"

    def process_batch(self, raw_metrics: List[RawMetricPoint]) -> List[Dict]:
        """
        Processes a batch of incoming raw metric data points.

        Performs basic validation and standardizes output to ensure
        'usage_percent' is correctly extracted.
        """
        processed_results = []
        for point in raw_metrics:
            # Assuming the raw value is available, and we validate its type
            raw_value = point.get("value")

            if isinstance(raw_value, (int, float)) and 0 <= raw_value <= 100:
                processed_results.append(
                    {
                        "timestamp": point["timestamp"],
                        "usage_percent": float(raw_value),  # Standardize output as float percentage
                        "source": point.get("target"),  # Useful for debugging which server generated it
                    }
                )
            else:
                print(f"[WARNING] Skipped invalid CPU reading at {point.get('timestamp')}: Value was {raw_value}")

        return processed_results

    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:  # type: ignore
        """
        Calculates derived metrics (e.g., Moving Average and Standard Deviation).

        Args:
            historical_data: A list of raw points representing history for this metric type.

        Returns:
            A dictionary containing the calculated statistics, or None if insufficient data.
        """
        if len(historical_data) < 2:
            return {"message": "Insufficient historical data to calculate derived metrics."}

        # 1. Extract all valid percentage readings from the history
        values = []
        for point in historical_data:
            raw_value = point.get("value")
            if isinstance(raw_value, (int, float)):
                values.append(float(raw_value))

        # 2. Calculate Moving Average (Simple implementation for demonstration)
        # In a real system, this would use the 'ma_window' from config and specialized time series libraries.
        if len(values) >= 5:  # Require at least 5 points for meaningful average calculation
            avg = sum(values[-5:]) / min(len(values), 5)
            moving_average = round(avg, 2)
        else:
            moving_average = None

        # 3. Calculate Standard Deviation
        try:
            stdev = statistics.stdev(values)
        except statistics.StatisticsError:
            stdev = 0.0  # Happens if all values are the same or list is too short

        return {
            "moving_average_5min": moving_average,
            "standard_deviation": round(stdev, 2),
            "total_data_points_analyzed": len(values),
        }

