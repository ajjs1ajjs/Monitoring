"""Enterprise Web Dashboard for PyMon"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import os
from datetime import datetime

router = APIRouter()
security = HTTPBearer(auto_error=False)

DB_PATH = os.getenv("DB_PATH", "/var/lib/pymon/pymon.db")

def get_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class SiteModel(BaseModel):
    name: str
    url: str
    check_interval: int = 60
    timeout: int = 10
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False

def init_web_tables():
    try:
        # Ensure directory exists with proper permissions
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created database directory: {db_dir}")
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            check_interval INTEGER DEFAULT 60,
            timeout INTEGER DEFAULT 10,
            enabled BOOLEAN DEFAULT 1,
            notify_telegram BOOLEAN DEFAULT 0,
            notify_discord BOOLEAN DEFAULT 0,
            notify_slack BOOLEAN DEFAULT 0,
            notify_email BOOLEAN DEFAULT 0,
            created_at TEXT,
            last_check TEXT,
            last_status TEXT,
            last_response_time REAL
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            config TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS check_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            status TEXT,
            response_time REAL,
            checked_at TEXT
        )''')
        
        for channel in ['telegram', 'discord', 'slack', 'email']:
            c.execute("INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,))
        
        conn.commit()
        conn.close()
        print("Web tables initialized successfully")
    except Exception as e:
        print(f"Error initializing web tables: {e}")
        import traceback
        traceback.print_exc()
        raise

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            width: 100%;
            max-width: 400px;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { 
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 36px;
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #9ca3af; margin-bottom: 8px; }
        input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #fff;
            font-size: 16px;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s;
        }
        button:hover { transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">
            <h1>PyMon</h1>
            <p style="color: #9ca3af;">Enterprise Monitoring</p>
        </div>
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" required>
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
    <title>PyMon Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0e1a;
            --bg-card: rgba(17, 24, 39, 0.8);
            --accent-blue: #3b82f6;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
        }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .container { display: grid; grid-template-columns: 260px 1fr; }
        .sidebar {
            background: rgba(17, 24, 39, 0.9);
            border-right: 1px solid rgba(255,255,255,0.1);
            padding: 24px;
            height: 100vh;
            position: fixed;
            width: 260px;
        }
        .logo { text-align: center; margin-bottom: 32px; }
        .logo h1 {
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 28px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 10px;
            cursor: pointer;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.3s;
        }
        .nav-item:hover, .nav-item.active {
            background: rgba(59, 130, 246, 0.2);
            color: var(--text-primary);
        }
        .main { margin-left: 260px; padding: 32px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-blue), #06b6d4);
            color: white;
        }
        .btn-danger { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-bottom: 32px; }
        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        }
        .stat-value { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
        .stat-label { color: var(--text-secondary); font-size: 14px; }
        .success { color: #10b981; }
        .danger { color: #ef4444; }
        .warning { color: #f59e0b; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 16px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { color: var(--text-secondary); font-weight: 500; font-size: 12px; text-transform: uppercase; }
        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
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
            background: var(--bg-card);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 500px;
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: var(--text-secondary); }
        input, select {
            width: 100%;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #fff;
        }
        .tabs { display: flex; gap: 16px; margin-bottom: 24px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .tab { padding: 12px 20px; cursor: pointer; color: var(--text-secondary); border-bottom: 2px solid transparent; }
        .tab.active { color: var(--accent-blue); border-bottom-color: var(--accent-blue); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .toggle { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .toggle input { display: none; }
        .toggle-slider {
            width: 48px; height: 24px;
            background: rgba(75,85,99,0.5);
            border-radius: 12px;
            position: relative;
            transition: background 0.3s;
        }
        .toggle-slider::after {
            content: '';
            position: absolute;
            top: 2px; left: 2px;
            width: 20px; height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }
        .toggle input:checked + .toggle-slider { background: var(--accent-blue); }
        .toggle input:checked + .toggle-slider::after { transform: translateX(24px); }
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="logo">
                <h1>PyMon</h1>
            </div>
            <nav>
                <a href="#" class="nav-item active" onclick="showSection('dashboard')">
                    <i class="fas fa-home"></i> Dashboard
                </a>
                <a href="#" class="nav-item" onclick="showSection('sites')">
                    <i class="fas fa-globe"></i> Websites
                </a>
                <a href="#" class="nav-item" onclick="showSection('alerts')">
                    <i class="fas fa-bell"></i> Alerts
                </a>
                <a href="#" class="nav-item" onclick="showSection('notifications')">
                    <i class="fas fa-broadcast-tower"></i> Notifications
                </a>
                <a href="#" class="nav-item" onclick="showSection('apikeys')">
                    <i class="fas fa-key"></i> API Keys
                </a>
            </nav>
        </aside>
        
        <main class="main">
            <div class="header">
                <h2 id="page-title">Dashboard</h2>
                <button class="btn btn-primary" onclick="logout()">Logout</button>
            </div>
            
            <div id="section-dashboard" class="section-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value success" id="stat-online">0</div>
                        <div class="stat-label">Sites Online</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value danger" id="stat-offline">0</div>
                        <div class="stat-label">Sites Offline</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value warning" id="stat-alerts">0</div>
                        <div class="stat-label">Active Alerts</div>
                    </div>
                </div>
                <div class="card">
                    <h3 style="margin-bottom: 16px;">Response Times</h3>
                    <canvas id="chart" height="100"></canvas>
                </div>
            </div>
            
            <div id="section-sites" class="section-content" style="display:none">
                <div class="card">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 24px;">
                        <h3>Monitored Websites</h3>
                        <button class="btn btn-primary" onclick="openModal('siteModal')">Add Website</button>
                    </div>
                    <table>
                        <thead>
                            <tr><th>Status</th><th>Name</th><th>URL</th><th>Response</th><th>Actions</th></tr>
                        </thead>
                        <tbody id="sites-tbody"></tbody>
                    </table>
                </div>
            </div>
            
            <div id="section-notifications" class="section-content" style="display:none">
                <div class="card">
                    <h3 style="margin-bottom: 24px;">Notification Channels</h3>
                    <div class="tabs">
                        <div class="tab active" onclick="showTab('telegram')">Telegram</div>
                        <div class="tab" onclick="showTab('discord')">Discord</div>
                        <div class="tab" onclick="showTab('slack')">Slack</div>
                        <div class="tab" onclick="showTab('email')">Email</div>
                    </div>
                    <div id="tab-telegram" class="tab-content active">
                        <label class="toggle">
                            <input type="checkbox" id="telegram-enabled">
                            <div class="toggle-slider"></div>
                            <span>Enable Telegram</span>
                        </label>
                        <div class="form-group" style="margin-top: 16px;">
                            <label>Bot Token</label>
                            <input type="text" id="telegram-token" placeholder="Your bot token">
                        </div>
                        <div class="form-group">
                            <label>Chat ID</label>
                            <input type="text" id="telegram-chat" placeholder="Chat ID">
                        </div>
                        <button class="btn btn-primary" onclick="saveNotification('telegram')">Save</button>
                    </div>
                    <div id="tab-discord" class="tab-content">
                        <label class="toggle">
                            <input type="checkbox" id="discord-enabled">
                            <div class="toggle-slider"></div>
                            <span>Enable Discord</span>
                        </label>
                        <div class="form-group" style="margin-top: 16px;">
                            <label>Webhook URL</label>
                            <input type="text" id="discord-webhook" placeholder="Discord webhook URL">
                        </div>
                        <button class="btn btn-primary" onclick="saveNotification('discord')">Save</button>
                    </div>
                    <div id="tab-slack" class="tab-content">
                        <label class="toggle">
                            <input type="checkbox" id="slack-enabled">
                            <div class="toggle-slider"></div>
                            <span>Enable Slack</span>
                        </label>
                        <div class="form-group" style="margin-top: 16px;">
                            <label>Webhook URL</label>
                            <input type="text" id="slack-webhook" placeholder="Slack webhook URL">
                        </div>
                        <button class="btn btn-primary" onclick="saveNotification('slack')">Save</button>
                    </div>
                    <div id="tab-email" class="tab-content">
                        <label class="toggle">
                            <input type="checkbox" id="email-enabled">
                            <div class="toggle-slider"></div>
                            <span>Enable Email</span>
                        </label>
                        <div class="form-group" style="margin-top: 16px;">
                            <label>SMTP Host</label>
                            <input type="text" id="email-host" placeholder="smtp.gmail.com">
                        </div>
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="email-user" placeholder="your@email.com">
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="email-pass" placeholder="App password">
                        </div>
                        <button class="btn btn-primary" onclick="saveNotification('email')">Save</button>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <div class="modal" id="siteModal">
        <div class="modal-content">
            <h3 style="margin-bottom: 24px;">Add Website</h3>
            <div class="form-group">
                <label>Name</label>
                <input type="text" id="site-name" placeholder="My Website">
            </div>
            <div class="form-group">
                <label>URL</label>
                <input type="url" id="site-url" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label>Check Interval (seconds)</label>
                <input type="number" id="site-interval" value="60">
            </div>
            <div style="display: flex; gap: 12px; margin-top: 24px;">
                <button class="btn btn-primary" onclick="addSite()">Add</button>
                <button class="btn btn-danger" onclick="closeModal('siteModal')">Cancel</button>
            </div>
        </div>
    </div>
    
    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';
        
        function showSection(section) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            event.target.closest('.nav-item').classList.add('active');
            document.querySelectorAll('.section-content').forEach(el => el.style.display = 'none');
            document.getElementById('section-' + section).style.display = 'block';
            document.getElementById('page-title').textContent = section.charAt(0).toUpperCase() + section.slice(1);
            if (section === 'sites') loadSites();
        }
        
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }
        
        async function loadSites() {
            const resp = await fetch('/api/sites', { headers: { 'Authorization': `Bearer ${token}` }});
            const data = await resp.json();
            let online = 0, offline = 0;
            document.getElementById('sites-tbody').innerHTML = data.sites.map(s => {
                if (s.last_status === 'up') online++;
                else if (s.last_status === 'down') offline++;
                return `<tr>
                    <td><span class="badge badge-${s.last_status === 'up' ? 'success' : 'danger'}">${s.last_status || 'pending'}</span></td>
                    <td>${s.name}</td>
                    <td>${s.url}</td>
                    <td>${s.last_response_time ? Math.round(s.last_response_time) + 'ms' : '-'}</td>
                    <td>
                        <button class="btn btn-danger" onclick="deleteSite(${s.id})">Delete</button>
                    </td>
                </tr>`;
            }).join('');
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
        }
        
        async function addSite() {
            const data = {
                name: document.getElementById('site-name').value,
                url: document.getElementById('site-url').value,
                check_interval: parseInt(document.getElementById('site-interval').value),
                timeout: 10,
                notify_telegram: false, notify_discord: false, notify_slack: false, notify_email: false
            };
            await fetch('/api/sites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(data)
            });
            closeModal('siteModal');
            loadSites();
        }
        
        async function deleteSite(id) {
            if (!confirm('Delete this site?')) return;
            await fetch('/api/sites/' + id, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }});
            loadSites();
        }
        
        async function saveNotification(channel) {
            const config = { enabled: document.getElementById(channel + '-enabled').checked };
            if (channel === 'telegram') {
                config.telegram_bot_token = document.getElementById('telegram-token').value;
                config.telegram_chat_id = document.getElementById('telegram-chat').value;
            } else if (channel === 'discord') {
                config.discord_webhook = document.getElementById('discord-webhook').value;
            } else if (channel === 'slack') {
                config.slack_webhook = document.getElementById('slack-webhook').value;
            } else if (channel === 'email') {
                config.email_smtp_host = document.getElementById('email-host').value;
                config.email_user = document.getElementById('email-user').value;
                config.email_pass = document.getElementById('email-pass').value;
            }
            await fetch('/api/notifications/' + channel, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(config)
            });
            alert('Saved!');
        }
        
        function logout() { localStorage.removeItem('token'); window.location.href = '/login'; }
        
        // Init chart
        new Chart(document.getElementById('chart'), {
            type: 'line',
            data: {
                labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [120, 150, 110, 180, 140, 130],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true
                }]
            },
            options: {
                scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#9ca3af' } },
                    x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#9ca3af' } }
                },
                plugins: { legend: { labels: { color: '#9ca3af' } } }
            }
        });
        
        loadSites();
    </script>
</body>
</html>
"""

@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

@router.get("/api/sites")
async def list_sites():
    conn = get_db()
    sites = conn.execute("SELECT * FROM sites ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"sites": [dict(s) for s in sites]}

@router.post("/api/sites")
async def create_site(site: SiteModel):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO sites 
        (name, url, check_interval, timeout, enabled, notify_telegram, notify_discord, notify_slack, notify_email, created_at)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)''',
        (site.name, site.url, site.check_interval, site.timeout,
         int(site.notify_telegram), int(site.notify_discord), int(site.notify_slack), int(site.notify_email),
         datetime.utcnow().isoformat()))
    site_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": site_id, "status": "ok"}

@router.delete("/api/sites/{site_id}")
async def delete_site(site_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sites WHERE id=?", (site_id,))
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
