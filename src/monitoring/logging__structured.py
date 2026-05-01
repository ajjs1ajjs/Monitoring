"""Production logging: structlog, log aggregation."""

import json
from datetime import timezone


def get_structured_logger(  # noqa: D103, ANN204
    service_name: str = "monitoring",
) -> None:
    """Get a structured logger for production use."""
    
    return {
        "message": "",
        "level": "info",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service_name,
        "trace_id": create_trace_id_generator()(),
    }


def log_structured(  # noqa: D103, ANN204
    message: str, 
    level: str = "info",
) -> None:
    """Log structured data to file or aggregation system."""
    
    import logging
    
    logger = get_logger(level=level)
    logger.info(message)


def add_trace_context_to_logs(  # noqa: D103, ANN204
    trace_id: str | None = None,
) -> None:
    """Add distributed tracing context to logs."""
    
    if not trace_id:
        trace_id = create_trace_id_generator()(request.url.path)
    
    return {
        "trace_id": trace_id,
        "span_id": f"{trace_id[:8]}-{create_span_suffix()}",
    }


def add_zipkin_headers(  # noqa: D103, ANN204
    request: Request, 
    trace_id: str, 
    span_name: str = "monitoring_api",
) -> None:
    """Add Zipkin headers for distributed tracing."""
    
    return {
        "traceparent": f"00-{create_trace_context(trace_id)}-{span_name}",
        "zipkin-trace-id": trace_id,
    }
