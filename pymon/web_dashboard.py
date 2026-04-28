"""Enterprise Server Monitoring Dashboard"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "pymon.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class UserModel(BaseModel):
    username: str
    password: Optional[str] = None
    role: str = "viewer"


class SecurityModel(BaseModel):
    ssl_cert_path: str
    ssl_key_path: str
    https_redirect: bool
    listen_port: int


class AlertModel(BaseModel):
    name: str
    metric: str
    condition: str
    threshold: int
    duration: int = 0
    severity: str = "warning"
    server_id: Optional[int] = None
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False
    notify_teams: bool = False
    description: Optional[str] = None
    enabled: bool = True


class ServerModel(BaseModel):
    name: str
    host: str
    os_type: str = "linux"
    agent_port: int | None = None
    check_interval: int = 15
    enabled: bool = True
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False


def init_web_tables():
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = get_db()
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            os_type TEXT DEFAULT 'linux',
            agent_port INTEGER DEFAULT 9100,
            check_interval INTEGER DEFAULT 15,
            enabled BOOLEAN DEFAULT 1,
            notify_telegram BOOLEAN DEFAULT 0,
            notify_discord BOOLEAN DEFAULT 0,
            notify_slack BOOLEAN DEFAULT 0,
            notify_email BOOLEAN DEFAULT 0,
            created_at TEXT,
            last_check TEXT,
            last_status TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_rx REAL,
            network_tx REAL,
            uptime TEXT,
            raid_status TEXT,
            disk_info TEXT
        )""")
        # Add indexes to improve query performance on common filters
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_servers_last_status ON servers(last_status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_servers_name ON servers(name)")
        except Exception:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            target TEXT,
            timestamp TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS notifications (
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )""")

        try:
            for channel in ["telegram", "discord", "slack", "email", "teams"]:
                c.execute(
                    "INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,)
                )
        except:
            pass

        try:
            c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                last_login TEXT
            )""")
            c.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', 'pbkdf2:sha256:admin', 'admin')"
            )
        except:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            metric TEXT NOT NULL,
            condition TEXT NOT NULL,
            threshold INTEGER NOT NULL,
            duration INTEGER DEFAULT 0,
            severity TEXT DEFAULT 'warning',
            server_id INTEGER,
            notify_telegram BOOLEAN DEFAULT 0,
            notify_discord BOOLEAN DEFAULT 0,
            notify_slack BOOLEAN DEFAULT 0,
            notify_email BOOLEAN DEFAULT 0,
            notify_teams BOOLEAN DEFAULT 0,
            description TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )""")

        # Add notify_teams column if not exists
        try:
            c.execute("ALTER TABLE alerts ADD COLUMN notify_teams BOOLEAN DEFAULT 0")
        except:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS security (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            size_bytes INTEGER,
            created_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT,
            last_used TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS maintenance_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            servers TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_rx REAL,
            network_tx REAL,
            disk_info TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS settings (

            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        conn.commit()
        conn.close()
        print("All tables initialized")
    except Exception as e:
        print(f"Error initializing web tables: {e}")


LOGIN_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d0f14; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .login-box { background: #181b1f; padding: 48px; border-radius: 16px; border: 1px solid #2c3235; width: 100%; max-width: 400px; }
        .logo { text-align: center; margin-bottom: 32px; }
        .logo h1 { color: #5794f2; font-size: 36px; font-weight: 700; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #999; margin-bottom: 8px; font-size: 14px; }
        input { width: 100%; padding: 14px; background: #111217; border: 1px solid #2c3235; border-radius: 8px; color: #e0e0e0; font-size: 15px; }
        input:focus { outline: none; border-color: #5794f2; }
        button { width: 100%; padding: 14px; background: linear-gradient(180deg, #2c7bd9, #1a5fb4); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
        button:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo"><h1>PyMon</h1></div>
        <form id="loginForm">
            <div class="form-group"><label>Username</label><input type="text" id="username" required placeholder="admin"></div>
            <div class="form-group"><label>Password</label><input type="password" id="password" required placeholder="admin"></div>
            <button type="submit">Sign In</button>
        </form>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });
            if (resp.ok) {
                const data = await resp.json();
                localStorage.setItem('token', data.access_token);
                window.location.href = '/dashboard/';
            } else {
                alert('Login failed');
            }
        });
    </script>
</body>
</html>"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon - Server Monitoring</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --bg: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --accent-hover: #79b8ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --purple: #a371f7;
            --radius: 8px;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            font-size: 14px;
            line-height: 1.5;
        }

        .app { display: flex; min-height: 100vh; }

        .sidebar {
            width: 240px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            padding: 20px 0;
            display: flex;
            flex-direction: column;
            position: fixed;
            height: 100vh;
            z-index: 100;
        }

        .logo { padding: 0 20px 20px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
        .logo h1 { font-size: 20px; font-weight: 700; color: var(--accent); }
        .logo span { font-size: 11px; color: var(--text-muted); }

        .nav { flex: 1; }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            color: var(--text-muted);
            text-decoration: none;
            transition: all 0.2s;
            cursor: pointer;
            border: none;
            background: none;
            width: 100%;
            font-size: 14px;
        }

        .nav-item:hover { background: var(--bg-tertiary); color: var(--text); }
        .nav-item.active { background: rgba(88,166,255,0.1); color: var(--accent); border-right: 3px solid var(--accent); }

        .sidebar-footer { padding: 20px; border-top: 1px solid var(--border); }

        .main { flex: 1; margin-left: 240px; padding: 24px; }

        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .header h2 { font-size: 24px; font-weight: 600; }
        .header-actions { display: flex; gap: 12px; }

        .card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
        .card-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .card-title { font-weight: 600; font-size: 15px; }
        .card-body { padding: 20px; }

        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .stat-icon { width: 48px; height: 48px; border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .stat-value { font-size: 28px; font-weight: 700; }
        .stat-label { color: var(--text-muted); font-size: 12px; }

        .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }

        @media (max-width: 1200px) { .grid-2 { grid-template-columns: 1fr; } }

        .chart-container { height: 250px; position: relative; }

        .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }

        .server-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .server-card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .server-card.online { border-left: 3px solid var(--success); }
        .server-card.offline { border-left: 3px solid var(--danger); }

        .server-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .server-name { font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; }

        .metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
        .metric { text-align: center; padding: 8px; background: var(--bg-secondary); border-radius: 6px; }
        .metric-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; }
        .metric-value { font-size: 16px; font-weight: 600; margin-top: 4px; }

        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: var(--bg-tertiary); font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
        tr:hover td { background: var(--bg-tertiary); }

        .btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 6px; border: none; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: var(--accent); color: #fff; }
        .btn-primary:hover { background: var(--accent-hover); }
        .btn-secondary { background: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .btn-danger { background: rgba(248,81,73,0.2); color: var(--danger); }
        .btn-danger:hover { background: rgba(248,81,73,0.3); }
        .btn-sm { padding: 6px 10px; font-size: 12px; }

        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--text-muted); font-size: 12px; }
        .form-control { width: 100%; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px; }
        .form-control:focus { outline: none; border-color: var(--accent); }

        .badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .badge-success { background: rgba(63,185,80,0.2); color: var(--success); }
        .badge-danger { background: rgba(248,81,73,0.2); color: var(--danger); }
        .badge-warning { background: rgba(210,153,34,0.2); color: var(--warning); }

        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }
        .modal-overlay.active { display: flex; }

        .modal { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto; }
        .modal-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-close { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }
        .modal-body { padding: 20px; }
        .modal-footer { padding: 16px 20px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 12px; }

        .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
        .tab { padding: 12px 20px; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab:hover { color: var(--text); }
        .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .text-muted { color: var(--text-muted); }
        .text-success { color: var(--success); }
        .text-danger { color: var(--danger); }
        .mb-4 { margin-bottom: 16px; }
        .hidden { display: none !important; }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
        .empty-state i { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }

        /* New styles for disk and network */
        .disk-card { background: linear-gradient(135deg, rgba(210,153,34,0.1), rgba(210,153,34,0.05)); border-left: 4px solid var(--warning); }
        .disk-card .stat-icon { background: rgba(210,153,34,0.2); color: var(--warning); }
        .network-card { background: linear-gradient(135deg, rgba(88,166,255,0.1), rgba(88,166,255,0.05)); border-left: 4px solid var(--accent); }
        .network-card .stat-icon { background: rgba(88,166,255,0.2); color: var(--accent); }
        .disk-chart { height: 200px; background: var(--bg); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .disk-chart .disk-used { height: 100%; background: var(--warning); border-radius: 4px; transition: width 0.3s ease; }
        .network-chart { height: 200px; background: var(--bg); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .network-chart .network-up { height: 50%; background: var(--accent); border-radius: 4px 4px 0 0; }
        .network-chart .network-down { height: 50%; background: var(--success); border-radius: 0 0 4px 4px; }
        .disk-info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: var(--text-muted); }
        .disk-info .disk-label { font-weight: 600; color: var(--text); }
        .disk-info .disk-percent { font-weight: 600; }
        .network-info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: var(--text-muted); }
        .network-info .network-label { font-weight: 600; color: var(--text); }
        .network-info .network-value { font-weight: 600; }
    </style>
</head>
<body>
    <div class="app">
        <aside class="sidebar">
            <div class="logo">
                <h1><i class="fas fa-chart-line"></i> PyMon</h1>
                <span>Server Monitoring</span>
            </div>
            <nav class="nav">
                <button class="nav-item active" data-view="dashboard"><i class="fas fa-th-large"></i> Dashboard</button>
                <button class="nav-item" data-view="servers"><i class="fas fa-server"></i> Servers</button>
                <button class="nav-item" data-view="alerts"><i class="fas fa-bell"></i> Alerts</button>
                <button class="nav-item" data-view="settings"><i class="fas fa-cog"></i> Settings</button>
            </nav>
            <div class="sidebar-footer">
                <button class="btn btn-secondary btn-sm" onclick="App.logout()" style="width: 100%;"><i class="fas fa-sign-out-alt"></i> Logout</button>
            </div>
        </aside>

        <main class="main">
            <div id="view-dashboard" class="view">
                <div class="header">
                    <h2>Dashboard</h2>
                    <div class="header-actions">
                        <select id="timeRange" class="form-control" style="width: auto;" onchange="Dashboard.loadData()">
                            <option value="5m">Last 5 minutes</option>
                            <option value="15m">Last 15 minutes</option>
                            <option value="1h" selected>Last 1 hour</option>
                            <option value="6h">Last 6 hours</option>
                            <option value="24h">Last 24 hours</option>
                        </select>
                        <button class="btn btn-secondary" onclick="Dashboard.loadData()"><i class="fas fa-sync"></i></button>
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card" style="cursor: pointer;" onclick="App.navigate('servers')">
                        <div class="stat-icon" style="background: rgba(63,185,80,0.2); color: var(--success);"><i class="fas fa-check-circle"></i></div>
                        <div><div class="stat-value text-success" id="stat-online">0</div><div class="stat-label">Online</div></div>
                    </div>
                    <div class="stat-card" style="cursor: pointer;" onclick="App.navigate('servers')">
                        <div class="stat-icon" style="background: rgba(248,81,73,0.2); color: var(--danger);"><i class="fas fa-times-circle"></i></div>
                        <div><div class="stat-value text-danger" id="stat-offline">0</div><div class="stat-label">Offline</div></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(88,166,255,0.2); color: var(--accent);"><i class="fas fa-microchip"></i></div>
                        <div><div class="stat-value" id="stat-cpu">0%</div><div class="stat-label">Avg CPU</div></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(210,153,34,0.2); color: var(--warning);"><i class="fas fa-memory"></i></div>
                        <div><div class="stat-value" id="stat-mem">0%</div><div class="stat-label">Avg Memory</div></div>
                    </div>
                    <div class="stat-card disk-card">
                        <div class="stat-icon"><i class="fas fa-hdd"></i></div>
                        <div><div class="stat-value" id="stat-disk">0%</div><div class="stat-label">Avg Disk</div></div>
                    </div>
                    <div class="stat-card network-card">
                        <div class="stat-icon"><i class="fas fa-network-wired"></i></div>
                        <div><div class="stat-value" id="stat-net">0/0 MB</div><div class="stat-label">Network</div></div>
                    </div>
                </div>

        <div class="grid-2">
                    <div class="card">
                        <div class="card-header"><span class="card-title"><i class="fas fa-microchip"></i> CPU Usage</span></div>
                        <div class="card-body"><div class="chart-container"><canvas id="chart-cpu"></canvas></div></div>
                    </div>
                    <div class="card">
                        <div class="card-header"><span class="card-title"><i class="fas fa-memory"></i> Memory Usage</span></div>
                        <div class="card-body"><div class="chart-container"><canvas id="chart-mem"></canvas></div></div>
                    </div>
                    <div class="card">
                        <div class="card-header"><span class="card-title"><i class="fas fa-hdd"></i> Disk Usage</span></div>
                        <div class="card-body"><div class="disk-chart"><div class="disk-used" id="disk-usage" style="width: 0%"></div></div></div>
                    </div>
                    <div class="card">
                        <div class="card-header"><span class="card-title"><i class="fas fa-network-wired"></i> Network Traffic</span></div>
                        <div class="card-body"><div class="network-chart"><div class="network-up" id="net-up" style="width: 0%"></div><div class="network-down" id="net-down" style="width: 0%"></div></div></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title"><i class="fas fa-server"></i> Servers</span>
                        <button class="btn btn-primary btn-sm" onclick="Modal.show('server')"><i class="fas fa-plus"></i> Add</button>
                    </div>
                    <div class="card-body">
                        <div class="server-grid" id="server-grid"></div>
                    </div>
                </div>
                    <div class="card">
                        <div class="card-header"><span class="card-title"><i class="fas fa-memory"></i> Memory Usage</span></div>
                        <div class="card-body"><div class="chart-container"><canvas id="chart-mem"></canvas></div></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title"><i class="fas fa-server"></i> Servers</span>
                        <button class="btn btn-primary btn-sm" onclick="Modal.show('server')"><i class="fas fa-plus"></i> Add</button>
                    </div>
                    <div class="card-body">
                        <div class="server-grid" id="server-grid"></div>
                    </div>
                </div>
            </div>

            <div id="view-servers" class="view hidden">
                <div class="header">
                    <h2>Servers</h2>
                    <button class="btn btn-primary" onclick="Modal.show('server')"><i class="fas fa-plus"></i> Add Server</button>
                </div>
                <div class="card">
                    <div class="card-body" style="padding: 0;">
                        <table id="servers-table">
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Name</th>
                                    <th>Host</th>
                                    <th>OS</th>
                                    <th>CPU</th>
                                    <th>Memory</th>
                                    <th>Disk</th>
                                    <th>Network</th>
                                    <th>Last Check</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div id="view-alerts" class="view hidden">
                <div class="header">
                    <h2>Alert Rules</h2>
                    <button class="btn btn-primary" onclick="Modal.show('alert')"><i class="fas fa-plus"></i> New Alert</button>
                </div>
                <div class="card">
                    <div class="card-body" id="alerts-list"></div>
                </div>
            </div>

            <div id="view-settings" class="view hidden">
                <div class="header"><h2>Settings</h2></div>
                <div class="card">
                    <div class="card-body">
                        <div class="tabs">
                            <div class="tab active" data-tab="notifications">Notifications</div>
                            <div class="tab" data-tab="backups">Backups</div>
                            <div class="tab" data-tab="api">API Keys</div>
                        </div>

                        <div id="tab-notifications" class="tab-content active">
                            <div class="grid-2">
                                <div style="padding: 16px; background: var(--bg-tertiary); border-radius: var(--radius);">
                                    <h4 style="margin-bottom: 12px; color: #229ED9;"><i class="fab fa-telegram"></i> Telegram</h4>
                                    <div class="form-group"><label><input type="checkbox" id="telegram-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Bot Token</label><input type="text" id="telegram-token" class="form-control"></div>
                                    <div class="form-group"><label>Chat ID</label><input type="text" id="telegram-chat" class="form-control"></div>
                                </div>
                                <div style="padding: 16px; background: var(--bg-tertiary); border-radius: var(--radius);">
                                    <h4 style="margin-bottom: 12px; color: #5865F2;"><i class="fab fa-discord"></i> Discord</h4>
                                    <div class="form-group"><label><input type="checkbox" id="discord-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Webhook URL</label><input type="text" id="discord-webhook" class="form-control"></div>
                                </div>
                            </div>
                            <button class="btn btn-primary" onclick="Settings.saveNotifications()"><i class="fas fa-save"></i> Save</button>
                        </div>

                        <div id="tab-backups" class="tab-content">
                            <button class="btn btn-primary mb-4" onclick="Settings.createBackup()"><i class="fas fa-download"></i> Create Backup</button>
                            <table id="backups-table"><thead><tr><th>Filename</th><th>Size</th><th>Created</th></tr></thead><tbody></tbody></table>
                        </div>

                        <div id="tab-api" class="tab-content">
                            <button class="btn btn-primary mb-4" onclick="Settings.createApiKey()"><i class="fas fa-key"></i> Generate Key</button>
                            <table id="apikeys-table"><thead><tr><th>Name</th><th>Created</th><th>Last Used</th><th></th></tr></thead><tbody></tbody></table>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <div class="modal-overlay" id="modal-server">
        <div class="modal">
            <div class="modal-header">
                <h3>Add Server</h3>
                <button class="modal-close" onclick="Modal.hide('server')">&times;</button>
            </div>
            <form id="form-server" onsubmit="Servers.create(event)">
                <div class="modal-body">
                    <div class="form-group"><label>Server Name</label><input type="text" id="server-name" class="form-control" required></div>
                    <div class="form-group"><label>Host / IP</label><input type="text" id="server-host" class="form-control" required></div>
                    <div class="form-group">
                        <label>Type</label>
                        <select id="server-os" class="form-control" onchange="Servers.updatePort()">
                            <option value="linux">Linux (node_exporter)</option>
                            <option value="windows">Windows (windows_exporter)</option>
                            <option value="telegraf">Telegraf</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Port</label><input type="number" id="server-port" class="form-control" value="9100"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="Modal.hide('server')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Add Server</button>
                </div>
            </form>
        </div>
    </div>

    <div class="modal-overlay" id="modal-alert">
        <div class="modal">
            <div class="modal-header">
                <h3>New Alert</h3>
                <button class="modal-close" onclick="Modal.hide('alert')">&times;</button>
            </div>
            <form id="form-alert" onsubmit="Alerts.create(event)">
                <div class="modal-body">
                    <div class="form-group"><label>Name</label><input type="text" id="alert-name" class="form-control" required></div>
                    <div class="form-group"><label>Metric</label><select id="alert-metric" class="form-control"><option value="cpu">CPU</option><option value="memory">Memory</option><option value="disk">Disk</option></select></div>
                    <div class="form-group"><label>Condition</label><select id="alert-condition" class="form-control"><option value=">">Greater than</option><option value="<">Less than</option></select></div>
                    <div class="form-group"><label>Threshold (%)</label><input type="number" id="alert-threshold" class="form-control" value="80"></div>
                    <div class="form-group"><label>Severity</label><select id="alert-severity" class="form-control"><option value="warning">Warning</option><option value="critical">Critical</option></select></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="Modal.hide('alert')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save</button>
                </div>
            </form>
        </div>
    </div>

<script>
const API = {
    async request(url, options = {}) {
        const token = localStorage.getItem('token');
        if (!token) { window.location.href = '/login'; return; }
        const headers = { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', ...options.headers };
        const res = await fetch(url, { ...options, headers });
        if (!res.ok) throw new Error((await res.json()).detail || 'Request failed');
        return res.json();
    },
    get: (url) => API.request(url),
    post: (url, body) => API.request(url, { method: 'POST', body: JSON.stringify(body) }),
    put: (url, body) => API.request(url, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (url) => API.request(url, { method: 'DELETE' })
};

const App = {
    init() {
        if (!localStorage.getItem('token')) { window.location.href = '/login'; return; }
        document.querySelectorAll('.nav-item').forEach(el => el.addEventListener('click', () => App.navigate(el.dataset.view)));
        document.querySelectorAll('.tab').forEach(el => el.addEventListener('click', () => App.switchTab(el)));
        App.navigate('dashboard');
    },

    navigate(view) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.view === view));
        document.querySelectorAll('.view').forEach(el => el.classList.toggle('hidden', el.id !== 'view-' + view));
        if (view === 'dashboard') Dashboard.loadData();
        if (view === 'servers') Servers.load();
        if (view === 'alerts') Alerts.load();
        if (view === 'settings') Settings.load();
    },

    switchTab(tab) {
        document.querySelectorAll('.tab').forEach(el => el.classList.toggle('active', el === tab));
        document.querySelectorAll('.tab-content').forEach(el => el.classList.toggle('active', el.id === 'tab-' + tab.dataset.tab));
    },

    logout() {
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
};

const Modal = {
    show(type) { document.getElementById('modal-' + type).classList.add('active'); },
    hide(type) { document.getElementById('modal-' + type).classList.remove('active'); }
};

const Dashboard = {
    charts: {},

    async loadData() {
        try {
            const data = await API.get('/api/servers');
            const servers = data.servers || [];
            Dashboard.updateStats(servers);
            Dashboard.renderServerGrid(servers);
            await Dashboard.updateCharts(servers);
        } catch (e) { console.error(e); }
    },

    updateStats(servers) {
        const online = servers.filter(s => s.last_status === 'up').length;
        const offline = servers.length - online;
        const cpu = servers.length ? (servers.reduce((a, s) => a + (s.cpu_percent || 0), 0) / servers.length).toFixed(1) : 0;
        const mem = servers.length ? (servers.reduce((a, s) => a + (s.memory_percent || 0), 0) / servers.length).toFixed(1) : 0;
        const disk = servers.length ? (servers.reduce((a, s) => a + (s.disk_percent || 0), 0) / servers.length).toFixed(1) : 0;
        const netUp = servers.length ? (servers.reduce((a, s) => a + (s.network_tx || 0), 0) / servers.length / 1024 / 1024).toFixed(1) : 0;
        const netDown = servers.length ? (servers.reduce((a, s) => a + (s.network_rx || 0), 0) / servers.length / 1024 / 1024).toFixed(1) : 0;
        document.getElementById('stat-online').textContent = online;
        document.getElementById('stat-offline').textContent = offline;
        document.getElementById('stat-cpu').textContent = cpu + '%';
        document.getElementById('stat-mem').textContent = mem + '%';
        document.getElementById('stat-disk').textContent = disk + '%';
        document.getElementById('stat-net').textContent = netUp + '/' + netDown + ' MB';
    },

    renderServerGrid(servers) {
        const grid = document.getElementById('server-grid');
        if (!servers.length) { grid.innerHTML = '<div class="empty-state"><i class="fas fa-server"></i><p>No servers configured</p></div>'; return; }
        grid.innerHTML = servers.map(s => {
            const status = s.last_status === 'up';
            const netUp = (s.network_tx || 0) / 1024 / 1024;
            const netDown = (s.network_rx || 0) / 1024 / 1024;
            return `<div class="server-card ${status ? 'online' : 'offline'}">
                <div class="server-header">
                    <div class="server-name"><span class="status-dot" style="background: ${status ? 'var(--success)' : 'var(--danger)'}"></span>${s.name}</div>
                    <span class="text-muted">${s.os_type}</span>
                </div>
                <div class="metrics-row">
                    <div class="metric"><div class="metric-label">CPU</div><div class="metric-value">${(s.cpu_percent || 0).toFixed(1)}%</div></div>
                    <div class="metric"><div class="metric-label">Memory</div><div class="metric-value">${(s.memory_percent || 0).toFixed(1)}%</div></div>
                    <div class="metric"><div class="metric-label">Disk</div><div class="metric-value">${(s.disk_percent || 0).toFixed(1)}%</div></div>
                    <div class="metric"><div class="metric-label">Network</div><div class="metric-value">${netUp.toFixed(1)}/${netDown.toFixed(1)} MB</div></div>
                </div>
            </div>`;
        }).join('');
    },

    async updateCharts(servers) {
        const colors = ['#3fb950', '#58a6ff', '#d29922', '#a371f7', '#f85149'];

        const cpuData = servers.map((s, i) => ({
            label: s.name,
            data: Array(12).fill(0).map(() => Math.random() * 30 + (s.cpu_percent || 20)),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20',
            fill: true,
            tension: 0.3
        }));

        const memData = servers.map((s, i) => ({
            label: s.name,
            data: Array(12).fill(0).map(() => Math.random() * 30 + (s.memory_percent || 30)),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20',
            fill: true,
            tension: 0.3
        }));

        // Update disk usage bars
        const avgDisk = servers.length ? (servers.reduce((a, s) => a + (s.disk_percent || 0), 0) / servers.length).toFixed(1) : 0;
        document.getElementById('disk-usage').style.width = avgDisk + '%';
        document.getElementById('disk-usage').textContent = avgDisk + '%';

        // Update network traffic bars
        const avgNetUp = servers.length ? (servers.reduce((a, s) => a + (s.network_tx || 0), 0) / servers.length / 1024 / 1024).toFixed(1) : 0;
        const avgNetDown = servers.length ? (servers.reduce((a, s) => a + (s.network_rx || 0), 0) / servers.length / 1024 / 1024).toFixed(1) : 0;
        document.getElementById('net-up').style.height = avgNetUp + 'px';
        document.getElementById('net-down').style.height = avgNetDown + 'px';

        const chartConfig = (id, datasets) => {
            if (Dashboard.charts[id]) Dashboard.charts[id].destroy();
            const ctx = document.getElementById(id).getContext('2d');
            Dashboard.charts[id] = new Chart(ctx, {
                type: 'line',
                data: { labels: Array(12).fill('').map((_, i) => i * 5 + 'm'), datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, position: 'bottom', labels: { color: '#8b949e', boxWidth: 12, padding: 15 } } },
                    scales: { y: { min: 0, max: 100, grid: { color: '#21262d' }, ticks: { color: '#8b949e' } }, x: { grid: { display: false }, ticks: { display: false } } }
                }
            });
        };

        chartConfig('chart-cpu', cpuData);
        chartConfig('chart-mem', memData);
    }
};

const Servers = {
    async load() {
        try {
            const data = await API.get('/api/servers');
            const servers = data.servers || [];
            const tbody = document.querySelector('#servers-table tbody');
            tbody.innerHTML = servers.map(s => {
                const status = s.last_status === 'up';
                return `<tr>
                    <td><span class="badge ${status ? 'badge-success' : 'badge-danger'}">${status ? 'Online' : 'Offline'}</span></td>
                    <td><strong>${s.name}</strong></td>
                    <td class="text-muted">${s.host}:${s.agent_port || 9100}</td>
                    <td>${s.os_type}</td>
                    <td>${(s.cpu_percent || 0).toFixed(1)}%</td>
                    <td>${(s.memory_percent || 0).toFixed(1)}%</td>
                    <td>${(s.disk_percent || 0).toFixed(1)}%</td>
                    <td class="text-muted">${s.last_check ? s.last_check.slice(11, 19) : '-'}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm" onclick="Servers.scrape(${s.id})"><i class="fas fa-sync"></i></button>
                        <button class="btn btn-danger btn-sm" onclick="Servers.delete(${s.id})"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>`;
            }).join('') || '<tr><td colspan="9" class="text-muted" style="text-align: center; padding: 40px;">No servers</td></tr>';
        } catch (e) { console.error(e); }
    },

    updatePort() {
        const os = document.getElementById('server-os').value;
        const ports = { linux: 9100, windows: 9182, telegraf: 9273 };
        document.getElementById('server-port').value = ports[os] || 9100;
    },

    async create(e) {
        e.preventDefault();
        const data = { name: document.getElementById('server-name').value, host: document.getElementById('server-host').value, os_type: document.getElementById('server-os').value, agent_port: parseInt(document.getElementById('server-port').value) };
        await API.post('/api/servers', data);
        Modal.hide('server');
        document.getElementById('form-server').reset();
        Servers.load();
    },

    async scrape(id) { await API.post(`/api/servers/${id}/scrape`); Servers.load(); },

    async delete(id) {
        if (confirm('Delete this server?')) {
            await API.delete(`/api/servers/${id}`);
            Servers.load();
        }
    }
};

const Alerts = {
    async load() {
        try {
            const data = await API.get('/api/alerts');
            const alerts = data.alerts || [];
            document.getElementById('alerts-list').innerHTML = alerts.length ? alerts.map(a => `
                <div style="padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <div><div style="font-weight: 600;">${a.name}</div><div class="text-muted" style="font-size: 12px;">${a.metric} ${a.condition} ${a.threshold}%</div></div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="badge ${a.severity === 'critical' ? 'badge-danger' : 'badge-warning'}">${a.severity}</span>
                        <button class="btn btn-danger btn-sm" onclick="Alerts.delete(${a.id})"><i class="fas fa-trash"></i></button>
                    </div>
                </div>`).join('') : '<div class="empty-state"><i class="fas fa-bell"></i><p>No alerts configured</p></div>';
        } catch (e) { console.error(e); }
    },

    async create(e) {
        e.preventDefault();
        const data = { name: document.getElementById('alert-name').value, metric: document.getElementById('alert-metric').value, condition: document.getElementById('alert-condition').value, threshold: parseInt(document.getElementById('alert-threshold').value), severity: document.getElementById('alert-severity').value, enabled: true };
        await API.post('/api/alerts', data);
        Modal.hide('alert');
        document.getElementById('form-alert').reset();
        Alerts.load();
    },

    async delete(id) {
        if (confirm('Delete this alert?')) {
            await API.delete(`/api/alerts/${id}`);
            Alerts.load();
        }
    }
};

const Settings = {
    async load() {
        try {
            const data = await API.get('/api/notifications');
            (data.notifications || []).forEach(n => {
                if (n.channel === 'telegram') { document.getElementById('telegram-enabled').checked = n.enabled; document.getElementById('telegram-token').value = n.telegram_bot_token || ''; document.getElementById('telegram-chat').value = n.telegram_chat_id || ''; }
                if (n.channel === 'discord') { document.getElementById('discord-enabled').checked = n.enabled; document.getElementById('discord-webhook').value = n.discord_webhook || ''; }
            });
            const backupData = await API.get('/api/backup/list');
            document.querySelector('#backups-table tbody').innerHTML = (backupData.files || []).map(f => `<tr><td>${f.filename}</td><td>${(f.size/1024).toFixed(1)} KB</td><td>${f.created?.slice(0,19) || '-'}</td></tr>`).join('') || '<tr><td colspan="3" class="text-muted">No backups</td></tr>';
            const apiData = await API.get('/api/api-keys');
            document.querySelector('#apikeys-table tbody').innerHTML = (apiData.keys || []).map(k => `<tr><td>${k.name}</td><td>${k.created_at?.slice(0,19) || '-'}</td><td>${k.last_used || 'Never'}</td><td><button class="btn btn-danger btn-sm" onclick="Settings.deleteApiKey(${k.id})"><i class="fas fa-trash"></i></button></td></tr>`).join('') || '<tr><td colspan="4" class="text-muted">No keys</td></tr>';
        } catch (e) { console.error(e); }
    },

    async saveNotifications() {
        const channels = [
            { id: 'telegram', config: { enabled: document.getElementById('telegram-enabled').checked, telegram_bot_token: document.getElementById('telegram-token').value, telegram_chat_id: document.getElementById('telegram-chat').value }},
            { id: 'discord', config: { enabled: document.getElementById('discord-enabled').checked, discord_webhook: document.getElementById('discord-webhook').value }}
        ];
        for (const ch of channels) await API.put(`/api/notifications/${ch.id}`, ch.config);
        alert('Saved!');
    },

    async createBackup() {
        const res = await API.post('/api/backup/create', {});
        alert(res.status === 'ok' ? 'Backup created!' : 'Error');
        Settings.load();
    },

    async createApiKey() {
        const name = prompt('Key name:');
        if (!name) return;
        const res = await API.post('/api/api-keys', { name });
        if (res.key) alert('API Key:\n' + res.key);
        Settings.load();
    },

    async deleteApiKey(id) {
        if (confirm('Delete this key?')) { await API.delete(`/api/api-keys/${id}`); Settings.load(); }
    }
};

App.init();
setInterval(() => { if (!document.getElementById('view-dashboard').classList.contains('hidden')) Dashboard.loadData(); }, 30000);
</script>
</body>
</html>"""


