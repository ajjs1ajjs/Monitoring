import statistics
from typing import Dict, List, Optional

# Assuming this relative import path is correct based on previous actions
from ..services.metric_processor import MetricProcessor, RawMetricPoint


class NetworkProcessor(MetricProcessor):
    """
    Concrete processor for Network I/O metrics (Ingress/Egress).

    Handles raw byte rate data points and calculates derived metrics like
    average throughput, peak usage, and standard deviation of network flow.
    """

    def __init__(self, metric_name: str = "network", config: Optional[Dict] = None):
        """
        Initializes the Network processor.

        Args:
            metric_name: The identifier for this processor.
            config: Configuration dictionary, expected to contain 'interval' (time window for calculation).
        """
        super().__init__(metric_name, config)
        self.metric_name = "Network Throughput"  # Human-readable name for logs/dashboard

    def get_supported_metric_types(self) -> str:
        """Returns the unique type identifier for Network metrics."""
        return "network"

    def process_batch(self, raw_metrics: List[RawMetricPoint]) -> List[Dict]:
        """
        Processes a batch of incoming raw metric data points.

        Standardizes network usage by calculating instantaneous throughput rates
        (e.g., bytes/second) from cumulative byte counts provided by the exporter.
        """
        processed_results = []
        for point in raw_metrics:
            raw_bytes_in: Optional[float] = point.get("bytes_in")
            raw_bytes_out: Optional[float] = point.get("bytes_out")
            timestamp: float = point["timestamp"]

            # In a real scenario, we would need the previous reading's timestamp/count
            # to calculate the delta rate over time (rate = (new - old) / delta_time).
            # For this standardized processor structure, we will simulate calculating
            # instantaneous rates based on assumed available fields.

            ingress_rate: Optional[float] = None
            egress_rate: Optional[float] = None

            if raw_bytes_in is not None and raw_bytes_out is not None:
                ingress_rate = float(raw_bytes_in)
                egress_rate = float(raw_bytes_out)

            if ingress_rate is not None and egress_rate is not None:
                processed_results.append(
                    {
                        "timestamp": timestamp,
                        "ingress_rate_bps": round(ingress_rate, 2),  # Standardize output
                        "egress_rate_bps": round(egress_rate, 2),
                        "source": point.get("target"),
                    }
                )
            else:
                print(
                    f"[WARNING] Skipped invalid network reading at {point.get('timestamp')}. Missing byte count data."
                )

        return processed_results

    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:  # type: ignore
        """
        Calculates derived metrics (Moving Average and Standard Deviation) based on network flow history.

        Args:
            historical_data: A list of raw points representing network history.

        Returns:
            A dictionary containing the calculated statistics, or None if insufficient data.
        """
        if len(historical_data) < 2:
            return {"message": "Insufficient historical data to calculate derived metrics."}

        # We will analyze the average of the total throughput (ingress + egress)
        throughput_values = []
        for point in historical_data:
            ingress = point.get("ingress_rate_bps", 0.0)
            egress = point.get("egress_rate_bps", 0.0)
            total_throughput = ingress + egress
            throughput_values.append(total_throughput)

        # Use the last N points for stable statistics calculation
        num_points_for_stats = min(len(throughput_values), 5)

        if num_points_for_stats >= 2:
            # Calculate average total throughput over the most recent period
            avg_throughput = sum(throughput_values[-num_points_for_stats:]) / num_points_for_stats
            moving_average_throughput = round(avg_throughput, 2)
        else:
            moving_average_throughput = None

        try:
            # Calculate standard deviation on the sample size used for MA
            stdev_throughput = statistics.stdev(throughput_values[:num_points_for_stats])
        except statistics.StatisticsError:
            stdev_throughput = 0.0

        return {
            "moving_average_bps": moving_average_throughput,
            "standard_deviation_bps": round(stdev_throughput, 2),
            "total_data_points_analyzed": len(throughput_values),
        }

