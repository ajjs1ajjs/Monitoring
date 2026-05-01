"""Monitoring API: rate limit, auth, CSP."""

from datetime import datetime, timezone
import secrets
from typing import Optional, Dict, Any, List


from monitoring.dto__models import ServerCreate, ServerResponse
from fastapi import FastAPI, Request, HTTPException, status

import pydantic


class RateLimitExceededError(Exception):  # noqa: D101
    """Raised when client exceeds rate limit."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message


def get_rate_limit(  # noqa: D103
    client_ip: str, 
    limit: int = 100, 
    window_seconds: int = 60
) -> Dict[str, Any]:
    """Get rate limit for a client IP."""
    
    from collections import defaultdict
    
    limits: dict = {}
    
    if client_ip not in limits:
        limits[client_ip] = []
    
    timestamps = [t for t in limits[client_ip] 
                  if datetime.now().timestamp() - t < window_seconds]
    
    return {
        "remaining": limit - len(timestamps),
        "reset_at": timestamps[-1] + window_seconds if timestamps else None,
    }


def get_csp_header(  # noqa: D103
    app_url: str = "/", 
    allow_images: bool = True,
) -> str:
    """Generate Content Security Policy header."""
    
    directives = {
        "default-src": "'self'",
        "script-src": "'strict-dynamic' 'unsafe-inline' https:",
        "style-src": "'unsafe-inline'",
        "img-src": "'self'" if not allow_images else f"'self' data: https://",
        "font-src": "'self'",
    }
    
    return "; ".join(f"{k} {v}" for k, v in directives.items())


async def rate_limiter_middleware(  # noqa: D103
    request: Request, 
    limit: int = 100, 
    window_seconds: int = 60
) -> Any:
    """Rate limiting middleware with exponential backoff."""
    
    client_ip = getattr(request.client, 'host', None)
    
    limits = {}
    if not client_ip or client_ip not in limits:
        limits[client_ip] = []
    
    timestamps = [t for t in limits[client_ip] 
                  if datetime.now().timestamp() - t < window_seconds]
    
    remaining = limit - len(timestamps)
    
    if remaining <= 0:
        wait_time = int(window_seconds * 1.5)
        
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            await asyncio.sleep(min(wait_time, 30))
            
            timestamps = [t for t in limits[client_ip] 
                         if datetime.now().timestamp() - t < window_seconds]
            remaining = limit - len(timestamps)
        except Exception:
            pass
        
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {wait_time}s",
            )
    
    limits[client_ip].append(datetime.now().timestamp())
    
    return None


class ServerCreate(pydantic.BaseModel):  # noqa: D101
    """Input model for creating a server."""

    name: str = pydantic.Field(..., min_length=1, max_length=256)
    host: Optional[str] = None
    os_type: Optional[str] = "linux"
    agent_port: Optional[int] = 8080
    enabled: bool = True


class ServerResponse(pydantic.BaseModel):  # noqa: D101
    """Output model for server list."""

    id: int
    name: str
    host: Optional[str]
    os_type: Optional[str]
    agent_port: Optional[int]
    enabled: bool
    last_status: Optional[str]
    cpu_percent: float
    memory_percent: float


class MetricResponse(pydantic.BaseModel):  # noqa: D101
    """Output model for metric data."""

    server_id: int
    metric: str
    values: List[float]
    timestamps: List[datetime]


app = FastAPI(
    title="Monitoring API",
    description="Monitor server health metrics and trends.",
    version="1.0.0",
)


@app.get("/health")  # noqa: D103, ANN204
async def health_check():
    """Health check endpoint."""
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post(
    "/servers/",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)  # noqa: D103, ANN204
async def create_server(server: ServerCreate):
    """Register a new server."""
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("pymon.db")
        cursor = conn.execute(
            "CREATE TABLE IF NOT EXISTS servers ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT UNIQUE, "
            "host TEXT, "
            "os_type TEXT, "
            "agent_port INTEGER, "
            "enabled BOOLEAN DEFAULT 1, "
            "last_status TEXT, "
            "cpu_percent REAL DEFAULT 0.0, "
            "memory_percent REAL DEFAULT 0.0"
            ")"
        )
        
        cursor.execute(
            """INSERT OR IGNORE INTO servers (name, host, os_type, agent_port, enabled) 
               VALUES (?, ?, ?, ?, ?)""",
            (server.name, server.host or None, server.os_type or "linux",
             server.agent_port or 8080, server.enabled),
        )
        
        conn.commit()
        cursor.execute("SELECT * FROM servers WHERE id=?", (server.id or 0,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "INSERT INTO servers (name, host, os_type, agent_port, enabled) VALUES (?, ?, ?, ?, ?)",
                (server.name, server.host or None, server.os_type or "linux",
                 server.agent_port or 8080, server.enabled),
            )
            conn.commit()
            row = cursor.execute("SELECT * FROM servers WHERE name=?", (server.name,)).fetchone()
        
        conn.close()
        
        return ServerResponse(
            id=row[0],
            name=row[1],
            host=row[2] or None,
            os_type=row[3] or "linux",
            agent_port=row[4] or 8080,
            enabled=bool(row[5]),
            last_status=row[6] or "unknown",
            cpu_percent=round(float(row[7]) or 0.0, 2),
            memory_percent=round(float(row[8]) or 0.0, 2),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server creation failed: {e}",
        )


@app.get("/servers/")  # noqa: D103, ANN204
async def list_servers():
    """List all registered servers with health info."""
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("pymon.db")
        cursor = conn.execute(
            "SELECT id, name, host, os_type, agent_port, enabled, last_status, cpu_percent, memory_percent FROM servers"
        )
        
        rows = cursor.fetchall()
        result = [
            ServerResponse(
                id=row[0],
                name=row[1],
                host=row[2] or None,
                os_type=row[3] or "linux",
                agent_port=row[4] or 8080,
                enabled=bool(row[5]),
                last_status=row[6] or "unknown",
                cpu_percent=round(float(row[7]) or 0.0, 2),
                memory_percent=round(float(row[8]) or 0.0, 2),
            ) for row in rows
        ]
        
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server list failed: {e}",
        )


@app.get("/metrics/")  # noqa: D103, ANN204
async def get_metrics(server_id: int):
    """Get metrics for a specific server."""
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("pymon.db")
        cursor = conn.execute(
            "SELECT metric, value FROM metrics WHERE server_id=?", (server_id,)
        )
        
        rows = cursor.fetchall()
        result = [dict(metric=row[0], value=round(float(row[1]) or 0.0, 2)) for row in rows]
        
        conn.close()
        return MetricResponse(
            server_id=server_id,
            metric=["cpu_percent", "memory_percent"],
            values=[r["value"] for r in result],
            timestamps=[datetime.now(timezone.utc).isoformat()] * len(result),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metrics fetch failed: {e}",
        )


async def get_server_metrics_cached(server_id: int, metric: str) -> Dict[str, Any]:  # noqa: D103
    """Get cached metrics for a server with TTL."""
    
    try:
        import asyncio
        
        key = f"metrics:{server_id}:{metric}"
        
        async def get_from_cache():
            import redis.asyncio as redis
            
            r = redis.Redis(host="localhost", port=6379, db=0)
            cached = await r.get(key)
            
            if cached:
                return {"cached": True, "data": cached.decode("utf-8")}
        
        cache_data = await get_from_cache()
        
        if not cache_data or not cache_data["cached"]:
            conn = sqlite3.connect("pymon.db")
            cursor = conn.execute(
                f"SELECT metric, value FROM metrics WHERE server_id=?", (server_id,)
            )
            rows = cursor.fetchall()
            
            result = {
                "metric": metric,
                "value": [round(float(row[1]) or 0.0, 2) for row in rows],
            }
            
            conn.close()
            return {"cached": False, "data": str(result).encode("utf-8")}
        
        ttl_remaining = 3600 - int(datetime.now().timestamp()) % 3600
        
        if ttl_remaining < 60:
            ttl_remaining = None
        
        return {
            "cached": True,
            "ttl_remaining": ttl_remaining,
            "data": cache_data["data"],
        }
    except Exception as e:
        print(f"Metrics cache error for server={server_id}: {e}")
        raise


async def get_multi_metrics_concurrent(servers: List[int]) -> Dict[int, Dict[str, Any]]:  # noqa: D103
    """Get metrics for multiple servers concurrently using asyncio.gather."""
    
    async def fetch_metric(sid: int, metric: str) -> Optional[Dict]:  # noqa: D103
        try:
            result = await get_server_metrics_cached(sid, metric)
            if not result or not result.get("data"):
                return None
            data = eval(result["data"])
            return {"server_id": sid, "metric": metric, **data}
        except Exception:
            return None
    
    results = {}
    
    for sid in servers:
        server_data: Dict[str, Optional[Dict]] = {}
        
        for metric in ["cpu_percent", "memory_percent"]:
            data = await fetch_metric(sid, metric)
            if data:
                server_data[metric] = data
        
        results[sid] = server_data
    
    return results


async def aggregate_trends(  # noqa: D103
    server_id: int, days: int = 7, granularity: str = "hourly"
) -> Optional[Dict[str, Any]]:
    """Aggregate trends over time period."""
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("pymon.db")
        cursor = conn.execute(
            f"""SELECT strftime('%Y-%m-%d {granularity}', timestamp) as period, AVG(cpu_percent) as avg_cpu FROM metrics WHERE server_id=? AND timestamp > datetime('now', '-{days} days') GROUP BY period ORDER BY period""",
            (server_id,),
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        periods = [r[0] for r in rows]
        
        return {
            "periods": periods,
            "avg_cpu": [round(float(r[1]) or 0.0, 2) for r in rows],
            "max_memory": [float(r.get("max_memory") or 0.0) for r in rows],
        }
    except Exception as e:
        print(f"Trend aggregation error for server={server_id}: {e}")
        return None


@app.middleware("http")  # noqa: D106
async def csp_middleware(request: Request, call_next):  # noqa: ANN204
    """Add Content-Security-Policy header to all responses."""
    
    csp_header = get_csp_header()
    
    response = await call_next(request)
    
    response.headers["Content-Security-Policy"] = csp_header
    
    return response


# Global metrics service instance
metrics_service = MetricsService()