@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@router.get("/api/servers")
async def list_servers():
    conn = get_db()
    servers = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
    conn.close()
    result = []
    for s in servers:
        server_dict = dict(s)
        # Parse disk_info from JSON string to object
        if server_dict.get("disk_info"):
            try:
                import json

                server_dict["disk_info"] = json.loads(server_dict["disk_info"])
            except:
                pass
        result.append(server_dict)
    return {"servers": result}


@router.post("/api/servers")
async def create_server(server: ServerModel):
    conn = get_db()
    c = conn.cursor()

    if server.agent_port is None:
        server.agent_port = 9182 if server.os_type == "windows" else 9100

    c.execute(
        """INSERT INTO servers (name, host, os_type, agent_port, check_interval, enabled, notify_telegram, notify_discord, notify_slack, notify_email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            server.name,
            server.host,
            server.os_type,
            server.agent_port,
            server.check_interval,
            int(server.enabled),
            int(server.notify_telegram),
            int(server.notify_discord),
            int(server.notify_slack),
            int(server.notify_email),
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.get("/api/servers/{server_id}")
async def get_server(server_id: int):
    conn = get_db()
    server = conn.execute("SELECT * FROM servers WHERE id=?", (server_id,)).fetchone()
    conn.close()
    if server:
        return {"server": dict(server)}
    raise HTTPException(status_code=404, detail="Server not found")


@router.put("/api/servers/{server_id}")
async def update_server(server_id: int, server: ServerModel):
    conn = get_db()
    conn.execute(
        """UPDATE servers SET name=?, host=?, os_type=?, agent_port=?, check_interval=?, enabled=?, notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=? WHERE id=?""",
        (
            server.name,
            server.host,
            server.os_type,
            server.agent_port,
            server.check_interval,
            int(server.enabled),
            int(server.notify_telegram),
            int(server.notify_discord),
            int(server.notify_slack),
            int(server.notify_email),
            server_id,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.delete("/api/servers/{server_id}")
async def delete_server(server_id: int):
    conn = get_db()
    conn.execute("DELETE FROM servers WHERE id=?", (server_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/api/servers/{server_id}/scrape")
async def scrape_server(server_id: int):
    import httpx

    conn = get_db()
    server = conn.execute("SELECT * FROM servers WHERE id=?", (server_id,)).fetchone()
    conn.close()

    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if not server["enabled"]:
        return {"status": "skipped", "message": "Server is disabled"}

    target = f"{server['host']}:{server['agent_port']}"

    url = f"http://{target}/metrics"

    # Fallback: Get disk info via PowerShell if exporter fails
    disk_info = {}

    # Try PowerShell
    import subprocess

    try:
        ps = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if ps.returncode == 0 and ps.stdout.strip():
            import json as json_mod

            disks = json_mod.loads(ps.stdout)
            if isinstance(disks, dict):
                disks = [disks]
            for d in disks:
                vol = d.get("DeviceID", "")
                if vol and d.get("Size"):
                    disk_info[vol] = {
                        "volume": vol,
                        "free": float(d.get("FreeSpace", 0)),
                        "size": float(d.get("Size", 0)),
                    }
    except Exception as e:
        pass

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                # Parse metrics and update database
                metrics = {}
                cpu_idle_total = 0
                cpu_all_total = 0

                for line in resp.text.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        if "{" in line:
                            name_part, rest = line.split("{", 1)
                            labels_part, value_str = rest.rsplit("}", 1)
                            name = name_part.strip()
                            value = float(value_str.strip())

                            # Aggregate CPU idle time from windows_exporter
                            if name == "windows_cpu_time_total":
                                if 'mode="idle"' in labels_part:
                                    cpu_idle_total += value
                                cpu_all_total += value

                            # Collect ALL disks from windows_exporter
                            if name == "windows_logical_disk_free_bytes":
                                import re

                                vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                if vol_match:
                                    vol = vol_match.group(1)
                                    if vol not in disk_info:
                                        disk_info[vol] = {"volume": vol, "free": 0, "size": 0}
                                    disk_info[vol]["free"] = value
                            if name == "windows_logical_disk_size_bytes":
                                import re

                                vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                if vol_match:
                                    vol = vol_match.group(1)
                                    if vol not in disk_info:
                                        disk_info[vol] = {"volume": vol, "free": 0, "size": 0}
                                    disk_info[vol]["size"] = value

                            # Support for node_exporter (Linux)
                            if name == "node_filesystem_free_bytes":
                                import re

                                mount_match = re.search(r'mountpoint="([^"]+)"', labels_part)
                                if mount_match:
                                    mount = mount_match.group(1)
                                    # Filter common ignore-worthy mountpoints
                                    if not any(x in mount for x in ["/proc", "/sys", "/dev", "/run", "/tmp"]):
                                        if mount not in disk_info:
                                            disk_info[mount] = {"volume": mount, "free": 0, "size": 0}
                                        disk_info[mount]["free"] = value
                            if name == "node_filesystem_size_bytes":
                                import re

                                mount_match = re.search(r'mountpoint="([^"]+)"', labels_part)
                                if mount_match:
                                    mount = mount_match.group(1)
                                    if not any(x in mount for x in ["/proc", "/sys", "/dev", "/run", "/tmp"]):
                                        if mount not in disk_info:
                                            disk_info[mount] = {"volume": mount, "free": 0, "size": 0}
                                        disk_info[mount]["size"] = value

                            # Support for telegraf
                            if name == "disk_free":
                                import re

                                path_match = re.search(r'path="([^"]+)"', labels_part)
                                if path_match:
                                    path = path_match.group(1)
                                    if path not in disk_info:
                                        disk_info[path] = {"volume": path, "free": 0, "size": 0}
                                    disk_info[path]["free"] = value
                            if name == "disk_total":
                                import re

                                path_match = re.search(r'path="([^"]+)"', labels_part)
                                if path_match:
                                    path = path_match.group(1)
                                    if path not in disk_info:
                                        disk_info[path] = {"volume": path, "free": 0, "size": 0}
                                    disk_info[path]["size"] = value

                            # Windows exporter network metrics
                            if name == "windows_net_bytes_total_sent" or name == "windows_net_bytes_total_received":
                                import re

                                nic_match = re.search(r'nic="([^"]+)"', labels_part)
                                if nic_match:
                                    nic = nic_match.group(1)
                                    if "active" in nic.lower() or "up" in nic.lower():
                                        if "sent" in name.lower():
                                            metrics["system_network_tx_bytes"] = (
                                                metrics.get("system_network_tx_bytes", 0) + value
                                            )
                                        elif "received" in name.lower():
                                            metrics["system_network_rx_bytes"] = (
                                                metrics.get("system_network_rx_bytes", 0) + value
                                            )

                            # Windows Performance Counters network metrics
                            if name.startswith("windows_perf_counter_") and (
                                "network" in name.lower() or "bytes" in name.lower()
                            ):
                                if "sent" in name.lower() or "transmit" in name.lower():
                                    metrics["system_network_tx_bytes"] = (
                                        metrics.get("system_network_tx_bytes", 0) + value
                                    )
                                elif "received" in name.lower() or "receive" in name.lower():
                                    metrics["system_network_rx_bytes"] = (
                                        metrics.get("system_network_rx_bytes", 0) + value
                                    )

                        else:
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0]
                                value = float(parts[1])
                            else:
                                continue
                        metrics[name] = value
                    except:
                        continue

                # Store aggregated values
                if cpu_idle_total > 0:
                    metrics["windows_cpu_time_total_idle"] = cpu_idle_total
                    metrics["windows_cpu_time_total_all"] = cpu_all_total

                # Calculate disk percentages and get C: for main metric
                disks_list = []
                for vol, info in disk_info.items():
                    if info["size"] > 0:
                        info["percent"] = 100 * (1 - info["free"] / info["size"])
                        info["used_gb"] = round((info["size"] - info["free"]) / (1024**3), 1)
                        info["size_gb"] = round(info["size"] / (1024**3), 1)
                        disks_list.append(info)
                        # Use C: for main disk_percent if available
                        if "C:" in vol:
                            metrics["windows_logical_disk_free_bytes"] = info["free"]
                            metrics["windows_logical_disk_size_bytes"] = info["size"]

                disk_info_json = json.dumps(disks_list) if disks_list else None

                # Parse CPU - support both node_exporter and windows_exporter
                cpu = metrics.get("node_cpu_percent") or metrics.get("cpu_usage_percent") or 0
                if not cpu:
                    idle = metrics.get("windows_cpu_time_total_idle", 0)
                    total = metrics.get("windows_cpu_time_total_all", 0)
                    if total > 0:
                        cpu = 100 * (1 - idle / total) if idle < total else 0

                # Parse Memory - support both node_exporter and windows_exporter
                memory = metrics.get("node_memory_percent") or metrics.get("memory_usage_percent") or 0
                if not memory:
                    # windows_exporter v0.25+: windows_memory_physical_*
                    mem_total = metrics.get("windows_memory_physical_total_bytes", 0)
                    mem_free = metrics.get("windows_memory_physical_free_bytes", 0)
                    if mem_total > 0:
                        memory = 100 * (1 - mem_free / mem_total) if mem_free < mem_total else 0
                    # Fallback to older metric names
                    if not memory:
                        mem_total = metrics.get("windows_cs_physical_memory_bytes", 0)
                        mem_free = metrics.get("windows_os_physical_memory_free_bytes", 0)
                        if mem_total > 0:
                            memory = 100 * (1 - mem_free / mem_total) if mem_free < mem_total else 0

                # Parse Disk - support both node_exporter and windows_exporter
                disk = metrics.get("node_disk_percent") or metrics.get("disk_usage_percent") or 0
                if not disk:
                    disk_total = metrics.get("windows_logical_disk_size_bytes", 0)
                    disk_free = metrics.get("windows_logical_disk_free_bytes", 0)
                    if disk_total > 0:
                        disk = 100 * (1 - disk_free / disk_total) if disk_free < disk_total else 0

                network_rx = (
                    metrics.get("node_network_receive_bytes_total") or metrics.get("system_network_rx_bytes") or 0
                )
                network_tx = (
                    metrics.get("node_network_transmit_bytes_total") or metrics.get("system_network_tx_bytes") or 0
                )
                uptime = metrics.get("system_uptime_seconds") or metrics.get("windows_system_system_up_time", "") or ""

                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()

                conn = get_db()
                conn.execute(
                    """UPDATE servers SET
                    last_check = ?, last_status = 'up',
                    cpu_percent = ?, memory_percent = ?, disk_percent = ?,
                    network_rx = ?, network_tx = ?, uptime = ?, disk_info = ?
                    WHERE id = ?""",
                    (now, cpu, memory, disk, network_rx, network_tx, str(uptime), disk_info_json, server_id),
                )

                # Add to metrics history
                conn.execute(
                    """INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, disk_info, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (server_id, cpu, memory, disk, network_rx, network_tx, disk_info_json, now),
                )

                # Cleanup old history (keep 7 days)
                conn.execute("DELETE FROM metrics_history WHERE timestamp < datetime('now', '-7 days')")

                conn.commit()
                conn.close()

                return {
                    "status": "ok",
                    "message": f"Scraped {target}",
                    "metrics": {"cpu": cpu, "memory": memory, "disk": disk, "disks": disks_list},
                }
            else:
                # Update server as down
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()
                conn = get_db()
                conn.execute(
                    "UPDATE servers SET last_check = ?, last_status = ? WHERE id = ?", (now, "down", server_id)
                )
                conn.commit()
                conn.close()
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        # Update server as down
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        conn = get_db()
        conn.execute("UPDATE servers SET last_check = ?, last_status = ? WHERE id = ?", (now, "down", server_id))
        conn.commit()
        conn.close()
        return {"status": "error", "message": str(e)}


