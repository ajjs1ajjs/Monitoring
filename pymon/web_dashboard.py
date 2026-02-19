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
    <title>PyMon - Server Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0a0e1a;
            --card: #111827;
            --border: #1f2937;
            --text: #f9fafb;
            --muted: #9ca3af;
            --blue: #3b82f6;
            --green: #10b981;
            --red: #ef4444;
            --yellow: #f59e0b;
        }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .layout { display: grid; grid-template-columns: 260px 1fr; }
        .sidebar {
            background: var(--card);
            border-right: 1px solid var(--border);
            height: 100vh;
            position: fixed;
            width: 260px;
            padding: 24px 20px;
            box-sizing: border-box;
        }
        .logo { margin-bottom: 40px; }
        .logo h1 {
            background: linear-gradient(135deg, var(--blue), #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 32px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 18px;
            margin-bottom: 6px;
            border-radius: 12px;
            cursor: pointer;
            color: var(--muted);
            font-weight: 500;
            transition: all 0.2s;
            text-decoration: none;
        }
        .nav-item:hover, .nav-item.active {
            background: rgba(59, 130, 246, 0.15);
            color: var(--text);
        }
        .nav-item i { width: 24px; font-size: 18px; }
        .main { margin-left: 260px; padding: 32px; min-height: 100vh; width: calc(100% - 260px); box-sizing: border-box; overflow-x: hidden; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }
        .header h2 { font-size: 32px; }
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-size: 15px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--blue), #06b6d4);
            color: white;
        }
        .btn-danger { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .btn-secondary { background: rgba(75, 85, 99, 0.3); color: var(--text); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; margin-bottom: 32px; }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-4px); }
        .stat-icon {
            width: 56px; height: 56px;
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 26px;
            margin-bottom: 18px;
        }
        .stat-value { font-size: 38px; font-weight: 800; margin-bottom: 6px; }
        .stat-label { color: var(--muted); font-size: 15px; }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            width: 100%;
            box-sizing: border-box;
            overflow-wrap: break-word;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        .card-title { font-size: 20px; font-weight: 700; }
        table { width: 100%; border-collapse: collapse; display: block; overflow-x: auto; white-space: nowrap; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
        th { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 700;
        }
        .badge-success { background: rgba(16, 185, 129, 0.2); color: var(--green); }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--yellow); }
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
            border-radius: 20px;
            padding: 40px;
            width: 90%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }
        .modal-close {
            background: none; border: none; color: var(--muted);
            font-size: 28px; cursor: pointer;
        }
        .form-group { margin-bottom: 24px; }
        label {
            display: block;
            margin-bottom: 10px;
            color: var(--muted);
            font-weight: 600;
            font-size: 15px;
        }
        input, select {
            width: 100%;
            padding: 16px;
            background: rgba(0,0,0,0.3);
            border: 2px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 16px;
            transition: all 0.2s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: var(--blue);
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
        }
        input::placeholder { color: #4b5563; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .toggle { display: flex; align-items: center; gap: 14px; cursor: pointer; }
        .toggle input { display: none; }
        .toggle-slider {
            width: 52px; height: 28px;
            background: rgba(75, 85, 99, 0.5);
            border-radius: 14px;
            position: relative;
            transition: all 0.3s;
        }
        .toggle-slider::after {
            content: '';
            position: absolute;
            top: 2px; left: 2px;
            width: 24px; height: 24px;
            background: white;
            border-radius: 50%;
            transition: all 0.3s;
        }
        .toggle input:checked + .toggle-slider { background: var(--blue); }
        .toggle input:checked + .toggle-slider::after { transform: translateX(24px); }
        .toggles { display: flex; flex-wrap: wrap; gap: 24px; margin-top: 8px; }
        .install-box {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 12px;
            padding: 24px;
            margin-top: 24px;
            width: 100%;
            box-sizing: border-box;
            word-wrap: break-word;
        }
        .install-box h4 { margin-bottom: 12px; color: var(--blue); word-wrap: break-word; }
        .install-box code {
            background: rgba(0,0,0,0.4);
            padding: 16px;
            border-radius: 8px;
            display: block;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.5;
        }
        .os-tabs {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        .os-tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            color: var(--muted);
        }
        .os-tab.active {
            background: var(--blue);
            color: white;
            border-color: var(--blue);
        }
    </style>
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="logo">
                <h1>PyMon</h1>
            </div>
            <nav>
                <a href="#" class="nav-item active" onclick="showSection('dashboard')">
                    <i class="fas fa-home"></i> Dashboard
                </a>
                <a href="#" class="nav-item" onclick="showSection('servers')">
                    <i class="fas fa-server"></i> Servers
                </a>
                <a href="#" class="nav-item" onclick="showSection('alerts')">
                    <i class="fas fa-bell"></i> Alerts
                </a>
                <a href="#" class="nav-item" onclick="showSection('notifications')">
                    <i class="fas fa-broadcast-tower"></i> Notifications
                </a>
            </nav>
        </aside>
        
        <main class="main">
            <div class="header">
                <h2 id="page-title">Dashboard</h2>
                <button class="btn btn-primary" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
            </div>
            
            <!-- Dashboard Section -->
            <div id="section-dashboard" class="section-content">
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2); color: var(--green);">
                            <i class="fas fa-server"></i>
                        </div>
                        <div class="stat-value" id="stat-online" style="color: var(--green);">0</div>
                        <div class="stat-label">Servers Online</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(239, 68, 68, 0.2); color: var(--red);">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <div class="stat-value" id="stat-offline" style="color: var(--red);">0</div>
                        <div class="stat-label">Servers Offline</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(59, 130, 246, 0.2); color: var(--blue);">
                            <i class="fab fa-linux"></i>
                        </div>
                        <div class="stat-value" id="stat-linux" style="color: var(--blue);">0</div>
                        <div class="stat-label">Linux Servers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.2); color: var(--yellow);">
                            <i class="fab fa-windows"></i>
                        </div>
                        <div class="stat-value" id="stat-windows" style="color: var(--yellow);">0</div>
                        <div class="stat-label">Windows Servers</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3 style="margin-bottom: 20px;">System Overview</h3>
                    <canvas id="overviewChart" height="100"></canvas>
                </div>
            </div>
            
            <!-- Servers Section -->
            <div id="section-servers" class="section-content" style="display:none">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Monitored Servers</h3>
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
                    <h3 style="margin-bottom: 20px;"><i class="fas fa-download"></i> Agent Installation</h3>
                    <p style="color: var(--muted); margin-bottom: 20px;">Install the PyMon agent on your servers to start collecting metrics.</p>
                    
                    <div class="os-tabs">
                        <div class="os-tab active" onclick="showOsTab('linux')">Linux</div>
                        <div class="os-tab" onclick="showOsTab('windows')">Windows</div>
                    </div>
                    
                    <div id="install-linux" class="install-box">
                        <h4><i class="fab fa-linux"></i> Linux Installation (systemd)</h4>
                        <code>curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</code>
                        <p style="margin-top: 12px; color: var(--muted); font-size: 14px;">Supports: Ubuntu, Debian, CentOS, RHEL, Fedora</p>
                    </div>
                    
                    <div id="install-windows" class="install-box" style="display:none;">
                        <h4><i class="fab fa-windows"></i> Windows Installation</h4>
                        <p style="margin-bottom: 12px;">Download and run the installer:</p>
                        <code>Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-windows.ps1" -OutFile "install.ps1"; .\install.ps1</code>
                        <p style="margin-top: 12px; color: var(--muted); font-size: 14px;">Or download MSI: <a href="#" style="color: var(--blue);">pymon-agent.msi</a></p>
                    </div>
                </div>
            </div>
            
            <!-- Notifications Section -->
            <div id="section-notifications" class="section-content" style="display:none">
                <div class="card">
                    <h3 class="card-title">Notification Channels</h3>
                    <p style="color: var(--muted); margin-bottom: 24px;">Configure where to receive alerts when servers go down.</p>
                    
                    <div class="toggles" style="margin-bottom: 32px;">
                        <label class="toggle">
                            <input type="checkbox" id="notify-telegram">
                            <div class="toggle-slider"></div>
                            <span><i class="fab fa-telegram"></i> Telegram</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="notify-discord">
                            <div class="toggle-slider"></div>
                            <span><i class="fab fa-discord"></i> Discord</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="notify-slack">
                            <div class="toggle-slider"></div>
                            <span><i class="fab fa-slack"></i> Slack</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="notify-email">
                            <div class="toggle-slider"></div>
                            <span><i class="fas fa-envelope"></i> Email</span>
                        </label>
                    </div>
                    
                    <div id="config-telegram" style="display:none;">
                        <div class="form-group">
                            <label>Bot Token</label>
                            <input type="text" id="telegram-token" placeholder="123456789:ABCdef...">
                        </div>
                        <div class="form-group">
                            <label>Chat ID</label>
                            <input type="text" id="telegram-chat" placeholder="-1001234567890">
                        </div>
                    </div>
                    
                    <div id="config-discord" style="display:none;">
                        <div class="form-group">
                            <label>Webhook URL</label>
                            <input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/...">
                        </div>
                    </div>
                    
                    <div id="config-slack" style="display:none;">
                        <div class="form-group">
                            <label>Webhook URL</label>
                            <input type="text" id="slack-webhook" placeholder="https://hooks.slack.com/services/...">
                        </div>
                    </div>
                    
                    <div id="config-email" style="display:none;">
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
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="email-user" placeholder="your@email.com">
                        </div>
                        <div class="form-group">
                            <label>Password / App Token</label>
                            <input type="password" id="email-pass" placeholder="••••••••">
                        </div>
                    </div>
                    
                    <button class="btn btn-primary" onclick="saveNotifications()">
                        <i class="fas fa-save"></i> Save Configuration
                    </button>
                </div>
            </div>
        </main>
    </div>
    
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
                    <div class="toggles">
                        <label class="toggle">
                            <input type="checkbox" id="server-notify-telegram">
                            <div class="toggle-slider"></div>
                            <span>Telegram</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="server-notify-discord">
                            <div class="toggle-slider"></div>
                            <span>Discord</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="server-notify-slack">
                            <div class="toggle-slider"></div>
                            <span>Slack</span>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" id="server-notify-email">
                            <div class="toggle-slider"></div>
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
    
    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';
        
        let currentOsTab = 'linux';
        
        function showSection(section) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            event.target.closest('.nav-item').classList.add('active');
            document.querySelectorAll('.section-content').forEach(el => el.style.display = 'none');
            document.getElementById('section-' + section).style.display = 'block';
            const titles = { dashboard: 'Dashboard', servers: 'Servers', alerts: 'Alerts', notifications: 'Notifications' };
            document.getElementById('page-title').textContent = titles[section];
            if (section === 'servers') loadServers();
        }
        
        function showOsTab(os) {
            document.querySelectorAll('.os-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('install-linux').style.display = os === 'linux' ? 'block' : 'none';
            document.getElementById('install-windows').style.display = os === 'windows' ? 'block' : 'none';
        }
        
        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }
        
        async function loadServers() {
            try {
                const resp = await fetch('/api/servers', { headers: { 'Authorization': `Bearer ${token}` }});
                const data = await resp.json();
                let online = 0, offline = 0, linux = 0, windows = 0;
                document.getElementById('servers-tbody').innerHTML = data.servers.map(s => {
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
                            <button class="btn btn-danger" onclick="deleteServer(${s.id})" style="padding: 8px 16px; font-size: 13px;">
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
        
        // Toggle notification configs
        document.querySelectorAll('input[id^="notify-"]').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const channel = e.target.id.replace('notify-', '');
                document.getElementById('config-' + channel).style.display = e.target.checked ? 'block' : 'none';
            });
        });
        
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
            alert('Saved!');
        }
        
        function logout() { localStorage.removeItem('token'); window.location.href = '/login'; }
        
        // Chart
        new Chart(document.getElementById('overviewChart'), {
            type: 'line',
            data: {
                labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                datasets: [{
                    label: 'CPU Usage %',
                    data: [25, 30, 45, 60, 40, 35],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Memory %',
                    data: [40, 42, 55, 65, 50, 48],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } }
                },
                plugins: { legend: { labels: { color: '#9ca3af' } } }
            }
        });
        
        loadServers();
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
