"""CLI entry point"""

import argparse
import asyncio
import os

import uvicorn

from pymon import __version__


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default=None, help="Host to bind (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=None, help="Port to bind (default: 8090)")
    server_parser.add_argument("--config", "-c", default=None, help="Path to config file (YAML or JSON)")
    server_parser.add_argument("--storage", default=None, choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default=None, help="Database path (for sqlite)")
    server_parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    server_parser.add_argument("--no-scrape", action="store_true", help="Disable scrape manager")

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
        print(f"Scrape targets: {len(config.scrape_configs)}")
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
            app = create_app(config, enable_scrape=not args.no_scrape)
            uvicorn.run(app, host=host, port=port)
    else:
        parser.print_help()


def create_app(config=None, enable_scrape=True):
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pymon.api.endpoints import api
    from pymon.web.dashboard import web
    from pymon.auth import init_auth_tables
    
    if config is None:
        from pymon.config import load_config
        config = load_config()

    app = FastAPI(title="PyMon", version=__version__, docs_url="/docs", redoc_url="/redoc")
    
    app.mount("", api)
    app.mount("/dashboard", web)

    init_auth_tables()

    scrape_manager = None
    
    @app.on_event("startup")
    async def startup():
        nonlocal scrape_manager
        
        if enable_scrape and config.scrape_configs:
            from pymon.scrape import ScrapeManager
            scrape_manager = ScrapeManager(config)
            scrape_manager.start()
            print(f"ScrapeManager started with {len(scrape_manager.targets)} targets")
    
    @app.on_event("shutdown")
    async def shutdown():
        if scrape_manager:
            await scrape_manager.close()

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
