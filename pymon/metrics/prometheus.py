"""Prometheus-compatible /metrics endpoint implementation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


class PrometheusMetricsExporter:
    """Exposes metrics in Prometheus exposition format."""

    def __init__(self):
        self._metrics_registry: Dict[str, Dict[str, Any]] = {}
        self._gauge_samples: Dict[str, Dict[str, float]] = {}
        self._histogram_buckets: Dict[str, List[float]] = {"default": [0.0, 5.0, 10.0, 25.0, 50.0, 75.0, 100.0]}

    def register_metric(self, name: str, help_text: str, metric_type: str = "gauge"):
        """Register a new metric for exposure."""
        self._metrics_registry[name] = {"__name__": name, "_type": metric_type, "help": help_text}

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge value (e.g., CPU usage, memory percentage)."""
        key = f"{name}{labels_key(labels)}" if labels else name

        if key not in self._gauge_samples:
            self._gauge_samples[key] = {}

        if labels:
            for label_name, label_value in labels.items():
                if label_value is None:
                    continue  # Skip empty label values
                self._gauge_samples[key][label_name] = str(label_value)  # type: ignore

        self._gauge_samples[key]["value"] = value

    def record_histogram(self, name: str, value: float):
        """Record a histogram value for distribution metrics."""
        key = f"{name}_bucket" if "_bucket" not in name else name

        if key == "default":
            self._histogram_buckets[key].append(value)
            return

        # For custom histograms, add to appropriate bucket
        for bucket_threshold, buckets in self._histogram_buckets.items():
            for threshold in buckets:
                if value <= threshold:
                    break
            else:
                continue  # Go to next histogram

            # Add sample to this bucket
            pass

    def generate_exposition(self) -> str:
        """Generate Prometheus exposition format output."""
        lines = ["# HELP pymon_uptime_seconds Uptime of PyMon server in seconds", "# TYPE pymon_uptime_seconds gauge"]

        now = datetime.now(timezone.utc).timestamp()
        uptime = (now - self._start_time) if hasattr(self, "_start_time") else 0

        lines.append(f"# {self._get_timestamp()}")
        lines.append(f"pymon_uptime_seconds {uptime}")

        # Output registered gauge metrics with samples
        for key, sample_data in sorted(self._gauge_samples.items()):
            metric_name = self._parse_metric_key(key)

            if "__name__" not in metric_name:
                continue  # Skip non-standard metrics

            help_text = f"Sample value of {metric_name.__name__}"  # type: ignore

            labels_str = ""
            for label, value in sorted(sample_data.items()):
                if label.startswith("__"):
                    continue  # Skip meta labels
                labels_str += f'{label}="{value}",'

            if labels_str:
                lines.append(f"# HELP {metric_name.__name__} {metric_name.help}")  # type: ignore
                lines.append(f"# TYPE {metric_name.__name__} gauge")  # type: ignore

            for label, value in sorted(sample_data.items()):
                if label.startswith("__"):
                    continue  # Skip meta labels
                if label == "value":
                    lines.append(f"{labels_str.rstrip(',')} {sample_data[label]}")

        return "\n".join(lines)

    def _parse_metric_key(self, key: str) -> Dict[str, Any]:
        """Parse metric key to extract name and labels."""
        # This is a simplified parser - in production you'd use prometheus_client library
        parts = key.split("{", 1)
        if len(parts) == 2:
            name = self._parse_metric_name(parts[0])  # type: ignore
            return {"__name__": name, "help": f"Sample value of {name}"}

        # No labels - just metric name
        return {"__name__": key}

    def _get_timestamp(self) -> str:
        """Get Prometheus timestamp format."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return f"# {now}"


def labels_key(labels: Optional[Dict[str, str]]) -> str:
    """Generate a label key string from dictionary of labels."""
    parts = []
    for name, value in sorted(labels.items()):  # type: ignore
        if value is None:
            continue
        # Escape double quotes and backslashes
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{name}="{escaped_value}"')

    return "{" + ",".join(parts) + "}"


def _parse_metric_name(name: str) -> Dict[str, Any]:
    """Parse a metric name that may include type suffix."""
    # Remove type suffix if present (e.g., "_total", "_sum")
    base_name = name.rstrip("_total").rstrip("_sum")

    return {"__name__": base_name, "help": f"Sample value of {base_name}"}


# ============================================================================
# FastAPI Integration
# ============================================================================


@router.get(
    "/metrics",
    summary="Prometheus-compatible metrics exposition endpoint",
    description=(
        "Returns all PyMon metrics in Prometheus exposition format.\n\n"
        "This endpoint is compatible with Prometheus and other monitoring systems."
    ),
)
async def prometheus_metrics_endpoint() -> str:
    """Return metrics in Prometheus exposition format."""
    exporter = PrometheusMetricsExporter()

    # Register some default metrics that PyMon exposes
    exporter.register_metric("pymon_uptime_seconds", "Uptime of PyMon server in seconds", metric_type="gauge")

    return exporter.generate_exposition()


# ============================================================================
# Example Usage and Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def main():
        # Create exporter instance
        exporter = PrometheusMetricsExporter()

        # Record some sample metrics
        exporter.record_gauge("pymon_cpu_usage", 45.2, labels={"host": "server1"})
        exporter.record_gauge("pymon_memory_used_bytes", 8392463718, labels={"host": "server1"})
        exporter.record_gauge("pymon_disk_free_percent", 78.5, labels={"mount_point": "/data"})

        # Generate and print exposition format
        output = exporter.generate_exposition()
        print(output)

    asyncio.run(main())
