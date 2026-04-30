"""Simple Dashboard without complex charts"""

import os
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List


router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "pymon.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


SIMPLE_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Simple Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        
        .header { background: #16213e; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #0f3460; }
        .logo { font-size: 24px; font-weight: bold; color: #00d4ff; }
        .user-info { color: #888; font-size: 14px; }
        
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; padding: 20px; }
        .stat { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 36px; font-weight: bold; }
        .stat-label { color: #888; margin-top: 5px; }
        .online { color: #00ff88; }
        .offline { color: #ff4444; }
        
        .container { padding: 20px; }
        .section-title { font-size: 20px; margin-bottom: 15px; color: #00d4ff; }
        
        .server-list { display: grid; gap: 10px; }
        .server-card { background: #16213e; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .server-name { font-weight: bold; font-size: 16px; }
        .server-host { color: #888; font-size: 12px; }
        .server-status { padding: 5px 15px; border-radius: 20px; font-size: 12px; }
        .status-up { background: #00ff88; color: #000; }
        .status-down { background: #ff4444; color: #fff; }
        
        .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 10px; }
        .metric { background: #0f3460; padding: 10px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 20px; font-weight: bold; }
        .metric-label { font-size: 11px; color: #888; }
        
        .add-form { background: #16213e; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .add-form input, .add-form select { padding: 10px; margin: 5px; border-radius: 5px; border: none; background: #0f3460; color: #fff; }
        .add-form button { padding: 10px 20px; background: #00d4ff; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        
        .error { background: #ff4444; color: white; padding: 10px; border-radius: 5px; margin: 10px; }
        .no-data { color: #888; text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">📊 PyMon</div>
        <div class="user-info">Admin | <a href="/logout" style="color:#00d4ff;">Logout</a></div>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value online" id="onlineCount">0</div>
            <div class="stat-label">Online</div>
        </div>
        <div class="stat">
            <div class="stat-value offline" id="offlineCount">0</div>
            <div class="stat-label">Offline</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="cpuAvg">0%</div>
            <div class="stat-label">Avg CPU</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="memAvg">0%</div>
            <div class="stat-label">Avg Memory</div>
        </div>
    </div>
    
    <div class="container">
        <div class="section-title">Servers</div>
        <div id="serverList">
            <div class="no-data">No servers added yet. Add one below.</div>
        </div>
        
        <div class="add-form">
            <div class="section-title">Add New Server</div>
            <input type="text" id="serverName" placeholder="Server Name">
            <input type="text" id="serverHost" placeholder="Host:Port (e.g. 192.168.1.1:9182)">
            <select id="serverOs">
                <option value="windows">Windows</option>
                <option value="linux">Linux</option>
            </select>
            <button onclick="addServer()">Add Server</button>
        </div>
    </div>

    <script>
        let token = localStorage.getItem('token');
        
        if (!token) {
            window.location.href = '/login';
        }
        
        async function loadData() {
            try {
                const resp = await fetch('/api/v1/servers', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                
                if (resp.status === 401) {
                    localStorage.removeItem('token');
                    window.location.href = '/login';
                    return;
                }
                
                const data = await resp.json();
                const servers = data.servers || [];
                
                // Update stats
                const online = servers.filter(s => s.last_status === 'up').length;
                const offline = servers.length - online;
                
                document.getElementById('onlineCount').textContent = online;
                document.getElementById('offlineCount').textContent = offline;
                
                if (servers.length > 0) {
                    const cpu = servers.reduce((a, s) => a + (s.cpu_percent || 0), 0) / servers.length;
                    const mem = servers.reduce((a, s) => a + (s.memory_percent || 0), 0) / servers.length;
                    document.getElementById('cpuAvg').textContent = cpu.toFixed(1) + '%';
                    document.getElementById('memAvg').textContent = mem.toFixed(1) + '%';
                }
                
                // Render servers
                const list = document.getElementById('serverList');
                if (servers.length === 0) {
                    list.innerHTML = '<div class="no-data">No servers added yet. Add one below.</div>';
                } else {
                    list.innerHTML = servers.map(s => `
                        <div class="server-card">
                            <div>
                                <div class="server-name">${s.name}</div>
                                <div class="server-host">${s.host}:${s.agent_port} (${s.os_type})</div>
                            </div>
                            <div>
                                <div class="metrics">
                                    <div class="metric">
                                        <div class="metric-value">${(s.cpu_percent || 0).toFixed(1)}%</div>
                                        <div class="metric-label">CPU</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">${(s.memory_percent || 0).toFixed(1)}%</div>
                                        <div class="metric-label">MEM</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">${(s.disk_percent || 0).toFixed(1)}%</div>
                                        <div class="metric-label">DISK</div>
                                    </div>
                                </div>
                                <div style="text-align:center;margin-top:10px;">
                                    <span class="server-status ${s.last_status === 'up' ? 'status-up' : 'status-down'}">${s.last_status || 'unknown'}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }
            } catch(e) {
                console.error(e);
            }
        }
        
        async function addServer() {
            const name = document.getElementById('serverName').value;
            const host = document.getElementById('serverHost').value;
            const os = document.getElementById('serverOs').value;
            
            if (!name || !host) {
                alert('Please fill all fields');
                return;
            }
            
            const [hostPart, port] = host.split(':');
            const agentPort = port ? parseInt(port) : (os === 'windows' ? 9182 : 9100);
            
            try {
                const resp = await fetch('/api/v1/servers', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: name,
                        host: hostPart,
                        os_type: os,
                        agent_port: agentPort
                    })
                });
                
                if (resp.ok) {
                    document.getElementById('serverName').value = '';
                    document.getElementById('serverHost').value = '';
                    loadData();
                } else {
                    alert('Failed to add server');
                }
            } catch(e) {
                alert('Error: ' + e);
            }
        }
        
        loadData();
        setInterval(loadData, 10000);
    </script>
</body>
</html>"""


@router.get("/dashboard-simple")
async def dashboard_simple():
    return HTMLResponse(content=SIMPLE_DASHBOARD_HTML)


@router.get("/")
async def root():
    return HTMLResponse(content=SIMPLE_DASHBOARD_HTML)


class ServerCreate(BaseModel):
    name: str
    host: str
    os_type: str = "windows"
    agent_port: int = 9180


@router.post("/api/v1/servers", tags=["servers"])
async def create_server_simple(data: ServerCreate):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO servers (name, host, os_type, agent_port, enabled, created_at, last_status) 
           VALUES (?, ?, ?, ?, 1, ?, 'unknown')""",
        (data.name, data.host, data.os_type, data.agent_port, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    server_id = c.lastrowid
    conn.close()
    return {"status": "ok", "server_id": server_id}
