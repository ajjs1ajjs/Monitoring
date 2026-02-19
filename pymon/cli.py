"""CLI entry point"""

import argparse
import json
import os
import sys

import uvicorn

from pymon import __version__


def load_config(config_path: str) -> dict:
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default=None, help="Host to bind (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=None, help="Port to bind (default: 8090)")
    server_parser.add_argument("--config", default=None, help="Path to config file")
    server_parser.add_argument("--storage", default=None, choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default=None, help="Database path (for sqlite)")
    server_parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")

    args = parser.parse_args()

    if args.command == "server":
        config_path = args.config or os.getenv("CONFIG_PATH", "config.json")
        config = load_config(config_path)
        
        server_config = config.get("server", {})
        storage_config = config.get("storage", {})
        auth_config_data = config.get("auth", {})
        
        host = args.host or server_config.get("host", "0.0.0.0")
        port = args.port or server_config.get("port", 8090)
        storage = args.storage or storage_config.get("backend", "sqlite")
        db_path = args.db or storage_config.get("path", "pymon.db")

        os.environ.setdefault("STORAGE_BACKEND", storage)
        os.environ.setdefault("DB_PATH", db_path)

        from pymon.auth import init_auth_tables, auth_config
        from pymon.storage import init_storage

        init_storage(backend=storage, db_path=db_path)
        auth_config.db_path = db_path
        if auth_config_data.get("admin_username"):
            auth_config.admin_username = auth_config_data["admin_username"]
        if auth_config_data.get("admin_password"):
            auth_config.admin_password = auth_config_data["admin_password"]
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
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pymon.api.endpoints import api
    from pymon.web.dashboard import web
    from pymon.auth import init_auth_tables

    app = FastAPI(title="PyMon", version=__version__, docs_url="/docs", redoc_url="/redoc")
    
    app.mount("", api)
    app.mount("/dashboard", web)

    init_auth_tables()

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """<!DOCTYPE html>
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

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


if __name__ == "__main__":
    main()
