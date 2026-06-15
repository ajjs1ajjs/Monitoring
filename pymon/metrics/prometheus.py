"""Prometheus-compatible /metrics endpoint implementation using the existing MetricsRegistry."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from pymon.metrics.collector import registry

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus-compatible metrics exposition endpoint",
    description=(
        "Returns all PyMon metrics in Prometheus exposition format.\n\n"
        "This endpoint is compatible with Prometheus and other monitoring systems."
    ),
)
async def prometheus_metrics_endpoint():
    """Return metrics in Prometheus exposition format."""
    return PlainTextResponse(
        content=registry.export_prometheus(),
        media_type="text/plain; version=0.0.4",
    )
