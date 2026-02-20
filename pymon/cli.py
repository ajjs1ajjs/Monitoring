"""CLI entry point"""

import argparse
import asyncio
import os
import sys
import traceback
from contextlib import asynccontextmanager

import uvicorn

from pymon import __version__

scrape_manager = None


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    server_parser.add_argument("--port", type=int, default=8090, help="Port to bind")
    server_parser.add_argument("--config", "-c", default=None, help="Path to config file")
    server_parser.add_argument("--storage", default="sqlite", choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default=None, help="Database path (defaults to config value)")

    args = parser.parse_args()

    if args.command == "server":
        try:
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

            print(f"Initializing storage...", file=sys.stderr)
            from pymon.auth import init_auth_tables, auth_config as auth_cfg
            from pymon.storage import init_storage

            init_storage(backend=storage, db_path=db_path)
            
            print(f"Setting auth_config.db_path to: {db_path}", file=sys.stderr)
            auth_cfg.db_path = db_path
            auth_cfg.admin_username = config.auth.admin_username
            auth_cfg.admin_password = config.auth.admin_password
            
            db_dir = os.path.dirname(db_path)
            if not db_dir:
                db_dir = "."
            abs_db_dir = os.path.abspath(db_dir)
            if not os.path.exists(abs_db_dir):
                print(f"Creating DB directory: {abs_db_dir}", file=sys.stderr)
                os.makedirs(abs_db_dir, exist_ok=True)
            db_path = os.path.abspath(db_path)
            auth_cfg.db_path = db_path
            
            print(f"DB Path in auth_config: {auth_cfg.db_path}", file=sys.stderr)
            
            print(f"Initializing auth tables...", file=sys.stderr)
            init_auth_tables()

            print(f"Starting PyMon server on {host}:{port}")
            print(f"Dashboard: http://{host}:{port}/dashboard/")

            app = create_app()
            uvicorn.run(app, host=host, port=port)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


@asynccontextmanager
async def lifespan(app):
    global scrape_manager
    from pymon import web_dashboard
    
    try:
        from pymon.scrape import ScrapeManager
        from pymon.config import load_config
        
        config_path = os.getenv("CONFIG_PATH", "config.yml")
        config = load_config(config_path)
        
        conn = web_dashboard.get_db()
        servers = conn.execute("SELECT * FROM servers WHERE enabled=1").fetchall()
        conn.close()
        
        if servers:
            scrape_manager = ScrapeManager(config)
            for server in servers:
                scrape_manager.add_server_target(server)
            
            if scrape_manager.targets:
                scrape_manager.start()
                print(f"Background scraping started (interval: {config.scrape_configs[0].scrape_interval if config.scrape_configs else 60}s, targets: {len(scrape_manager.targets)})", file=sys.stderr)
        else:
            print("No servers to scrape", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not start background scraping: {e}", file=sys.stderr)
    
    yield
    
    if scrape_manager:
        scrape_manager.stop()
        print("Background scraping stopped", file=sys.stderr)


def create_app():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, RedirectResponse
    from fastapi.middleware.cors import CORSMiddleware
    
    from pymon.api.endpoints import api
    from pymon import web_dashboard
    from pymon.auth import init_auth_tables

    print("Creating FastAPI app...", file=sys.stderr)
    
    app = FastAPI(title="PyMon", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        print("Initializing auth tables...", file=sys.stderr)
        init_auth_tables()
        print("Initializing web tables...", file=sys.stderr)
        web_dashboard.init_web_tables()
        print("All tables initialized", file=sys.stderr)
    except Exception as e:
        print(f"Error initializing tables: {e}", file=sys.stderr)
        traceback.print_exc()
        raise

    app.include_router(api, prefix="/api/v1")
    app.include_router(web_dashboard.router)

    @app.get("/")
    async def root():
        return RedirectResponse(url="/dashboard/")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        return web_dashboard.LOGIN_HTML

    return app


if __name__ == "__main__":
    main()
