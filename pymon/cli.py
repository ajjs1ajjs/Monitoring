"""CLI entry point"""

import argparse
import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import uvicorn

from pymon import __version__

scrape_manager = None


@asynccontextmanager
async def lifespan(app):
    global scrape_manager
    import asyncio

    from pymon.api.deps import manager

    manager.set_loop(asyncio.get_event_loop())

    try:
        from pymon.config import load_config
        from pymon.scrape import ScrapeManager, ServiceChecker

        config_path = os.getenv("CONFIG_PATH", "config.yml")
        config = load_config(config_path)

        scrape_manager = ScrapeManager(config)
        service_checker = ServiceChecker()
        app.state.scrape_manager = scrape_manager
        app.state.service_checker = service_checker

        try:
            await scrape_manager.start()
            await service_checker.start()
            print("Background scraping & service checker started", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not start background tasks: {e}", file=sys.stderr)

    except Exception as e:
        print(f"Warning: Could not start background scraping: {e}", file=sys.stderr)
        app.state.scrape_manager = None
        app.state.service_checker = None

    yield

    if scrape_manager:
        await scrape_manager.stop()
    if 'service_checker' in dir() and service_checker:
        await service_checker.stop()
    print("Background tasks stopped", file=sys.stderr)


def create_app():
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates

    from pymon.api.endpoints import api

    # Setup basic rotating logger for prod-like environments
    log_dir = os.path.join(".", "logs")
    os.makedirs(log_dir, exist_ok=True)
    logfile = os.path.join(log_dir, "pymon.log")
    try:
        handler = RotatingFileHandler(logfile, maxBytes=10 * 1024 * 1024, backupCount=5)
        logging.basicConfig(handlers=[handler], level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    app = FastAPI(title="PyMon", version=__version__, lifespan=lifespan)

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    templates = Jinja2Templates(directory=templates_dir)

    # Configure CORS origins from environment so prod can lock down access
    raw_origins = os.getenv("PYMON_ALLOWED_ORIGINS")
    if raw_origins:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    else:
        origins = ["http://localhost:10000", "http://127.0.0.1:10000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api, prefix="/api/v1")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/favicon.ico")
    async def favicon():
        ico_path = os.path.join(static_dir, "favicon.ico")
        svg_path = os.path.join(static_dir, "favicon.svg")
        if os.path.exists(ico_path):
            return FileResponse(ico_path)
        elif os.path.exists(svg_path):
            return FileResponse(svg_path)
        return None

    @app.get("/dashboard")
    @app.get("/dashboard/")
    async def dashboard(request: Request):
        return templates.TemplateResponse(request=request, name="dashboard.html")

    @app.get("/")
    async def root():
        return RedirectResponse(url="/dashboard/")

    @app.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse(request=request, name="login.html")

    return app


def main():
    parser = argparse.ArgumentParser(description="PyMon - Python Monitoring System", prog="pymon")
    parser.add_argument("--version", action="version", version=f"PyMon {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    server_parser = subparsers.add_parser("server", help="Start the monitoring server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    server_parser.add_argument("--port", type=int, default=10000, help="Port to bind")
    server_parser.add_argument("--config", "-c", default=None, help="Path to config file")
    server_parser.add_argument("--storage", default="sqlite", choices=["memory", "sqlite"], help="Storage backend")
    server_parser.add_argument("--db", default=None, help="Database path (defaults to config value)")

    subparsers.add_parser("reset-admin", help="Reset admin password to '291263'")

    args = parser.parse_args()

    if args.command == "server":
        try:
            config_path = args.config or os.getenv("CONFIG_PATH", "config.yml")

            # Auto-generate a default config if it does not exist
            if not os.path.exists(config_path):
                try:
                    from pymon.config import PyMonConfig

                    cfg = PyMonConfig()
                    # Ensure directory exists for the config path
                    cfg_dir = os.path.dirname(os.path.abspath(config_path)) or "."
                    os.makedirs(cfg_dir, exist_ok=True)
                    cfg.to_yaml(config_path)
                    print(f"Generated default config at {config_path}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: could not generate default config: {e}", file=sys.stderr)

            from pymon.config import load_config

            config = load_config(config_path)

            host = args.host or config.server.host
            port = args.port or config.server.port
            storage = args.storage or config.storage.backend
            db_path = args.db or config.storage.path

            os.environ.setdefault("STORAGE_BACKEND", storage)
            os.environ.setdefault("DB_PATH", db_path)
            os.environ.setdefault("CONFIG_PATH", config_path)

            print("Initializing storage (SQLite)...", file=sys.stderr)
            from pymon.auth import auth_config as auth_cfg
            from pymon.auth import init_auth_tables
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

            print("Initializing auth tables...", file=sys.stderr)
            init_auth_tables()

            print("Initializing database tables...", file=sys.stderr)
            from pymon.database import init_database
            init_database()

            print(f"Starting PyMon server on {host}:{port}")
            print(f"Dashboard: http://{host}:{port}/dashboard/")

            app = create_app()
            # Prefer TLS settings from env, but also allow TLS config from config.yml via TLS envs
            tls_enabled = os.getenv("TLS_ENABLED", "false").lower() in ("1", "true", "yes", "on")
            tls_cert = (
                os.getenv("TLS_CERT")
                or os.getenv("TLS_CERT_PATH")
                or (os.getenv("TLS_CERT_PATH") if tls_enabled else None)
            )
            tls_key = (
                os.getenv("TLS_KEY")
                or os.getenv("TLS_KEY_PATH")
                or (os.getenv("TLS_KEY_PATH") if tls_enabled else None)
            )
            if tls_enabled and tls_cert and tls_key:
                uvicorn.run(app, host=host, port=port, ssl_certfile=tls_cert, ssl_keyfile=tls_key)
            else:
                uvicorn.run(app, host=host, port=port)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    elif args.command == "reset-admin":
        try:
            import sqlite3

            from pymon.auth import init_auth_tables

            db_path = os.getenv("DB_PATH", "pymon.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("DELETE FROM users WHERE username='admin'")
                conn.commit()
                conn.close()
                print(f"Deleted existing admin from {db_path}")

            init_auth_tables()
            print("--------------------------------------------------")
            print("SUCCESS: Admin password has been reset!")
            print("Login: admin")
            print("Password: 291263")
            print("--------------------------------------------------")
        except Exception as e:
            print(f"ERROR: Failed to reset admin: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
