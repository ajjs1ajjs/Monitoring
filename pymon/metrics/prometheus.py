"""Prometheus-compatible /metrics endpoint implementation."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from pymon.metrics.collector import registry

router = APIRouter()


class PrometheusMetricsExporter:
    """Exposes PyMon's in-process metrics in Prometheus exposition format."""

    def __init__(self):
        self._start_time = datetime.now(timezone.utc).timestamp()

    def generate_exposition(self) -> str:
        lines = ["# HELP pymon_uptime_seconds Uptime of PyMon server in seconds",
                 "# TYPE pymon_uptime_seconds gauge"]

        uptime = datetime.now(timezone.utc).timestamp() - self._start_time
        lines.append(f"pymon_uptime_seconds {uptime}")

        registry_output = registry.export_prometheus()
        if registry_output:
            lines.append(registry_output)

        return "\n".join(lines)


# ============================================================================
# FastAPI Integration
# ============================================================================


_exporter_instance: PrometheusMetricsExporter | None = None


def get_metrics_exporter() -> PrometheusMetricsExporter:
    global _exporter_instance
    if _exporter_instance is None:
        _exporter_instance = PrometheusMetricsExporter()
    return _exporter_instance


@router.get(
    "/metrics",
    summary="Prometheus-compatible metrics exposition endpoint",
    description=(
        "Returns all PyMon metrics in Prometheus exposition format.\n\n"
        "This endpoint is compatible with Prometheus and other monitoring systems."
    ),
    response_class=PlainTextResponse,
)
async def prometheus_metrics_endpoint() -> str:
    """Return metrics in Prometheus exposition format."""
    exporter = get_metrics_exporter()
    return exporter.generate_exposition()
