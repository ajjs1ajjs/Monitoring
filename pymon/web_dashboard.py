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

class ServerModel(BaseModel):
    name: str
    host: str
    os_type: str = "linux"  # linux or windows
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
        
        # Servers table for system monitoring
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
            agent_version TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            recorded_at TEXT
        )''')
        
        for channel in ['telegram', 'discord', 'slack', 'email']:
            c.execute("INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing web tables: {e}")
        raise

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Server Monitoring</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            padding: 48px;
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.1);
            width: 100%;
            max-width: 440px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
        }
        .logo { text-align: center; margin-bottom: 40px; }
        .logo h1 { 
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 42px;
            font-weight: 800;
        }
        .form-group { margin-bottom: 24px; }
        label { display: block; color: #94a3af; margin-bottom: 10px; font-size: 15px; font-weight: 500; }
        input {
            width: 100%;
            padding: 16px;
            background: rgba(0,0,0,0.3);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1); }
        button {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 17px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 16px;
        }
        button:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">
            <h1>PyMon</h1>
            <p style="color: #64748b; margin-top: 8px;">Server Monitoring</p>
        </div>
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" required placeholder="admin">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" required placeholder="••••••">
            </div>
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
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Grafana Style Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0d0f14;
            --card: #181b1f;
            --border: #2c3235;
            --text: #e0e0e0;
            --muted: #999;
            --blue: #5794f2;
            --green: #73bf69;
            --red: #f2495c;
            --yellow: #f2cc0c;
            --orange: #ff780a;
            --purple: #b877d9;
            --cyan: #00d8d8;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            font-size: 13px;
        }
        /* Top Navigation - Grafana Style */
        .top-nav {
            background: linear-gradient(90deg, #161719 0%, #1f2326 100%);
            border-bottom: 1px solid var(--border);
            padding: 0 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 48px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .nav-left { display: flex; align-items: center; gap: 24px; }
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .logo h1 {
            color: var(--blue);
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        .logo-icon {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--blue), #2c7bd9);
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: white;
        }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            color: var(--muted);
            font-weight: 500;
            font-size: 13px;
            transition: all 0.15s;
            text-decoration: none;
            border: none;
            background: transparent;
        }
        .nav-item:hover {
            color: var(--text);
            background: rgba(255,255,255,0.05);
        }
        .nav-item.active {
            background: rgba(87, 148, 242, 0.15);
            color: var(--blue);
        }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .server-selector {
            padding: 6px 10px;
            background: #111217;
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 13px;
            min-width: 160px;
            cursor: pointer;
        }
        .server-selector:focus { outline: none; border-color: var(--blue); }
        .main { padding: 16px; min-height: calc(100vh - 48px); }
        
        /* Dashboard Toolbar - Grafana Style */
        .dashboard-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding: 8px 12px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 4px;
        }
        .toolbar-left { display: flex; align-items: center; gap: 16px; }
        .toolbar-right { display: flex; align-items: center; gap: 8px; }
        .breadcrumb {
            color: var(--muted);
            font-size: 13px;
        }
        .breadcrumb span { color: var(--text); }
        .time-range {
            display: flex;
            gap: 2px;
            background: #111217;
            border-radius: 4px;
            padding: 2px;
            border: 1px solid var(--border);
        }
        .time-btn {
            padding: 4px 10px;
            background: transparent;
            border: none;
            border-radius: 3px;
            color: var(--muted);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .time-btn:hover { color: var(--text); }
        .time-btn.active {
            background: #2c3235;
            color: var(--text);
        }
        .refresh-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #111217;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 4px 8px;
        }
        .refresh-btn {
            background: transparent;
            border: none;
            color: var(--muted);
            cursor: pointer;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .refresh-btn:hover { color: var(--text); }
        .refresh-interval {
            color: var(--muted);
            font-size: 12px;
        }
        
        /* Panels Grid - Grafana Style */
        .panels-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }
        .panel {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }
        .panel::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(180deg, rgba(255,255,255,0.02) 0%, transparent 100%);
        }
        .panel-title {
            font-size: 13px;
            font-weight: 500;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 8px var(--green);
            animation: pulse 2s ease-in-out infinite;
        }
        .status-dot.warning {
            background: var(--yellow);
            box-shadow: 0 0 8px var(--yellow);
        }
        .status-dot.error {
            background: var(--red);
            box-shadow: 0 0 8px var(--red);
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
        }
        .panel-actions {
            display: flex;
            gap: 4px;
        }
        .panel-btn {
            padding: 4px 8px;
            background: transparent;
            border: none;
            color: var(--muted);
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
        }
        .panel-btn:hover { 
            color: var(--text); 
            background: rgba(255,255,255,0.05);
        }
        .panel-body {
            display: flex;
            height: 280px;
        }
        .panel-chart {
            flex: 1;
            padding: 12px;
            position: relative;
            min-width: 0;
        }
        .panel-legend {
            width: 140px;
            border-left: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
            overflow-y: auto;
            font-size: 11px;
        }
        .legend-header {
            display: grid;
            grid-template-columns: 1fr 45px 45px;
            padding: 8px 10px;
            border-bottom: 1px solid var(--border);
            color: var(--muted);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            font-weight: 600;
        }
        .legend-item {
            display: grid;
            grid-template-columns: 12px 1fr 45px 45px;
            align-items: center;
            padding: 6px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            cursor: pointer;
            transition: background 0.15s;
        }
        .legend-item:hover { background: rgba(255,255,255,0.03); }
        .legend-item.hidden { opacity: 0.3; }
        .legend-color {
            width: 10px;
            height: 10px;
            border-radius: 2px;
            margin-right: 8px;
        }
        .legend-name {
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 11px;
        }
        .legend-value {
            color: var(--muted);
            text-align: right;
            font-size: 11px;
            font-variant-numeric: tabular-nums;
        }
        
        /* Stats Row */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .stat-icon {
            width: 40px;
            height: 40px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        .stat-content { flex: 1; }
        .stat-value { 
            font-size: 24px; 
            font-weight: 600; 
            margin-bottom: 2px;
            font-variant-numeric: tabular-nums;
        }
        .stat-label { color: var(--muted); font-size: 12px; }
        
        /* Tables */
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .card-title { 
            font-size: 14px; 
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        table { 
            width: 100%; 
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td { 
            padding: 10px 12px; 
            text-align: left; 
            border-bottom: 1px solid var(--border); 
        }
        th { 
            color: var(--muted); 
            font-size: 11px; 
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
            background: rgba(0,0,0,0.2);
        }
        tr:hover { background: rgba(255,255,255,0.02); }
        .badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-success { background: rgba(115, 191, 105, 0.15); color: var(--green); }
        .badge-danger { background: rgba(242, 73, 92, 0.15); color: var(--red); }
        .badge-warning { background: rgba(242, 204, 12, 0.15); color: var(--yellow); }
        
        /* Alerts Section */
        .alert-rule {
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .alert-rule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .alert-rule-title {
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .alert-toggle {
            width: 36px;
            height: 20px;
            background: var(--green);
            border-radius: 10px;
            position: relative;
            cursor: pointer;
            transition: background 0.2s;
        }
        .alert-toggle::after {
            content: '';
            position: absolute;
            top: 2px;
            right: 2px;
            width: 16px;
            height: 16px;
            background: white;
            border-radius: 50%;
            transition: transform 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        .alert-toggle.disabled {
            background: #444;
        }
        .alert-toggle.disabled::after { right: auto; left: 2px; }
        .alert-conditions {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 12px;
        }
        .condition-box {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .condition-label { 
            color: var(--muted); 
            margin-bottom: 4px;
            font-size: 11px;
            text-transform: uppercase;
        }
        .condition-value { 
            font-weight: 600; 
            color: var(--text);
            font-size: 13px;
        }
        .alert-notifications {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .notification-tag {
            padding: 4px 10px;
            background: rgba(87, 148, 242, 0.15);
            border-radius: 3px;
            font-size: 11px;
            color: var(--blue);
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(4px);
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 24px;
            width: 90%;
            max-width: 500px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-close {
            background: none; 
            border: none; 
            color: var(--muted);
            font-size: 20px; 
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
        }
        .modal-close:hover { 
            color: var(--text);
            background: rgba(255,255,255,0.05);
        }
        .form-group { margin-bottom: 16px; }
        label {
            display: block;
            margin-bottom: 6px;
            color: var(--muted);
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px 12px;
            background: #111217;
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 13px;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--blue);
        }
        .form-row { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 12px; 
        }
        .form-row-3 { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 12px; 
        }
        
        /* Buttons */
        .btn {
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            transition: all 0.15s;
        }
        .btn-primary {
            background: linear-gradient(180deg, #2c7bd9 0%, #1a5fb4 100%);
            color: white;
            border: 1px solid #1a5fb4;
        }
        .btn-primary:hover { 
            background: linear-gradient(180deg, #3d8bea 0%, #2c7bd9 100%);
        }
        .btn-danger { 
            background: rgba(242, 73, 92, 0.15); 
            color: var(--red);
            border: 1px solid rgba(242, 73, 92, 0.3);
        }
        .btn-danger:hover { 
            background: rgba(242, 73, 92, 0.25); 
        }
        .btn-secondary { 
            background: rgba(255,255,255,0.05); 
            color: var(--text);
            border: 1px solid var(--border);
        }
        .btn-secondary:hover { 
            background: rgba(255,255,255,0.1); 
        }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        /* Install Box */
        .install-box {
            background: rgba(87, 148, 242, 0.05);
            border: 1px solid rgba(87, 148, 242, 0.2);
            border-radius: 4px;
            padding: 16px;
            margin-top: 12px;
        }
        .install-box h4 { 
            margin-bottom: 10px; 
            color: var(--blue); 
            font-size: 13px;
            font-weight: 600;
        }
        .code-block {
            position: relative;
            background: #111217;
            border: 1px solid var(--border);
            border-radius: 4px;
            margin: 10px 0;
        }
        .code-block code {
            display: block;
            padding: 12px 40px 12px 12px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            color: var(--text);
            background: transparent;
            border: none;
        }
        .copy-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 4px 8px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 3px;
            color: var(--muted);
            font-size: 11px;
            cursor: pointer;
            opacity: 0;
            transition: all 0.2s;
        }
        .code-block:hover .copy-btn {
            opacity: 1;
        }
        .copy-btn:hover {
            background: rgba(255,255,255,0.2);
            color: var(--text);
        }
        .copy-btn.copied {
            background: var(--green);
            color: white;
            opacity: 1;
        }
        .install-steps {
            margin-top: 16px;
        }
        .install-step {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            padding: 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
            border-left: 3px solid var(--blue);
        }
        .step-number {
            width: 24px;
            height: 24px;
            background: var(--blue);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
        }
        .step-content {
            flex: 1;
        }
        .step-title {
            font-weight: 600;
            margin-bottom: 4px;
            font-size: 13px;
        }
        .step-desc {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 8px;
        }
        .os-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
        }
        .os-tab {
            padding: 8px 16px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 4px;
            cursor: pointer;
            color: var(--muted);
            font-size: 13px;
        }
        .os-tab.active {
            background: var(--blue);
            color: white;
            border-color: var(--blue);
        }
        
        /* Section display */
        .section-content { display: none; }
        .section-content.active { display: block; }
        
        /* Chart Customization */
        canvas {
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        }
        }
        .time-btn {
            padding: 8px 16px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--muted);
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .time-btn:hover, .time-btn.active {
            background: var(--blue);
            border-color: var(--blue);
            color: white;
        }
        .refresh-btn {
            padding: 8px 16px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            color: var(--green);
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .refresh-btn:hover { background: rgba(16, 185, 129, 0.2); }
        
        /* Panel Grid */
        .panels-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
        }
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-title .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--green);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .panel-actions {
            display: flex;
            gap: 8px;
        }
        .panel-btn {
            padding: 6px 10px;
            background: transparent;
            border: none;
            color: var(--muted);
            cursor: pointer;
            border-radius: 4px;
            font-size: 13px;
        }
        .panel-btn:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .panel-body {
            display: flex;
            height: 320px;
        }
        .panel-chart {
            flex: 1;
            padding: 16px;
            position: relative;
        }
        .panel-legend {
            width: 180px;
            border-left: 1px solid var(--border);
            background: rgba(0,0,0,0.1);
            overflow-y: auto;
        }
        .legend-header {
            display: flex;
            justify-content: space-between;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 11px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            padding: 10px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .legend-item:hover { background: rgba(255,255,255,0.03); }
        .legend-item.hidden { opacity: 0.4; }
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 2px;
            margin-right: 10px;
            flex-shrink: 0;
        }
        .legend-info {
            flex: 1;
            min-width: 0;
        }
        .legend-name {
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .legend-value {
            color: var(--muted);
            font-size: 11px;
            margin-top: 2px;
        }
        
        /* Buttons */
        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--blue), #06b6d4);
            color: white;
        }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
        .btn-danger { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .btn-danger:hover { background: rgba(239, 68, 68, 0.3); }
        .btn-secondary { background: rgba(75, 85, 99, 0.3); color: var(--text); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        /* Stats Cards */
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 24px; }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .stat-icon {
            width: 48px; height: 48px;
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
        }
        .stat-content { flex: 1; }
        .stat-value { font-size: 28px; font-weight: 700; margin-bottom: 2px; }
        .stat-label { color: var(--muted); font-size: 13px; }
        
        /* Tables */
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .card-title { font-size: 18px; font-weight: 700; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
        th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
        tr:hover { background: rgba(255,255,255,0.02); }
        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: var(--green); }
        .badge-danger { background: rgba(239, 68, 68, 0.15); color: var(--red); }
        .badge-warning { background: rgba(245, 158, 11, 0.15); color: var(--yellow); }
        
        /* Alerts Section */
        .alert-rule {
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 16px;
        }
        .alert-rule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .alert-rule-title {
            font-weight: 600;
            font-size: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .alert-enabled {
            width: 40px;
            height: 22px;
            background: var(--green);
            border-radius: 11px;
            position: relative;
            cursor: pointer;
        }
        .alert-enabled::after {
            content: '';
            position: absolute;
            top: 2px; right: 2px;
            width: 18px; height: 18px;
            background: white;
            border-radius: 50%;
        }
        .alert-enabled.disabled {
            background: rgba(75, 85, 99, 0.5);
        }
        .alert-enabled.disabled::after { right: auto; left: 2px; }
        .alert-conditions {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }
        .condition-box {
            background: rgba(0,0,0,0.3);
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
        }
        .condition-label { color: var(--muted); margin-bottom: 4px; }
        .condition-value { font-weight: 600; color: var(--text); }
        .alert-notifications {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .notification-tag {
            padding: 6px 12px;
            background: rgba(59, 130, 246, 0.15);
            border-radius: 6px;
            font-size: 12px;
            color: var(--blue);
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        .modal-close {
            background: none; border: none; color: var(--muted);
            font-size: 24px; cursor: pointer;
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: var(--muted);
            font-weight: 500;
            font-size: 14px;
        }
        input, select, textarea {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--blue);
        }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-row-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        
        /* Install Box */
        .install-box {
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 10px;
            padding: 20px;
            margin-top: 16px;
        }
        .install-box h4 { margin-bottom: 12px; color: var(--blue); font-size: 14px; }
        .install-box code {
            background: rgba(0,0,0,0.4);
            padding: 12px;
            border-radius: 6px;
            display: block;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .os-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }
        .os-tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            color: var(--muted);
            font-size: 14px;
        }
        .os-tab.active {
            background: var(--blue);
            color: white;
            border-color: var(--blue);
        }
        
        /* Section display */
        .section-content { display: none; }
        .section-content.active { display: block; }
    </style>
</head>
<body>
    <!-- Top Navigation Bar - Grafana Style -->
    <nav class="top-nav">
        <div class="nav-left">
            <div class="logo">
                <div class="logo-icon">P</div>
                <h1>PyMon</h1>
            </div>
            <div class="nav-menu">
                <button class="nav-item active" data-section="dashboard">
                    <i class="fas fa-chart-line"></i> Dashboard
                </button>
                <button class="nav-item" data-section="servers">
                    <i class="fas fa-server"></i> Servers
                </button>
                <button class="nav-item" data-section="alerts">
                    <i class="fas fa-bell"></i> Alerts
                </button>
                <button class="nav-item" data-section="notifications">
                    <i class="fas fa-cog"></i> Settings
                </button>
            </div>
        </div>
        <div class="nav-right">
            <select class="server-selector" id="serverSelector" onchange="changeServer()">
                <option value="">All Servers</option>
            </select>
            <button class="btn btn-secondary btn-sm" onclick="logout()">
                <i class="fas fa-sign-out-alt"></i>
            </button>
        </div>
    </nav>
    
    <main class="main">
        <!-- Dashboard Section -->
        <div id="section-dashboard" class="section-content active">
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(115, 191, 105, 0.15); color: var(--green);">
                        <i class="fas fa-server"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-online" style="color: var(--green);">0</div>
                        <div class="stat-label">Online</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(242, 73, 92, 0.15); color: var(--red);">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-offline" style="color: var(--red);">0</div>
                        <div class="stat-label">Offline</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(87, 148, 242, 0.15); color: var(--blue);">
                        <i class="fab fa-linux"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-linux" style="color: var(--blue);">0</div>
                        <div class="stat-label">Linux</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(242, 204, 12, 0.15); color: var(--yellow);">
                        <i class="fab fa-windows"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-windows" style="color: var(--yellow);">0</div>
                        <div class="stat-label">Windows</div>
                    </div>
                </div>
            </div>
            
            <!-- Dashboard Toolbar - Grafana Style -->
            <div class="dashboard-toolbar">
                <div class="toolbar-left">
                    <span class="breadcrumb">
                        <i class="fas fa-home"></i> Home <span style="margin: 0 8px; color: var(--border);">/</span> <span>Dashboard</span>
                    </span>
                </div>
                <div class="toolbar-right">
                    <div class="time-range">
                        <button class="time-btn" data-range="5m">5m</button>
                        <button class="time-btn" data-range="15m">15m</button>
                        <button class="time-btn" data-range="30m">30m</button>
                        <button class="time-btn active" data-range="1h">1h</button>
                        <button class="time-btn" data-range="6h">6h</button>
                        <button class="time-btn" data-range="24h">24h</button>
                    </div>
                    <div class="refresh-controls">
                        <button class="refresh-btn" onclick="refreshDashboard()">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                        <span class="refresh-interval">5s</span>
                    </div>
                </div>
            </div>
            
            <!-- Charts Grid - Grafana Style -->
            <div class="panels-grid">
                <!-- CPU Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            CPU
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="cpuChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                                <span>Max</span>
                            </div>
                            <div id="cpuLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Memory Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            Memory
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="memoryChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                                <span>Max</span>
                            </div>
                            <div id="memoryLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Disk Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            Disk Usage
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="diskChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                                <span>Max</span>
                            </div>
                            <div id="diskLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Network Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            Network I/O
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="networkChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                                <span>Max</span>
                            </div>
                            <div id="networkLegend"></div>
                        </div>
                    </div>
                </div>

                <!-- Disk Queue Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            Disk Queue
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="diskQueueChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                                <span>Max</span>
                            </div>
                            <div id="diskQueueLegend"></div>
                        </div>
                    </div>
                </div>

                <!-- Exporter Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <span class="status-dot"></span>
                            Exporter
                        </div>
                        <div class="panel-actions">
                            <button class="panel-btn"><i class="fas fa-ellipsis-v"></i></button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="panel-chart">
                            <canvas id="exporterChart"></canvas>
                        </div>
                        <div class="panel-legend">
                            <div class="legend-header">
                                <span style="grid-column: 2;">Name</span>
                                <span>Last</span>
                            </div>
                            <div id="exporterLegend"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Servers Section -->
        <div id="section-servers" class="section-content">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title"><i class="fas fa-server"></i> Monitored Servers</h3>
                    <button class="btn btn-primary" onclick="openModal('addServerModal')">
                        <i class="fas fa-plus"></i> Add Server
                    </button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Name</th>
                            <th>Host</th>
                            <th>OS</th>
                            <th>CPU</th>
                            <th>Memory</th>
                            <th>Disk</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="servers-tbody"></tbody>
                </table>
            </div>
            
            <div class="card">
                <h3 class="card-title" style="margin-bottom: 16px;"><i class="fas fa-download"></i> Agent Installation</h3>
                <p style="color: var(--muted); margin-bottom: 16px;">Install the PyMon agent on your servers to start collecting metrics.</p>
                
                <div class="os-tabs">
                    <div class="os-tab active" onclick="showOsTab('linux')">Linux</div>
                    <div class="os-tab" onclick="showOsTab('windows')">Windows</div>
                </div>
                
                <div id="install-linux" class="install-box">
                    <h4><i class="fab fa-linux"></i> Linux Agent Installation</h4>
                    <p style="color: var(--muted); margin-bottom: 12px;">Supports: Ubuntu, Debian, CentOS, RHEL, Fedora, AlmaLinux, Rocky Linux</p>
                    
                    <div class="install-steps">
                        <div class="install-step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <div class="step-title">Download and run installer</div>
                                <div class="step-desc">Run this command on your Linux server:</div>
                                <div class="code-block">
                                    <code id="linux-install-cmd">curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</code>
                                    <button class="copy-btn" onclick="copyToClipboard('linux-install-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <div class="step-title">Configure agent</div>
                                <div class="step-desc">Edit configuration file:</div>
                                <div class="code-block">
                                    <code id="linux-config-cmd">sudo nano /etc/systemd/system/pymon-agent.service</code>
                                    <button class="copy-btn" onclick="copyToClipboard('linux-config-cmd', this)">Copy</button>
                                </div>
                                <div class="step-desc" style="margin-top: 8px;">Set your PyMon server URL:</div>
                                <div class="code-block">
                                    <code id="linux-env-cmd">Environment="PYMON_SERVER=http://YOUR_SERVER_IP:8090"</code>
                                    <button class="copy-btn" onclick="copyToClipboard('linux-env-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <div class="step-title">Start the service</div>
                                <div class="step-desc">Start and enable the agent:</div>
                                <div class="code-block">
                                    <code id="linux-start-cmd">sudo systemctl start pymon-agent && sudo systemctl enable pymon-agent</code>
                                    <button class="copy-btn" onclick="copyToClipboard('linux-start-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">4</div>
                            <div class="step-content">
                                <div class="step-title">Check status</div>
                                <div class="step-desc">Verify agent is running:</div>
                                <div class="code-block">
                                    <code id="linux-status-cmd">sudo systemctl status pymon-agent</code>
                                    <button class="copy-btn" onclick="copyToClipboard('linux-status-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 16px; padding: 12px; background: rgba(242, 204, 12, 0.1); border-radius: 4px; border-left: 3px solid var(--yellow);">
                        <p style="color: var(--yellow); font-size: 12px; margin: 0;">
                            <i class="fas fa-lightbulb"></i> <strong>Tip:</strong> The agent collects CPU, Memory, Disk, Network metrics and supports RAID monitoring via mdadm, MegaRAID, HP Smart Array.
                        </p>
                    </div>
                </div>
                
                <div id="install-windows" class="install-box" style="display:none;">
                    <h4><i class="fab fa-windows"></i> Windows Agent Installation</h4>
                    <p style="color: var(--muted); margin-bottom: 12px;">Requires: Windows Server 2016+ or Windows 10/11, PowerShell 5.1+</p>
                    
                    <div class="install-steps">
                        <div class="install-step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <div class="step-title">Open PowerShell as Administrator</div>
                                <div class="step-desc">Right-click PowerShell and select "Run as Administrator"</div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <div class="step-title">Download and install</div>
                                <div class="step-desc">Run installation command:</div>
                                <div class="code-block">
                                    <code id="windows-install-cmd">Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-windows.ps1" -OutFile "install.ps1"; Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\install.ps1</code>
                                    <button class="copy-btn" onclick="copyToClipboard('windows-install-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <div class="step-title">Configure agent</div>
                                <div class="step-desc">Edit config file at:</div>
                                <div class="code-block">
                                    <code id="windows-config-path">C:\Program Files\PyMonAgent\config.env</code>
                                    <button class="copy-btn" onclick="copyToClipboard('windows-config-path', this)">Copy</button>
                                </div>
                                <div class="step-desc" style="margin-top: 8px;">Set your PyMon server URL:</div>
                                <div class="code-block">
                                    <code id="windows-env-cmd">SERVER_URL=http://YOUR_SERVER_IP:8090</code>
                                    <button class="copy-btn" onclick="copyToClipboard('windows-env-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">4</div>
                            <div class="step-content">
                                <div class="step-title">Start the service</div>
                                <div class="step-desc">Start Windows service:</div>
                                <div class="code-block">
                                    <code id="windows-start-cmd">Start-Service PyMonAgent</code>
                                    <button class="copy-btn" onclick="copyToClipboard('windows-start-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="install-step">
                            <div class="step-number">5</div>
                            <div class="step-content">
                                <div class="step-title">Check status</div>
                                <div class="step-desc">Verify service is running:</div>
                                <div class="code-block">
                                    <code id="windows-status-cmd">Get-Service PyMonAgent</code>
                                    <button class="copy-btn" onclick="copyToClipboard('windows-status-cmd', this)">Copy</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 16px; padding: 12px; background: rgba(242, 204, 12, 0.1); border-radius: 4px; border-left: 3px solid var(--yellow);">
                        <p style="color: var(--yellow); font-size: 12px; margin: 0;">
                            <i class="fas fa-lightbulb"></i> <strong>Tip:</strong> If service creation fails, you can run agent in console mode: <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">& 'C:\Program Files\PyMonAgent\pymon-agent.bat'</code>
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Alerts Section -->
        <div id="section-alerts" class="section-content">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title"><i class="fas fa-bell"></i> Alert Rules</h3>
                    <button class="btn btn-primary" onclick="openModal('addAlertModal')">
                        <i class="fas fa-plus"></i> New Alert Rule
                    </button>
                </div>
                <p style="color: var(--muted); margin-bottom: 20px;">Configure alert rules to receive notifications when metrics exceed thresholds.</p>
                
                <div id="alertRules">
                    <!-- CPU Alert Rule -->
                    <div class="alert-rule">
                        <div class="alert-rule-header">
                            <div class="alert-rule-title">
                                <i class="fas fa-microchip" style="color: var(--blue);"></i>
                                High CPU Usage
                            </div>
                            <div class="alert-enabled" onclick="this.classList.toggle('disabled')"></div>
                        </div>
                        <div class="alert-conditions">
                            <div class="condition-box">
                                <div class="condition-label">Metric</div>
                                <div class="condition-value">CPU Usage %</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Condition</div>
                                <div class="condition-value">> 80%</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Duration</div>
                                <div class="condition-value">5 minutes</div>
                            </div>
                        </div>
                        <div class="alert-notifications">
                            <span class="notification-tag"><i class="fab fa-telegram"></i> Telegram</span>
                            <span class="notification-tag"><i class="fas fa-envelope"></i> Email</span>
                        </div>
                    </div>
                    
                    <!-- Memory Alert Rule -->
                    <div class="alert-rule">
                        <div class="alert-rule-header">
                            <div class="alert-rule-title">
                                <i class="fas fa-memory" style="color: var(--green);"></i>
                                High Memory Usage
                            </div>
                            <div class="alert-enabled" onclick="this.classList.toggle('disabled')"></div>
                        </div>
                        <div class="alert-conditions">
                            <div class="condition-box">
                                <div class="condition-label">Metric</div>
                                <div class="condition-value">Memory Usage %</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Condition</div>
                                <div class="condition-value">> 85%</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Duration</div>
                                <div class="condition-value">3 minutes</div>
                            </div>
                        </div>
                        <div class="alert-notifications">
                            <span class="notification-tag"><i class="fab fa-discord"></i> Discord</span>
                        </div>
                    </div>
                    
                    <!-- Disk Alert Rule -->
                    <div class="alert-rule">
                        <div class="alert-rule-header">
                            <div class="alert-rule-title">
                                <i class="fas fa-hdd" style="color: var(--yellow);"></i>
                                Disk Space Low
                            </div>
                            <div class="alert-enabled disabled" onclick="this.classList.toggle('disabled')"></div>
                        </div>
                        <div class="alert-conditions">
                            <div class="condition-box">
                                <div class="condition-label">Metric</div>
                                <div class="condition-value">Disk Usage %</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Condition</div>
                                <div class="condition-value">> 90%</div>
                            </div>
                            <div class="condition-box">
                                <div class="condition-label">Duration</div>
                                <div class="condition-value">Immediate</div>
                            </div>
                        </div>
                        <div class="alert-notifications">
                            <span class="notification-tag"><i class="fab fa-telegram"></i> Telegram</span>
                            <span class="notification-tag"><i class="fab fa-slack"></i> Slack</span>
                            <span class="notification-tag"><i class="fas fa-envelope"></i> Email</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Settings Section -->
        <div id="section-notifications" class="section-content">
            <div class="card">
                <h3 class="card-title" style="margin-bottom: 20px;"><i class="fas fa-broadcast-tower"></i> Notification Channels</h3>
                <p style="color: var(--muted); margin-bottom: 24px;">Configure where to receive alerts when servers go down.</p>
                
                <div style="margin-bottom: 32px;">
                    <div class="form-group">
                        <label class="toggle-label" style="display: flex; align-items: center; gap: 12px; cursor: pointer;">
                            <input type="checkbox" id="notify-telegram" style="width: auto;" onchange="toggleConfig('telegram')">
                            <span><i class="fab fa-telegram" style="color: #0088cc;"></i> Telegram</span>
                        </label>
                    </div>
                    <div id="config-telegram" style="display:none; padding-left: 28px;">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Bot Token</label>
                                <input type="text" id="telegram-token" placeholder="123456789:ABCdef...">
                            </div>
                            <div class="form-group">
                                <label>Chat ID</label>
                                <input type="text" id="telegram-chat" placeholder="-1001234567890">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 32px;">
                    <div class="form-group">
                        <label class="toggle-label" style="display: flex; align-items: center; gap: 12px; cursor: pointer;">
                            <input type="checkbox" id="notify-discord" style="width: auto;" onchange="toggleConfig('discord')">
                            <span><i class="fab fa-discord" style="color: #7289da;"></i> Discord</span>
                        </label>
                    </div>
                    <div id="config-discord" style="display:none; padding-left: 28px;">
                        <div class="form-group">
                            <label>Webhook URL</label>
                            <input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/...">
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 32px;">
                    <div class="form-group">
                        <label class="toggle-label" style="display: flex; align-items: center; gap: 12px; cursor: pointer;">
                            <input type="checkbox" id="notify-slack" style="width: auto;" onchange="toggleConfig('slack')">
                            <span><i class="fab fa-slack" style="color: #4a154b;"></i> Slack</span>
                        </label>
                    </div>
                    <div id="config-slack" style="display:none; padding-left: 28px;">
                        <div class="form-group">
                            <label>Webhook URL</label>
                            <input type="text" id="slack-webhook" placeholder="https://hooks.slack.com/services/...">
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 32px;">
                    <div class="form-group">
                        <label class="toggle-label" style="display: flex; align-items: center; gap: 12px; cursor: pointer;">
                            <input type="checkbox" id="notify-email" style="width: auto;" onchange="toggleConfig('email')">
                            <span><i class="fas fa-envelope" style="color: var(--red);"></i> Email (SMTP)</span>
                        </label>
                    </div>
                    <div id="config-email" style="display:none; padding-left: 28px;">
                        <div class="form-row">
                            <div class="form-group">
                                <label>SMTP Host</label>
                                <input type="text" id="email-host" placeholder="smtp.gmail.com">
                            </div>
                            <div class="form-group">
                                <label>Port</label>
                                <input type="number" id="email-port" value="587">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Username</label>
                                <input type="text" id="email-user" placeholder="your@email.com">
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <input type="password" id="email-pass" placeholder="App password">
                            </div>
                        </div>
                    </div>
                </div>
                
                <button class="btn btn-primary" onclick="saveNotifications()">
                    <i class="fas fa-save"></i> Save Configuration
                </button>
            </div>
        </div>
    </main>
    
    <!-- Add Server Modal -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Add Server to Monitor</h3>
                <button class="modal-close" onclick="closeModal('addServerModal')">&times;</button>
            </div>
            <form onsubmit="addServer(event)">
                <div class="form-group">
                    <label>Server Name</label>
                    <input type="text" id="server-name" placeholder="Production DB Server" required>
                </div>
                <div class="form-group">
                    <label>Hostname or IP Address</label>
                    <input type="text" id="server-host" placeholder="192.168.1.100 or server.company.com" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Operating System</label>
                        <select id="server-os">
                            <option value="linux">Linux</option>
                            <option value="windows">Windows</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Check Interval (seconds)</label>
                        <input type="number" id="server-interval" value="15">
                    </div>
                </div>
                <div class="form-group">
                    <label>Notification Channels</label>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="server-notify-telegram">
                            <span>Telegram</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="server-notify-discord">
                            <span>Discord</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="server-notify-slack">
                            <span>Slack</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="server-notify-email">
                            <span>Email</span>
                        </label>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">
                    <i class="fas fa-plus"></i> Add Server
                </button>
            </form>
        </div>
    </div>
    
    <!-- Edit Server Modal -->
    <div class="modal" id="editServerModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Edit Server</h3>
                <button class="modal-close" onclick="closeModal('editServerModal')">&times;</button>
            </div>
            <form onsubmit="updateServer(event)">
                <input type="hidden" id="edit-server-id">
                <div class="form-group">
                    <label>Server Name</label>
                    <input type="text" id="edit-server-name" required>
                </div>
                <div class="form-group">
                    <label>Hostname or IP Address</label>
                    <input type="text" id="edit-server-host" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Operating System</label>
                        <select id="edit-server-os">
                            <option value="linux">Linux</option>
                            <option value="windows">Windows</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Check Interval (seconds)</label>
                        <input type="number" id="edit-server-interval" value="15">
                    </div>
                </div>
                <div class="form-group">
                    <label>Notification Channels</label>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="edit-server-notify-telegram">
                            <span>Telegram</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="edit-server-notify-discord">
                            <span>Discord</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="edit-server-notify-slack">
                            <span>Slack</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="edit-server-notify-email">
                            <span>Email</span>
                        </label>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">
                    <i class="fas fa-save"></i> Save Changes
                </button>
            </form>
        </div>
    </div>
    
    <!-- Add Alert Modal -->
    <div class="modal" id="addAlertModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Create Alert Rule</h3>
                <button class="modal-close" onclick="closeModal('addAlertModal')">&times;</button>
            </div>
            <form onsubmit="addAlertRule(event)">
                <div class="form-group">
                    <label>Rule Name</label>
                    <input type="text" id="alert-name" placeholder="e.g., High CPU Alert" required>
                </div>
                <div class="form-row-3">
                    <div class="form-group">
                        <label>Metric</label>
                        <select id="alert-metric">
                            <option value="cpu">CPU Usage %</option>
                            <option value="memory">Memory Usage %</option>
                            <option value="disk">Disk Usage %</option>
                            <option value="network">Network I/O</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Condition</label>
                        <select id="alert-condition">
                            <option value=">">Greater than (&gt;)</option>
                            <option value="<">Less than (&lt;)</option>
                            <option value="=">Equal to (=)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Threshold</label>
                        <input type="number" id="alert-threshold" placeholder="80" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Duration</label>
                    <select id="alert-duration">
                        <option value="0">Immediate</option>
                        <option value="1">1 minute</option>
                        <option value="5" selected>5 minutes</option>
                        <option value="15">15 minutes</option>
                        <option value="30">30 minutes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Notification Channels</label>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="alert-notify-telegram" checked>
                            <span>Telegram</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="alert-notify-discord">
                            <span>Discord</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="alert-notify-slack">
                            <span>Slack</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="alert-notify-email">
                            <span>Email</span>
                        </label>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">
                    <i class="fas fa-save"></i> Create Alert Rule
                </button>
            </form>
        </div>
    </div>
    
    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';
        
        let servers = [];
        let charts = {};
        
        // Chart colors
        const chartColors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
            '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'
        ];
        
        function showSection(section) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.section-content').forEach(el => {
                el.classList.remove('active');
                el.style.display = 'none';
            });
            
            // Find and activate the clicked button
            const clickedBtn = document.querySelector(`.nav-item[data-section="${section}"]`);
            if (clickedBtn) clickedBtn.classList.add('active');
            
            const sectionEl = document.getElementById('section-' + section);
            if (sectionEl) {
                sectionEl.style.display = 'block';
                setTimeout(() => sectionEl.classList.add('active'), 10);
            }
            
            if (section === 'servers') loadServers();
            if (section === 'dashboard') initCharts();
        }
        
        // Setup navigation event listeners
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', function() {
                const section = this.getAttribute('data-section');
                if (section) showSection(section);
            });
        });
        
        function showOsTab(os) {
            document.querySelectorAll('.os-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('install-linux').style.display = os === 'linux' ? 'block' : 'none';
            document.getElementById('install-windows').style.display = os === 'windows' ? 'block' : 'none';
        }
        
        function toggleConfig(channel) {
            const checkbox = document.getElementById('notify-' + channel);
            document.getElementById('config-' + channel).style.display = checkbox.checked ? 'block' : 'none';
        }
        
        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }
        
        function changeServer() {
            const serverId = document.getElementById('serverSelector').value;
            console.log('Selected server:', serverId);
            // Reload charts for selected server
            initCharts();
        }
        
        function refreshDashboard() {
            const btn = document.querySelector('.refresh-btn i');
            btn.classList.add('fa-spin');
            setTimeout(() => {
                btn.classList.remove('fa-spin');
                initCharts();
            }, 1000);
        }
        
        async function loadServers() {
            try {
                const resp = await fetch('/api/servers', { headers: { 'Authorization': `Bearer ${token}` }});
                const data = await resp.json();
                servers = data.servers || [];
                
                let online = 0, offline = 0, linux = 0, windows = 0;
                
                // Update server selector
                const selector = document.getElementById('serverSelector');
                selector.innerHTML = '<option value="">All Servers</option>' + 
                    servers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
                
                document.getElementById('servers-tbody').innerHTML = servers.map(s => {
                    if (s.last_status === 'up') online++;
                    else if (s.last_status === 'down') offline++;
                    if (s.os_type === 'linux') linux++;
                    else if (s.os_type === 'windows') windows++;
                    return `<tr>
                        <td><span class="badge badge-${s.last_status === 'up' ? 'success' : s.last_status === 'down' ? 'danger' : 'warning'}">${s.last_status || 'pending'}</span></td>
                        <td><strong>${s.name}</strong></td>
                        <td>${s.host}</td>
                        <td><i class="fab fa-${s.os_type === 'linux' ? 'linux' : 'windows'}"></i> ${s.os_type}</td>
                        <td>${s.cpu_percent ? s.cpu_percent.toFixed(1) + '%' : '-'}</td>
                        <td>${s.memory_percent ? s.memory_percent.toFixed(1) + '%' : '-'}</td>
                        <td>${s.disk_percent ? s.disk_percent.toFixed(1) + '%' : '-'}</td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="editServer(${s.id})" style="margin-right: 8px;">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>`;
                }).join('') || '<tr><td colspan="8" style="text-align:center;padding:40px;color:var(--muted)"><i class="fas fa-server" style="font-size:48px;display:block;margin-bottom:16px;"></i>No servers configured</td></tr>';
                
                document.getElementById('stat-online').textContent = online;
                document.getElementById('stat-offline').textContent = offline;
                document.getElementById('stat-linux').textContent = linux;
                document.getElementById('stat-windows').textContent = windows;
            } catch (e) { console.error(e); }
        }
        
        // Grafana-style colors
        const grafanaColors = [
            '#73bf69', '#f2cc0c', '#5794f2', '#b877d9', 
            '#ff780a', '#00d8d8', '#f2495c', '#9673b5'
        ];
        
        function initCharts() {
            // Destroy existing charts
            Object.values(charts).forEach(c => c && c.destroy());
            charts = {};
            
            // Generate time labels based on selected range
            const timeLabels = generateTimeLabels(currentTimeRange);
            const dataPoints = timeLabels.length;
            
            // CPU Chart
            const cpuData = servers.length > 0 ? servers.map((s, i) => ({
                label: s.name,
                data: Array(dataPoints).fill(0).map(() => 30 + Math.random() * 60),
                borderColor: grafanaColors[i % grafanaColors.length],
                backgroundColor: grafanaColors[i % grafanaColors.length] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4
            })) : [{
                label: 'APPSRV1',
                data: generateRandomData(dataPoints, 30, 90),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4
            }, {
                label: 'HIAS-01',
                data: generateRandomData(dataPoints, 20, 80),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4
            }, {
                label: 'APPSRV2',
                data: generateRandomData(dataPoints, 40, 95),
                borderColor: grafanaColors[2],
                backgroundColor: grafanaColors[2] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4
            }];
            
            charts.cpu = new Chart(document.getElementById('cpuChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: cpuData },
                options: getChartOptions('%', 0, 100)
            });
            updateLegend('cpuLegend', cpuData, '%');
            
            // Memory Chart
            const memoryData = servers.length > 0 ? servers.map((s, i) => ({
                label: s.name,
                data: Array(dataPoints).fill(0).map(() => 40 + Math.random() * 40),
                borderColor: grafanaColors[i % grafanaColors.length],
                backgroundColor: grafanaColors[i % grafanaColors.length] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4
            })) : [{
                label: 'HIAS-01',
                data: generateRandomData(dataPoints, 60, 90),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV6',
                data: generateRandomData(dataPoints, 55, 85),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV2',
                data: generateRandomData(dataPoints, 50, 75),
                borderColor: grafanaColors[2],
                backgroundColor: grafanaColors[2] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }];
            
            charts.memory = new Chart(document.getElementById('memoryChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: memoryData },
                options: getChartOptions('%', 0, 100)
            });
            updateLegend('memoryLegend', memoryData, '%');
            
            // Disk Chart
            const diskData = servers.length > 0 ? servers.map((s, i) => ({
                label: s.name,
                data: Array(dataPoints).fill(0).map(() => 50 + Math.random() * 40),
                borderColor: grafanaColors[i % grafanaColors.length],
                backgroundColor: grafanaColors[i % grafanaColors.length] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            })) : [{
                label: 'APPSRV11 [C:]',
                data: generateRandomData(dataPoints, 75, 90),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV10 [D:]',
                data: generateRandomData(dataPoints, 70, 88),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'HIAS-01 [T:]',
                data: generateRandomData(dataPoints, 80, 92),
                borderColor: grafanaColors[2],
                backgroundColor: grafanaColors[2] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }];
            
            charts.disk = new Chart(document.getElementById('diskChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: diskData },
                options: getChartOptions('%', 0, 100)
            });
            updateLegend('diskLegend', diskData, '%');
            
            // Network Chart
            const networkData = servers.length > 0 ? servers.map((s, i) => ({
                label: s.name,
                data: Array(dataPoints).fill(0).map(() => Math.random() * 50),
                borderColor: grafanaColors[i % grafanaColors.length],
                backgroundColor: grafanaColors[i % grafanaColors.length] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            })) : [{
                label: 'APPSRV1',
                data: generateRandomData(dataPoints, 10, 45),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV2',
                data: generateRandomData(dataPoints, 15, 50),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '15',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }];
            
            charts.network = new Chart(document.getElementById('networkChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: networkData },
                options: getChartOptions(' MB/s', 0, 60)
            });
            updateLegend('networkLegend', networkData, ' MB/s');
            
            // Disk Queue Chart
            const diskQueueData = [{
                label: 'APPSRV10 [C:]',
                data: generateRandomData(dataPoints, 0, 0.15),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '20',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV7 [C:]',
                data: generateRandomData(dataPoints, 0, 0.25),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '20',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV [D:]',
                data: generateRandomData(dataPoints, 0, 0.05),
                borderColor: grafanaColors[2],
                backgroundColor: grafanaColors[2] + '20',
                fill: true,
                tension: 0.3,
                borderWidth: 1.5,
                pointRadius: 0
            }];
            
            charts.diskQueue = new Chart(document.getElementById('diskQueueChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: diskQueueData },
                options: getChartOptions('', 0, 1.5)
            });
            updateLegend('diskQueueLegend', diskQueueData, '');
            
            // Exporter Chart
            const exporterData = [{
                label: 'APPSRV',
                data: Array(dataPoints).fill(1),
                borderColor: grafanaColors[0],
                backgroundColor: grafanaColors[0] + '30',
                fill: true,
                tension: 0,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV10',
                data: Array(dataPoints).fill(1),
                borderColor: grafanaColors[1],
                backgroundColor: grafanaColors[1] + '30',
                fill: true,
                tension: 0,
                borderWidth: 1.5,
                pointRadius: 0
            }, {
                label: 'APPSRV11',
                data: Array(dataPoints).fill(1),
                borderColor: grafanaColors[2],
                backgroundColor: grafanaColors[2] + '30',
                fill: true,
                tension: 0,
                borderWidth: 1.5,
                pointRadius: 0
            }];
            
            charts.exporter = new Chart(document.getElementById('exporterChart'), {
                type: 'line',
                data: { labels: timeLabels, datasets: exporterData },
                options: getChartOptions('', 0, 2, false)
            });
            updateLegend('exporterLegend', exporterData, '', false);
        }
        
        function generateTimeLabels(range) {
            const labels = [];
            const now = new Date();
            let points = 12;
            let interval = 5; // minutes
            
            switch(range) {
                case '5m': points = 10; interval = 0.5; break;
                case '15m': points = 15; interval = 1; break;
                case '30m': points = 15; interval = 2; break;
                case '1h': points = 12; interval = 5; break;
                case '6h': points = 12; interval = 30; break;
                case '24h': points = 12; interval = 120; break;
            }
            
            for (let i = points - 1; i >= 0; i--) {
                const time = new Date(now.getTime() - i * interval * 60000);
                labels.push(time.getHours().toString().padStart(2, '0') + ':' + time.getMinutes().toString().padStart(2, '0'));
            }
            return labels;
        }
        
        function generateRandomData(points, min, max) {
            return Array(points).fill(0).map(() => min + Math.random() * (max - min));
        }
        
        function getChartOptions(suffix, min, max, showLegend = false) {
            return {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { 
                    intersect: false, 
                    mode: 'index' 
                },
                scales: {
                    y: { 
                        min: min, 
                        max: max,
                        grid: { 
                            color: 'rgba(255,255,255,0.03)',
                            drawBorder: false
                        }, 
                        ticks: { 
                            color: '#666',
                            font: { size: 10 },
                            callback: v => v + suffix
                        } 
                    },
                    x: { 
                        grid: { display: false }, 
                        ticks: { 
                            color: '#666',
                            font: { size: 10 }
                        } 
                    }
                },
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(24, 27, 31, 0.95)',
                        borderColor: '#2c3235',
                        borderWidth: 1,
                        titleColor: '#e0e0e0',
                        bodyColor: '#e0e0e0',
                        padding: 10,
                        displayColors: true,
                        boxPadding: 4
                    }
                }
            };
        }
                type: 'line',
                data: { labels: timeLabels, datasets: networkData },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: 'index' },
                    scales: {
                        y: { 
                            grid: { color: 'rgba(255,255,255,0.05)' }, 
                            ticks: { color: '#9ca3af', callback: v => v + ' MB/s' } 
                        },
                        x: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 10 } } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
            updateLegend('networkLegend', networkData, ' MB/s');
        }
        
        function updateLegend(elementId, datasets, suffix, showMinMax = true) {
            const container = document.getElementById(elementId);
            container.innerHTML = datasets.map((ds, i) => {
                const lastValue = ds.data[ds.data.length - 1];
                const maxValue = Math.max(...ds.data);
                const minValue = Math.min(...ds.data);
                
                if (showMinMax) {
                    return `
                        <div class="legend-item" onclick="toggleDataset('${elementId}', ${i}, '${suffix}')">
                            <div class="legend-color" style="background: ${ds.borderColor}"></div>
                            <div class="legend-name" title="${ds.label}">${ds.label}</div>
                            <div class="legend-value">${lastValue.toFixed(1)}${suffix}</div>
                            <div class="legend-value" style="color: var(--muted);">${maxValue.toFixed(1)}${suffix}</div>
                        </div>
                    `;
                } else {
                    return `
                        <div class="legend-item" onclick="toggleDataset('${elementId}', ${i}, '${suffix}')">
                            <div class="legend-color" style="background: ${ds.borderColor}"></div>
                            <div class="legend-name" title="${ds.label}">${ds.label}</div>
                            <div class="legend-value">${lastValue.toFixed(1)}${suffix}</div>
                        </div>
                    `;
                }
            }).join('');
        }
        
        function toggleDataset(elementId, index, suffix) {
            // Toggle dataset visibility in chart
            const chartMap = {
                'cpuLegend': charts.cpu,
                'memoryLegend': charts.memory,
                'diskLegend': charts.disk,
                'networkLegend': charts.network,
                'diskQueueLegend': charts.diskQueue,
                'exporterLegend': charts.exporter
            };
            
            const chart = chartMap[elementId.replace('Legend', '') + 'Chart'] || chartMap[elementId];
            if (chart && chart.data.datasets[index]) {
                const meta = chart.getDatasetMeta(index);
                meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                chart.update();
                
                // Update legend item style
                const legendItems = document.getElementById(elementId).querySelectorAll('.legend-item');
                if (legendItems[index]) {
                    legendItems[index].classList.toggle('hidden');
                }
            }
        }
        
        let currentTimeRange = '1h';
        
        function setTimeRange(range) {
            currentTimeRange = range;
            document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
            const clickedBtn = document.querySelector(`.time-btn[data-range="${range}"]`);
            if (clickedBtn) clickedBtn.classList.add('active');
            initCharts();
        }
        
        // Setup time range button listeners
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const range = this.getAttribute('data-range');
                if (range) setTimeRange(range);
            });
        });
        
        // Setup refresh button
        document.querySelector('.refresh-btn')?.addEventListener('click', function() {
            this.querySelector('i')?.classList.add('fa-spin');
            setTimeout(() => {
                this.querySelector('i')?.classList.remove('fa-spin');
                initCharts();
            }, 1000);
        });
        
        // Setup logout button
        document.querySelector('.btn-secondary')?.addEventListener('click', function() {
            logout();
        });
        
        async function addServer(e) {
            e.preventDefault();
            const data = {
                name: document.getElementById('server-name').value,
                host: document.getElementById('server-host').value,
                os_type: document.getElementById('server-os').value,
                check_interval: parseInt(document.getElementById('server-interval').value),
                notify_telegram: document.getElementById('server-notify-telegram').checked,
                notify_discord: document.getElementById('server-notify-discord').checked,
                notify_slack: document.getElementById('server-notify-slack').checked,
                notify_email: document.getElementById('server-notify-email').checked
            };
            await fetch('/api/servers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(data)
            });
            closeModal('addServerModal');
            loadServers();
        }
        
        async function deleteServer(id) {
            if (!confirm('Delete this server?')) return;
            await fetch('/api/servers/' + id, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }});
            loadServers();
        }
        
        async function editServer(id) {
            try {
                const resp = await fetch('/api/servers/' + id, { headers: { 'Authorization': `Bearer ${token}` }});
                const data = await resp.json();
                const server = data.server;
                
                document.getElementById('edit-server-id').value = server.id;
                document.getElementById('edit-server-name').value = server.name;
                document.getElementById('edit-server-host').value = server.host;
                document.getElementById('edit-server-os').value = server.os_type;
                document.getElementById('edit-server-interval').value = server.check_interval;
                document.getElementById('edit-server-notify-telegram').checked = server.notify_telegram;
                document.getElementById('edit-server-notify-discord').checked = server.notify_discord;
                document.getElementById('edit-server-notify-slack').checked = server.notify_slack;
                document.getElementById('edit-server-notify-email').checked = server.notify_email;
                
                openModal('editServerModal');
            } catch (e) {
                console.error('Error loading server:', e);
                alert('Failed to load server data');
            }
        }
        
        async function updateServer(e) {
            e.preventDefault();
            const id = document.getElementById('edit-server-id').value;
            const data = {
                name: document.getElementById('edit-server-name').value,
                host: document.getElementById('edit-server-host').value,
                os_type: document.getElementById('edit-server-os').value,
                check_interval: parseInt(document.getElementById('edit-server-interval').value),
                notify_telegram: document.getElementById('edit-server-notify-telegram').checked,
                notify_discord: document.getElementById('edit-server-notify-discord').checked,
                notify_slack: document.getElementById('edit-server-notify-slack').checked,
                notify_email: document.getElementById('edit-server-notify-email').checked
            };
            
            try {
                const resp = await fetch('/api/servers/' + id, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(data)
                });
                
                if (resp.ok) {
                    closeModal('editServerModal');
                    loadServers();
                } else {
                    alert('Failed to update server');
                }
            } catch (e) {
                console.error('Error updating server:', e);
                alert('Failed to update server');
            }
        }
        
        function addAlertRule(e) {
            e.preventDefault();
            alert('Alert rule created! (Demo functionality)');
            closeModal('addAlertModal');
        }
        
        async function saveNotifications() {
            const channels = ['telegram', 'discord', 'slack', 'email'];
            for (const channel of channels) {
                const enabled = document.getElementById('notify-' + channel).checked;
                const config = { enabled };
                if (channel === 'telegram') {
                    config.telegram_bot_token = document.getElementById('telegram-token').value;
                    config.telegram_chat_id = document.getElementById('telegram-chat').value;
                } else if (channel === 'discord') {
                    config.discord_webhook = document.getElementById('discord-webhook').value;
                } else if (channel === 'slack') {
                    config.slack_webhook = document.getElementById('slack-webhook').value;
                } else if (channel === 'email') {
                    config.email_smtp_host = document.getElementById('email-host').value;
                    config.email_smtp_port = parseInt(document.getElementById('email-port').value);
                    config.email_user = document.getElementById('email-user').value;
                    config.email_pass = document.getElementById('email-pass').value;
                }
                await fetch('/api/notifications/' + channel, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(config)
                });
            }
            alert('Configuration saved!');
        }
        
        function logout() { localStorage.removeItem('token'); window.location.href = '/login'; }
        
        function copyToClipboard(elementId, btn) {
            const element = document.getElementById(elementId);
            const text = element.textContent;
            
            navigator.clipboard.writeText(text).then(() => {
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = 'Copy';
                }, 2000);
            });
        }
        
        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            console.log('PyMon dashboard initializing...');
            
            // Setup nav buttons
            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.addEventListener('click', function() {
                    const section = this.getAttribute('data-section');
                    if (section) showSection(section);
                });
            });
            
            // Setup time buttons
            document.querySelectorAll('.time-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const range = this.getAttribute('data-range');
                    if (range) setTimeRange(range);
                });
            });
            
            // Setup refresh button
            const refreshBtn = document.querySelector('.refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function() {
                    const icon = this.querySelector('i');
                    if (icon) icon.classList.add('fa-spin');
                    setTimeout(() => {
                        if (icon) icon.classList.remove('fa-spin');
                        initCharts();
                    }, 1000);
                });
            }
            
            // Setup logout button
            const logoutBtn = document.querySelector('.btn-secondary');
            if (logoutBtn) {
                logoutBtn.addEventListener('click', logout);
            }
            
            loadServers();
            setTimeout(initCharts, 100);
        });
    </script>
</body>
</html>
"""

# API Routes
@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

@router.get("/api/servers")
async def list_servers():
    conn = get_db()
    servers = conn.execute("SELECT * FROM servers ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"servers": [dict(s) for s in servers]}

@router.post("/api/servers")
async def create_server(server: ServerModel):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO servers 
        (name, host, os_type, agent_port, check_interval, enabled, notify_telegram, notify_discord, notify_slack, notify_email, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)''',
        (server.name, server.host, server.os_type, server.agent_port, server.check_interval,
         int(server.notify_telegram), int(server.notify_discord), int(server.notify_slack), int(server.notify_email),
         datetime.utcnow().isoformat()))
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
    conn.execute('''UPDATE servers 
        SET name=?, host=?, os_type=?, agent_port=?, check_interval=?,
            notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=?
        WHERE id=?''',
        (server.name, server.host, server.os_type, server.agent_port, server.check_interval,
         int(server.notify_telegram), int(server.notify_discord), int(server.notify_slack), int(server.notify_email),
         server_id))
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
