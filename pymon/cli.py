"""CLI entry point"""

import argparse
import asyncio
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
            
            # Ensure DB directory exists
            db_dir = os.path.dirname(db_path)
            if not db_dir:  # If no directory in path, use current directory
                db_dir = "."
            abs_db_dir = os.path.abspath(db_dir)
            if not os.path.exists(abs_db_dir):
                print(f"Creating DB directory: {abs_db_dir}", file=sys.stderr)
                os.makedirs(abs_db_dir, exist_ok=True)
                # Set proper permissions
                import stat
                os.chmod(abs_db_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
            # Update db_path to absolute path
            db_path = os.path.abspath(db_path)
            auth_cfg.db_path = db_path
            
            print(f"DB Path in auth_config: {auth_cfg.db_path}", file=sys.stderr)
            print(f"DB directory exists: {os.path.exists(os.path.dirname(db_path))}", file=sys.stderr)
            
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

    # Background task for scraping servers
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(scrape_servers_periodically())

    # Simple background task for scraping servers
    async def scrape_servers_periodically():
        """Background task to scrape all registered servers"""
        await asyncio.sleep(5)  # Wait for app to start
        while True:
            try:
                import httpx
                servers = web_dashboard.get_db().execute("SELECT * FROM servers WHERE enabled=1").fetchall()
                for server in servers:
                    try:
                        host = server['host']
                        port = server.get('agent_port', 9100)
                        status = 'down'
                        cpu = memory = disk = network_rx = network_tx = 0
                        uptime = ''
                        raid_status = None
                        
                        client = httpx.Client(timeout=3.0)
                        try:
                            resp = client.get(f"http://{host}:{port}/health")
                            if resp.status_code == 200:
                                status = 'up'
                                try:
                                    m = client.get(f"http://{host}:{port}/api/metrics")
                                    if m.status_code == 200:
                                        data = m.json()
                                        cpu = float(data.get('cpu_percent', 0) or 0)
                                        memory = float(data.get('memory_percent', 0) or 0)
                                        disk = float(data.get('disk_percent', 0) or 0)
                                        network_rx = float(data.get('network_rx', 0) or 0)
                                        network_tx = float(data.get('network_tx', 0) or 0)
                                        uptime = str(data.get('uptime', ''))
                                        if data.get('raid'):
                                            import json
                                            raid_status = json.dumps(data.get('raid', {}))
                                except:
                                    pass
                        except:
                            pass
                        finally:
                            client.close()
                        
                        from datetime import datetime
                        conn = web_dashboard.get_db()
                        conn.execute('''UPDATE servers SET last_status=?, last_check=?, cpu_percent=?, memory_percent=?, disk_percent=?, network_rx=?, network_tx=?, uptime=?, raid_status=? WHERE id=?''',
                            (status, datetime.utcnow().isoformat(), cpu, memory, disk, network_rx, network_tx, uptime, raid_status, server['id']))
                        conn.commit()
                        conn.close()
                    except:
                        pass
            except:
                pass
            await asyncio.sleep(30)

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
