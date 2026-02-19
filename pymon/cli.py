"""CLI entry point"""

import argparse
import os
import sys
import traceback

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
            auth_cfg.db_path = db_path
            auth_cfg.admin_username = config.auth.admin_username
            auth_cfg.admin_password = config.auth.admin_password
            
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


def create_app():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, RedirectResponse
    from fastapi.middleware.cors import CORSMiddleware
    
    from pymon.api.endpoints import api
    from pymon import web_dashboard
    from pymon.auth import init_auth_tables

    print("Creating FastAPI app...", file=sys.stderr)
    
    app = FastAPI(title="PyMon", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        # Initialize DB tables
        print("Initializing auth tables...", file=sys.stderr)
        init_auth_tables()
        print("Initializing web tables...", file=sys.stderr)
        web_dashboard.init_web_tables()
        print("All tables initialized", file=sys.stderr)
    except Exception as e:
        print(f"Error initializing tables: {e}", file=sys.stderr)
        traceback.print_exc()
        raise

    # Mount routers
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