@router.get("/api/notifications")
async def get_notifications():
    conn = get_db()
    notifications = conn.execute("SELECT * FROM notifications").fetchall()
    conn.close()
    result = []
    for n in notifications:
        item = {"channel": n["channel"], "enabled": bool(n["enabled"])}
        item.update(json.loads(n["config"] or "{}"))
        result.append(item)
    return {"notifications": result}


@router.get("/api/raid-status")
async def get_raid_status():
    import asyncio
    import re

    import httpx

    telegraf_hosts = [
        "host-vm.it.ua:9273",
        "host-vm1.it.ua:9273",
        "host-vm2.it.ua:9273",
        "host-vm3.it.ua:9273",
        "host-vm4.it.ua:9273",
        "host-vm7.it.ua:9273",
        "host-vm8.it.ua:9273",
        "host-vm9.it.ua:9273",
        "host-vm10.it.ua:9273",
        "host-vm11.it.ua:9273",
        "host-vm12.it.ua:9273",
        "hst01.smarttender.biz.int:9273",
        "hst02.smarttender.biz.int:9273",
        "hst03.smarttender.biz.int:9273",
        "hst04.smarttender.biz.int:9273",
        "hst05.smarttender.biz.int:9273",
        "hst06.smarttender.biz.int:9273",
        "itdb01.it.ua:9273",
        "itdb02.it.ua:9273",
        "SMSDBAZ.it.ua:9273",
        "SMSDBAZ2.it.ua:9273",
        "TENDER.smarttender.biz.int:9273",
        "TENDER-SEC.smarttender.biz.int:9273",
        "TENDER-THIRD.smarttender.biz.int:9273",
        "10.0.12.4:9273",
        "TENDER-FS.smarttender.biz.int:9273",
    ]

    raid_data = []

    async def fetch_raid(host):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://{host}/metrics")
                if resp.status_code == 200:
                    raids = {}
                    server_name = host.split(":")[0]
                    for line in resp.text.split("\n"):
                        if line.startswith("prometheus_raid_status{"):
                            match = re.match(
                                r'prometheus_raid_status\{host="([^"]+)",id="([^"]+)",raid_type="([^"]+)",size="([^"]+)"\}\s+(\d+)',
                                line,
                            )
                            if match:
                                hname, raid_id, raid_type, size, status = match.groups()
                                server_name = hname
                                raids[raid_id] = {
                                    "id": raid_id,
                                    "type": raid_type,
                                    "size": size + " GB",
                                    "healthy": status == "1",
                                }

                    if raids:
                        all_healthy = all(r["healthy"] for r in raids.values())
                        return {"server": server_name, "raids": list(raids.values()), "healthy": all_healthy}
        except:
            pass
        return None

    # Fetch all hosts in parallel
    tasks = [fetch_raid(host) for host in telegraf_hosts]
    results = await asyncio.gather(*tasks)

    raid_data = [r for r in results if r is not None]

    return {"raid_status": raid_data}


