"""Enterprise Server Monitoring Dashboard"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import os
from datetime import datetime

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "/var/lib/pymon/pymon.db")

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
    agent_port: int = 9100
    check_interval: int = 15
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
        
        c.execute('''CREATE TABLE IF NOT EXISTS servers (
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
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )''')
        
        try:
            for channel in ['telegram', 'discord', 'slack', 'email']:
                c.execute("INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,))
        except:
            pass
        
        try:
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                last_login TEXT
            )''')
            c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', 'pbkdf2:sha256:admin', 'admin')")
        except:
            pass
        
        c.execute('''CREATE TABLE IF NOT EXISTS alerts (
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
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS security (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            size_bytes INTEGER,
            created_at TEXT
        )''')

        conn.commit()
        conn.close()
        print("All tables initialized")
    except Exception as e:
        print(f"Error initializing web tables: {e}")

LOGIN_HTML = r'''<!DOCTYPE html>
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
</html>'''

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Server Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0d0f14; --card: #181b1f; --border: #2c3235; --text: #e0e0e0; --muted: #999; --blue: #5794f2; --green: #73bf69; --red: #f2495c; --yellow: #f2cc0c; --purple: #b877d9; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; font-size: 13px; }
        .top-nav { background: linear-gradient(90deg, #1a1d24, #252930); border-bottom: 1px solid var(--border); padding: 0 16px; display: flex; justify-content: space-between; align-items: center; height: 52px; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 12px rgba(0,0,0,0.5); }
        .nav-left { display: flex; align-items: center; gap: 20px; }
        .logo { display: flex; align-items: center; gap: 8px; }
        .logo-icon { width: 24px; height: 24px; background: linear-gradient(135deg, var(--blue), #2c7bd9); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: white; font-weight: bold; }
        .logo h1 { color: var(--blue); font-size: 18px; font-weight: 600; }
        .nav-menu { display: flex; gap: 2px; }
        .nav-item { display: flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 6px; cursor: pointer; color: var(--muted); font-weight: 500; font-size: 12px; border: none; background: transparent; transition: all 0.2s; }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.1); transform: translateY(-1px); }
        .nav-item.active { background: linear-gradient(135deg, rgba(87,148,242,0.3), rgba(44,123,217,0.3)); color: var(--blue); box-shadow: 0 2px 8px rgba(87,148,242,0.3); }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .server-selector { padding: 5px 10px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 12px; min-width: 150px; }
        .main { padding: 16px; }
        .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
        .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); transition: all 0.2s; }
        .stat-card:hover, .stat-card.clickable { cursor: pointer; transform: translateY(-2px); }
        .stat-card.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
        .stat-card.active { border-color: var(--blue); box-shadow: 0 0 12px rgba(87,148,242,0.4); }
        .stat-icon { width: 40px; height: 40px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .stat-value { font-size: 24px; font-weight: 600; }
        .stat-label { color: var(--muted); font-size: 12px; }
        .dashboard-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 8px 12px; background: var(--card); border: 1px solid var(--border); border-radius: 4px; }
        .time-range { display: flex; gap: 2px; background: #111217; border-radius: 4px; padding: 2px; border: 1px solid var(--border); }
        .time-btn { padding: 4px 10px; background: transparent; border: none; border-radius: 3px; color: var(--muted); font-size: 12px; cursor: pointer; }
        .time-btn.active { background: #2c3235; color: var(--text); }
        .panels-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .panel { background: var(--card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.3); transition: all 0.3s; }
        .panel.expanded { grid-column: span 2; }
        .panel.expanded .panel-body { height: 350px; }
        .panel-body { display: flex; height: 180px; }
        .panel-chart { flex: 1; padding: 8px; position: relative; min-width: 0; }
        .panel-legend { width: 280px; border-left: 1px solid var(--border); background: rgba(0,0,0,0.2); overflow-y: auto; font-size: 11px; flex-shrink: 0; }
        .legend-header { display: flex; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted); font-size: 10px; text-transform: uppercase; font-weight: 600; }
        .legend-header-name { flex: 1; text-align: left; }
        .legend-header-last { width: 45px; text-align: right; }
        .legend-header-max { width: 45px; text-align: right; }
        .legend-item { display: flex; padding: 6px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); }
        .legend-color { width: 8px; height: 8px; border-radius: 2px; margin-right: 8px; margin-top: 2px; flex-shrink: 0; }
        .legend-name { flex: 1; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .legend-value-last { width: 45px; text-align: right; font-size: 11px; color: var(--muted); }
        .legend-value-max { width: 45px; text-align: right; font-size: 11px; color: var(--muted); }
        .legend-item { display: flex; align-items: center; padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); gap: 12px; }
        .legend-color { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
        .legend-name { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; min-width: 80px; flex: 1; }
        .legend-value { color: var(--muted); text-align: right; font-size: 12px; flex-shrink: 0; width: 50px; }
        .legend-item { display: flex; align-items: center; padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); gap: 8px; }
        .legend-color { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
        .legend-name { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; min-width: 0; flex: 1; }
        .legend-value { color: var(--muted); text-align: center; font-size: 11px; flex-shrink: 0; width: 45px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .card-title { font-size: 14px; font-weight: 600; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        .btn { padding: 8px 16px; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; box-shadow: 0 2px 8px rgba(44,123,217,0.4); }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(44,123,217,0.6); }
        .btn-secondary { background: rgba(255,255,255,0.08); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: rgba(255,255,255,0.12); }
        .btn-danger { background: linear-gradient(135deg, rgba(242,73,92,0.3), rgba(242,73,92,0.15)); color: var(--red); }
        .btn-danger:hover { background: linear-gradient(135deg, rgba(242,73,92,0.5), rgba(242,73,92,0.3)); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 24px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 20px; cursor: pointer; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 13px; }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: var(--blue); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .section-content { display: none; }
        .section-content.active { display: block; }
        .install-box { background: rgba(87,148,242,0.05); border: 1px solid rgba(87,148,242,0.2); border-radius: 4px; padding: 16px; margin-top: 12px; }
        .install-box h4 { margin-bottom: 10px; color: var(--blue); font-size: 13px; font-weight: 600; }
        .code-block { position: relative; background: #111217; border: 1px solid var(--border); border-radius: 4px; margin: 10px 0; }
        .code-block code { display: block; padding: 12px; font-family: Monaco,Consolas,monospace; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; color: var(--text); }
        .copy-btn { position: absolute; top: 8px; right: 8px; padding: 4px 8px; background: rgba(255,255,255,0.1); border: none; border-radius: 3px; color: var(--muted); font-size: 11px; cursor: pointer; }
        .install-step { display: flex; gap: 12px; margin-bottom: 16px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 4px; border-left: 3px solid var(--blue); }
        .step-number { width: 24px; height: 24px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
        .step-title { font-weight: 600; margin-bottom: 4px; font-size: 13px; }
        .alert-rule { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 4px; padding: 16px; margin-bottom: 12px; }
        .alert-rule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .alert-rule-title { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .alert-conditions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
        .condition-box { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 4px; font-size: 12px; }
        .condition-label { color: var(--muted); margin-bottom: 4px; font-size: 11px; text-transform: uppercase; }
        .condition-value { font-weight: 600; color: var(--text); font-size: 13px; }
        .notification-tag { padding: 4px 10px; background: rgba(87,148,242,0.15); border-radius: 3px; font-size: 11px; color: var(--blue); margin-right: 6px; }
        .tab-menu { display: flex; gap: 2px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
        .tab-item { padding: 8px 16px; cursor: pointer; color: var(--muted); font-weight: 500; border-bottom: 2px solid transparent; }
        .tab-item.active { color: var(--blue); border-bottom-color: var(--blue); }
        .badge { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-success { background: linear-gradient(135deg, rgba(115,191,105,0.3), rgba(115,191,105,0.15)); color: var(--green); }
        .badge-danger { background: linear-gradient(135deg, rgba(242,73,92,0.3), rgba(242,73,92,0.15)); color: var(--red); }
        .badge-warning { background: linear-gradient(135deg, rgba(242,204,12,0.3), rgba(242,204,12,0.15)); color: var(--yellow); }
        .badge-info { background: linear-gradient(135deg, rgba(87,148,242,0.3), rgba(87,148,242,0.15)); color: var(--blue); }
        .raid-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
        .raid-card { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
        .raid-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .raid-card-title { font-weight: 600; font-size: 13px; }
        .raid-status { display: flex; align-items: center; gap: 6px; font-size: 12px; }
        .raid-disks { margin-top: 8px; }
        .raid-disk { display: flex; justify-content: space-between; padding: 6px 8px; background: rgba(0,0,0,0.2); border-radius: 3px; margin-bottom: 4px; font-size: 12px; }
        
        /* Server Status Panel */
        .server-panel { background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
        .server-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .metric-box { background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; text-align: center; }
        .metric-label { color: var(--muted); font-size: 10px; text-transform: uppercase; }
        .metric-value { font-weight: 600; font-size: 14px; }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="nav-left">
            <div class="logo"><div class="logo-icon">P</div><h1>PyMon</h1></div>
            <div class="nav-menu">
                <button class="nav-item active" data-section="dashboard"><i class="fas fa-chart-line"></i> Dashboard</button>
                <button class="nav-item" data-section="servers"><i class="fas fa-server"></i> Servers</button>
                <button class="nav-item" data-section="alerts"><i class="fas fa-bell"></i> Alerts</button>
                <button class="nav-item" data-section="raid"><i class="fas fa-hdd"></i> RAID</button>
                <button class="nav-item" data-section="settings"><i class="fas fa-cog"></i> Settings</button>
            </div>
        </div>
        <div class="nav-right">
            <button class="btn btn-secondary btn-sm" id="logoutBtn"><i class="fas fa-sign-out-alt"></i> Logout</button>
        </div>
    </nav>
    <main class="main">
        <div id="section-dashboard" class="section-content active">
            <div class="stats-row">
                <div class="stat-card" data-filter="online" id="card-online"><div class="stat-icon" style="background: rgba(115,191,105,0.15); color: var(--green);"><i class="fas fa-check-circle"></i></div><div class="stat-content"><div class="stat-value" id="stat-online" style="color: var(--green);">0</div><div class="stat-label">Online</div></div></div>
                <div class="stat-card" data-filter="offline" id="card-offline"><div class="stat-icon" style="background: rgba(242,73,92,0.15); color: var(--red);"><i class="fas fa-times-circle"></i></div><div class="stat-content"><div class="stat-value" id="stat-offline" style="color: var(--red);">0</div><div class="stat-label">Offline</div></div></div>
                <div class="stat-card" data-filter="linux" id="card-linux"><div class="stat-icon" style="background: rgba(87,148,242,0.15); color: var(--blue);"><i class="fab fa-linux"></i></div><div class="stat-content"><div class="stat-value" id="stat-linux" style="color: var(--blue);">0</div><div class="stat-label">Linux</div></div></div>
                <div class="stat-card" data-filter="windows" id="card-windows"><div class="stat-icon" style="background: rgba(242,204,12,0.15); color: var(--yellow);"><i class="fab fa-windows"></i></div><div class="stat-content"><div class="stat-value" id="stat-windows" style="color: var(--yellow);">0</div><div class="stat-label">Windows</div></div></div>
            </div>
            <div class="dashboard-toolbar">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="color: var(--muted); font-size: 13px;">Home / Dashboard</span>
                    <select class="server-selector" id="dashboardServerSelector" onchange="filterDashboard()"><option value="">All Servers</option></select>
                    <button class="btn btn-secondary btn-sm" onclick="clearFilter()" id="clearFilterBtn" style="display:none;">Clear Filter</button>
                </div>
                <div class="time-range">
                    <button class="time-btn" data-range="5m">5m</button>
                    <button class="time-btn" data-range="15m">15m</button>
                    <button class="time-btn active" data-range="1h">1h</button>
                    <button class="time-btn" data-range="6h">6h</button>
                    <button class="time-btn" data-range="24h">24h</button>
                </div>
            </div>
            
            <!-- Resizable Panels -->
            <div class="panels-grid" id="panelsGrid">
                <div class="panel" style="min-height: 180px;"><div class="panel-header"><div class="panel-title"><span class="status-dot"></span>CPU</div><div class="panel-resize" onclick="togglePanelSize(this)"><i class="fas fa-expand"></i></div></div><div class="panel-body"><div class="panel-chart"><canvas id="cpuChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span class="legend-header-name">Name</span><span class="legend-header-last">Last</span><span class="legend-header-max">Max</span></div><div id="cpuLegend"></div></div></div></div>
                <div class="panel" style="min-height: 180px;"><div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Memory</div><div class="panel-resize" onclick="togglePanelSize(this)"><i class="fas fa-expand"></i></div></div><div class="panel-body"><div class="panel-chart"><canvas id="memoryChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span class="legend-header-name">Name</span><span class="legend-header-last">Last</span><span class="legend-header-max">Max</span></div><div id="memoryLegend"></div></div></div></div>
                <div class="panel" style="min-height: 180px;"><div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Disk</div><div class="panel-resize" onclick="togglePanelSize(this)"><i class="fas fa-expand"></i></div></div><div class="panel-body"><div class="panel-chart"><canvas id="diskChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span class="legend-header-name">Name</span><span class="legend-header-last">Last</span><span class="legend-header-max">Max</span></div><div id="diskLegend"></div></div></div></div>
                <div class="panel" style="min-height: 180px;"><div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Network</div><div class="panel-resize" onclick="togglePanelSize(this)"><i class="fas fa-expand"></i></div></div><div class="panel-body"><div class="panel-chart"><canvas id="networkChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span class="legend-header-name">Name</span><span class="legend-header-last">Last</span><span class="legend-header-max">Max</span></div><div id="networkLegend"></div></div></div></div>
            </div>
            
            <!-- RAID & Exporter Status -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title"><i class="fas fa-hdd"></i> RAID Status</h3></div>
                    <div id="raidStatusPanel" style="max-height: 200px; overflow-y: auto;">
                        <p style="color: var(--muted); text-align: center; padding: 20px;">No RAID data</p>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title"><i class="fas fa-export"></i> Exporter Status</h3></div>
                    <div id="exporterStatusPanel" style="max-height: 200px; overflow-y: auto;">
                        <p style="color: var(--muted); text-align: center; padding: 20px;">No exporters</p>
                    </div>
                </div>
            </div>
        </div>
        <div id="section-servers" class="section-content">
            <div class="card">
                <div class="card-header"><h3 class="card-title">Monitored Servers</h3><button class="btn btn-primary" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button></div>
                <table><thead><tr><th>Status</th><th>Name</th><th>Host</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Actions</th></tr></thead><tbody id="servers-tbody"></tbody></table>
            </div>
            <div class="card">
                <h3 class="card-title" style="margin-bottom: 16px;">Agent Installation</h3>
                <div class="install-box">
                    <h4>Linux Agent</h4>
                    <div class="install-step"><div class="step-number">1</div><div class="step-content"><div class="step-title">Download and run installer</div><div class="code-block"><code id="linux-install">curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</code><button class="copy-btn" data-target="linux-install">Copy</button></div></div></div>
                </div>
                <div class="install-box">
                    <h4>Windows Agent</h4>
                    <div class="install-step"><div class="step-number">1</div><div class="step-content"><div class="step-title">Run in PowerShell as Administrator</div><div class="code-block"><code id="windows-install">powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-windows.ps1' -OutFile 'install.ps1'; .\install.ps1"</code><button class="copy-btn" data-target="windows-install">Copy</button></div></div></div>
                </div>
            </div>
        </div>
        <div id="section-alerts" class="section-content">
            <div class="tab-menu">
                <div class="tab-item active" data-tab="global">Global Alerts</div>
                <div class="tab-item" data-tab="server">Server Alerts</div>
            </div>
            <div class="card">
                <div class="card-header"><h3 class="card-title">Alert Rules</h3><button class="btn btn-primary" id="addAlertBtn"><i class="fas fa-plus"></i> New Alert</button></div>
                <p style="color: var(--muted); margin-bottom: 20px;">Configure alerts to receive notifications when metrics exceed thresholds.</p>
                <div id="alertsList"></div>
            </div>
        </div>
        <div id="section-raid" class="section-content">
            <div class="card">
                <div class="card-header"><h3 class="card-title"><i class="fas fa-hdd"></i> RAID Status</h3><button class="btn btn-secondary btn-sm" id="refreshRaidBtn"><i class="fas fa-sync"></i> Refresh</button></div>
                <div id="raidGrid" class="raid-grid"><p style="color: var(--muted); padding: 20px; text-align: center;">No RAID data available.</p></div>
            </div>
        </div>
        <div id="section-settings" class="section-content">
            <div class="tab-menu">
                <div class="tab-item active" data-tab="notif">Notifications</div>
                <div class="tab-item" data-tab="security">Security</div>
                <div class="tab-item" data-tab="backups">Backups</div>
            </div>
            <div id="settings-notif" class="tab-content">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4 style="font-size: 12px; color: #0088cc; margin-bottom: 10px;"><i class="fab fa-telegram"></i> TELEGRAM</h4>
                        <div class="form-group"><label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" id="telegram-enabled" style="width: auto;"> Enabled</label></div>
                        <div id="telegram-config" style="display: none;">
                            <div class="form-group"><label>Bot Token</label><input type="text" id="telegram-token" placeholder="123456789:ABCdef..."></div>
                            <div class="form-group"><label>Chat ID</label><input type="text" id="telegram-chat" placeholder="-1001234567890"></div>
                        </div>
                    </div>
                    <div>
                        <h4 style="font-size: 12px; color: #5865F2; margin-bottom: 10px;"><i class="fab fa-discord"></i> DISCORD</h4>
                        <div class="form-group"><label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" id="discord-enabled" style="width: auto;"> Enable Discord</label></div>
                        <div id="discord-config" style="display: none;"><div class="form-group"><label>Webhook URL</label><input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/..."></div></div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                    <div>
                        <h4 style="font-size: 12px; color: #4A154B; margin-bottom: 10px;"><i class="fab fa-slack"></i> SLACK</h4>
                        <div class="form-group"><label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" id="slack-enabled" style="width: auto;"> Enabled</label></div>
                        <div id="slack-config" style="display: none;"><div class="form-group"><label>Webhook URL</label><input type="text" id="slack-webhook" placeholder="https://hooks.slack.com/services/..."></div></div>
                    </div>
                    <div>
                        <h4 style="font-size: 12px; color: var(--red); margin-bottom: 10px;"><i class="fas fa-envelope"></i> EMAIL</h4>
                        <div class="form-group"><label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" id="email-enabled" style="width: auto;"> Enabled</label></div>
                        <div id="email-config" style="display: none;">
                            <div class="form-row"><div class="form-group"><label>Host</label><input type="text" id="email-host" placeholder="smtp.gmail.com"></div><div class="form-group"><label>Port</label><input type="number" id="email-port" value="587"></div></div>
                            <div class="form-group"><label>User</label><input type="text" id="email-user" placeholder="user@gmail.com"></div>
                            <div class="form-group"><label>Password</label><input type="password" id="email-pass" placeholder="app password"></div>
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary" id="saveNotifyBtn" style="margin-top: 20px;"><i class="fas fa-save"></i> Save Settings</button>
            </div>
            <div id="settings-security" class="tab-content" style="display: none;">
                <div class="form-row">
                    <div class="form-group"><label>SSL Certificate Path</label><input type="text" id="ssl-cert" placeholder="/path/to/fullchain.pem"></div>
                    <div class="form-group"><label>SSL Private Key Path</label><input type="text" id="ssl-key" placeholder="/path/to/privkey.pem"></div>
                </div>
                <div class="form-group"><label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" id="https-redirect" style="width: auto;"> Redirect HTTP to HTTPS</label></div>
                <div class="form-group"><label>Listen Port</label><input type="number" id="listen-port" value="8090"></div>
                <button class="btn btn-primary" id="saveSecurityBtn" style="margin-top: 20px;"><i class="fas fa-save"></i> Save Settings</button>
            </div>
            <div id="settings-backups" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Database Backups</h3><button class="btn btn-primary" id="createBackupBtn"><i class="fas fa-plus"></i> Create Backup</button></div>
                    <table><thead><tr><th>Filename</th><th>Size</th><th>Created</th><th>Actions</th></tr></thead><tbody id="backups-tbody"></tbody></table>
                </div>
            </div>
        </div>
    </main>
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header"><h3>Add Server</h3><button class="modal-close" id="closeServerModal">&times;</button></div>
            <form id="addServerForm">
                <div class="form-group"><label>Server Name</label><input type="text" id="server-name" required placeholder="Production Server"></div>
                <div class="form-group"><label>Host / IP Address</label><input type="text" id="server-host" required placeholder="192.168.1.100"></div>
                <div class="form-row">
                    <div class="form-group"><label>Operating System</label><select id="server-os"><option value="linux">Linux</option><option value="windows">Windows</option></select></div>
                    <div class="form-group"><label>Check Interval (sec)</label><input type="number" id="server-interval" value="15"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%">Add Server</button>
            </form>
        </div>
    </div>
    <div class="modal" id="alertModal">
        <div class="modal-content">
            <div class="modal-header"><h3 id="alertModalTitle">Add Alert Rule</h3><button class="modal-close" id="closeAlertModal">&times;</button></div>
            <form id="alertForm">
                <input type="hidden" id="alert-id">
                <div class="form-group"><label>Alert Name</label><input type="text" id="alert-name" required placeholder="High CPU Alert"></div>
                <div class="form-row">
                    <div class="form-group"><label>Server (Global = none)</label><select id="alert-server"><option value="">Global (All Servers)</option></select></div>
                    <div class="form-group"><label>Metric</label><select id="alert-metric"><option value="cpu">CPU Usage</option><option value="memory">Memory Usage</option><option value="disk">Disk Usage</option><option value="network">Network I/O</option></select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Condition</label><select id="alert-condition"><option value=">">Greater than (&gt;)</option><option value="<">Less than (&lt;)</option></select></div>
                    <div class="form-group"><label>Threshold (%)</label><input type="number" id="alert-threshold" value="80" min="0" max="100"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Duration</label><select id="alert-duration"><option value="0">Immediate</option><option value="1">1 minute</option><option value="5">5 minutes</option><option value="15">15 minutes</option></select></div>
                    <div class="form-group"><label>Severity</label><select id="alert-severity"><option value="critical">Critical</option><option value="warning">Warning</option></select></div>
                </div>
                <div class="form-group">
                    <label>Notification Channels</label>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 8px;">
                        <label style="display: flex; align-items: center; gap: 5px;"><input type="checkbox" id="alert-notify-telegram"> Telegram</label>
                        <label style="display: flex; align-items: center; gap: 5px;"><input type="checkbox" id="alert-notify-discord"> Discord</label>
                        <label style="display: flex; align-items: center; gap: 5px;"><input type="checkbox" id="alert-notify-slack"> Slack</label>
                        <label style="display: flex; align-items: center; gap: 5px;"><input type="checkbox" id="alert-notify-email"> Email</label>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%">Save Alert</button>
            </form>
        </div>
    </div>
    <script>
    const token = localStorage.getItem('token');
    if (!token) window.location.href = '/login';
    
    let servers = [];
    let alerts = [];
    let charts = {};
    let currentRange = '1h';
    let currentFilter = '';
    let currentServerFilter = '';
    const grafanaColors = ["#73bf69", "#f2cc0c", "#5794f2", "#ff780a", "#b877d9", "#00d8d8", "#f2495c", "#9673b9"];
    const colors = grafanaColors;
    let currentAlertTab = 'global';
    
    // Add click handlers for stat cards
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.stat-card[data-filter]').forEach(card => {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function() {
                filterBy(this.dataset.filter);
            });
        });
    });
    
    // Filter functions
    function filterBy(type) {
        if (currentFilter === type) {
            currentFilter = '';
            document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        } else {
            currentFilter = type;
            document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
            const card = document.getElementById('card-' + type);
            if (card) card.classList.add('active');
        }
        updateDashboard();
    }
    
    function filterDashboard() {
        currentServerFilter = document.getElementById('dashboardServerSelector').value;
        const btn = document.getElementById('clearFilterBtn');
        btn.style.display = currentServerFilter ? 'inline-flex' : 'none';
        updateDashboard();
    }
    
    function clearFilter() {
        currentFilter = '';
        currentServerFilter = '';
        document.getElementById('dashboardServerSelector').value = '';
        document.getElementById('clearFilterBtn').style.display = 'none';
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        updateDashboard();
    }
    
    function togglePanelSize(btn) {
        const panel = btn.closest('.panel');
        panel.classList.toggle('expanded');
    }
    
    function getFilteredServers() {
        let filtered = [...servers];
        if (currentServerFilter) {
            filtered = filtered.filter(s => s.id == currentServerFilter);
        }
        if (currentFilter === 'online') filtered = filtered.filter(s => s.last_status === 'up');
        if (currentFilter === 'offline') filtered = filtered.filter(s => s.last_status !== 'up');
        if (currentFilter === 'linux') filtered = filtered.filter(s => s.os_type === 'linux');
        if (currentFilter === 'windows') filtered = filtered.filter(s => s.os_type === 'windows');
        return filtered;
    }
    
    function updateDashboard() {
        const filtered = getFilteredServers();
        updateCharts(filtered);
        updateRAIDStatusPanel(filtered);
        updateExporterStatusPanel(filtered);
    }
    
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.addEventListener("click", function() {
            const section = this.dataset.section;
            if (section) showSection(section);
        });
    });
    
    // Tab switching for settings
    document.querySelectorAll("#section-settings .tab-menu .tab-item").forEach(btn => {
        btn.addEventListener("click", function() {
            document.querySelectorAll("#section-settings .tab-menu .tab-item").forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const tab = this.dataset.tab;
            document.querySelectorAll("#section-settings .tab-content").forEach(c => c.style.display = 'none');
            document.getElementById('settings-' + tab).style.display = 'block';
        });
    });
    
    // Tab switching for alerts
    document.querySelectorAll("#section-alerts .tab-menu .tab-item").forEach(btn => {
        btn.addEventListener("click", function() {
            document.querySelectorAll("#section-alerts .tab-menu .tab-item").forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentAlertTab = this.dataset.tab;
            loadAlerts();
        });
    });
    
    function showSection(section) {
        document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const sectionEl = document.getElementById('section-' + section);
        if (sectionEl) sectionEl.classList.add('active');
        document.querySelectorAll('.nav-item').forEach(el => {
            if (el.dataset.section === section) el.classList.add('active');
        });
        if (section === 'dashboard') setTimeout(initCharts, 100);
        if (section === 'servers') loadServers();
        if (section === 'alerts') loadAlerts();
        if (section === 'raid') loadRAID();
        if (section === 'settings') { loadNotifications(); loadBackups(); }
    }
    
    document.getElementById('logoutBtn').addEventListener('click', function() {
        localStorage.removeItem('token');
        window.location.href = '/login';
    });
    
    document.querySelectorAll(".time-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            document.querySelectorAll(".time-btn").forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentRange = this.dataset.range;
            initCharts();
        });
    });
    
    document.getElementById('addServerBtn').addEventListener('click', function() {
        document.getElementById('addServerModal').classList.add('active');
    });
    document.getElementById('closeServerModal').addEventListener('click', function() {
        document.getElementById('addServerModal').classList.remove('active');
    });
    document.getElementById('addServerForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await fetch('/api/servers', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            body: JSON.stringify({
                name: document.getElementById('server-name').value,
                host: document.getElementById('server-host').value,
                os_type: document.getElementById('server-os').value,
                check_interval: parseInt(document.getElementById('server-interval').value)
            })
        });
        document.getElementById('addServerModal').classList.remove('active');
        loadServers();
    });
    
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const text = document.getElementById(target).textContent;
            navigator.clipboard.writeText(text);
            this.textContent = 'Copied!';
            setTimeout(() => this.textContent = 'Copy', 2000);
        });
    });
    
    async function loadServers() {
        try {
            const resp = await fetch('/api/servers', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            servers = data.servers || [];
            let online = 0, offline = 0, linux = 0, windows = 0;
            document.getElementById('serverSelector').innerHTML = '<option value="">All Servers</option>' + servers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            document.getElementById('dashboardServerSelector').innerHTML = '<option value="">All Servers</option>' + servers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            document.getElementById('alert-server').innerHTML = '<option value="">Global (All Servers)</option>' + servers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            document.getElementById('servers-tbody').innerHTML = servers.map(s => {
                if (s.last_status === 'up') online++; else offline++;
                if (s.os_type === 'linux') linux++; else windows++;
                const statusBadge = s.last_status === 'up' ? '<span class="badge badge-success">' + (s.last_status || 'pending') + '</span>' : '<span class="badge badge-danger">' + (s.last_status || 'offline') + '</span>';
                return '<tr><td>' + statusBadge + '</td><td><strong>' + s.name + '</strong></td><td>' + s.host + '</td><td>' + s.os_type + '</td><td>' + (s.cpu_percent ? s.cpu_percent.toFixed(1) + '%' : '-') + '</td><td>' + (s.memory_percent ? s.memory_percent.toFixed(1) + '%' : '-') + '</td><td>' + (s.disk_percent ? s.disk_percent.toFixed(1) + '%' : '-') + '</td><td><button class="btn btn-danger btn-sm" onclick="deleteServer(' + s.id + ')">Delete</button></td></tr>';
            }).join('') || '<tr><td colspan="8" style="text-align:center;padding:40px;color:#999;">No servers</td></tr>';
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            document.getElementById('stat-linux').textContent = linux;
            document.getElementById('stat-windows').textContent = windows;
            updateRAIDStatusPanel();
            updateExporterStatusPanel();
        } catch(e) { console.error(e); }
    }
    
    function updateRAIDStatusPanel() {
        const filtered = getFilteredServers();
        const panel = document.getElementById('raidStatusPanel');
        const raidServers = filtered.filter(s => s.raid_status);
        if (!raidServers.length) {
            panel.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;">No RAID data</p>';
            return;
        }
        panel.innerHTML = raidServers.map(s => {
            let raidData = {status: 'unknown', disks: []};
            try { if (s.raid_status) raidData = JSON.parse(s.raid_status); } catch(e) {}
            const statusColor = raidData.status === 'healthy' ? 'var(--green)' : 'var(--red)';
            return '<div style="margin-bottom: 8px;"><div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><strong>' + s.name + '</strong><span class="badge ' + (raidData.status === 'healthy' ? 'badge-success' : 'badge-danger') + '">' + (raidData.status || 'Unknown') + '</span></div>' +
                (raidData.disks || []).map(d => '<div style="display: flex; justify-content: space-between; padding: 4px 8px; background: rgba(0,0,0,0.2); border-radius: 3px; margin-bottom: 2px; font-size: 11px;"><span>' + d.name + '</span><span class="badge ' + (d.status === 'online' ? 'badge-success' : 'badge-danger') + '">' + d.status + '</span></div>').join('') + '</div>';
        }).join('');
    }
    
    function updateExporterStatusPanel() {
        const filtered = getFilteredServers();
        const panel = document.getElementById('exporterStatusPanel');
        if (!filtered.length) {
            panel.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;">No exporters</p>';
            return;
        }
        panel.innerHTML = filtered.map(s => {
            const isUp = s.last_status === 'up';
            return '<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; margin-bottom: 6px;">' +
                '<div><strong>' + s.name + '</strong><br><span style="color: var(--muted); font-size: 11px;">' + s.host + ':' + (s.agent_port || 9100) + '</span></div>' +
                '<div style="text-align: right;"><span class="badge ' + (isUp ? 'badge-success' : 'badge-danger') + '">' + (isUp ? 'Online' : 'Offline') + '</span><br><span style="color: var(--muted); font-size: 10px;">' + (s.last_check || 'Never') + '</span></div>' +
                '</div>';
        }).join('');
    }
    
    async function deleteServer(id) {
        if (confirm('Delete server?')) {
            await fetch('/api/servers/' + id, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadServers();
        }
    }
    
    function initCharts() {
        Object.values(charts).forEach(c => c && c.destroy());
        charts = {};
        const labels = generateLabels();
        const filtered = getFilteredServers();
        const getData = (key, min, max) => filtered.length ? filtered.map((s,i) => ({label:s.name,data:rand(12,min,max),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,min,max),borderColor:colors[0],backgroundColor:colors[0]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type:'line',data:{labels:labels,datasets:getData('cpu',20,90)},options:chartOpts('%',0,100)});
        updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
        charts.memory = new Chart(document.getElementById('memoryChart'), {type:'line',data:{labels:labels,datasets:getData('memory',30,90)},options:chartOpts('%',0,100)});
        updateLegend('memoryLegend', charts.memory.data.datasets, '%');
        charts.disk = new Chart(document.getElementById('diskChart'), {type:'line',data:{labels:labels,datasets:getData('disk',40,95)},options:chartOpts('%',0,100)});
        updateLegend('diskLegend', charts.disk.data.datasets, '%');
        charts.network = new Chart(document.getElementById('networkChart'), {type:'line',data:{labels:labels,datasets:getData('network',10,80)},options:chartOpts(' MB/s',0,80)});
        updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
    }
    
    function updateCharts(filtered) {
        if (!charts.cpu) { initCharts(); return; }
        const labels = generateLabels();
        const getData = (key, min, max) => filtered.length ? filtered.map((s,i) => ({label:s.name,data:rand(12,min,max),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,min,max),borderColor:colors[0],backgroundColor:colors[0]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.cpu.data.labels = labels;
        charts.cpu.data.datasets = getData('cpu',20,90);
        charts.cpu.update();
        updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
        charts.memory.data.labels = labels;
        charts.memory.data.datasets = getData('memory',30,90);
        charts.memory.update();
        updateLegend('memoryLegend', charts.memory.data.datasets, '%');
        charts.disk.data.labels = labels;
        charts.disk.data.datasets = getData('disk',40,95);
        charts.disk.update();
        updateLegend('diskLegend', charts.disk.data.datasets, '%');
        charts.network.data.labels = labels;
        charts.network.data.datasets = getData('network',10,80);
        charts.network.update();
        updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
    }
    
    function generateLabels() {
        const labels = [];
        const now = new Date();
        const pts = 12;
        let intv = 5;
        if (currentRange === '5m') intv = 0.5;
        else if (currentRange === '15m') intv = 1;
        else if (currentRange === '6h') intv = 30;
        else if (currentRange === '24h') intv = 120;
        for (let i = pts-1; i >= 0; i--) {
            const t = new Date(now.getTime() - i * intv * 60000);
            labels.push(t.getHours().toString().padStart(2,'0') + ':' + t.getMinutes().toString().padStart(2,'0'));
        }
        return labels;
    }
    
    function rand(n, min, max) { return Array(n).fill(0).map(() => min + Math.random() * (max - min)); }
    
    function chartOpts(suffix, min, max) {
        return { responsive: true, maintainAspectRatio: false, interaction: {intersect: false, mode: 'index'}, scales: { y: {min:min, max:max, grid:{color:'rgba(255,255,255,0.03)'}, ticks:{color:'#666',font:{size:10},callback:v=>v+suffix}}, x: {grid:{display:false}, ticks:{color:'#666',font:{size:10}}}}, plugins: {legend:{display:false}} };
    }
    
    function updateLegend(id, datasets, suffix) {
        const el = document.getElementById(id);
        el.innerHTML = datasets.map((ds,i) => {
            const last = ds.data[ds.data.length-1];
            const mx = Math.max(...ds.data);
            return '<div class="legend-item"><div class="legend-color" style="background:'+ds.borderColor+'"></div><div class="legend-name">'+ds.label+'</div><div class="legend-value-last">'+last.toFixed(1)+suffix+'</div><div class="legend-value-max">'+mx.toFixed(1)+suffix+'</div></div>';
        }).join('');
    }
    
    document.getElementById('addAlertBtn').addEventListener('click', function() {
        document.getElementById('alert-id').value = '';
        document.getElementById('alertForm').reset();
        document.getElementById('alertModalTitle').textContent = 'Add Alert Rule';
        document.getElementById('alertModal').classList.add('active');
    });
    
    document.getElementById('closeAlertModal').addEventListener('click', function() {
        document.getElementById('alertModal').classList.remove('active');
    });
    
    document.getElementById('alertForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('alert-id').value;
        const alertData = {
            name: document.getElementById('alert-name').value,
            metric: document.getElementById('alert-metric').value,
            condition: document.getElementById('alert-condition').value,
            threshold: parseInt(document.getElementById('alert-threshold').value),
            duration: parseInt(document.getElementById('alert-duration').value),
            severity: document.getElementById('alert-severity').value,
            server_id: document.getElementById('alert-server').value || null,
            notify_telegram: document.getElementById('alert-notify-telegram').checked,
            notify_discord: document.getElementById('alert-notify-discord').checked,
            notify_slack: document.getElementById('alert-notify-slack').checked,
            notify_email: document.getElementById('alert-notify-email').checked,
            enabled: true
        };
        const url = id ? '/api/alerts/' + id : '/api/alerts';
        const method = id ? 'PUT' : 'POST';
        await fetch(url, { method, headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify(alertData) });
        document.getElementById('alertModal').classList.remove('active');
        loadAlerts();
    });
    
    async function loadAlerts() {
        try {
            const resp = await fetch('/api/alerts', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            alerts = data.alerts || [];
            const metricIcons = {cpu: 'fa-microchip', memory: 'fa-memory', disk: 'fa-hdd', network: 'fa-network-wired'};
            const metricColors = {cpu: 'var(--blue)', memory: 'var(--green)', disk: 'var(--yellow)', network: 'var(--purple)'};
            const filtered = alerts.filter(a => {
                if (currentAlertTab === 'global') return a.server_id === null || a.server_id === 0;
                if (currentAlertTab === 'server') return a.server_id !== null && a.server_id !== 0;
                return true;
            });
            document.getElementById('alertsList').innerHTML = filtered.map(a => {
                const notifyTags = [];
                if (a.notify_telegram) notifyTags.push('<span class="notification-tag"><i class="fab fa-telegram"></i></span>');
                if (a.notify_discord) notifyTags.push('<span class="notification-tag"><i class="fab fa-discord"></i></span>');
                if (a.notify_slack) notifyTags.push('<span class="notification-tag"><i class="fab fa-slack"></i></span>');
                if (a.notify_email) notifyTags.push('<span class="notification-tag"><i class="fas fa-envelope"></i></span>');
                const serverName = a.server_id ? servers.find(s => s.id == a.server_id)?.name || 'Server ' + a.server_id : 'Global';
                const severityBadge = a.severity === 'critical' ? 'badge-danger' : 'badge-warning';
                return '<div class="alert-rule"><div class="alert-rule-header"><div class="alert-rule-title"><i class="fas ' + (metricIcons[a.metric] || 'fa-bell') + '" style="color: ' + (metricColors[a.metric] || 'var(--blue)') + ';"></i> ' + a.name + ' <span class="badge ' + severityBadge + '">' + a.severity + '</span></div><div><button class="btn btn-danger btn-sm" onclick="deleteAlert(' + a.id + ')">Delete</button></div></div><div class="alert-conditions"><div class="condition-box"><div class="condition-label">Scope</div><div class="condition-value">' + serverName + '</div></div><div class="condition-box"><div class="condition-label">Metric</div><div class="condition-value">' + a.metric.toUpperCase() + '</div></div><div class="condition-box"><div class="condition-label">Condition</div><div class="condition-value">' + a.condition + ' ' + a.threshold + '%</div></div></div><div class="alert-notifications">' + (notifyTags.length ? notifyTags.join('') : '<span style="color: var(--muted);">No notifications</span>') + '</div></div>';
            }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No alert rules configured.</p>';
        } catch(e) { console.error(e); }
    }
    
    async function deleteAlert(id) {
        if (confirm('Delete this alert?')) {
            await fetch('/api/alerts/' + id, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadAlerts();
        }
    }
    
    async function loadRAID() {
        const grid = document.getElementById('raidGrid');
        if (!servers.length) { grid.innerHTML = '<p style="color: var(--muted); padding: 20px; text-align: center;">No servers added yet.</p>'; return; }
        const raidServers = servers.filter(s => s.raid_status);
        if (!raidServers.length) { grid.innerHTML = '<p style="color: var(--muted); padding: 20px; text-align: center;">No RAID data available.</p>'; return; }
        grid.innerHTML = raidServers.map(s => {
            let raidData = {status: 'unknown', disks: []};
            try { if (s.raid_status) raidData = JSON.parse(s.raid_status); } catch(e) {}
            const statusColor = raidData.status === 'healthy' ? 'var(--green)' : 'var(--red)';
            const statusIcon = raidData.status === 'healthy' ? 'fa-check-circle' : 'fa-exclamation-triangle';
            return '<div class="raid-card"><div class="raid-card-header"><div class="raid-card-title">' + s.name + '</div><div class="raid-status"><i class="fas ' + statusIcon + '" style="color: ' + statusColor + ';"></i> ' + (raidData.status || 'Unknown') + '</div></div><div class="raid-disks">' + (raidData.disks || []).map(d => '<div class="raid-disk"><span>' + d.name + '</span><span class="badge ' + (d.status === 'online' ? 'badge-success' : 'badge-danger') + '">' + d.status + '</span></div>').join('') + '</div></div>';
        }).join('');
    }
    
    document.getElementById('refreshRaidBtn').addEventListener('click', loadRAID);
    
    ['telegram', 'discord', 'slack', 'email'].forEach(ch => {
        const enabled = document.getElementById(ch + '-enabled');
        if (enabled) {
            enabled.addEventListener('change', function() {
                document.getElementById(ch + '-config').style.display = this.checked ? 'block' : 'none';
            });
        }
    });
    
    async function loadNotifications() {
        try {
            const resp = await fetch('/api/notifications', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            data.notifications.forEach(n => {
                const enabled = document.getElementById(n.channel + '-enabled');
                if (enabled) { enabled.checked = n.enabled; document.getElementById(n.channel + '-config').style.display = n.enabled ? 'block' : 'none'; }
                if (n.channel === 'telegram') { document.getElementById('telegram-token').value = n.telegram_bot_token || ''; document.getElementById('telegram-chat').value = n.telegram_chat_id || ''; }
                if (n.channel === 'discord') document.getElementById('discord-webhook').value = n.discord_webhook || '';
                if (n.channel === 'slack') document.getElementById('slack-webhook').value = n.slack_webhook || '';
                if (n.channel === 'email') { document.getElementById('email-host').value = n.email_smtp_host || ''; document.getElementById('email-port').value = n.email_smtp_port || 587; document.getElementById('email-user').value = n.email_user || ''; document.getElementById('email-pass').value = n.email_pass || ''; }
            });
        } catch(e) { console.error(e); }
    }
    
    document.getElementById('saveNotifyBtn').addEventListener('click', async function() {
        const channels = {
            telegram: {enabled: document.getElementById('telegram-enabled').checked, telegram_bot_token: document.getElementById('telegram-token').value, telegram_chat_id: document.getElementById('telegram-chat').value},
            discord: {enabled: document.getElementById('discord-enabled').checked, discord_webhook: document.getElementById('discord-webhook').value},
            slack: {enabled: document.getElementById('slack-enabled').checked, slack_webhook: document.getElementById('slack-webhook').value},
            email: {enabled: document.getElementById('email-enabled').checked, email_smtp_host: document.getElementById('email-host').value, email_smtp_port: parseInt(document.getElementById('email-port').value)||587, email_user: document.getElementById('email-user').value, email_pass: document.getElementById('email-pass').value}
        };
        for (const [channel, config] of Object.entries(channels)) {
            await fetch('/api/notifications/' + channel, {method: 'PUT', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify(config)});
        }
        alert('Settings saved!');
    });
    
    async function loadBackups() {
        try {
            const resp = await fetch('/api/backups', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            document.getElementById('backups-tbody').innerHTML = data.backups.map(b => '<tr><td>' + b.filename + '</td><td>' + (b.size_bytes ? (b.size_bytes/1024).toFixed(1) + ' KB' : '-') + '</td><td>' + b.created_at + '</td><td><button class="btn btn-danger btn-sm">Delete</button></td></tr>').join('') || '<tr><td colspan="4" style="text-align:center;color:#999;">No backups</td></tr>';
        } catch(e) { console.error(e); }
    }
    
    document.getElementById('createBackupBtn').addEventListener('click', async function() {
        await fetch('/api/backups', {method: 'POST', headers: {'Authorization': 'Bearer ' + token}});
        loadBackups();
    });
    
    loadServers();
    setTimeout(initCharts, 100);
    </script>
</body>
</html>'''

@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

@router.get("/api/servers")
async def list_servers():
    conn = get_db()
    servers = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
    conn.close()
    return {"servers": [dict(s) for s in servers]}

@router.post("/api/servers")
async def create_server(server: ServerModel):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO servers (name, host, os_type, agent_port, check_interval, enabled, notify_telegram, notify_discord, notify_slack, notify_email, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)''',
        (server.name, server.host, server.os_type, server.agent_port, server.check_interval,
         int(server.notify_telegram), int(server.notify_discord), int(server.notify_slack), int(server.notify_email),
         datetime.utcnow().isoformat()))
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
    conn.execute('''UPDATE servers SET name=?, host=?, os_type=?, agent_port=?, check_interval=?, notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=? WHERE id=?''',
        (server.name, server.host, server.os_type, server.agent_port, server.check_interval,
         int(server.notify_telegram), int(server.notify_discord), int(server.notify_slack), int(server.notify_email), server_id))
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

@router.get("/api/notifications")
async def get_notifications():
    conn = get_db()
    notifications = conn.execute("SELECT * FROM notifications").fetchall()
    conn.close()
    result = []
    for n in notifications:
        item = {"channel": n['channel'], "enabled": bool(n['enabled'])}
        item.update(json.loads(n['config'] or '{}'))
        result.append(item)
    return {"notifications": result}

@router.put("/api/notifications/{channel}")
async def update_notification(channel: str, config: dict):
    conn = get_db()
    conn.execute("UPDATE notifications SET enabled=?, config=? WHERE channel=?",
                 (int(config.get('enabled', False)), json.dumps(config), channel))
    conn.commit()
    conn.close()
    return {"status": "ok"}

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
        conn.execute('''INSERT INTO alerts (name, metric, condition, threshold, duration, severity, server_id, notify_telegram, notify_discord, notify_slack, notify_email, description, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (alert.name, alert.metric, alert.condition, alert.threshold, alert.duration, alert.severity, alert.server_id,
             int(alert.notify_telegram), int(alert.notify_discord), int(alert.notify_slack), int(alert.notify_email),
             alert.description, int(alert.enabled), datetime.utcnow().isoformat()))
        conn.commit()
    except Exception as e:
        print(f"Error creating alert: {e}")
    conn.close()
    return {"status": "ok"}

@router.put("/api/alerts/{alert_id}")
async def update_alert(alert_id: int, alert: AlertModel):
    conn = get_db()
    conn.execute('''UPDATE alerts SET name=?, metric=?, condition=?, threshold=?, duration=?, severity=?, server_id=?, notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=?, description=?, enabled=? WHERE id=?''',
        (alert.name, alert.metric, alert.condition, alert.threshold, alert.duration, alert.severity, alert.server_id,
         int(alert.notify_telegram), int(alert.notify_discord), int(alert.notify_slack), int(alert.notify_email),
         alert.description, int(alert.enabled), alert_id))
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

@router.post("/api/backups")
async def create_backup():
    try:
        BACKUP_DIR = "/var/lib/pymon/backups"
        os.makedirs(BACKUP_DIR, exist_ok=True)
        filename = f"pymon_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        dest = os.path.join(BACKUP_DIR, filename)
        import shutil
        shutil.copy2(DB_PATH, dest)
        size = os.path.getsize(dest)
        conn = get_db()
        conn.execute("INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
                     (filename, size, datetime.utcnow().isoformat()))
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
