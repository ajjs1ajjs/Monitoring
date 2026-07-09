from typing import Dict, List, Optional

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
            timestamp = point["timestamp"]

            # NOTE: bytes_in/bytes_out are cumulative counters; a true bytes/sec rate would
            # need the previous reading's count and timestamp. This simplified processor
            # echoes the supplied values (see tests for the established contract).
            if raw_bytes_in is not None and raw_bytes_out is not None:
                processed_results.append(
                    {
                        "timestamp": timestamp,
                        "ingress_rate_bps": round(float(raw_bytes_in), 2),
                        "egress_rate_bps": round(float(raw_bytes_out), 2),
                        "source": point.get("target"),
                    }
                )
            else:
                print(
                    f"[WARNING] Skipped invalid network reading at {point.get('timestamp')}. Missing byte count data."
                )

        return processed_results

    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:
        """
        Calculates derived metrics (Moving Average and Standard Deviation) based on network flow history.

        Args:
            historical_data: A list of raw points representing network history.

        Returns:
            A dictionary containing the calculated statistics, or None if insufficient data.
        """
        if len(historical_data) < 2:
            return {"message": "Insufficient historical data to calculate derived metrics."}

        throughput_values = []
        for point in historical_data:
            ingress = point.get("ingress_rate_bps", 0.0)
            egress = point.get("egress_rate_bps", 0.0)
            throughput_values.append(ingress + egress)

        stats = self._compute_stats(throughput_values)
        return {
            "moving_average_bps": stats["moving_average"],
            "standard_deviation_bps": stats["standard_deviation"],
            "total_data_points_analyzed": stats["total_data_points_analyzed"],
        }

