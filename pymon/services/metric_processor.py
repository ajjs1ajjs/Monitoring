from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Define a standardized structure for raw metric data points
RawMetricPoint = Dict[str, Any]


class MetricProcessor(ABC):
    """
    Abstract Base Class (Interface) for all metric processing handlers.

    This interface enforces a standard contract for converting raw scraped
    metrics into structured, derived, or analyzed data ready for storage
    or dashboard visualization. Implementing this class decouples the
    data processing logic from the core monitoring scheduler and API layer.
    """

    def __init__(self, metric_name: str, config: Optional[Dict] = None):
        """
        Initializes the processor with a specific metric name or type.

        Args:
            metric_name: The identifier for the metrics this processor handles (e.g., 'cpu_usage', 'disk_io').
            config: Optional dictionary of configuration parameters needed (e.g., aggregation windows).
        """
        self.metric_name = metric_name
        self.config = config if config is not None else {}

    @abstractmethod
    def process_batch(self, raw_metrics: List[RawMetricPoint]) -> List[Dict]:
        """
        Processes a batch of incoming raw metric data points.

        This method should perform basic cleaning, validation, and immediate
        transformation (e.g., converting units or aggregating simple values).

        Args:
            raw_metrics: A list of dictionaries, where each dict represents a
                          single scraped metric point from an exporter.
                          Expected structure: [{'metric': '...', 'value': X, 'timestamp': T}, ...]

        Returns:
            A list of processed and standardized metrics ready for storage or display.
            Each dictionary in the returned list should be consistent.
        """
        raise NotImplementedError("Subclasses must implement process_batch method.")

    @abstractmethod
    def calculate_derived_metrics(self, historical_data: List[RawMetricPoint]) -> Optional[Dict]:
        """
        Calculates advanced or derived metrics based on historical data.

        This is used for calculations that require looking at trends over time,
        such as standard deviation, moving averages, rate-of-change (RoC),
        or complex threshold analysis. The 'historical_data' list should
        contain enough context for the calculation to proceed.

        Args:
            historical_data: A list of raw metric points representing historical time series data.

        Returns:
            A dictionary containing derived metrics, or None if calculation is not possible/applicable.
        """
        raise NotImplementedError("Subclasses must implement calculate_derived_metrics method.")

    @abstractmethod
    def get_supported_metric_types(self) -> str:
        """
        Returns a descriptive string identifying the type of metric this processor handles.
        Useful for logging and routing within the core scheduler.
        """
        raise NotImplementedError("Subclasses must implement get_supported_metric_types method.")

    # --- Utility Methods (Optional, but good practice) ---

    def is_configured(self) -> bool:
        """Checks if the processor has necessary configuration to run."""
        return bool(self.config)