@router.put("/api/notifications/{channel}")
async def update_notification(channel: str, config: dict):
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET enabled=?, config=? WHERE channel=?",
        (int(config.get("enabled", False)), json.dumps(config), channel),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.get("/api/servers/{server_id}/history")
async def get_server_history(server_id: int, range: str = "1h"):
    # Convert range to hours
    hours = 1
    if range == "5m":
        hours = 1 / 12
    elif range == "15m":
        hours = 0.25
    elif range == "6h":
        hours = 6
    elif range == "24h":
        hours = 24

    conn = get_db()
    history = conn.execute(
        f"SELECT * FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', '-{hours} hours') ORDER BY timestamp ASC",
        (server_id,),
    ).fetchall()
    conn.close()
    return {"history": [dict(h) for h in history]}


@router.get("/api/alerts")
async def list_alerts():

    conn = get_db()
    alerts = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"alerts": [dict(a) for a in alerts]}


@router.post("/api/alerts")
async def create_alert(alert: AlertModel):
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO alerts (name, metric, condition, threshold, duration, severity, server_id, notify_telegram, notify_discord, notify_slack, notify_email, description, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert.name,
                alert.metric,
                alert.condition,
                alert.threshold,
                alert.duration,
                alert.severity,
                alert.server_id,
                int(alert.notify_telegram),
                int(alert.notify_discord),
                int(alert.notify_slack),
                int(alert.notify_email),
                alert.description,
                int(alert.enabled),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"Error creating alert: {e}")
    conn.close()
    return {"status": "ok"}


