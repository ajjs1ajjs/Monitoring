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

        c.execute("""CREATE TABLE IF NOT EXISTS notifications (
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )""")

        try:
            for channel in ["telegram", "discord", "slack", "email"]:
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
            description TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )""")

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
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon Enterprise</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0b0c0f; --card: #14161a; --card-hover: #1a1d22; --border: #262a30;
            --text: #e0e0e0; --muted: #8b8d98; --blue: #5794f2; --green: #73bf69;
            --red: #f2495c; --yellow: #f2cc0c; --purple: #b877d9; --cyan: #00d8d8;
            --blue-glow: rgba(87,148,242,0.15); --green-glow: rgba(115,191,105,0.15);
            --red-glow: rgba(242,73,92,0.15); --yellow-glow: rgba(242,204,12,0.15);
        }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; font-size: 13px; }
        .top-nav { background: linear-gradient(180deg, #1a1d22, #14161a); border-bottom: 1px solid var(--border); padding: 0 20px; height: 56px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--blue), #2c7bd9); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white; font-weight: bold; }
        .logo h1 { color: var(--blue); font-size: 20px; font-weight: 700; }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item { padding: 10px 18px; border-radius: 8px; cursor: pointer; color: var(--muted); font-size: 13px; background: transparent; border: none; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active { background: var(--blue-glow); color: var(--blue); }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .time-range { display: flex; gap: 2px; background: var(--card); border-radius: 8px; padding: 3px; }
        .time-btn { padding: 6px 14px; background: transparent; border: none; border-radius: 5px; color: var(--muted); font-size: 12px; cursor: pointer; }
        .time-btn.active { background: var(--blue); color: white; }
        .btn { padding: 8px 16px; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; }
        .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
        .btn-danger { background: linear-gradient(135deg, rgba(242,73,92,0.3), rgba(242,73,92,0.15)); color: var(--red); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .main { padding: 20px; max-width: 1920px; margin: 0 auto; }
        .stats-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
        .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .stat-value { font-size: 28px; font-weight: 700; }
        .stat-label { color: var(--muted); font-size: 12px; margin-top: 4px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .grid-item { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .grid-item.col-4 { grid-column: span 4; }
        .grid-item.col-6 { grid-column: span 6; }
        .grid-item.col-8 { grid-column: span 8; }
        .grid-item.col-12 { grid-column: span 12; }
        .panel { height: 100%; display: flex; flex-direction: column; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); }
        .panel-title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .panel-body { flex: 1; padding: 16px; min-height: 200px; }
        .chart-container { width: 100%; height: 250px; }
        .chart-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; }
        .legend-item { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
        .legend-item:hover { background: rgba(255,255,255,0.05); }
        .legend-color { width: 12px; height: 12px; border-radius: 3px; }
        .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; max-height: 500px; overflow-y: auto; }
        .server-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; cursor: pointer; transition: all 0.2s; }
        .server-card.online { border-left: 3px solid var(--green); }
        .server-card.offline { border-left: 3px solid var(--red); }
        .server-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
        .server-name { font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .server-status { width: 8px; height: 8px; border-radius: 50%; }
        .server-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .metric-box { background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center; }
        .metric-label { font-size: 10px; color: var(--muted); text-transform: uppercase; }
        .metric-value { font-size: 18px; font-weight: 600; }
        .metric-progress { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; margin-top: 6px; }
        .metric-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        tr:hover td { background: rgba(255,255,255,0.02); }
        .badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
        .badge-success { background: var(--green-glow); color: var(--green); }
        .badge-danger { background: var(--red-glow); color: var(--red); }
        .badge-warning { background: var(--yellow-glow); color: var(--yellow); }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 24px; cursor: pointer; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 600; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 13px; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
        .tab { padding: 12px 20px; color: var(--muted); cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; }
        .tab.active { color: var(--blue); border-bottom-color: var(--blue); }
        .section-content { display: none; }
        .section-content.active { display: block; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="logo"><div class="logo-icon">P</div><h1>PyMon</h1></div>
        <div class="nav-menu">
            <button class="nav-item active" data-section="dashboard"><i class="fas fa-chart-line"></i> Dashboard</button>
            <button class="nav-item" data-section="servers"><i class="fas fa-server"></i> Servers</button>
            <button class="nav-item" data-section="alerts"><i class="fas fa-bell"></i> Alerts</button>
            <button class="nav-item" data-section="settings"><i class="fas fa-cog"></i> Settings</button>
        </div>
        <div class="nav-right">
            <div class="time-range">
                <button class="time-btn" data-range="5m">5m</button>
                <button class="time-btn" data-range="15m">15m</button>
                <button class="time-btn active" data-range="1h">1h</button>
                <button class="time-btn" data-range="6h">6h</button>
                <button class="time-btn" data-range="24h">24h</button>
            </div>
            <button class="btn btn-secondary btn-sm" id="refreshBtn"><i class="fas fa-sync"></i></button>
            <button class="btn btn-secondary btn-sm" id="logoutBtn"><i class="fas fa-sign-out-alt"></i></button>
        </div>
    </nav>
    
    <main class="main">
        <!-- Dashboard Section -->
        <div id="section-dashboard" class="section-content active">
            <div class="stats-overview">
                <div class="stat-card" onclick="filterBy('online')">
                    <div class="stat-icon" style="background: var(--green-glow); color: var(--green);"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-online" style="color: var(--green);">0</div>
                        <div class="stat-label">Online Servers</div>
                    </div>
                </div>
                <div class="stat-card" onclick="filterBy('offline')">
                    <div class="stat-icon" style="background: var(--red-glow); color: var(--red);"><i class="fas fa-times-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-offline" style="color: var(--red);">0</div>
                        <div class="stat-label">Offline Servers</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--blue-glow); color: var(--blue);"><i class="fas fa-microchip"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-cpu-avg">0%</div>
                        <div class="stat-label">Avg CPU Usage</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--yellow-glow); color: var(--yellow);"><i class="fas fa-memory"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-mem-avg">0%</div>
                        <div class="stat-label">Avg Memory Usage</div>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-microchip" style="color: var(--blue);"></i> CPU Usage</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="cpuChart"></canvas></div>
                            <div class="chart-legend" id="cpuLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-memory" style="color: var(--yellow);"></i> Memory Usage</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="memoryChart"></canvas></div>
                            <div class="chart-legend" id="memoryLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-hdd" style="color: var(--green);"></i> Disk Usage (All Partitions)</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="diskChart"></canvas></div>
                            <div class="chart-legend" id="diskLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-network-wired" style="color: var(--purple);"></i> Network Traffic</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="networkChart"></canvas></div>
                            <div class="chart-legend" id="networkLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-12">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-server" style="color: var(--cyan);"></i> Server Map</div>
                            <div style="display: flex; gap: 12px;">
                                <input type="text" id="serverSearch" placeholder="Search servers..." style="padding: 6px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); width: 200px;">
                                <button class="btn btn-primary btn-sm" id="addServerBtnDashboard"><i class="fas fa-plus"></i> Add Server</button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="server-grid" id="serverGrid"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Servers Section -->
        <div id="section-servers" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title"><i class="fas fa-server"></i> Monitored Servers</div>
                        <button class="btn btn-primary btn-sm" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <table id="serversTable"><thead><tr><th>Status</th><th>Name</th><th>Host:Port</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last Check</th><th>Actions</th></tr></thead><tbody></tbody></table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Alerts Section -->
        <div id="section-alerts" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title"><i class="fas fa-bell"></i> Alert Rules</div>
                        <button class="btn btn-primary btn-sm" id="addAlertBtn"><i class="fas fa-plus"></i> New Alert</button>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div id="alertsList"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Settings Section -->
        <div id="section-settings" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><i class="fas fa-cog"></i> Settings</div></div>
                    <div class="panel-body">
                        <div class="tabs">
                            <div class="tab active" data-tab="notifications">Notifications</div>
                            <div class="tab" data-tab="backups">Backups</div>
                            <div class="tab" data-tab="api">API Keys</div>
                        </div>
                        <div id="tab-notifications">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                                <div style="padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                                    <h4 style="margin-bottom: 12px; color: var(--cyan);"><i class="fab fa-telegram"></i> Telegram</h4>
                                    <div class="form-group"><label style="display: flex; gap: 8px; align-items: center;"><input type="checkbox" id="telegram-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Bot Token</label><input type="text" id="telegram-token" placeholder="123456789:ABCdef..."></div>
                                    <div class="form-group"><label>Chat ID</label><input type="text" id="telegram-chat" placeholder="-1001234567890"></div>
                                </div>
                                <div style="padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                                    <h4 style="margin-bottom: 12px; color: #5865F2;"><i class="fab fa-discord"></i> Discord</h4>
                                    <div class="form-group"><label style="display: flex; gap: 8px; align-items: center;"><input type="checkbox" id="discord-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Webhook URL</label><input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/..."></div>
                                </div>
                            </div>
                            <button class="btn btn-primary" style="margin-top: 16px;" id="saveNotifyBtn"><i class="fas fa-save"></i> Save Settings</button>
                        </div>
                        <div id="tab-backups" style="display: none;">
                            <button class="btn btn-primary" id="createBackupBtn"><i class="fas fa-download"></i> Create Backup</button>
                            <div style="margin-top: 16px;"><table id="backupsTable"><thead><tr><th>Filename</th><th>Size</th><th>Created</th></tr></thead><tbody></tbody></table></div>
                        </div>
                        <div id="tab-api" style="display: none;">
                            <button class="btn btn-primary" id="createApiKeyBtn"><i class="fas fa-plus"></i> Generate Key</button>
                            <div style="margin-top: 16px;"><table id="apiKeysTable"><thead><tr><th>Name</th><th>Created</th><th>Last Used</th><th>Actions</th></tr></thead><tbody></tbody></table></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <!-- Modals -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title">Add Server</div><button class="modal-close" id="closeServerModal">&times;</button></div>
            <form id="addServerForm">
                <div class="form-group"><label>Server Name</label><input type="text" id="server-name" required placeholder="Production Server"></div>
                <div class="form-group"><label>Host / IP Address</label><input type="text" id="server-host" required placeholder="192.168.1.100"></div>
                <div class="form-row">
                    <div class="form-group"><label>Operating System</label><select id="server-os"><option value="linux">Linux (node_exporter:9100)</option><option value="windows">Windows (windows_exporter:9182)</option></select></div>
                    <div class="form-group"><label>Agent Port</label><input type="number" id="server-port" value="9100"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Add Server</button>
            </form>
        </div>
    </div>
    
    <div class="modal" id="alertModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title" id="alertModalTitle">Add Alert</div><button class="modal-close" id="closeAlertModal">&times;</button></div>
            <form id="alertForm">
                <input type="hidden" id="alert-id">
                <div class="form-group"><label>Alert Name</label><input type="text" id="alert-name" required placeholder="High CPU Alert"></div>
                <div class="form-row">
                    <div class="form-group"><label>Server (optional)</label><select id="alert-server"><option value="">Global (All Servers)</option></select></div>
                    <div class="form-group"><label>Metric</label><select id="alert-metric"><option value="cpu">CPU Usage</option><option value="memory">Memory</option><option value="disk">Disk</option><option value="network">Network</option></select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Condition</label><select id="alert-condition"><option value=">">Greater than</option><option value="<">Less than</option></select></div>
                    <div class="form-group"><label>Threshold (%)</label><input type="number" id="alert-threshold" value="80"></div>
                </div>
                <div class="form-group"><label>Severity</label><select id="alert-severity"><option value="warning">Warning</option><option value="critical">Critical</option></select></div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Save Alert</button>
            </form>
        </div>
    </div>

<script>
const token = localStorage.getItem('token');
if (!token) window.location.href = '/login';
let servers = [];
let charts = {};
let currentRange = '1h';
const colors = ['#73bf69', '#f2cc0c', '#5794f2', '#ff780a', '#b877d9', '#00d8d8', '#f2495c', '#9673b9'];

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', function() { showSection(this.dataset.section); }));
document.querySelectorAll('.time-btn').forEach(btn => btn.addEventListener('click', function() { document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active')); this.classList.add('active'); currentRange = this.dataset.range; loadData(); }));
document.getElementById('logoutBtn').addEventListener('click', () => { localStorage.removeItem('token'); window.location.href = '/login'; });
document.getElementById('refreshBtn').addEventListener('click', () => loadData());
document.getElementById('addServerBtn').addEventListener('click', () => document.getElementById('addServerModal').classList.add('active'));
document.getElementById('addServerBtnDashboard').addEventListener('click', () => document.getElementById('addServerModal').classList.add('active'));
document.getElementById('closeServerModal').addEventListener('click', () => document.getElementById('addServerModal').classList.remove('active'));
document.getElementById('serverSearch').addEventListener('input', updateServerGrid);
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', function() { document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); this.classList.add('active'); document.querySelectorAll('[id^="tab-"]').forEach(d => d.style.display = 'none'); document.getElementById('tab-' + this.dataset.tab).style.display = 'block'; }));

document.getElementById('addServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const port = parseInt(document.getElementById('server-port').value) || (document.getElementById('server-os').value === 'windows' ? 9182 : 9100);
    await fetch('/api/servers', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({ name: document.getElementById('server-name').value, host: document.getElementById('server-host').value, os_type: document.getElementById('server-os').value, agent_port: port }) });
    document.getElementById('addServerModal').classList.remove('active');
    document.getElementById('addServerForm').reset();
    loadData();
});

document.getElementById('saveNotifyBtn').addEventListener('click', async () => {
    const config = {
        telegram: { enabled: document.getElementById('telegram-enabled').checked, telegram_bot_token: document.getElementById('telegram-token').value, telegram_chat_id: document.getElementById('telegram-chat').value },
        discord: { enabled: document.getElementById('discord-enabled').checked, discord_webhook: document.getElementById('discord-webhook').value }
    };
    for (const [channel, cfg] of Object.entries(config)) {
        await fetch('/api/notifications/' + channel, { method: 'PUT', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify(cfg) });
    }
    alert('Settings saved!');
});

document.getElementById('createBackupBtn').addEventListener('click', async () => {
    const resp = await fetch('/api/backup/create', { method: 'POST', headers: {'Authorization': 'Bearer ' + token} });
    const data = await resp.json();
    if (data.status === 'ok') { alert('Backup created!'); loadBackups(); } else { alert('Error: ' + data.detail); }
});

document.getElementById('createApiKeyBtn').addEventListener('click', async () => {
    const name = prompt('Enter API key name:');
    if (name) {
        const resp = await fetch('/api/api-keys', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name}) });
        const data = await resp.json();
        if (data.key) { alert('API Key created! Copy it now:\n\n' + data.key); loadApiKeys(); }
    }
});

document.getElementById('addAlertBtn').addEventListener('click', () => { document.getElementById('alert-id').value = ''; document.getElementById('alertForm').reset(); document.getElementById('alertModalTitle').textContent = 'Add Alert'; document.getElementById('alertModal').classList.add('active'); });
document.getElementById('closeAlertModal').addEventListener('click', () => document.getElementById('alertModal').classList.remove('active'));
document.getElementById('alertForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('alert-id').value;
    const data = { name: document.getElementById('alert-name').value, metric: document.getElementById('alert-metric').value, condition: document.getElementById('alert-condition').value, threshold: parseInt(document.getElementById('alert-threshold').value), severity: document.getElementById('alert-severity').value, server_id: document.getElementById('alert-server').value || null, enabled: true };
    const url = id ? '/api/alerts/' + id : '/api/alerts';
    const method = id ? 'PUT' : 'POST';
    await fetch(url, { method, headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify(data) });
    document.getElementById('alertModal').classList.remove('active');
    loadAlerts();
});

function showSection(section) {
    document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById('section-' + section)?.classList.add('active');
    document.querySelector(`.nav-item[data-section="${section}"]`)?.classList.add('active');
    if (section === 'settings') { loadNotifications(); loadBackups(); loadApiKeys(); }
}

async function loadData() {
    try {
        const resp = await fetch('/api/servers', {headers: {'Authorization': 'Bearer ' + token}});
        const data = await resp.json();
        servers = data.servers || [];
        updateStats();
        updateCharts();
        updateServerGrid();
        updateServerTable();
        loadAlerts();
        populateAlertServerSelect();
    } catch(e) { console.error(e); }
}

function updateStats() {
    const online = servers.filter(s => s.last_status === 'up').length;
    const offline = servers.length - online;
    const cpuAvg = servers.length ? (servers.reduce((a, s) => a + (s.cpu_percent || 0), 0) / servers.length).toFixed(1) : 0;
    const memAvg = servers.length ? (servers.reduce((a, s) => a + (s.memory_percent || 0), 0) / servers.length).toFixed(1) : 0;
    document.getElementById('stat-online').textContent = online;
    document.getElementById('stat-offline').textContent = offline;
    document.getElementById('stat-cpu-avg').textContent = cpuAvg + '%';
    document.getElementById('stat-mem-avg').textContent = memAvg + '%';
}

async function updateCharts() {
    const labels = generateLabels();
    if (!charts.cpu) {
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.memory = new Chart(document.getElementById('memoryChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.disk = new Chart(document.getElementById('diskChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.network = new Chart(document.getElementById('networkChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts(' MB/s', 0, null)});
    }
    
    const histories = await Promise.all(servers.map(s => fetchServerHistory(s.id)));
    
    const cpuData = [], memData = [], diskData = [], netData = [];
    servers.forEach((s, i) => {
        const h = histories[i] || [];
        const color = colors[i % colors.length];
        const common = {label: s.name, borderColor: color, backgroundColor: color + '20', fill: true, tension: 0.3};
        cpuData.push({...common, data: h.length ? h.map(x => x.cpu_percent) : rand(12, s.cpu_percent || 30, 20)});
        memData.push({...common, data: h.length ? h.map(x => x.memory_percent) : rand(12, s.memory_percent || 40, 15)});
        netData.push({...common, data: h.length ? h.map(x => (x.network_rx || 0) / 1024 / 1024) : rand(12, 10, 5)});
        
        // Parse disk_info for multiple disks
        const diskMap = {};
        h.forEach(x => {
            if (x.disk_info) {
                try {
                    const info = typeof x.disk_info === 'string' ? JSON.parse(x.disk_info) : x.disk_info;
                    if (Array.isArray(info)) {
                        info.forEach(d => {
                            const vol = d.volume || d.path || '?';
                            if (!diskMap[vol]) diskMap[vol] = new Array(h.length).fill(null);
                            diskMap[vol][h.indexOf(x)] = d.percent;
                        });
                    }
                } catch(e) {}
            }
        });
        
        if (Object.keys(diskMap).length > 0) {
            Object.keys(diskMap).forEach((vol, j) => {
                diskData.push({...common, label: s.name + ' (' + vol + ')', borderColor: colors[(i + j) % colors.length], backgroundColor: colors[(i + j) % colors.length] + '20', data: diskMap[vol]});
            });
        } else {
            diskData.push({...common, data: h.length ? h.map(x => x.disk_percent) : rand(12, s.disk_percent || 50, 10)});
        }
    });
    
    charts.cpu.data.datasets = cpuData.length ? cpuData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.cpu.update();
    updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
    
    charts.memory.data.datasets = memData.length ? memData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.memory.update();
    updateLegend('memoryLegend', charts.memory.data.datasets, '%');
    
    charts.disk.data.datasets = diskData.length ? diskData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.disk.update();
    updateLegend('diskLegend', charts.disk.data.datasets, '%');
    
    charts.network.data.datasets = netData.length ? netData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.network.update();
    updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
}

async function fetchServerHistory(id) {
    try {
        const resp = await fetch(`/api/servers/${id}/history?range=${currentRange}`, {headers: {'Authorization': 'Bearer ' + token}});
        const data = await resp.json();
        return data.history || [];
    } catch(e) { return []; }
}

function updateLegend(id, datasets, unit) {
    const el = document.getElementById(id);
    el.innerHTML = datasets.map(ds => `<div class="legend-item"><div class="legend-color" style="background: ${ds.borderColor}"></div><span>${ds.label}</span><span style="margin-left: auto; color: var(--muted);">${ds.data[ds.data.length-1]?.toFixed(1) || 0}${unit}</span></div>`).join('');
}

function updateServerGrid() {
    const search = document.getElementById('serverSearch').value.toLowerCase();
    const filtered = servers.filter(s => !search || s.name.toLowerCase().includes(search) || s.host.toLowerCase().includes(search));
    const el = document.getElementById('serverGrid');
    el.innerHTML = filtered.map(s => {
        const status = s.last_status === 'up' ? 'online' : 'offline';
        const statusColor = s.last_status === 'up' ? 'var(--green)' : 'var(--red)';
        const cpuColor = (s.cpu_percent || 0) > 80 ? 'var(--red)' : (s.cpu_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        const memColor = (s.memory_percent || 0) > 80 ? 'var(--red)' : (s.memory_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        return `
        <div class="server-card ${status}" onclick="scrapeServer(${s.id})">
            <div class="server-header">
                <div class="server-name"><div class="server-status" style="background: ${statusColor}"></div>${s.name}</div>
                <span style="color: var(--muted); font-size: 11px;">${s.os_type}</span>
            </div>
            <div class="server-metrics">
                <div class="metric-box">
                    <div class="metric-label">CPU</div>
                    <div class="metric-value" style="color: ${cpuColor}">${(s.cpu_percent || 0).toFixed(1)}%</div>
                    <div class="metric-progress"><div class="metric-fill" style="width: ${s.cpu_percent || 0}%; background: ${cpuColor}"></div></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Memory</div>
                    <div class="metric-value" style="color: ${memColor}">${(s.memory_percent || 0).toFixed(1)}%</div>
                    <div class="metric-progress"><div class="metric-fill" style="width: ${s.memory_percent || 0}%; background: ${memColor}"></div></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Disk</div>
                    <div class="metric-value" style="color: var(--blue)">${(s.disk_percent || 0).toFixed(1)}%</div>
                </div>
            </div>
        </div>`;
    }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No servers</p>';
}

function updateServerTable() {
    const el = document.querySelector('#serversTable tbody');
    el.innerHTML = servers.map(s => {
        const statusBadge = s.last_status === 'up' ? '<span class="badge badge-success"><i class="fas fa-circle"></i> Online</span>' : '<span class="badge badge-danger"><i class="fas fa-circle"></i> Offline</span>';
        return `<tr>
            <td>${statusBadge}</td>
            <td><strong>${s.name}</strong></td>
            <td style="color: var(--muted)">${s.host}:${s.agent_port || 9100}</td>
            <td>${s.os_type}</td>
            <td>${(s.cpu_percent || 0).toFixed(1)}%</td>
            <td>${(s.memory_percent || 0).toFixed(1)}%</td>
            <td>${(s.disk_percent || 0).toFixed(1)}%</td>
            <td style="color: var(--muted)">${s.last_check ? s.last_check.substring(11, 19) : '-'}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="scrapeServer(${s.id}); event.stopPropagation();"><i class="fas fa-sync"></i></button>
                <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id}); event.stopPropagation();"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" style="text-align: center; padding: 40px; color: var(--muted);">No servers configured</td></tr>';
}

async function loadAlerts() {
    const resp = await fetch('/api/alerts', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const alerts = data.alerts || [];
    const el = document.getElementById('alertsList');
    el.innerHTML = alerts.length ? alerts.map(a => `
        <div style="padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 600;">${a.name}</div>
                <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">${a.metric.toUpperCase()} ${a.condition} ${a.threshold}%</div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="badge ${a.severity === 'critical' ? 'badge-danger' : 'badge-warning'}">${a.severity}</span>
                <button class="btn btn-danger btn-sm" onclick="deleteAlert(${a.id})"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('') : '<p style="color: var(--muted); text-align: center; padding: 40px;">No alert rules configured</p>';
}

function populateAlertServerSelect() {
    const el = document.getElementById('alert-server');
    el.innerHTML = '<option value="">Global (All Servers)</option>' + servers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function loadNotifications() {
    const resp = await fetch('/api/notifications', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    (data.notifications || []).forEach(n => {
        if (n.channel === 'telegram') {
            document.getElementById('telegram-enabled').checked = n.enabled;
            document.getElementById('telegram-token').value = n.telegram_bot_token || '';
            document.getElementById('telegram-chat').value = n.telegram_chat_id || '';
        }
        if (n.channel === 'discord') {
            document.getElementById('discord-enabled').checked = n.enabled;
            document.getElementById('discord-webhook').value = n.discord_webhook || '';
        }
    });
}

async function loadBackups() {
    const resp = await fetch('/api/backup/list', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const files = data.files || [];
    document.querySelector('#backupsTable tbody').innerHTML = files.map(f => `<tr><td>${f.filename}</td><td>${(f.size/1024).toFixed(1)} KB</td><td>${f.created ? f.created.substring(0, 19) : '-'}</td></tr>`).join('') || '<tr><td colspan="3" style="text-align: center; color: var(--muted);">No backups</td></tr>';
}

async function loadApiKeys() {
    const resp = await fetch('/api/api-keys', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const keys = data.keys || [];
    document.querySelector('#apiKeysTable tbody').innerHTML = keys.map(k => `<tr><td>${k.name}</td><td>${k.created_at ? k.created_at.substring(0, 19) : '-'}</td><td>${k.last_used || 'Never'}</td><td><button class="btn btn-danger btn-sm" onclick="deleteApiKey(${k.id})"><i class="fas fa-trash"></i></button></td></tr>`).join('') || '<tr><td colspan="4" style="text-align: center; color: var(--muted);">No API keys</td></tr>';
}

async function scrapeServer(id) {
    try {
        const btn = event?.target?.closest('button') || document.body;
        const icon = btn.querySelector('i');
        if (icon) icon.classList.add('animate-spin');
        await fetch(`/api/servers/${id}/scrape`, { method: 'POST', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
        setTimeout(() => icon?.classList.remove('animate-spin'), 500);
    } catch(e) { alert('Error: ' + e.message); }
}

async function deleteServer(id) {
    if (confirm('Delete this server?')) {
        await fetch(`/api/servers/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
    }
}

async function deleteAlert(id) {
    if (confirm('Delete this alert?')) {
        await fetch(`/api/alerts/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadAlerts();
    }
}

async function deleteApiKey(id) {
    if (confirm('Delete this API key?')) {
        await fetch(`/api/api-keys/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadApiKeys();
    }
}

function filterBy(type) {
    if (type === 'online') { document.getElementById('serverSearch').value = ''; }
    else if (type === 'offline') { document.getElementById('serverSearch').value = ''; }
}

function generateLabels() {
    const labels = [];
    const now = new Date();
    for (let i = 11; i >= 0; i--) { const t = new Date(now.getTime() - i * 5 * 60000); labels.push(t.getHours().toString().padStart(2,'0') + ':' + t.getMinutes().toString().padStart(2,'0')); }
    return labels;
}

function rand(n, base, variance) { const arr = []; let val = base; for (let i = 0; i < n; i++) { val = Math.max(0, Math.min(100, val + (Math.random() - 0.5) * variance)); arr.push(val); } return arr; }

function chartOpts(suffix, min, max) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        scales: {
            y: { min, max, grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#666', font: { size: 10 }, callback: v => v + suffix } },
            x: { grid: { display: false }, ticks: { color: '#666', font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
    };
}

setInterval(loadData, 30000);
loadData();
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
                                    if not any(x in mount for x in ['/proc', '/sys', '/dev', '/run', '/tmp']):
                                        if mount not in disk_info:
                                            disk_info[mount] = {"volume": mount, "free": 0, "size": 0}
                                        disk_info[mount]["free"] = value
                            if name == "node_filesystem_size_bytes":
                                import re
                                mount_match = re.search(r'mountpoint="([^"]+)"', labels_part)
                                if mount_match:
                                    mount = mount_match.group(1)
                                    if not any(x in mount for x in ['/proc', '/sys', '/dev', '/run', '/tmp']):
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
                conn.execute(
                    "DELETE FROM metrics_history WHERE timestamp < datetime('now', '-7 days')"
                )

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
    if range == "5m": hours = 1/12
    elif range == "15m": hours = 0.25
    elif range == "6h": hours = 6
    elif range == "24h": hours = 24

    conn = get_db()
    history = conn.execute(
        f"SELECT * FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', '-{hours} hours') ORDER BY timestamp ASC",
        (server_id,)
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
