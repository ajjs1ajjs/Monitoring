"""Web UI templates and routes"""

from datetime import datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import os

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "pymon.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_web_tables():
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
        notify_sms BOOLEAN DEFAULT 0,
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
        checked_at TEXT,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )''')
    
    for channel in ['telegram', 'discord', 'slack', 'email', 'sms']:
        c.execute("INSERT OR IGNORE INTO notifications (channel, enabled, config) VALUES (?, 0, '{}')", (channel,))
    
    conn.commit()
    conn.close()


class SiteCreate(BaseModel):
    name: str
    url: str
    check_interval: int = 60
    timeout: int = 10
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False
    notify_sms: bool = False


class NotificationConfig(BaseModel):
    channel: str
    enabled: bool
    config: dict


# API Routes
@router.get("/api/sites")
async def list_sites():
    conn = get_db()
    sites = conn.execute("SELECT * FROM sites ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"sites": [dict(s) for s in sites]}


@router.post("/api/sites")
async def create_site(site: SiteCreate):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO sites 
        (name, url, check_interval, timeout, enabled, 
         notify_telegram, notify_discord, notify_slack, notify_email, notify_sms, created_at)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)''',
        (site.name, site.url, site.check_interval, site.timeout,
         int(site.notify_telegram), int(site.notify_discord), int(site.notify_slack),
         int(site.notify_email), int(site.notify_sms), datetime.utcnow().isoformat()))
    site_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": site_id, "status": "ok"}


@router.put("/api/sites/{site_id}")
async def update_site(site_id: int, site: SiteCreate):
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE sites SET 
        name=?, url=?, check_interval=?, timeout=?,
        notify_telegram=?, notify_discord=?, notify_slack=?, notify_email=?, notify_sms=?
        WHERE id=?''',
        (site.name, site.url, site.check_interval, site.timeout,
         int(site.notify_telegram), int(site.notify_discord), int(site.notify_slack),
         int(site.notify_email), int(site.notify_sms), site_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.delete("/api/sites/{site_id}")
async def delete_site(site_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sites WHERE id=?", (site_id,))
    conn.execute("DELETE FROM check_history WHERE site_id=?", (site_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/api/sites/{site_id}/check")
async def check_site_now(site_id: int):
    conn = get_db()
    site = conn.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
    if not site:
        conn.close()
        raise HTTPException(404, "Site not found")
    
    import httpx
    import time
    
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=site['timeout']) as client:
            resp = await client.get(site['url'], follow_redirects=True)
        response_time = (time.time() - start) * 1000
        status = "up" if resp.status_code < 400 else "down"
    except Exception as e:
        status = "down"
        response_time = 0
    
    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE sites SET last_check=?, last_status=?, last_response_time=? WHERE id=?",
                 (now, status, response_time, site_id))
    conn.execute("INSERT INTO check_history (site_id, status, response_time, checked_at) VALUES (?, ?, ?, ?)",
                 (site_id, status, response_time, now))
    conn.commit()
    conn.close()
    
    return {"status": status, "response_time": response_time}


@router.get("/api/sites/{site_id}/history")
async def get_site_history(site_id: int, hours: int = 24):
    conn = get_db()
    from datetime import datetime, timedelta
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    history = conn.execute(
        "SELECT * FROM check_history WHERE site_id=? AND checked_at > ? ORDER BY checked_at DESC LIMIT 100",
        (site_id, since)
    ).fetchall()
    conn.close()
    return {"history": [dict(h) for h in history]}


@router.get("/api/notifications")
async def get_notifications():
    conn = get_db()
    notifications = conn.execute("SELECT * FROM notifications").fetchall()
    conn.close()
    result = []
    for n in notifications:
        item = {"channel": n['channel'], "enabled": bool(n['enabled'])}
        item.update(json.loads(n['config']))
        result.append(item)
    return {"notifications": result}


@router.put("/api/notifications/{channel}")
async def update_notification(channel: str, config: dict):
    conn = get_db()
    c = conn.cursor()
    
    existing = c.execute("SELECT id FROM notifications WHERE channel=?", (channel,)).fetchone()
    if not existing:
        c.execute("INSERT INTO notifications (channel, enabled, config) VALUES (?, ?, ?)",
                  (channel, int(config.get('enabled', False)), json.dumps(config)))
    else:
        c.execute("UPDATE notifications SET enabled=?, config=? WHERE channel=?",
                  (int(config.get('enabled', False)), json.dumps(config), channel))
    
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Web Pages
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: #1e293b;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            width: 100%;
            max-width: 400px;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #3b82f6; font-size: 32px; }
        .logo p { color: #64748b; margin-top: 5px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #94a3b8; margin-bottom: 8px; font-weight: 500; }
        input {
            width: 100%;
            padding: 14px 16px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
        }
        .error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">
            <h1>PyMon</h1>
            <p>Monitoring System</p>
        </div>
        <div class="error" id="error"></div>
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" required autocomplete="current-password">
            </div>
            <button type="submit">Sign In</button>
        </form>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const error = document.getElementById('error');
            try {
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
                    const data = await resp.json();
                    error.textContent = data.detail || 'Login failed';
                    error.style.display = 'block';
                }
            } catch (e) {
                error.textContent = 'Connection error';
                error.style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    return LOGIN_HTML