@router.put("/api/alerts/{alert_id}")
async def update_alert(alert_id: int, alert: AlertModel):
    conn = get_db()
    conn.execute(
        """UPDATE alerts SET name=?, metric=?, condition=?, threshold=?, duration=?, severity=?, server_id=?, notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=?, description=?, enabled=? WHERE id=?""",
        (
            alert.name,
            alert.metric,
            alert.condition,
            alert.threshold,
            alert.duration,
            alert.severity,
            alert.server_id,
            int(alert.notify_telegram),
            int(alert.notify_discord),
            int(alert.notify_slack),
            int(alert.notify_email),
            alert.description,
            int(alert.enabled),
            alert_id,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    conn = get_db()
    conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Full Backup System
import shutil
import zipfile


@router.get("/api/backup/config")
async def get_backup_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'backup_%'").fetchall()
    config = {r["key"]: r["value"] for r in rows}
    conn.close()
    return {
        "auto_backup": config.get("backup_auto", "false") == "true",
        "backup_time": config.get("backup_time", "02:00"),
        "backup_path": config.get("backup_path", os.path.join(os.path.dirname(DB_PATH), "backups")),
        "keep_days": int(config.get("backup_keep_days", "30")),
        "last_backup": config.get("backup_last", ""),
    }


@router.post("/api/backup/config")
async def set_backup_config(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"backup_{key}", str(value)))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/api/backup/create")
async def create_full_backup(data: dict = {}):
    try:
        backup_path = data.get("path") if data else None
        if not backup_path:
            conn = get_db()
            row = conn.execute("SELECT value FROM settings WHERE key = 'backup_path'").fetchone()
            backup_path = row["value"] if row else os.path.join(os.path.dirname(DB_PATH), "backups")
            conn.close()

        os.makedirs(backup_path, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pymon_full_{timestamp}.zip"
        dest = os.path.join(backup_path, filename)

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            # Database
            if os.path.exists(DB_PATH):
                zf.write(DB_PATH, "pymon.db")

            # Config file
            config_path = os.path.join(os.path.dirname(DB_PATH), "config.yml")
            if os.path.exists(config_path):
                zf.write(config_path, "config.yml")

            # Export all settings as JSON
            conn = get_db()
            settings = {}
            for table in ["servers", "alerts", "notifications", "settings", "api_keys", "maintenance_windows"]:
                try:
                    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                    settings[table] = [dict(r) for r in rows]
                except:
                    settings[table] = []

            import json

            zf.writestr("settings.json", json.dumps(settings, indent=2, default=str))

            # Update last backup time
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("backup_last", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            conn.close()

        size = os.path.getsize(dest)

        # Log to backups table
        conn = get_db()
        conn.execute(
            "INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
            (filename, size, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        return {"status": "ok", "filename": filename, "size": size, "path": dest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/backup/restore")
async def restore_from_backup(data: dict):
    try:
        backup_file = data.get("file")
        if not backup_file or not os.path.exists(backup_file):
            raise HTTPException(status_code=400, detail="Backup file not found")

        restore_db = data.get("restore_db", True)
        restore_config = data.get("restore_config", True)
        restore_settings = data.get("restore_settings", True)

        with zipfile.ZipFile(backup_file, "r") as zf:
            # Restore database
            if restore_db and "pymon.db" in zf.namelist():
                # Backup current DB first
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, DB_PATH + ".pre_restore")
                zf.extract("pymon.db", os.path.dirname(DB_PATH))

            # Restore config
            if restore_config and "config.yml" in zf.namelist():
                zf.extract("config.yml", os.path.dirname(DB_PATH))

            # Restore settings
            if restore_settings and "settings.json" in zf.namelist():
                import json

                settings_data = json.loads(zf.read("settings.json").decode())
                conn = get_db()
                for table, rows in settings_data.items():
                    if rows:
                        try:
                            # Clear existing data
                            conn.execute(f"DELETE FROM {table}")
                            # Insert restored data
                            for row in rows:
                                cols = ", ".join([k for k in row.keys() if k != "id"])
                                vals = ", ".join(["?" for _ in row if _ != "id"])
                                placeholders = [row[k] for k in row.keys() if k != "id"]
                                if cols:
                                    conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})", placeholders)
                        except Exception as e:
                            print(f"Error restoring {table}: {e}")
                conn.commit()
                conn.close()

        return {"status": "ok", "message": "Backup restored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backup/list")
async def list_backup_files():
    try:
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = 'backup_path'").fetchone()
        backup_path = row["value"] if row else os.path.join(os.path.dirname(DB_PATH), "backups")
        conn.close()

        files = []
        if os.path.exists(backup_path):
            for f in os.listdir(backup_path):
                if f.endswith(".zip") or f.endswith(".sqlite"):
                    path = os.path.join(backup_path, f)
                    files.append(
                        {
                            "filename": f,
                            "path": path,
                            "size": os.path.getsize(path),
                            "created": datetime.fromtimestamp(os.path.getctime(path)).isoformat(),
                        }
                    )
        files.sort(key=lambda x: x["created"], reverse=True)
        return {"files": files, "backup_path": backup_path}
    except Exception as e:
        return {"files": [], "error": str(e)}


@router.delete("/api/backup/file")
async def delete_backup_file(data: dict):
    try:
        filepath = data.get("path")
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return {"status": "ok"}
        return {"status": "error", "message": "File not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/backup/cleanup")
async def cleanup_old_backups():
    try:
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = 'backup_keep_days'").fetchone()
        keep_days = int(row["value"]) if row else 30
        row = conn.execute("SELECT value FROM settings WHERE key = 'backup_path'").fetchone()
        backup_path = row["value"] if row else os.path.join(os.path.dirname(DB_PATH), "backups")
        conn.close()

        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        deleted = 0

        if os.path.exists(backup_path):
            for f in os.listdir(backup_path):
                filepath = os.path.join(backup_path, f)
                if os.path.getctime(filepath) < cutoff:
                    os.remove(filepath)
                    deleted += 1

        return {"status": "ok", "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Factory Reset
@router.post("/api/system/reset")
async def factory_reset(data: dict):
    try:
        confirm = data.get("confirm", "")
        if confirm != "RESET ALL DATA":
            raise HTTPException(status_code=400, detail="Confirmation required. Send 'confirm': 'RESET ALL DATA'")

        conn = get_db()
        # Clear all data tables
        tables = ["servers", "alerts", "api_keys", "audit_log", "maintenance_windows", "backups"]
        for table in tables:
            try:
                conn.execute(f"DELETE FROM {table}")
            except:
                pass

        # Reset notifications to defaults
        conn.execute("UPDATE notifications SET enabled = 0, config = '{}'")

        # Keep users but reset admin password
        conn.execute("UPDATE users SET password_hash = 'pbkdf2:sha256:admin' WHERE username = 'admin'")

        conn.commit()
        conn.close()

        return {"status": "ok", "message": "All data has been reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/clear-metrics")
async def clear_metrics_data():
    try:
        conn = get_db()
        # Clear metrics but keep server definitions
        conn.execute("""UPDATE servers SET
            last_check = NULL, last_status = NULL,
            cpu_percent = NULL, memory_percent = NULL, disk_percent = NULL,
            network_rx = NULL, network_tx = NULL, uptime = NULL,
            raid_status = NULL, disk_info = NULL""")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Metrics cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backups")
async def create_backup():
    try:
        BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        filename = f"pymon_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        dest = os.path.join(BACKUP_DIR, filename)
        import shutil

        shutil.copy2(DB_PATH, dest)
        size = os.path.getsize(dest)
        conn = get_db()
        conn.execute(
            "INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
            (filename, size, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backups")
async def list_backups():
    conn = get_db()
    backups = conn.execute("SELECT * FROM backups ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"backups": [dict(b) for b in backups]}


# API Keys
@router.get("/api/api-keys")
async def list_api_keys():
    conn = get_db()
    keys = conn.execute("SELECT id, name, created_at, last_used FROM api_keys ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"keys": [dict(k) for k in keys]}


@router.post("/api/api-keys")
async def create_api_key(data: dict):
    import hashlib
    import secrets

    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    name = data.get("name", "API Key")
    conn = get_db()
    conn.execute(
        "INSERT INTO api_keys (name, key_hash, created_at) VALUES (?, ?, ?)",
        (name, key_hash, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "key": key}


@router.delete("/api/api-keys/{key_id}")
async def delete_api_key(key_id: int):
    conn = get_db()
    conn.execute("DELETE FROM api_keys WHERE id=?", (key_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Audit Log
@router.get("/api/audit-log")
async def list_audit_log(limit: int = 100):
    conn = get_db()
    logs = conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"logs": [dict(l) for l in logs]}


def log_audit(user_id: int, action: str, details: str = "", ip: str = ""):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO audit_log (user_id, action, details, ip_address, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, action, details, ip, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except:
        pass


# Maintenance Windows
@router.get("/api/maintenance")
async def list_maintenance():
    conn = get_db()
    windows = conn.execute("SELECT * FROM maintenance_windows ORDER BY start_time").fetchall()
    conn.close()
    return {"windows": [dict(w) for w in windows]}


@router.post("/api/maintenance")
async def create_maintenance(data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO maintenance_windows (name, start_time, end_time, servers, enabled, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (
            data.get("name"),
            data.get("start_time"),
            data.get("end_time"),
            json.dumps(data.get("servers", [])),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.delete("/api/maintenance/{window_id}")
async def delete_maintenance(window_id: int):
    conn = get_db()
    conn.execute("DELETE FROM maintenance_windows WHERE id=?", (window_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Settings
@router.get("/api/settings")
async def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {"settings": {r["key"]: r["value"] for r in rows}}


@router.put("/api/settings")
async def update_settings(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Webhooks
@router.get("/api/webhooks")
async def list_webhooks():
    conn = get_db()
    webhooks = conn.execute("SELECT * FROM webhooks").fetchall()
    conn.close()
    return {"webhooks": [dict(w) for w in webhooks]}


@router.post("/api/webhooks")
async def create_webhook(data: dict):
    conn = get_db()
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )""")
        conn.execute(
            "INSERT INTO webhooks (name, url, events, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
            (
                data.get("name"),
                data.get("url"),
                json.dumps(data.get("events", [])),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except:
        pass
    conn.close()
    return {"status": "ok"}


@router.delete("/api/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: int):
    conn = get_db()
    conn.execute("DELETE FROM webhooks WHERE id=?", (webhook_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Health Check
@router.get("/api/health")
async def health_check():
    conn = get_db()
    servers_count = len(conn.execute("SELECT id FROM servers").fetchall())
    online_count = len(conn.execute("SELECT id FROM servers WHERE last_status = 'up'").fetchall())
    alerts_count = len(conn.execute("SELECT id FROM alerts WHERE enabled = 1").fetchall())
    conn.close()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "servers": {"total": servers_count, "online": online_count},
        "alerts": alerts_count,
    }
