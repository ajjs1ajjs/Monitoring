"""Metrics business logic module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymon.config import PyMonConfig


@dataclass
class MetricRecord:
    """A single metric record."""

    name: str
    value: float
    labels: dict[str, str] = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.labels is None:
            self.labels = {}


class IMetricsProcessor(ABC):
    """Abstract base class for metrics processors."""

    @abstractmethod
    async def process(self, config: PyMonConfig) -> None:
        """Process collected metric data.

        Args:
            config: The application configuration.
        """
        pass

    @abstractmethod
    async def collect(self, target_url: str, timeout: int = 10) -> list[MetricRecord]:
        """Collect metrics from a target URL.

        Args:
            target_url: The Prometheus scrape endpoint URL.
            timeout: Request timeout in seconds.

        Returns:
            List of metric records parsed from the response.
        """
        pass


class DefaultMetricsProcessor(IMetricsProcessor):
    """Default implementation using prometheus_client."""

    def __init__(self, config: PyMonConfig) -> None:
        self.config = config
        self.processed_count = 0

    async def collect(self, target_url: str, timeout: int = 10) -> list[MetricRecord]:
        """Collect and parse metrics from a Prometheus exporter."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(target_url)
                response.raise_for_status()
                # Parse Prometheus text format here (simplified for now)
                pass
        except Exception as e:
            print(f"Failed to collect metrics from {target_url}: {e}")

        return []


class MetricsAggregator(IMetricsProcessor):
    """Aggregate multiple metric sources."""

    def __init__(self, config: PyMonConfig) -> None:
        self.config = config
        self.processors: list[IMetricsProcessor] = []

    async def add_processor(self, processor: IMetricsProcessor) -> None:
        """Add a metrics processor to the aggregation pipeline."""
        self.processors.append(processor)

    async def process(self, target_url: str, timeout: int = 10) -> list[MetricRecord]:
        """Process all registered processors and aggregate results.

        Args:
            target_url: The metrics endpoint URL.
            timeout: Request timeout in seconds.

        Returns:
            Aggregated list of metric records from all processors.
        """
        all_records: list[MetricRecord] = []
        for processor in self.processors:
            try:
                records = await processor.collect(target_url, timeout)
                all_records.extend(records)
            except Exception as e:
                print(f"Processor error: {processor.__class__.__name__}: {e}")

        self.processed_count += len(all_records)
        return all_records
