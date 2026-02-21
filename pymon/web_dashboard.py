"""Enterprise Server Monitoring Dashboard"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import os
from datetime import datetime, timezone

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
        
        c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT,
            last_used TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS maintenance_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            servers TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
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
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); }
        .panel-title { font-size: 12px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 8px; }
        .panel-resize { background: none; border: none; color: var(--muted); cursor: pointer; padding: 4px; border-radius: 4px; transition: all 0.2s; }
        .panel-resize:hover { color: var(--text); background: rgba(255,255,255,0.1); }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
        .panel.expanded { grid-column: span 2; }
        .panel.expanded .panel-body { height: 350px; }
        .panel-body { display: flex; height: 180px; }
        .panel-chart { flex: 1; padding: 8px; position: relative; min-width: 0; }
        .panel-legend { width: 280px; border-left: 1px solid var(--border); background: rgba(0,0,0,0.2); overflow-y: auto; font-size: 11px; flex-shrink: 0; }
        .legend-header { display: flex; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted); font-size: 10px; text-transform: uppercase; font-weight: 600; cursor: pointer; }
        .legend-header:hover { color: var(--blue); }
        .legend-header-name { flex: 1; text-align: left; }
        .legend-header-last { width: 45px; text-align: right; cursor: pointer; position: relative; }
        .legend-header-last::after { content: ''; position: absolute; right: 2px; top: 50%; transform: translateY(-50%); border: 4px solid transparent; }
        .legend-header-last.sort-asc::after { border-bottom-color: var(--blue); margin-top: -4px; }
        .legend-header-last.sort-desc::after { border-top-color: var(--blue); margin-top: 4px; }
        .legend-header-max { width: 45px; text-align: right; cursor: pointer; position: relative; }
        .legend-header-max::after { content: ''; position: absolute; right: 2px; top: 50%; transform: translateY(-50%); border: 4px solid transparent; }
        .legend-header-max.sort-asc::after { border-bottom-color: var(--blue); margin-top: -4px; }
        .legend-header-max.sort-desc::after { border-top-color: var(--blue); margin-top: 4px; }
        .legend-item { display: flex; padding: 6px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); cursor: pointer; }
        .legend-item:hover { background: rgba(255,255,255,0.05); }
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
                    <button class="btn btn-secondary btn-sm" onclick="clearFilter()" id="clearFilterBtn" style="display:none;"><i class="fas fa-times"></i> Clear</button>
                    <button class="btn btn-primary btn-sm" onclick="refreshDashboard()"><i class="fas fa-sync"></i> Refresh</button>
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

            <!-- RAID Status - Extended -->
            <div class="card" style="margin-top: 16px;">
                <div class="card-header">
                    <h3 class="card-title"><i class="fas fa-hdd"></i> RAID Arrays Status</h3>
                    <button class="btn btn-secondary btn-sm" id="refreshRaidBtn"><i class="fas fa-sync"></i> Refresh</button>
                </div>
                <div id="raidStats" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 6px; margin-bottom: 12px;">
                    <div style="text-align: center;"><div style="font-size: 24px; color: var(--blue);" id="raidTotalServers">-</div><div style="color: var(--muted); font-size: 11px;">Servers with RAID</div></div>
                    <div style="text-align: center;"><div style="font-size: 24px; color: var(--green);" id="raidHealthy">-</div><div style="color: var(--muted); font-size: 11px;">Healthy Arrays</div></div>
                    <div style="text-align: center;"><div style="font-size: 24px; color: var(--red);" id="raidDegraded">-</div><div style="color: var(--muted); font-size: 11px;">Degraded Arrays</div></div>
                    <div style="text-align: center;"><div style="font-size: 24px; color: var(--yellow);" id="raidTotalSize">-</div><div style="color: var(--muted); font-size: 11px;">Total Capacity</div></div>
                </div>
                <div id="raidStatusPanel" style="max-height: 400px; overflow-y: auto;">
                    <p style="color: var(--muted); text-align: center; padding: 20px;">Loading RAID data...</p>
                </div>
            </div>
        </div>
        <div id="section-servers" class="section-content">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Monitored Servers</h3>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <input type="text" id="serverSearch" placeholder="Search name/host..." style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text); width: 140px;">
                        <select id="filterStatus" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="">All Status</option>
                            <option value="up">Online</option>
                            <option value="down">Offline</option>
                        </select>
                        <select id="filterOS" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="">All OS</option>
                            <option value="windows">Windows</option>
                            <option value="linux">Linux</option>
                        </select>
                        <select id="filterCPU" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="">CPU Any</option>
                            <option value="90">CPU > 90%</option>
                            <option value="80">CPU > 80%</option>
                            <option value="70">CPU > 70%</option>
                            <option value="50">CPU > 50%</option>
                        </select>
                        <select id="filterMemory" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="">Memory Any</option>
                            <option value="95">Memory > 95%</option>
                            <option value="90">Memory > 90%</option>
                            <option value="80">Memory > 80%</option>
                            <option value="70">Memory > 70%</option>
                        </select>
                        <select id="filterDisk" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="">Disk Any</option>
                            <option value="95">Disk > 95%</option>
                            <option value="90">Disk > 90%</option>
                            <option value="80">Disk > 80%</option>
                            <option value="70">Disk > 70%</option>
                        </select>
                        <select id="serverSortSelect" style="padding: 6px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
                            <option value="name">Sort: Name</option>
                            <option value="status">Sort: Status</option>
                            <option value="cpu">Sort: CPU</option>
                            <option value="memory">Sort: Memory</option>
                            <option value="disk">Sort: Disk</option>
                        </select>
                        <button class="btn btn-secondary btn-sm" id="clearFiltersBtn"><i class="fas fa-times"></i> Clear</button>
                        <button class="btn btn-primary" id="addServerBtn"><i class="fas fa-plus"></i> Add</button>
                    </div>
                </div>
                <div id="filterStats" style="padding: 8px 12px; background: rgba(0,0,0,0.2); font-size: 12px; color: var(--muted); margin-bottom: 8px;"></div>
                <table><thead><tr><th>Status</th><th>Name</th><th>Host:Port</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last Check</th><th>Actions</th></tr></thead><tbody id="servers-tbody"></tbody></table>
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
        <div id="section-settings" class="section-content">
            <div class="tab-menu">
                <div class="tab-item active" data-tab="notif">Notifications</div>
                <div class="tab-item" data-tab="security">Security</div>
                <div class="tab-item" data-tab="backups">Backups</div>
                <div class="tab-item" data-tab="apikeys">API Keys</div>
                <div class="tab-item" data-tab="audit">Audit Log</div>
                <div class="tab-item" data-tab="maintenance">Maintenance</div>
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
                    <div class="card-header"><h3 class="card-title"><i class="fas fa-database"></i> Backup & Restore</h3></div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div style="padding: 12px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <h4 style="margin-bottom: 10px; color: var(--green);"><i class="fas fa-download"></i> Create Backup</h4>
                            <div class="form-group"><label>Save to path:</label><input type="text" id="backupPath" placeholder="backups" style="width: 100%;"></div>
                            <button class="btn btn-success" id="createBackupBtn" style="width: 100%;"><i class="fas fa-plus"></i> Create Full Backup</button>
                        </div>
                        <div style="padding: 12px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <h4 style="margin-bottom: 10px; color: var(--yellow);"><i class="fas fa-upload"></i> Restore Backup</h4>
                            <div class="form-group"><label>Backup file path:</label><input type="text" id="restorePath" placeholder="backups\pymon_full_xxx.zip" style="width: 100%;"></div>
                            <div style="margin-bottom: 8px;">
                                <label style="margin-right: 12px;"><input type="checkbox" id="restoreDb" checked> Database</label>
                                <label style="margin-right: 12px;"><input type="checkbox" id="restoreConfig" checked> Config</label>
                                <label><input type="checkbox" id="restoreSettings" checked> Settings</label>
                            </div>
                            <button class="btn btn-warning" id="restoreBackupBtn" style="width: 100%;"><i class="fas fa-undo"></i> Restore from Backup</button>
                        </div>
                    </div>
                    
                    <h4 style="margin-bottom: 8px;"><i class="fas fa-list"></i> Backup Files</h4>
                    <table><thead><tr><th>Filename</th><th>Size</th><th>Created</th><th>Actions</th></tr></thead><tbody id="backups-tbody"></tbody></table>
                </div>
            </div>
            <div id="settings-apikeys" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">API Keys</h3><button class="btn btn-primary" id="createApiKeyBtn"><i class="fas fa-plus"></i> Generate Key</button></div>
                    <p style="color: var(--muted); margin-bottom: 16px;">API keys allow external systems to access PyMon API.</p>
                    <table><thead><tr><th>Name</th><th>Key</th><th>Created</th><th>Last Used</th><th>Actions</th></tr></thead><tbody id="apikeys-tbody"></tbody></table>
                </div>
            </div>
            <div id="settings-audit" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Audit Log</h3><button class="btn btn-secondary btn-sm" id="refreshAuditBtn"><i class="fas fa-sync"></i> Refresh</button></div>
                    <p style="color: var(--muted); margin-bottom: 16px;">Track all user actions and system events.</p>
                    <table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Details</th><th>IP</th></tr></thead><tbody id="audit-tbody"></tbody></table>
                </div>
            </div>
            <div id="settings-maintenance" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Maintenance Windows</h3><button class="btn btn-primary" id="addMaintenanceBtn"><i class="fas fa-plus"></i> Add Window</button></div>
                    <p style="color: var(--muted); margin-bottom: 16px;">Define maintenance periods when alerts are suppressed.</p>
                    <div id="maintenanceList"></div>
                </div>
                <div class="card" style="margin-top: 16px;">
                    <div class="card-header"><h3 class="card-title">Data Retention</h3></div>
                    <div class="form-group"><label>Keep metrics for (days)</label><input type="number" id="retention-days" value="30"></div>
                    <div class="form-group"><label>Keep audit logs for (days)</label><input type="number" id="audit-retention-days" value="90"></div>
                    <button class="btn btn-primary" id="saveRetentionBtn"><i class="fas fa-save"></i> Save</button>
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
                    <div class="form-group"><label>Metric</label><select id="alert-metric"><option value="cpu">CPU Usage</option><option value="memory">Memory Usage</option><option value="disk">Disk Usage</option><option value="network">Network I/O</option><option value="exporter">Exporter Status</option><option value="raid">RAID Status</option></select></div>
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
    let legendSortBy = null;
    let legendSortAsc = true;
    let legendServerFilter = null;
    
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
        initCharts();
    }
    
    function filterDashboard() {
        currentServerFilter = document.getElementById('dashboardServerSelector').value;
        legendServerFilter = currentServerFilter;
        const btn = document.getElementById('clearFilterBtn');
        btn.style.display = currentServerFilter ? 'inline-flex' : 'none';
        initCharts();
    }
    
    function clearFilter() {
        currentFilter = '';
        currentServerFilter = '';
        legendServerFilter = null;
        document.getElementById('dashboardServerSelector').value = '';
        document.getElementById('clearFilterBtn').style.display = 'none';
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        updateDashboard();
    }
    
    async function refreshDashboard() {
        const btn = event.target.closest('button');
        const icon = btn.querySelector('i');
        icon.classList.add('fa-spin');
        await loadServers();
        initCharts();
        setTimeout(() => icon.classList.remove('fa-spin'), 500);
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
        updateRAIDStatusPanel();
    }
    
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.addEventListener("click", function() {
            const section = this.dataset.section;
            if (section) showSection(section);
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
            let allServers = data.servers || [];
            
            // Get filter values
            const search = document.getElementById('serverSearch').value.toLowerCase();
            const filterStatus = document.getElementById('filterStatus').value;
            const filterOS = document.getElementById('filterOS').value;
            const filterCPU = parseFloat(document.getElementById('filterCPU').value) || 0;
            const filterMemory = parseFloat(document.getElementById('filterMemory').value) || 0;
            const filterDisk = parseFloat(document.getElementById('filterDisk').value) || 0;
            const sortBy = document.getElementById('serverSortSelect').value;
            
            // Apply filters
            servers = allServers.filter(s => {
                // Search filter
                if (search && !s.name.toLowerCase().includes(search) && !s.host.toLowerCase().includes(search)) {
                    return false;
                }
                // Status filter
                if (filterStatus && s.last_status !== filterStatus) {
                    return false;
                }
                // OS filter
                if (filterOS && s.os_type !== filterOS) {
                    return false;
                }
                // CPU filter
                if (filterCPU > 0 && (!s.cpu_percent || s.cpu_percent < filterCPU)) {
                    return false;
                }
                // Memory filter
                if (filterMemory > 0 && (!s.memory_percent || s.memory_percent < filterMemory)) {
                    return false;
                }
                // Disk filter
                if (filterDisk > 0 && (!s.disk_percent || s.disk_percent < filterDisk)) {
                    return false;
                }
                return true;
            });
            
            // Sort servers
            servers.sort((a, b) => {
                if (sortBy === 'status') {
                    if (a.last_status === 'up' && b.last_status !== 'up') return -1;
                    if (a.last_status !== 'up' && b.last_status === 'up') return 1;
                    return 0;
                } else if (sortBy === 'cpu') {
                    return (b.cpu_percent || 0) - (a.cpu_percent || 0);
                } else if (sortBy === 'memory') {
                    return (b.memory_percent || 0) - (a.memory_percent || 0);
                } else if (sortBy === 'disk') {
                    return (b.disk_percent || 0) - (a.disk_percent || 0);
                }
                return a.name.localeCompare(b.name);
            });
            
            // Update stats
            let online = 0, offline = 0, linux = 0, windows = 0;
            allServers.forEach(s => {
                if (s.last_status === 'up') online++; else offline++;
                if (s.os_type === 'linux') linux++; else windows++;
            });
            
            document.getElementById('dashboardServerSelector').innerHTML = '<option value="">All Servers</option>' + allServers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            document.getElementById('alert-server').innerHTML = '<option value="">Global (All Servers)</option>' + allServers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            
            // Filter stats
            const filterStats = document.getElementById('filterStats');
            let statsText = 'Showing ' + servers.length + ' of ' + allServers.length + ' servers';
            const activeFilters = [];
            if (search) activeFilters.push('search:"' + search + '"');
            if (filterStatus) activeFilters.push('status:' + filterStatus);
            if (filterOS) activeFilters.push('OS:' + filterOS);
            if (filterCPU > 0) activeFilters.push('CPU>' + filterCPU + '%');
            if (filterMemory > 0) activeFilters.push('MEM>' + filterMemory + '%');
            if (filterDisk > 0) activeFilters.push('DISK>' + filterDisk + '%');
            if (activeFilters.length > 0) {
                statsText += ' | Filters: ' + activeFilters.join(', ');
            }
            filterStats.textContent = statsText;
            
            document.getElementById('servers-tbody').innerHTML = servers.map(s => {
                const statusBadge = s.last_status === 'up' ? '<span class="badge badge-success">up</span>' : '<span class="badge badge-danger">offline</span>';
                
                // Host with port
                const hostDisplay = s.host + ':' + (s.agent_port || 9100);
                
                // CPU with color
                const cpuVal = s.cpu_percent ? s.cpu_percent.toFixed(1) : '-';
                const cpuColor = s.cpu_percent > 90 ? 'var(--red)' : s.cpu_percent > 70 ? 'var(--yellow)' : 'var(--text)';
                const cpuDisplay = s.cpu_percent ? '<span style="color:' + cpuColor + '">' + cpuVal + '%</span>' : '-';
                
                // Memory with color
                const memVal = s.memory_percent ? s.memory_percent.toFixed(1) : '-';
                const memColor = s.memory_percent > 90 ? 'var(--red)' : s.memory_percent > 70 ? 'var(--yellow)' : 'var(--text)';
                const memDisplay = s.memory_percent ? '<span style="color:' + memColor + '">' + memVal + '%</span>' : '-';
                
                // Parse disk info
                let diskDisplay = '-';
                if (s.disk_info) {
                    try {
                        const disks = JSON.parse(s.disk_info);
                        diskDisplay = disks.filter(d => d.volume.includes(':')).map(d => {
                            const vol = d.volume.replace(':', '');
                            const pct = d.percent ? d.percent.toFixed(0) : '?';
                            const color = d.percent > 90 ? 'var(--red)' : d.percent > 80 ? 'var(--yellow)' : 'var(--green)';
                            return '<span style="margin-right:4px;padding:2px 4px;background:rgba(0,0,0,0.3);border-radius:3px;font-size:11px;"><span style="color:' + color + '">' + vol + '</span>:' + pct + '%</span>';
                        }).join('');
                    } catch(e) {}
                } else if (s.disk_percent) {
                    const diskColor = s.disk_percent > 90 ? 'var(--red)' : s.disk_percent > 80 ? 'var(--yellow)' : 'var(--text)';
                    diskDisplay = '<span style="color:' + diskColor + '">' + s.disk_percent.toFixed(1) + '%</span>';
                }
                
                // Last check time
                const lastCheck = s.last_check ? s.last_check.substring(11, 19) : '-';
                
                return '<tr><td>' + statusBadge + '</td><td><strong>' + s.name + '</strong></td><td style="font-size:11px;color:var(--muted);">' + hostDisplay + '</td><td>' + s.os_type + '</td><td>' + cpuDisplay + '</td><td>' + memDisplay + '</td><td>' + diskDisplay + '</td><td style="font-size:11px;color:var(--muted);">' + lastCheck + '</td><td><button class="btn btn-secondary btn-sm" onclick="scrapeServer(' + s.id + ')" title="Scrape now"><i class="fas fa-sync"></i></button> <button class="btn btn-danger btn-sm" onclick="deleteServer(' + s.id + ')" title="Delete"><i class="fas fa-trash"></i></button></td></tr>';
            }).join('') || '<tr><td colspan="9" style="text-align:center;padding:40px;color:#999;">No servers match filters</td></tr>';
            
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            document.getElementById('stat-linux').textContent = linux;
            document.getElementById('stat-windows').textContent = windows;
            updateRAIDStatusPanel();
        } catch(e) { console.error(e); }
    }
    
    // Filter event listeners
    ['serverSearch', 'filterStatus', 'filterOS', 'filterCPU', 'filterMemory', 'filterDisk', 'serverSortSelect'].forEach(id => {
        document.getElementById(id).addEventListener('change', loadServers);
        document.getElementById(id).addEventListener('input', loadServers);
    });
    
    document.getElementById('clearFiltersBtn').addEventListener('click', function() {
        document.getElementById('serverSearch').value = '';
        document.getElementById('filterStatus').value = '';
        document.getElementById('filterOS').value = '';
        document.getElementById('filterCPU').value = '';
        document.getElementById('filterMemory').value = '';
        document.getElementById('filterDisk').value = '';
        document.getElementById('serverSortSelect').value = 'name';
        loadServers();
    });

    async function updateRAIDStatusPanel() {
        const panel = document.getElementById('raidStatusPanel');
        panel.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading RAID data...</p>';
        
        try {
            const resp = await fetch('/api/raid-status');
            const data = await resp.json();
            const raidData = data.raid_status || [];
            
            if (!raidData.length) {
                panel.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;">No RAID data available</p>';
                document.getElementById('raidTotalServers').textContent = '0';
                document.getElementById('raidHealthy').textContent = '0';
                document.getElementById('raidDegraded').textContent = '0';
                document.getElementById('raidTotalSize').textContent = '0 TB';
                return;
            }
            
            // Calculate statistics
            let totalRaids = 0, healthyRaids = 0, degradedRaids = 0, totalSizeGB = 0;
            raidData.forEach(s => {
                s.raids.forEach(r => {
                    totalRaids++;
                    if (r.healthy) healthyRaids++; else degradedRaids++;
                    const size = parseInt(r.size) || 0;
                    totalSizeGB += size;
                });
            });
            
            // Update stats
            document.getElementById('raidTotalServers').textContent = raidData.length;
            document.getElementById('raidHealthy').textContent = healthyRaids;
            document.getElementById('raidDegraded').textContent = degradedRaids;
            document.getElementById('raidTotalSize').textContent = Math.round(totalSizeGB / 1024) + ' TB';
            
            // Sort by health (degraded first)
            raidData.sort((a, b) => a.healthy - b.healthy);
            
            panel.innerHTML = raidData.map(s => {
                const statusColor = s.healthy ? 'var(--green)' : 'var(--red)';
                const statusIcon = s.healthy ? 'fa-check-circle' : 'fa-exclamation-triangle';
                const borderColor = s.healthy ? 'rgba(115,191,105,0.3)' : 'rgba(242,73,92,0.5)';
                
                // Calculate server totals
                const serverSize = s.raids.reduce((sum, r) => sum + (parseInt(r.size) || 0), 0);
                
                return '<div style="margin-bottom: 12px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 3px solid ' + borderColor + ';">' +
                    '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">' +
                    '<div><i class="fas fa-server" style="color: var(--muted); margin-right: 8px;"></i><strong style="font-size: 13px;">' + s.server + '</strong></div>' +
                    '<div><span style="color: var(--muted); font-size: 11px; margin-right: 12px;">' + s.raids.length + ' arrays | ' + Math.round(serverSize/1024) + ' TB</span>' +
                    '<span class="badge ' + (s.healthy ? 'badge-success' : 'badge-danger') + '"><i class="fas ' + statusIcon + '"></i> ' + (s.healthy ? 'Healthy' : 'Degraded') + '</span></div></div>' +
                    '<table style="width: 100%; font-size: 11px; border-collapse: collapse;">' +
                    '<tr style="color: var(--muted); border-bottom: 1px solid var(--border);"><th style="padding: 6px; text-align: left;">ID</th><th style="padding: 6px; text-align: left;">Type</th><th style="padding: 6px; text-align: right;">Size</th><th style="padding: 6px; text-align: center;">Status</th></tr>' +
                    s.raids.map(r => {
                        const rowBg = r.healthy ? '' : 'background: rgba(242,73,92,0.1);';
                        return '<tr style="' + rowBg + ' border-bottom: 1px solid rgba(255,255,255,0.03);">' +
                        '<td style="padding: 6px;"><span style="background: rgba(87,148,242,0.2); padding: 2px 6px; border-radius: 3px;">RAID' + r.id + '</span></td>' +
                        '<td style="padding: 6px;"><span style="color: ' + (r.type.includes('10') ? 'var(--purple)' : r.type.includes('6') ? 'var(--blue)' : r.type.includes('5') ? 'var(--green)' : 'var(--yellow)') + ';">' + r.type + '</span></td>' +
                        '<td style="padding: 6px; text-align: right; color: var(--muted);">' + r.size + '</td>' +
                        '<td style="padding: 6px; text-align: center;"><span class="badge ' + (r.healthy ? 'badge-success' : 'badge-danger') + '" style="font-size: 10px;">' + (r.healthy ? 'OK' : 'FAILED') + '</span></td></tr>';
                    }).join('') + '</table></div>';
            }).join('');
        } catch(e) {
            panel.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;">Error loading RAID data: ' + e.message + '</p>';
        }
    }

    async function deleteServer(id) {
        if (confirm('Delete server?')) {
            await fetch('/api/servers/' + id, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadServers();
        }
    }
    
    async function scrapeServer(id) {
        const btn = event.target.closest('button');
        const icon = btn.querySelector('i');
        icon.classList.add('fa-spin');
        try {
            const resp = await fetch('/api/servers/' + id + '/scrape', {method: 'POST', headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            if (data.status === 'ok') {
                await loadServers();
            } else {
                alert('Scrape failed: ' + data.message);
            }
        } catch(e) {
            alert('Scrape error: ' + e.message);
        }
        setTimeout(() => icon.classList.remove('fa-spin'), 500);
    }
    
    async function fetchMetricData(metricName) {
        try {
            const now = new Date();
            const start = new Date(now.getTime() - getRangeMs(currentRange));
            const resp = await fetch(`/api/v1/query?query=${metricName}&start=${start.toISOString()}&end=${now.toISOString()}&step=60`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            const data = await resp.json();
            return data.result || [];
        } catch(e) {
            return [];
        }
    }
    
    function getRangeMs(range) {
        const ms = {'5m':5*60*1000,'15m':15*60*1000,'1h':60*60*1000,'6h':6*60*60*1000,'24h':24*60*60*1000};
        return ms[range] || ms['1h'];
    }
    
    function generateTimeSeriesData(currentValue, points) {
        const data = [];
        let val = currentValue || Math.random() * 50 + 20;
        for (let i = 0; i < points; i++) {
            val = Math.max(0, Math.min(100, val + (Math.random() - 0.5) * 10));
            data.push(val);
        }
        return data;
    }
    
    async function initCharts() {
        Object.values(charts).forEach(c => c && c.destroy());
        charts = {};
        const labels = generateLabels();
        const filtered = getFilteredServers();
        
        const getData = (key, min, max) => {
            if (!filtered.length) return [{label:'No Data',data:rand(12,0,5),borderColor:colors[0],backgroundColor:colors[0]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
            
            return filtered.map((s,i) => {
                let val = s[key + '_percent'];
                if (val === null || val === undefined) {
                    if (key === 'network') val = s['network_rx'];
                    if (val === null || val === undefined) val = null;
                }
                return {
                    label: s.name,
                    data: generateTimeSeriesData(val, 12),
                    borderColor: colors[i % colors.length],
                    backgroundColor: colors[i % colors.length] + '15',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 1.5,
                    pointRadius: 0
                };
            });
        };
        
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type:'line',data:{labels:labels,datasets:getData('cpu',0,100)},options:chartOpts('%',0,100)});
        updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
        
        charts.memory = new Chart(document.getElementById('memoryChart'), {type:'line',data:{labels:labels,datasets:getData('memory',0,100)},options:chartOpts('%',0,100)});
        updateLegend('memoryLegend', charts.memory.data.datasets, '%');
        
        charts.disk = new Chart(document.getElementById('diskChart'), {type:'line',data:{labels:labels,datasets:getData('disk',0,100)},options:chartOpts('%',0,100)});
        updateLegend('diskLegend', charts.disk.data.datasets, '%');
        
        charts.network = new Chart(document.getElementById('networkChart'), {type:'line',data:{labels:labels,datasets:getData('network',0,100)},options:chartOpts(' MB/s',0,100)});
        updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
    }
    
    async function updateCharts(filtered) {
        if (!charts.cpu) { initCharts(); return; }
        const labels = generateLabels();
        
        const getData = (key, min, max) => {
            if (!filtered.length) return [{label:'No Data',data:rand(12,0,5),borderColor:colors[0],backgroundColor:colors[0]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
            
            return filtered.map((s,i) => {
                let val = s[key + '_percent'];
                if (val === null || val === undefined) {
                    if (key === 'network') val = s['network_rx'];
                    if (val === null || val === undefined) val = null;
                }
                return {
                    label: s.name,
                    data: generateTimeSeriesData(val, 12),
                    borderColor: colors[i % colors.length],
                    backgroundColor: colors[i % colors.length] + '15',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 1.5,
                    pointRadius: 0
                };
            });
        };
        
        charts.cpu.data.labels = labels;
        charts.cpu.data.datasets = getData('cpu', 0, 100);
        charts.cpu.update();
        updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
        
        charts.memory.data.labels = labels;
        charts.memory.data.datasets = getData('memory', 0, 100);
        charts.memory.update();
        updateLegend('memoryLegend', charts.memory.data.datasets, '%');
        
        charts.disk.data.labels = labels;
        charts.disk.data.datasets = getData('disk', 0, 100);
        charts.disk.update();
        updateLegend('diskLegend', charts.disk.data.datasets, '%');
        
        charts.network.data.labels = labels;
        charts.network.data.datasets = getData('network', 0, 100);
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
        const parent = el.parentElement;
        const header = parent.querySelector('.legend-header');
        
        const sorted = [...datasets].sort((a, b) => {
            if (!legendSortBy) return 0;
            const aLast = a.data[a.data.length - 1];
            const aMax = Math.max(...a.data);
            const bLast = b.data[b.data.length - 1];
            const bMax = Math.max(...b.data);
            if (legendSortBy === 'last') {
                return legendSortAsc ? aLast - bLast : bLast - aLast;
            } else if (legendSortBy === 'max') {
                return legendSortAsc ? aMax - bMax : bMax - aMax;
            }
            return 0;
        });
        
        el.innerHTML = sorted.map((ds, i) => {
            const last = ds.data[ds.data.length-1];
            const mx = Math.max(...ds.data);
            const server = servers.find(s => s.name === ds.label);
            const serverId = server ? server.id : null;
            const isActive = legendServerFilter && legendServerFilter == serverId;
            return '<div class="legend-item" data-server="'+serverId+'" data-name="'+ds.label+'" style="'+(isActive ? 'background: rgba(87,148,242,0.2); border-left: 2px solid var(--blue);' : '')+'"><div class="legend-color" style="background:'+ds.borderColor+'"></div><div class="legend-name">'+ds.label+'</div><div class="legend-value-last">'+last.toFixed(1)+suffix+'</div><div class="legend-value-max">'+mx.toFixed(1)+suffix+'</div></div>';
        }).join('');
        
        // Attach click handlers to legend items
        el.querySelectorAll('.legend-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.stopPropagation();
                const sid = this.dataset.server;
                const name = this.dataset.name;
                
                if (legendServerFilter == sid) {
                    legendServerFilter = null;
                    currentServerFilter = '';
                    document.getElementById('dashboardServerSelector').value = '';
                    document.getElementById('clearFilterBtn').style.display = 'none';
                } else {
                    legendServerFilter = sid;
                    currentServerFilter = sid;
                    document.getElementById('dashboardServerSelector').value = sid;
                    document.getElementById('clearFilterBtn').style.display = 'inline-flex';
                }
                
                initCharts();
            });
            
            item.style.cursor = 'pointer';
        });
        
        // Attach click handlers to header for sorting
        if (header) {
            const lastHeader = header.querySelector('.legend-header-last');
            const maxHeader = header.querySelector('.legend-header-max');
            
            if (lastHeader) {
                lastHeader.onclick = function(e) {
                    e.stopPropagation();
                    if (legendSortBy === 'last') {
                        legendSortAsc = !legendSortAsc;
                    } else {
                        legendSortBy = 'last';
                        legendSortAsc = true;
                    }
                    initCharts();
                };
                lastHeader.style.cursor = 'pointer';
                lastHeader.title = 'Sort by Last value';
                // Update indicator
                if (legendSortBy === 'last') {
                    lastHeader.innerHTML = 'Last ' + (legendSortAsc ? '&#9650;' : '&#9660;');
                } else {
                    lastHeader.innerHTML = 'Last';
                }
            }
            
            if (maxHeader) {
                maxHeader.onclick = function(e) {
                    e.stopPropagation();
                    if (legendSortBy === 'max') {
                        legendSortAsc = !legendSortAsc;
                    } else {
                        legendSortBy = 'max';
                        legendSortAsc = true;
                    }
                    initCharts();
                };
                maxHeader.style.cursor = 'pointer';
                maxHeader.title = 'Sort by Max value';
                // Update indicator
                if (legendSortBy === 'max') {
                    maxHeader.innerHTML = 'Max ' + (legendSortAsc ? '&#9650;' : '&#9660;');
                } else {
                    maxHeader.innerHTML = 'Max';
                }
            }
        }
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
    
    document.getElementById('refreshRaidBtn').addEventListener('click', updateRAIDStatusPanel);

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
            const resp = await fetch('/api/backup/list', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            const files = data.files || [];
            if (data.backup_path) {
                document.getElementById('backupPath').value = data.backup_path;
            }
            window.backupFiles = files;
            let html = '';
            for (let i = 0; i < files.length; i++) {
                const b = files[i];
                const size = b.size ? (b.size/1024).toFixed(1) + ' KB' : '-';
                const created = b.created ? b.created.substring(0, 19) : '-';
                html += '<tr><td>' + b.filename + '</td><td>' + size + '</td><td>' + created + '</td><td><button class="btn btn-danger btn-sm" data-idx="' + i + '" onclick="deleteBackupByIndex(' + i + ')"><i class="fas fa-trash"></i></button> <button class="btn btn-secondary btn-sm" data-idx="' + i + '" onclick="restoreByIndex(' + i + ')"><i class="fas fa-undo"></i></button></td></tr>';
            }
            document.getElementById('backups-tbody').innerHTML = html || '<tr><td colspan="4" style="text-align:center;color:#999;">No backups</td></tr>';
        } catch(e) { console.error(e); }
    }
    
    function deleteBackupByIndex(idx) {
        const file = window.backupFiles[idx];
        if (!file) return;
        if (!confirm('Delete ' + file.filename + '?')) return;
        deleteBackupFile(file.path);
    }
    
    function restoreByIndex(idx) {
        const file = window.backupFiles[idx];
        if (!file) return;
        restoreThisBackup(file.path);
    }
    
    function restoreThisBackup(path) {
        document.getElementById('restorePath').value = path;
        document.getElementById('restorePath').scrollIntoView();
    }
    
    async function deleteBackupFile(path) {
        if (!confirm('Delete this backup file?')) return;
        try {
            await fetch('/api/backup/file', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({path: path})
            });
            loadBackups();
        } catch(e) { alert('Error: ' + e.message); }
    }
    
    document.getElementById('createBackupBtn').addEventListener('click', async function() {
        const btn = this;
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
        btn.disabled = true;
        try {
            const backupPath = document.getElementById('backupPath').value || '';
            const resp = await fetch('/api/backup/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({path: backupPath})
            });
            const data = await resp.json();
            if (data.status === 'ok') {
                alert('Backup created!\nFile: ' + data.filename + '\nSize: ' + (data.size/1024).toFixed(1) + ' KB\nPath: ' + data.path);
                loadBackups();
            } else {
                alert('Error: ' + (data.detail || 'Unknown error'));
            }
        } catch(e) {
            alert('Error: ' + e.message);
        }
        btn.innerHTML = orig;
        btn.disabled = false;
    });
    
    document.getElementById('restoreBackupBtn').addEventListener('click', async function() {
        const filePath = document.getElementById('restorePath').value;
        if (!filePath) {
            alert('Please enter backup file path');
            return;
        }
        if (!confirm('Restore from backup?\n\nThis will overwrite current data!\nFile: ' + filePath)) {
            return;
        }
        
        const btn = this;
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Restoring...';
        btn.disabled = true;
        
        try {
            const resp = await fetch('/api/backup/restore', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({
                    file: filePath,
                    restore_db: document.getElementById('restoreDb').checked,
                    restore_config: document.getElementById('restoreConfig').checked,
                    restore_settings: document.getElementById('restoreSettings').checked
                })
            });
            const data = await resp.json();
            if (data.status === 'ok') {
                alert('Backup restored successfully!\nPlease restart the server to apply changes.');
            } else {
                alert('Error: ' + (data.detail || 'Unknown error'));
            }
        } catch(e) {
            alert('Error: ' + e.message);
        }
        btn.innerHTML = orig;
        btn.disabled = false;
    });
    
    // API Keys
    async function loadApiKeys() {
        try {
            const resp = await fetch('/api/api-keys', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            document.getElementById('apikeys-tbody').innerHTML = (data.keys || []).map(k => 
                '<tr><td>' + k.name + '</td><td><code style="background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:3px;">****</code></td><td>' + (k.created_at || '-') + '</td><td>' + (k.last_used || 'Never') + '</td><td><button class="btn btn-danger btn-sm" onclick="deleteApiKey(' + k.id + ')"><i class="fas fa-trash"></i></button></td></tr>'
            ).join('') || '<tr><td colspan="5" style="text-align:center;color:#999;">No API keys</td></tr>';
        } catch(e) { console.error(e); }
    }
    
    document.getElementById('createApiKeyBtn').addEventListener('click', async function() {
        const name = prompt('Enter API key name:');
        if (name) {
            const resp = await fetch('/api/api-keys', {method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name})});
            const data = await resp.json();
            if (data.key) {
                alert('API Key created! Copy it now (shown once):\\n\\n' + data.key);
                loadApiKeys();
            }
        }
    });
    
    async function deleteApiKey(id) {
        if (confirm('Delete this API key?')) {
            await fetch('/api/api-keys/' + id, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadApiKeys();
        }
    }
    
    // Audit Log
    async function loadAuditLog() {
        try {
            const resp = await fetch('/api/audit-log', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            document.getElementById('audit-tbody').innerHTML = (data.logs || []).map(l => 
                '<tr><td>' + (l.created_at || '-') + '</td><td>' + (l.user_id || 'System') + '</td><td>' + l.action + '</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">' + (l.details || '-') + '</td><td>' + (l.ip_address || '-') + '</td></tr>'
            ).join('') || '<tr><td colspan="5" style="text-align:center;color:#999;">No audit logs</td></tr>';
        } catch(e) { console.error(e); }
    }
    
    document.getElementById('refreshAuditBtn').addEventListener('click', loadAuditLog);
    
    // Maintenance
    async function loadMaintenance() {
        try {
            const resp = await fetch('/api/maintenance', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            document.getElementById('maintenanceList').innerHTML = (data.windows || []).map(w => 
                '<div style="display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(0,0,0,0.2);border-radius:6px;margin-bottom:8px;">' +
                '<div><strong>' + w.name + '</strong><br><span style="color:var(--muted);font-size:11px;">' + w.start_time + ' - ' + w.end_time + '</span></div>' +
                '<span class="badge ' + (w.enabled ? 'badge-success' : 'badge-warning') + '">' + (w.enabled ? 'Active' : 'Disabled') + '</span>' +
                '</div>'
            ).join('') || '<p style="color:var(--muted);text-align:center;padding:20px;">No maintenance windows configured</p>';
        } catch(e) { console.error(e); }
    }
    
    document.getElementById('addMaintenanceBtn').addEventListener('click', async function() {
        const name = prompt('Maintenance window name:');
        if (name) {
            const start = prompt('Start time (YYYY-MM-DD HH:MM):');
            const end = prompt('End time (YYYY-MM-DD HH:MM):');
            if (start && end) {
                await fetch('/api/maintenance', {method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name, start_time: start, end_time: end})});
                loadMaintenance();
            }
        }
    });
    
    // Settings tabs
    document.querySelectorAll("#section-settings .tab-menu .tab-item").forEach(btn => {
        btn.addEventListener("click", function() {
            document.querySelectorAll("#section-settings .tab-menu .tab-item").forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const tab = this.dataset.tab;
            document.querySelectorAll("#section-settings .tab-content").forEach(c => c.style.display = 'none');
            document.getElementById('settings-' + tab).style.display = 'block';
            if (tab === 'apikeys') loadApiKeys();
            if (tab === 'audit') loadAuditLog();
            if (tab === 'maintenance') loadMaintenance();
        });
    });
    
    let refreshInterval = null;
    
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(async () => {
            await loadServers();
            updateRAIDStatusPanel();
            if (document.getElementById('section-dashboard').classList.contains('active')) {
                initCharts();
            }
        }, 30000);
    }
    
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
    
    // Initialize event listeners
    document.addEventListener('DOMContentLoaded', function() {
        // Stat cards click
        document.querySelectorAll('.stat-card[data-filter]').forEach(card => {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function() {
                filterBy(this.dataset.filter);
            });
        });
        
        // Server selector change
        document.getElementById('dashboardServerSelector').addEventListener('change', function() {
            filterDashboard();
        });
        
        // Time range buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentRange = this.dataset.range;
                initCharts();
            });
        });
    });
    
    loadServers();
    updateRAIDStatusPanel();
    setTimeout(() => {
        initCharts();
        startAutoRefresh();
    }, 100);
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
         datetime.now(timezone.utc).isoformat()))
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

@router.post("/api/servers/{server_id}/scrape")
async def scrape_server(server_id: int):
    import httpx
    conn = get_db()
    server = conn.execute("SELECT * FROM servers WHERE id=?", (server_id,)).fetchone()
    conn.close()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    target = f"{server['host']}:{server['agent_port']}"
    url = f"http://{target}/metrics"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                # Parse metrics and update database
                metrics = {}
                cpu_idle_total = 0
                cpu_all_total = 0
                disk_info = {}
                
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    try:
                        if '{' in line:
                            name_part, rest = line.split('{', 1)
                            labels_part, value_str = rest.rsplit('}', 1)
                            name = name_part.strip()
                            value = float(value_str.strip())
                            
                            # Aggregate CPU idle time from windows_exporter
                            if name == 'windows_cpu_time_total':
                                if 'mode="idle"' in labels_part:
                                    cpu_idle_total += value
                                cpu_all_total += value
                            
                            # Collect ALL disks from windows_exporter
                            if name == 'windows_logical_disk_free_bytes':
                                import re
                                vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                if vol_match:
                                    vol = vol_match.group(1)
                                    if vol not in disk_info:
                                        disk_info[vol] = {'volume': vol, 'free': 0, 'size': 0}
                                    disk_info[vol]['free'] = value
                            if name == 'windows_logical_disk_size_bytes':
                                import re
                                vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                if vol_match:
                                    vol = vol_match.group(1)
                                    if vol not in disk_info:
                                        disk_info[vol] = {'volume': vol, 'free': 0, 'size': 0}
                                    disk_info[vol]['size'] = value
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
                    metrics['windows_cpu_time_total_idle'] = cpu_idle_total
                    metrics['windows_cpu_time_total_all'] = cpu_all_total
                
                # Calculate disk percentages and get C: for main metric
                disks_list = []
                for vol, info in disk_info.items():
                    if info['size'] > 0:
                        info['percent'] = 100 * (1 - info['free'] / info['size'])
                        info['used_gb'] = round((info['size'] - info['free']) / (1024**3), 1)
                        info['size_gb'] = round(info['size'] / (1024**3), 1)
                        disks_list.append(info)
                        # Use C: for main disk_percent if available
                        if 'C:' in vol:
                            metrics['windows_logical_disk_free_bytes'] = info['free']
                            metrics['windows_logical_disk_size_bytes'] = info['size']
                
                disk_info_json = json.dumps(disks_list) if disks_list else None
                
                # Parse CPU - support both node_exporter and windows_exporter
                cpu = metrics.get('node_cpu_percent') or metrics.get('cpu_usage_percent') or 0
                if not cpu:
                    idle = metrics.get('windows_cpu_time_total_idle', 0)
                    total = metrics.get('windows_cpu_time_total_all', 0)
                    if total > 0:
                        cpu = 100 * (1 - idle / total) if idle < total else 0
                
                # Parse Memory - support both node_exporter and windows_exporter
                memory = metrics.get('node_memory_percent') or metrics.get('memory_usage_percent') or 0
                if not memory:
                    mem_total = metrics.get('windows_cs_physical_memory_bytes', 0)
                    mem_free = metrics.get('windows_os_physical_memory_free_bytes', 0)
                    if mem_total > 0:
                        memory = 100 * (1 - mem_free / mem_total) if mem_free < mem_total else 0
                
                # Parse Disk - support both node_exporter and windows_exporter
                disk = metrics.get('node_disk_percent') or metrics.get('disk_usage_percent') or 0
                if not disk:
                    disk_total = metrics.get('windows_logical_disk_size_bytes', 0)
                    disk_free = metrics.get('windows_logical_disk_free_bytes', 0)
                    if disk_total > 0:
                        disk = 100 * (1 - disk_free / disk_total) if disk_free < disk_total else 0
                
                network_rx = metrics.get('node_network_receive_bytes_total') or metrics.get('system_network_rx_bytes') or 0
                network_tx = metrics.get('node_network_transmit_bytes_total') or metrics.get('system_network_tx_bytes') or 0
                uptime = metrics.get('system_uptime_seconds') or metrics.get('windows_system_system_up_time', '') or ''
                
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                
                conn = get_db()
                conn.execute('''UPDATE servers SET 
                    last_check = ?, last_status = 'up',
                    cpu_percent = ?, memory_percent = ?, disk_percent = ?,
                    network_rx = ?, network_tx = ?, uptime = ?, disk_info = ?
                    WHERE id = ?''',
                    (now, cpu, memory, disk, network_rx, network_tx, str(uptime), disk_info_json, server_id))
                conn.commit()
                conn.close()
                
                return {"status": "ok", "message": f"Scraped {target}", "metrics": {"cpu": cpu, "memory": memory, "disk": disk, "disks": disks_list}}
            else:
                # Update server as down
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                conn = get_db()
                conn.execute('UPDATE servers SET last_check = ?, last_status = ? WHERE id = ?',
                            (now, 'down', server_id))
                conn.commit()
                conn.close()
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        # Update server as down
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db()
        conn.execute('UPDATE servers SET last_check = ?, last_status = ? WHERE id = ?',
                    (now, 'down', server_id))
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
        item = {"channel": n['channel'], "enabled": bool(n['enabled'])}
        item.update(json.loads(n['config'] or '{}'))
        result.append(item)
    return {"notifications": result}

@router.get("/api/raid-status")
async def get_raid_status():
    import httpx
    import asyncio
    import re
    
    telegraf_hosts = [
        'host-vm.it.ua:9273', 'host-vm1.it.ua:9273', 'host-vm2.it.ua:9273', 'host-vm3.it.ua:9273',
        'host-vm4.it.ua:9273', 'host-vm7.it.ua:9273', 'host-vm8.it.ua:9273', 'host-vm9.it.ua:9273',
        'host-vm10.it.ua:9273', 'host-vm11.it.ua:9273', 'host-vm12.it.ua:9273',
        'hst01.smarttender.biz.int:9273', 'hst02.smarttender.biz.int:9273', 'hst03.smarttender.biz.int:9273',
        'hst04.smarttender.biz.int:9273', 'hst05.smarttender.biz.int:9273', 'hst06.smarttender.biz.int:9273',
        'itdb01.it.ua:9273', 'itdb02.it.ua:9273', 'SMSDBAZ.it.ua:9273', 'SMSDBAZ2.it.ua:9273',
        'TENDER.smarttender.biz.int:9273', 'TENDER-SEC.smarttender.biz.int:9273',
        'TENDER-THIRD.smarttender.biz.int:9273', '10.0.12.4:9273', 'TENDER-FS.smarttender.biz.int:9273',
    ]
    
    raid_data = []
    
    async def fetch_raid(host):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f'http://{host}/metrics')
                if resp.status_code == 200:
                    raids = {}
                    server_name = host.split(':')[0]
                    for line in resp.text.split('\n'):
                        if line.startswith('prometheus_raid_status{'):
                            match = re.match(r'prometheus_raid_status\{host="([^"]+)",id="([^"]+)",raid_type="([^"]+)",size="([^"]+)"\}\s+(\d+)', line)
                            if match:
                                hname, raid_id, raid_type, size, status = match.groups()
                                server_name = hname
                                raids[raid_id] = {
                                    "id": raid_id,
                                    "type": raid_type,
                                    "size": size + " GB",
                                    "healthy": status == "1"
                                }
                    
                    if raids:
                        all_healthy = all(r["healthy"] for r in raids.values())
                        return {
                            "server": server_name,
                            "raids": list(raids.values()),
                            "healthy": all_healthy
                        }
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
             alert.description, int(alert.enabled), datetime.now(timezone.utc).isoformat()))
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

# Full Backup System
import zipfile
import shutil

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
        "last_backup": config.get("backup_last", "")
    }

@router.post("/api/backup/config")
async def set_backup_config(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                     (f"backup_{key}", str(value)))
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
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pymon_full_{timestamp}.zip"
        dest = os.path.join(backup_path, filename)
        
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Database
            if os.path.exists(DB_PATH):
                zf.write(DB_PATH, 'pymon.db')
            
            # Config file
            config_path = os.path.join(os.path.dirname(DB_PATH), 'config.yml')
            if os.path.exists(config_path):
                zf.write(config_path, 'config.yml')
            
            # Export all settings as JSON
            conn = get_db()
            settings = {}
            for table in ['servers', 'alerts', 'notifications', 'settings', 'api_keys', 'maintenance_windows']:
                try:
                    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                    settings[table] = [dict(r) for r in rows]
                except:
                    settings[table] = []
            
            import json
            zf.writestr('settings.json', json.dumps(settings, indent=2, default=str))
            
            # Update last backup time
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        ("backup_last", datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        
        size = os.path.getsize(dest)
        
        # Log to backups table
        conn = get_db()
        conn.execute("INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
                     (filename, size, datetime.now(timezone.utc).isoformat()))
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
        
        with zipfile.ZipFile(backup_file, 'r') as zf:
            # Restore database
            if restore_db and 'pymon.db' in zf.namelist():
                # Backup current DB first
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, DB_PATH + ".pre_restore")
                zf.extract('pymon.db', os.path.dirname(DB_PATH))
            
            # Restore config
            if restore_config and 'config.yml' in zf.namelist():
                zf.extract('config.yml', os.path.dirname(DB_PATH))
            
            # Restore settings
            if restore_settings and 'settings.json' in zf.namelist():
                import json
                settings_data = json.loads(zf.read('settings.json').decode())
                conn = get_db()
                for table, rows in settings_data.items():
                    if rows:
                        try:
                            # Clear existing data
                            conn.execute(f"DELETE FROM {table}")
                            # Insert restored data
                            for row in rows:
                                cols = ', '.join([k for k in row.keys() if k != 'id'])
                                vals = ', '.join(['?' for _ in row if _ != 'id'])
                                placeholders = [row[k] for k in row.keys() if k != 'id']
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
                if f.endswith('.zip') or f.endswith('.sqlite'):
                    path = os.path.join(backup_path, f)
                    files.append({
                        "filename": f,
                        "path": path,
                        "size": os.path.getsize(path),
                        "created": datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                    })
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
        tables = ['servers', 'alerts', 'api_keys', 'audit_log', 'maintenance_windows', 'backups']
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
        conn.execute('''UPDATE servers SET 
            last_check = NULL, last_status = NULL,
            cpu_percent = NULL, memory_percent = NULL, disk_percent = NULL,
            network_rx = NULL, network_tx = NULL, uptime = NULL,
            raid_status = NULL, disk_info = NULL''')
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
        conn.execute("INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
                     (filename, size, datetime.now(timezone.utc).isoformat()))
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
    import secrets
    import hashlib
    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    name = data.get("name", "API Key")
    conn = get_db()
    conn.execute("INSERT INTO api_keys (name, key_hash, created_at) VALUES (?, ?, ?)",
                 (name, key_hash, datetime.now(timezone.utc).isoformat()))
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
        conn.execute("INSERT INTO audit_log (user_id, action, details, ip_address, created_at) VALUES (?, ?, ?, ?, ?)",
                     (user_id, action, details, ip, datetime.now(timezone.utc).isoformat()))
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
    conn.execute("INSERT INTO maintenance_windows (name, start_time, end_time, servers, enabled, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                 (data.get("name"), data.get("start_time"), data.get("end_time"), 
                  json.dumps(data.get("servers", [])), datetime.now(timezone.utc).isoformat()))
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
        conn.execute('''CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT
        )''')
        conn.execute("INSERT INTO webhooks (name, url, events, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
                     (data.get("name"), data.get("url"), json.dumps(data.get("events", [])), 
                      datetime.now(timezone.utc).isoformat()))
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
        "alerts": alerts_count
    }
