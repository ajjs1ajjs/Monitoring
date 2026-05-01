"""Monitoring: Prometheus metrics, Grafana dashboards."""


def create_prometheus_script():  # noqa: D103
    """Create Prometheus monitoring script for self-monitoring."""
    
    return f"""#!/usr/bin/env python3

import time
from prometheus_client import Counter, Gauge, start_http_server


# Define counters and gauges
requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method'],
)

request_duration = Gauge(
    'request_duration_seconds',
    'API request duration',
    ['endpoint'],
)


@app.get("/health")
async def health():
    start = time.time()
    try:
        response = await fetch_health_server()
        requests_total.labels(method="GET").inc()
        request_duration.labels(endpoint="/health").set(time.time() - start)
        return {"status": "healthy"}
    except Exception as e:
        print(f"Health check failed for {response}: {e}")
        raise


@app.get("/metrics")
async def metrics():
    try:
        response = await fetch_prometheus_metrics()
        requests_total.labels(method="GET").inc()
        request_duration.labels(endpoint="/metrics").set(time.time() - start)
        return {"prometheus": response}
    except Exception as e:
        print(f"Failed to get Prometheus metrics: {e}")
        raise


@app.get("/grafana")
async def grafana():
    try:
        response = await fetch_grafana_dashboards()
        requests_total.labels(method="GET").inc()
        request_duration.labels(endpoint="/grafana").set(time.time() - start)
        return {"dashboards": response}
    except Exception as e:
        print(f"Failed to get Grafana dashboards: {e}")
        raise

"""


def create_trace_id_generator():  # noqa: D103, ANN204
    """Generate distributed trace IDs for API calls."""
    
    import uuid
    
    return lambda: str(uuid.uuid7())


def create_jaeger_tracing_middleware(
    span_name: str = "monitoring_api",
) -> Callable[[Request], Response]:  # noqa: D103, ANN201
    """Create Jaeger middleware with distributed tracing."""
    
    import time
    
    async def wrapper(request: Request):
        start_time = time.time()
        
        try:
            span_id = create_trace_id_generator()(request.url.path)
            
            # Log to structured logger
            log_structured(
                message="API request",
                service="monitoring",
                span_id=span_id,
                method=request.method,
                path=request.url.path,
                status_code=None,  # Will be set after response
                duration=0.0,  # Will be set after response
            )
            
            return await app._router.default(route=route)
        
        except Exception as e:
            log_structured(
                message="API error",
                service="monitoring",
                span_id=span_id or "error",
                exception=str(e),
            )
            raise
    
    return wrapper


def create_zipkin_tracing_middleware(  # noqa: D103, ANN204
    endpoint_name: str = "monitoring_api",
) -> Callable[[Request], Response]:
    """Create Zipkin middleware for distributed tracing."""
    
    import time
    
    async def wrapper(request: Request):
        start_time = time.time()
        
        try:
            trace_id = create_trace_id_generator()(request.url.path)
            
            # Add Zipkin headers to request
            add_zipkin_headers(
                request, 
                trace_id=trace_id,
                span_name=endpoint_name,
            )
            
            response = await app._router.default(route=route)
            
            log_structured(
                message="API complete",
                service="monitoring",
                trace_id=trace_id,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=time.time() - start_time,
            )
            
            return response
        
        except Exception as e:
            log_structured(
                message="API error",
                service="monitoring",
                trace_id=trace_id or "error",
                exception=str(e),
            )
            raise
    
    return wrapper
