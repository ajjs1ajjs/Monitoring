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
            agent_version TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )''')
        
        for channel in ['telegram', 'discord', 'slack', 'email']:
            c.execute("INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing web tables: {e}")
        raise

DASHBOARD_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Server Monitoring</title>
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
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            font-size: 13px;
        }
        .top-nav {
            background: linear-gradient(90deg, #161719, #1f2326);
            border-bottom: 1px solid var(--border);
            padding: 0 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 48px;
        }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon {
            width: 24px; height: 24px;
            background: linear-gradient(135deg, var(--blue), #2c7bd9);
            border-radius: 4px;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px; color: white; font-weight: bold;
        }
        .logo h1 { color: var(--blue); font-size: 18px; font-weight: 600; }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item {
            display: flex; align-items: center; gap: 6px;
            padding: 8px 12px; border-radius: 4px;
            cursor: pointer; color: var(--muted); font-weight: 500; font-size: 13px;
            border: none; background: transparent;
        }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active { background: rgba(87,148,242,0.15); color: var(--blue); }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .server-selector {
            padding: 6px 10px; background: #111217; border: 1px solid var(--border);
            border-radius: 4px; color: var(--text); font-size: 13px; min-width: 160px;
        }
        .main { padding: 16px; }
        
        .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
        .stat-card {
            background: var(--card); border: 1px solid var(--border); border-radius: 4px;
            padding: 16px; display: flex; align-items: center; gap: 12px;
        }
        .stat-icon {
            width: 40px; height: 40px; border-radius: 6px;
            display: flex; align-items: center; justify-content: center; font-size: 18px;
        }
        .stat-value { font-size: 24px; font-weight: 600; }
        .stat-label { color: var(--muted); font-size: 12px; }
        
        .dashboard-toolbar {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; padding: 8px 12px; background: var(--card);
            border: 1px solid var(--border); border-radius: 4px;
        }
        .time-range { display: flex; gap: 2px; background: #111217; border-radius: 4px; padding: 2px; border: 1px solid var(--border); }
        .time-btn {
            padding: 4px 10px; background: transparent; border: none; border-radius: 3px;
            color: var(--muted); font-size: 12px; cursor: pointer;
        }
        .time-btn.active { background: #2c3235; color: var(--text); }
        
        .panels-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        .panel { background: var(--card); border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
        .panel-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 12px; border-bottom: 1px solid var(--border);
        }
        .panel-title { font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
        .panel-body { display: flex; height: 280px; }
        .panel-chart { flex: 1; padding: 12px; position: relative; }
        .panel-legend { width: 140px; border-left: 1px solid var(--border); background: rgba(0,0,0,0.2); overflow-y: auto; font-size: 11px; }
        .legend-header {
            display: grid; grid-template-columns: 1fr 45px 45px;
            padding: 8px 10px; border-bottom: 1px solid var(--border);
            color: var(--muted); font-size: 10px; text-transform: uppercase; font-weight: 600;
        }
        .legend-item {
            display: grid; grid-template-columns: 12px 1fr 45px 45px;
            align-items: center; padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.03);
            cursor: pointer;
        }
        .legend-color { width: 10px; height: 10px; border-radius: 2px; margin-right: 8px; }
        .legend-name { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; }
        .legend-value { color: var(--muted); text-align: right; font-size: 11px; }
        
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 16px; margin-bottom: 16px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .card-title { font-size: 14px; font-weight: 600; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        
        .btn {
            padding: 8px 16px; border-radius: 4px; border: none; font-weight: 500;
            cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px;
        }
        .btn-primary { background: linear-gradient(180deg, #2c7bd9, #1a5fb4); color: white; }
        .btn-secondary { background: rgba(255,255,255,0.05); color: var(--text); border: 1px solid var(--border); }
        .btn-danger { background: rgba(242,73,92,0.15); color: var(--red); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 24px; width: 90%; max-width: 500px; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 20px; cursor: pointer; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; }
        input, select { width: 100%; padding: 10px 12px; background: #111217; border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 13px; }
        input:focus, select:focus { outline: none; border-color: var(--blue); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        
        .section-content { display: none; }
        .section-content.active { display: block; }
        
        .install-box { background: rgba(87,148,242,0.05); border: 1px solid rgba(87,148,242,0.2); border-radius: 4px; padding: 16px; margin-top: 12px; }
        .install-box h4 { margin-bottom: 10px; color: var(--blue); font-size: 13px; font-weight: 600; }
        .code-block { position: relative; background: #111217; border: 1px solid var(--border); border-radius: 4px; margin: 10px 0; }
        .code-block code { display: block; padding: 12px; font-family: Monaco,Consolas,monospace; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; color: var(--text); }
        .copy-btn { position: absolute; top: 8px; right: 8px; padding: 4px 8px; background: rgba(255,255,255,0.1); border: none; border-radius: 3px; color: var(--muted); font-size: 11px; cursor: pointer; }
        .code-block:hover .copy-btn { opacity: 1; }
        .install-step { display: flex; gap: 12px; margin-bottom: 16px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 4px; border-left: 3px solid var(--blue); }
        .step-number { width: 24px; height: 24px; background: var(--blue); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
        .step-title { font-weight: 600; margin-bottom: 4px; font-size: 13px; }
        .step-desc { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
        
        .alert-rule { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 4px; padding: 16px; margin-bottom: 12px; }
        .alert-rule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .alert-rule-title { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .alert-conditions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
        .condition-box { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 4px; font-size: 12px; }
        .condition-label { color: var(--muted); margin-bottom: 4px; font-size: 11px; text-transform: uppercase; }
        .condition-value { font-weight: 600; color: var(--text); font-size: 13px; }
        .notification-tag { padding: 4px 10px; background: rgba(87,148,242,0.15); border-radius: 3px; font-size: 11px; color: var(--blue); }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="nav-left">
            <div class="logo">
                <div class="logo-icon">P</div>
                <h1>PyMon</h1>
            </div>
            <div class="nav-menu">
                <button class="nav-item active" data-section="dashboard">Dashboard</button>
                <button class="nav-item" data-section="servers">Servers</button>
                <button class="nav-item" data-section="alerts">Alerts</button>
                <button class="nav-item" data-section="settings">Settings</button>
            </div>
        </div>
        <div class="nav-right">
            <select class="server-selector" id="serverSelector">
                <option value="">All Servers</option>
            </select>
            <button class="btn btn-secondary btn-sm" id="logoutBtn">Logout</button>
        </div>
    </nav>
    
    <main class="main">
        <!-- Dashboard -->
        <div id="section-dashboard" class="section-content active">
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(115,191,105,0.15); color: var(--green);"><i class="fas fa-server"></i></div>
                    <div class="stat-content"><div class="stat-value" id="stat-online" style="color: var(--green);">0</div><div class="stat-label">Online</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(242,73,92,0.15); color: var(--red);"><i class="fas fa-exclamation-triangle"></i></div>
                    <div class="stat-content"><div class="stat-value" id="stat-offline" style="color: var(--red);">0</div><div class="stat-label">Offline</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(87,148,242,0.15); color: var(--blue);"><i class="fab fa-linux"></i></div>
                    <div class="stat-content"><div class="stat-value" id="stat-linux" style="color: var(--blue);">0</div><div class="stat-label">Linux</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(242,204,12,0.15); color: var(--yellow);"><i class="fab fa-windows"></i></div>
                    <div class="stat-content"><div class="stat-value" id="stat-windows" style="color: var(--yellow);">0</div><div class="stat-label">Windows</div></div>
                </div>
            </div>
            
            <div class="dashboard-toolbar">
                <span style="color: var(--muted); font-size: 13px;">Home / Dashboard</span>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <div class="time-range">
                        <button class="time-btn" data-range="5m">5m</button>
                        <button class="time-btn" data-range="15m">15m</button>
                        <button class="time-btn" data-range="1h">1h</button>
                        <button class="time-btn" data-range="6h">6h</button>
                        <button class="time-btn" data-range="24h">24h</button>
                    </div>
                </div>
            </div>
            
            <div class="panels-grid">
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><span class="status-dot"></span>CPU</div></div>
                    <div class="panel-body"><div class="panel-chart"><canvas id="cpuChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span>Name</span><span>Last</span><span>Max</span></div><div id="cpuLegend"></div></div></div>
                </div>
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Memory</div></div>
                    <div class="panel-body"><div class="panel-chart"><canvas id="memoryChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span>Name</span><span>Last</span><span>Max</span></div><div id="memoryLegend"></div></div></div>
                </div>
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Disk</div></div>
                    <div class="panel-body"><div class="panel-chart"><canvas id="diskChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span>Name</span><span>Last</span><span>Max</span></div><div id="diskLegend"></div></div></div>
                </div>
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><span class="status-dot"></span>Network</div></div>
                    <div class="panel-body"><div class="panel-chart"><canvas id="networkChart"></canvas></div><div class="panel-legend"><div class="legend-header"><span>Name</span><span>Last</span><span>Max</span></div><div id="networkLegend"></div></div></div>
                </div>
            </div>
        </div>
        
        <!-- Servers -->
        <div id="section-servers" class="section-content">
            <div class="card">
                <div class="card-header"><h3 class="card-title">Monitored Servers</h3><button class="btn btn-primary" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button></div>
                <table><thead><tr><th>Status</th><th>Name</th><th>Host</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Actions</th></tr></thead><tbody id="servers-tbody"></tbody></table>
            </div>
            <div class="card">
                <h3 class="card-title" style="margin-bottom: 16px;">Agent Installation</h3>
                <div class="install-box">
                    <h4>Linux Agent</h4>
                    <div class="install-step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <div class="step-title">Download and run installer</div>
                            <div class="code-block"><code id="linux-install">curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</code><button class="copy-btn" data-target="linux-install">Copy</button></div>
                        </div>
                    </div>
                    <div class="install-step">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <div class="step-title">Configure and start</div>
                            <div class="code-block"><code>sudo nano /etc/systemd/system/pymon-agent.service && sudo systemctl start pymon-agent</code></div>
                        </div>
                    </div>
                </div>
                <div class="install-box">
                    <h4>Windows Agent</h4>
                    <div class="install-step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <div class="step-title">Run in PowerShell as Administrator</div>
                            <div class="code-block"><code id="windows-install">Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-windows.ps1" -OutFile "install.ps1"; .\install.ps1</code><button class="copy-btn" data-target="windows-install">Copy</button></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Alerts -->
        <div id="section-alerts" class="section-content">
            <div class="card">
                <div class="card-header"><h3 class="card-title">Alert Rules</h3><button class="btn btn-primary" id="addAlertBtn"><i class="fas fa-plus"></i> New Alert</button></div>
                <div class="alert-rule">
                    <div class="alert-rule-header"><div class="alert-rule-title"><i class="fas fa-microchip" style="color: var(--blue);"></i> High CPU Usage</div></div>
                    <div class="alert-conditions"><div class="condition-box"><div class="condition-label">Metric</div><div class="condition-value">CPU > 80%</div></div><div class="condition-box"><div class="condition-label">Duration</div><div class="condition-value">5 min</div></div><div class="condition-box"><div class="condition-label">Notify</div><div class="condition-value">Telegram</div></div></div>
                </div>
                <div class="alert-rule">
                    <div class="alert-rule-header"><div class="alert-rule-title"><i class="fas fa-memory" style="color: var(--green);"></i> High Memory</div></div>
                    <div class="alert-conditions"><div class="condition-box"><div class="condition-label">Metric</div><div class="condition-value">Memory > 85%</div></div><div class="condition-box"><div class="condition-label">Duration</div><div class="condition-value">3 min</div></div><div class="condition-box"><div class="condition-label">Notify</div><div class="condition-value">Discord</div></div></div>
                </div>
            </div>
        </div>
        
        <!-- Settings -->
        <div id="section-settings" class="section-content">
            <div class="card">
                <h3 class="card-title" style="margin-bottom: 20px;">Notification Channels</h3>
                <div class="form-group"><label><input type="checkbox" id="notify-telegram"> Telegram</label></div>
                <div class="form-group"><label><input type="checkbox" id="notify-discord"> Discord</label></div>
                <div class="form-group"><label><input type="checkbox" id="notify-slack"> Slack</label></div>
                <div class="form-group"><label><input type="checkbox" id="notify-email"> Email</label></div>
                <button class="btn btn-primary" id="saveNotifyBtn">Save Configuration</button>
            </div>
        </div>
    </main>
    
    <!-- Add Server Modal -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header"><h3>Add Server</h3><button class="modal-close" id="closeServerModal">&times;</button></div>
            <form id="addServerForm">
                <div class="form-group"><label>Server Name</label><input type="text" id="server-name" required></div>
                <div class="form-group"><label>Host</label><input type="text" id="server-host" required></div>
                <div class="form-row">
                    <div class="form-group"><label>OS</label><select id="server-os"><option value="linux">Linux</option><option value="windows">Windows</option></select></div>
                    <div class="form-group"><label>Interval (sec)</label><input type="number" id="server-interval" value="15"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%">Add Server</button>
            </form>
        </div>
    </div>
    
    <script>
    const token = localStorage.getItem('token');
    if (!token) window.location.href = '/login';
    
    let servers = [];
    let charts = {};
    let currentRange = '1h';
    const colors = ['#73bf69','#f2cc0c','#5794f2','#b877d9','#ff780a','#00d8d8','#f2495c'];
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', function() {
            const section = this.getAttribute('data-section');
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.section-content').forEach(el => { el.classList.remove('active'); el.style.display = 'none'; });
            const el = document.getElementById('section-' + section);
            if (el) { el.style.display = 'block'; el.classList.add('active'); }
            if (section === 'servers') loadServers();
            if (section === 'dashboard') initCharts();
        });
    });
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', function() {
        localStorage.removeItem('token');
        window.location.href = '/login';
    });
    
    // Time range
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentRange = this.getAttribute('data-range');
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            initCharts();
        });
    });
    
    // Add Server
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
    
    // Copy buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const text = document.getElementById(target).textContent;
            navigator.clipboard.writeText(text);
            this.textContent = 'Copied!';
            setTimeout(() => this.textContent = 'Copy', 2000);
        });
    });
    
    // Load servers
    async function loadServers() {
        try {
            const resp = await fetch('/api/servers', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            servers = data.servers || [];
            let online = 0, offline = 0, linux = 0, windows = 0;
            
            document.getElementById('serverSelector').innerHTML = '<option value="">All Servers</option>' + 
                servers.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
            
            document.getElementById('servers-tbody').innerHTML = servers.map(s => {
                if (s.last_status === 'up') online++;
                else if (s.last_status === 'down') offline++;
                if (s.os_type === 'linux') linux++;
                else if (s.os_type === 'windows') windows++;
                return '<tr><td><span style="padding:4px 8px;background:rgba(115,191,105,0.15);color:#73bf69;border-radius:12px;font-size:11px;">' + (s.last_status || 'pending') + '</span></td><td><strong>' + s.name + '</strong></td><td>' + s.host + '</td><td>' + s.os_type + '</td><td>' + (s.cpu_percent ? s.cpu_percent.toFixed(1) + '%' : '-') + '</td><td>' + (s.memory_percent ? s.memory_percent.toFixed(1) + '%' : '-') + '</td><td>' + (s.disk_percent ? s.disk_percent.toFixed(1) + '%' : '-') + '</td><td><button class="btn btn-danger btn-sm" onclick="deleteServer(' + s.id + ')">Delete</button></td></tr>';
            }).join('') || '<tr><td colspan="8" style="text-align:center;padding:40px;color:#999;">No servers</td></tr>';
            
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            document.getElementById('stat-linux').textContent = linux;
            document.getElementById('stat-windows').textContent = windows;
        } catch(e) { console.error(e); }
    }
    
    async function deleteServer(id) {
        if (confirm('Delete server?')) {
            await fetch('/api/servers/' + id, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadServers();
        }
    }
    
    // Charts
    function initCharts() {
        Object.values(charts).forEach(c => c && c.destroy());
        charts = {};
        
        const labels = generateLabels();
        
        // CPU
        const cpuData = servers.length ? servers.map((s,i) => ({label:s.name,data:rand(12,30,90),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,30,80),borderColor:colors[0],backgroundColor:colors[0]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type:'line',data:{labels:labels,datasets:cpuData},options:chartOpts('%',0,100)});
        updateLegend('cpuLegend', cpuData, '%');
        
        // Memory
        const memData = servers.length ? servers.map((s,i) => ({label:s.name,data:rand(12,40,90),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,50,85),borderColor:colors[1],backgroundColor:colors[1]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.memory = new Chart(document.getElementById('memoryChart'), {type:'line',data:{labels:labels,datasets:memData},options:chartOpts('%',0,100)});
        updateLegend('memoryLegend', memData, '%');
        
        // Disk
        const diskData = servers.length ? servers.map((s,i) => ({label:s.name,data:rand(12,50,95),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,60,90),borderColor:colors[2],backgroundColor:colors[2]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.disk = new Chart(document.getElementById('diskChart'), {type:'line',data:{labels:labels,datasets:diskData},options:chartOpts('%',0,100)});
        updateLegend('diskLegend', diskData, '%');
        
        // Network
        const netData = servers.length ? servers.map((s,i) => ({label:s.name,data:rand(12,10,60),borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0})) : [{label:'Demo',data:rand(12,20,50),borderColor:colors[3],backgroundColor:colors[3]+'15',fill:true,tension:0.3,borderWidth:1.5,pointRadius:0}];
        charts.network = new Chart(document.getElementById('networkChart'), {type:'line',data:{labels:labels,datasets:netData},options:chartOpts(' MB/s',0,60)});
        updateLegend('networkLegend', netData, ' MB/s');
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
    
    function rand(n, min, max) {
        return Array(n).fill(0).map(() => min + Math.random() * (max - min));
    }
    
    function chartOpts(suffix, min, max) {
        return {
            responsive: true, maintainAspectRatio: false,
            interaction: {intersect: false, mode: 'index'},
            scales: {
                y: {min:min, max:max, grid:{color:'rgba(255,255,255,0.03)'}, ticks:{color:'#666',font:{size:10},callback:v=>v+suffix}},
                x: {grid:{display:false}, ticks:{color:'#666',font:{size:10}}}
            },
            plugins: {legend:{display:false}}
        };
    }
    
    function updateLegend(id, datasets, suffix) {
        const el = document.getElementById(id);
        el.innerHTML = datasets.map((ds,i) => {
            const last = ds.data[ds.data.length-1];
            const mx = Math.max(...ds.data);
            return '<div class="legend-item"><div class="legend-color" style="background:'+ds.borderColor+'"></div><div class="legend-name">'+ds.label+'</div><div class="legend-value">'+last.toFixed(1)+suffix+'</div><div class="legend-value">'+mx.toFixed(1)+suffix+'</div></div>';
        }).join('');
    }
    
    // Init
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
    servers = conn.execute("SELECT * FROM servers ORDER BY created_at DESC").fetchall()
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
