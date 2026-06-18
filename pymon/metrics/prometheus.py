"""Prometheus-compatible /metrics endpoint implementation."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter()


class PrometheusMetricsExporter:
    """Exposes metrics in Prometheus exposition format."""

    def __init__(self):
        self._metrics_registry: dict[str, dict[str, Any]] = {}
        self._gauge_samples: dict[str, dict[str, Any]] = {}
        self._histogram_buckets: dict[str, list[float]] = {"default": [0.0, 5.0, 10.0, 25.0, 50.0, 75.0, 100.0]}
        self._start_time = datetime.now(timezone.utc).timestamp()

    def register_metric(self, name: str, help_text: str, metric_type: str = "gauge"):
        """Register a new metric for exposure."""
        self._metrics_registry[name] = {"__name__": name, "_type": metric_type, "help": help_text}

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Record a gauge value (e.g., CPU usage, memory percentage)."""
        key = f"{name}{labels_key(labels)}" if labels else name

        if key not in self._gauge_samples:
            self._gauge_samples[key] = {}

        if labels:
            for label_name, label_value in labels.items():
                if label_value is None:
                    continue  # Skip empty label values
                self._gauge_samples[key][label_name] = str(label_value)

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
        uptime = now - self._start_time

        lines.append(f"pymon_uptime_seconds {uptime}")

        # Output registered gauge metrics with samples
        for key, sample_data in sorted(self._gauge_samples.items()):
            metric_name = self._parse_metric_key(key)
            metric_title = metric_name.get("__name__", key)
            metric_help = metric_name.get("help", f"Sample value of {metric_title}")

            label_parts = []
            value = None
            for label, lvalue in sorted(sample_data.items()):
                if label.startswith("__"):
                    continue  # Skip meta labels
                if label == "value":
                    value = lvalue
                    continue
                label_parts.append(f'{label}="{lvalue}"')

            if value is None:
                continue

            labels_str = "{" + ",".join(label_parts) + "}" if label_parts else ""
            lines.append(f"# HELP {metric_title} {metric_help}")
            lines.append(f"# TYPE {metric_title} gauge")
            lines.append(f"{metric_title}{labels_str} {value}")

        # Include the live in-process metrics registry (system_* gauges, counters, etc.)
        from pymon.metrics.collector import registry

        registry_output = registry.export_prometheus()
        if registry_output:
            lines.append(registry_output)

        return "\n".join(lines)

    def _parse_metric_key(self, key: str) -> dict[str, Any]:
        """Parse metric key to extract name and labels."""
        # This is a simplified parser - in production you'd use prometheus_client library
        name = _parse_metric_name(key.split("{", 1)[0])
        return {"__name__": name, "help": f"Sample value of {name}"}


def labels_key(labels: dict[str, str] | None) -> str:
    """Generate a label key string from dictionary of labels."""
    parts = []
    if labels is None:
        return "{}"
    for name, value in sorted(labels.items()):
        if value is None:
            continue
        # Escape double quotes and backslashes
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{name}="{escaped_value}"')

    return "{" + ",".join(parts) + "}"


def _parse_metric_name(name: str) -> str:
    """Parse a metric name, stripping a known type suffix if present."""
    for suffix in ("_total", "_sum"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


# ============================================================================
# FastAPI Integration
# ============================================================================


_exporter_instance: PrometheusMetricsExporter | None = None


def get_metrics_exporter() -> PrometheusMetricsExporter:
    global _exporter_instance
    if _exporter_instance is None:
        _exporter_instance = PrometheusMetricsExporter()
        _exporter_instance.register_metric("pymon_uptime_seconds", "Uptime of PyMon server in seconds", metric_type="gauge")
    return _exporter_instance


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
    exporter = get_metrics_exporter()
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
