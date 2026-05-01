"""Monitoring application package."""

from .dto__models import ServerCreate, ServerResponse
from .services__metrics import metrics_service as get_metrics_service


def get_metrics_service() -> "MetricsService":  # noqa: D103
    """Get or create MetricsService instance."""
    
    from .services__metrics import MetricsService
    
    return MetricsService()
