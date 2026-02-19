"""CLI entry point"""

import argparse
import os
import sys

import uvicorn

from pymon import __version__


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    server_parser.add_argument("--storage", default="sqlite", choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default="pymon.db", help="Database path (for sqlite)")
    server_parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")

    args = parser.parse_args()

    if args.command == "server":
        os.environ.setdefault("STORAGE_BACKEND", args.storage)
        os.environ.setdefault("DB_PATH", args.db)

        from pymon.auth import init_auth_tables, auth_config
        from pymon.storage import init_storage

        init_storage(backend=args.storage, db_path=args.db)
        auth_config.db_path = args.db
        init_auth_tables()

        print(f"Starting PyMon server on {args.host}:{args.port}")
        print(f"Storage: {args.storage}")
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard/")
        print(f"API Docs: http://{args.host}:{args.port}/api/docs")

        if args.reload or args.workers > 1:
            uvicorn.run(
                "pymon.cli:create_app",
                host=args.host,
                port=args.port,
                workers=args.workers,
                reload=args.reload,
            )
        else:
            app = create_app()
            uvicorn.run(app, host=args.host, port=args.port)
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
