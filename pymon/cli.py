"""CLI entry point"""

import argparse
import os

import uvicorn

from pymon import __version__


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    server_parser.add_argument("--port", type=int, default=8090, help="Port to bind")
    server_parser.add_argument("--config", "-c", default=None, help="Path to config file")
    server_parser.add_argument("--storage", default="sqlite", choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default="pymon.db", help="Database path")
    server_parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command == "server":
        config_path = args.config or os.getenv("CONFIG_PATH", "config.yml")
        
        from pymon.config import load_config
        config = load_config(config_path)
        
        host = args.host or config.server.host
        port = args.port or config.server.port
        storage = args.storage or config.storage.backend
        db_path = args.db or config.storage.path

        os.environ.setdefault("STORAGE_BACKEND", storage)
        os.environ.setdefault("DB_PATH", db_path)
        os.environ.setdefault("CONFIG_PATH", config_path)

        from pymon.auth import init_auth_tables, auth_config as auth_cfg
        from pymon.storage import init_storage

        init_storage(backend=storage, db_path=db_path)
        auth_cfg.db_path = db_path
        auth_cfg.admin_username = config.auth.admin_username
        auth_cfg.admin_password = config.auth.admin_password
        init_auth_tables()

        print(f"Starting PyMon server on {host}:{port}")
        print(f"Storage: {storage}")
        print(f"Config: {config_path}")
        print(f"Dashboard: http://{host}:{port}/dashboard/")
        print(f"API Docs: http://{host}:{port}/docs")

        if args.reload or args.workers > 1:
            uvicorn.run(
                "pymon.cli:create_app",
                host=host,
                port=port,
                workers=args.workers,
                reload=args.reload,
            )
        else:
            app = create_app()
            uvicorn.run(app, host=host, port=port)
    else:
        parser.print_help()


def create_app():
    from fastapi import FastAPI, Depends, HTTPException
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from datetime import datetime, timedelta
    
    from pymon.auth import (
        User, UserLogin, Token, PasswordChange,
        get_current_user, authenticate_user, change_password,
        create_api_key, list_api_keys, delete_api_key,
    )
    from pymon.metrics.collector import registry
    from pymon.metrics.models import Label, MetricType
    from pymon.storage import get_storage

    app = FastAPI(title="PyMon", version=__version__, docs_url="/docs", redoc_url="/redoc")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models
    class MetricPayload(BaseModel):
        name: str
        value: float
        type: str = "gauge"
        labels: list[dict[str, str]] = []
        help_text: str = ""

    class QueryRequest(BaseModel):
        query: str
        start: datetime
        end: datetime
        step: int = 60

    class APIKeyCreate(BaseModel):
        name: str

    # Health
    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/api/v1/health")
    async def api_health():
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    # Auth
    @app.post("/api/v1/auth/login", response_model=Token)
    async def login(data: UserLogin):
        return authenticate_user(data.username, data.password)

    @app.get("/api/v1/auth/me", response_model=User)
    async def get_me(current_user: User = Depends(get_current_user)):
        return current_user

    @app.post("/api/v1/auth/change-password")
    async def change_pwd(data: PasswordChange, current_user: User = Depends(get_current_user)):
        change_password(current_user.id, data.current_password, data.new_password)
        return {"status": "ok"}

    @app.post("/api/v1/auth/api-keys")
    async def create_key(data: APIKeyCreate, current_user: User = Depends(get_current_user)):
        key = create_api_key(current_user.id, data.name)
        return {"api_key": key, "name": data.name}

    @app.get("/api/v1/auth/api-keys")
    async def list_keys(current_user: User = Depends(get_current_user)):
        return {"api_keys": list_api_keys(current_user.id)}

    @app.delete("/api/v1/auth/api-keys/{key_id}")
    async def delete_key(key_id: int, current_user: User = Depends(get_current_user)):
        if delete_api_key(current_user.id, key_id):
            return {"status": "ok"}
        raise HTTPException(status_code=404, detail="API key not found")

    # Metrics
    @app.post("/api/v1/metrics")
    async def ingest_metric(payload: MetricPayload, current_user: User = Depends(get_current_user)):
        storage = get_storage()
        try:
            metric_type = MetricType(payload.type)
        except ValueError:
            metric_type = MetricType.GAUGE

        labels = [Label(name=l["name"], value=l["value"]) for l in payload.labels]
        registry.register(payload.name, metric_type, payload.help_text, labels)
        registry.set(payload.name, payload.value, labels)

        from pymon.metrics.models import Metric
        metric = Metric(
            name=payload.name, value=payload.value, metric_type=metric_type,
            labels=labels, help_text=payload.help_text
        )
        await storage.write(metric)
        return {"status": "ok"}

    @app.get("/api/v1/metrics")
    async def list_metrics(current_user: User = Depends(get_current_user)):
        return {"metrics": [m.to_dict() for m in registry.get_all_metrics()]}

    @app.get("/api/v1/query")
    async def query_metrics(
        query: str,
        start: datetime | None = None,
        end: datetime | None = None,
        step: int = 60,
        current_user: User = Depends(get_current_user),
    ):
        storage = get_storage()
        end = end or datetime.utcnow()
        start = start or (end - timedelta(hours=1))
        points = await storage.read(query, start, end, step=step)
        return {
            "query": query,
            "result": [{"timestamp": p.timestamp.isoformat(), "value": p.value} for p in points],
        }

    @app.get("/api/v1/series")
    async def list_series(current_user: User = Depends(get_current_user)):
        storage = get_storage()
        names = await storage.get_series_names()
        return {"series": names}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_export():
        return registry.export_prometheus()

    # Dashboard HTML
    DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PyMon Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 1rem 2rem; border-bottom: 1px solid #0f3460; }
        .header h1 { font-size: 1.5rem; color: #e94560; }
        .container { padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; }
        .panel { background: #16213e; border-radius: 8px; padding: 1rem; border: 1px solid #0f3460; }
        .panel h3 { margin-bottom: 1rem; color: #e94560; }
        .chart-container { height: 200px; }
        .stats { display: flex; gap: 2rem; margin-bottom: 2rem; }
        .stat { background: #16213e; padding: 1.5rem; border-radius: 8px; flex: 1; border: 1px solid #0f3460; }
        .stat-value { font-size: 2rem; color: #e94560; }
        .stat-label { color: #888; margin-top: 0.5rem; }
        a { color: #00d9ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>PyMon Dashboard</h1>
        <a href="/docs" style="margin-left: 1rem;">API Docs</a>
    </div>
    <div class="container">
        <div class="stats" id="stats"></div>
        <div class="grid" id="panels"></div>
    </div>
</body>
</html>
"""

    @app.get("/dashboard/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """
<!DOCTYPE html>
<html>
<head><title>PyMon</title></head>
<body style="font-family: sans-serif; background: #1a1a2e; color: #eee; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;">
<div style="text-align: center;">
    <h1 style="color: #e94560; font-size: 3rem;">PyMon</h1>
    <p style="color: #888;">Python Monitoring System</p>
    <div style="margin-top: 2rem;">
        <a href="/dashboard/" style="color: #00d9ff; margin: 0 1rem;">Dashboard</a>
        <a href="/docs" style="color: #00d9ff; margin: 0 1rem;">API Docs</a>
        <a href="/metrics" style="color: #00d9ff; margin: 0 1rem;">Prometheus Export</a>
    </div>
</div>
</body>
</html>"""

    return app


if __name__ == "__main__":
    main()
