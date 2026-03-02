"""Enterprise Server Monitoring Dashboard - Unified Charts"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "pymon.db")


class ServerModel(BaseModel):
    id: int
    name: str
    host: str
    agent_port: int = 9100
    os_type: str
    last_check: Optional[str] = None
    last_status: str = "unknown"
    cpu_percent: float = 0
    memory_percent: float = 0
    disk_percent: float = 0
    network_rx: float = 0
    network_tx: float = 0


class DiskModel(BaseModel):
    mount_point: str
    total: int
    used: int
    free: int
    percent: float
    device: str


class NetworkModel(BaseModel):
    interface: str
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    rx_dropped: int
    tx_dropped: int


class ChartData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]


class MetricData(BaseModel):
    cpu: ChartData
    memory: ChartData
    disk: ChartData
    network: ChartData


@router.get("/api/servers", response_model=List[ServerModel])
def get_servers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT * FROM servers")
        servers = [dict(row) for row in cursor.fetchall()]
        return servers
    finally:
        conn.close()


@router.get("/api/server/{server_id}", response_model=ServerModel)
def get_server(server_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Server not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/api/server/{server_id}/disks", response_model=List[DiskModel])
def get_server_disks(server_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT disk_info FROM servers WHERE id = ?", (server_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Server not found")
        
        disk_info = row[0]
        if not disk_info:
            return []
        
        disks = json.loads(disk_info)
        return [DiskModel(**disk) for disk in disks]
    finally:
        conn.close()


@router.get("/api/server/{server_id}/metrics", response_model=MetricData)
def get_server_metrics(server_id: int, range: str = "1h"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Calculate time range
        from datetime import timedelta
        time_ranges = {
            "5m": "-5 minutes",
            "15m": "-15 minutes",
            "1h": "-1 hour",
            "6h": "-6 hours",
            "24h": "-24 hours",
            "7d": "-7 days"
        }
        
        time_range = time_ranges.get(range, "-1 hour")
        
        # Get metrics history
        cursor = conn.execute(f"""
            SELECT 
                timestamp,
                cpu_percent,
                memory_percent,
                disk_percent,
                network_rx,
                network_tx
            FROM metrics_history 
            WHERE server_id = ? 
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp
        """, (server_id, time_range))
        
        rows = cursor.fetchall()
        if not rows:
            return MetricData(
                cpu = ChartData(labels=[], datasets=[]),
                memory = ChartData(labels=[], datasets=[]),
                disk = ChartData(labels=[], datasets=[]),
                network = ChartData(labels=[], datasets=[])
            )
        
        # Parse data
        labels = [row[0].split("T")[1].split(".")[0].split(":")[0] + ":" + row[0].split("T")[1].split(".")[0].split(":")[1] for row in rows]
        
        cpu_data = [row[1] for row in rows]
        memory_data = [row[2] for row in rows]
        disk_data = [row[3] for row in rows]
        network_rx_data = [row[4] / 1024 / 1024 for row in rows]  # Convert to MB
        network_tx_data = [row[5] / 1024 / 1024 for row in rows]  # Convert to MB
        
        return MetricData(
            cpu = ChartData(
                labels = labels,
                datasets = [{
                    "label": "CPU Usage",
                    "data": cpu_data,
                    "borderColor": "#3fb950",
                    "backgroundColor": "rgba(63,185,80,0.1)",
                    "fill": true,
                    "tension": 0.3
                }]
            ),
            memory = ChartData(
                labels = labels,
                datasets = [{
                    "label": "Memory Usage",
                    "data": memory_data,
                    "borderColor": "#d29922",
                    "backgroundColor": "rgba(210,153,34,0.1)",
                    "fill": true,
                    "tension": 0.3
                }]
            ),
            disk = ChartData(
                labels = labels,
                datasets = [{
                    "label": "Disk Usage",
                    "data": disk_data,
                    "borderColor": "#f85149",
                    "backgroundColor": "rgba(248,81,73,0.1)",
                    "fill": true,
                    "tension": 0.3
                }]
            ),
            network = ChartData(
                labels = labels,
                datasets = [
                    {
                        "label": "Network RX (MB)",
                        "data": network_rx_data,
                        "borderColor": "#58a6ff",
                        "backgroundColor": "rgba(88,166,255,0.1)",
                        "fill": true,
                        "tension": 0.3
                    },
                    {
                        "label": "Network TX (MB)",
                        "data": network_tx_data,
                        "borderColor": "#a371f7",
                        "backgroundColor": "rgba(163,113,247,0.1)",
                        "fill": true,
                        "tension": 0.3
                    }
                ]
            )
        )
    finally:
        conn.close()


@router.get("/api/dashboard/summary")
def get_dashboard_summary():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get online/offline stats
        online = conn.execute("SELECT COUNT(*) FROM servers WHERE last_status = ?", ("up",)).fetchone()[0]
        offline = conn.execute("SELECT COUNT(*) FROM servers WHERE last_status = ?", ("down",)).fetchone()[0]
        total = online + offline
        
        # Get average metrics
        avg_metrics = conn.execute("""
            SELECT 
                AVG(cpu_percent) as avg_cpu,
                AVG(memory_percent) as avg_memory,
                AVG(disk_percent) as avg_disk
            FROM servers
        """).fetchone()
        
        return {
            "online": online,
            "offline": offline,
            "total": total,
            "avg_cpu": avg_metrics[0] if avg_metrics[0] else 0,
            "avg_memory": avg_metrics[1] if avg_metrics[1] else 0,
            "avg_disk": avg_metrics[2] if avg_metrics[2] else 0
        }
    finally:
        conn.close()


@router.get("/api/dashboard/network_summary")
def get_network_summary():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("""
            SELECT 
                SUM(network_rx) as total_rx,
                SUM(network_tx) as total_tx
            FROM servers
        """)
        
        row = cursor.fetchone()
        if not row:
            return {"rx": 0, "tx": 0}
        
        return {
            "rx": row[0] / 1024 / 1024,  # Convert to MB
            "tx": row[1] / 1024 / 1024   # Convert to MB
        }
    finally:
        conn.close()


@router.get("/api/dashboard/metrics")
def get_dashboard_metrics():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get recent metrics for all servers
        cursor = conn.execute("""
            SELECT 
                server_id,
                MAX(cpu_percent) as max_cpu,
                MAX(memory_percent) as max_memory,
                MAX(disk_percent) as max_disk,
                SUM(network_rx) as total_rx,
                SUM(network_tx) as total_tx
            FROM metrics_history 
            WHERE timestamp > datetime('now', '-15 minutes')
            GROUP BY server_id
        """)
        
        metrics = cursor.fetchall()
        if not metrics:
            return {"servers": [], "summary": {"avg_cpu": 0, "avg_memory": 0, "avg_disk": 0}}
        
        # Calculate summary
        avg_cpu = sum(m[1] for m in metrics) / len(metrics) if metrics else 0
        avg_memory = sum(m[2] for m in metrics) / len(metrics) if metrics else 0
        avg_disk = sum(m[3] for m in metrics) / len(metrics) if metrics else 0
        
        return {
            "servers": [{
                "id": m[0],
                "cpu": m[1],
                "memory": m[2],
                "disk": m[3],
                "rx": m[4] / 1024 / 1024,
                "tx": m[5] / 1024 / 1024
            } for m in metrics],
            "summary": {
                "avg_cpu": avg_cpu,
                "avg_memory": avg_memory,
                "avg_disk": avg_disk
            }
        }
    finally:
        conn.close()


@router.get("/api/disks", response_model=List[DiskModel])
def get_all_disks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT id, disk_info FROM servers")
        rows = cursor.fetchall()
        
        all_disks = []
        for row in rows:
            if row[1]:
                disks = json.loads(row[1])
                for disk in disks:
                    disk["server_id"] = row[0]
                    all_disks.append(disk)
        
        return [DiskModel(**disk) for disk in all_disks]
    finally:
        conn.close()


@router.get("/api/networks", response_model=List[NetworkModel])
def get_all_networks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT id, network_rx, network_tx FROM servers")
        rows = cursor.fetchall()
        
        all_networks = []
        for row in rows:
            all_networks.append({
                "server_id": row[0],
                "interface": "eth0",
                "rx_bytes": row[1],
                "tx_bytes": row[2],
                "rx_errors": 0,
                "tx_errors": 0,
                "rx_dropped": 0,
                "tx_dropped": 0
            })
        
        return [NetworkModel(**net) for net in all_networks]
    finally:
        conn.close()


@router.get("/api/dashboard/charts")
def get_dashboard_charts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get recent data for all servers
        cursor = conn.execute("""
            SELECT 
                server_id,
                cpu_percent,
                memory_percent,
                disk_percent,
                network_rx,
                network_tx
            FROM metrics_history 
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp
        """)
        
        rows = cursor.fetchall()
        if not rows:
            return {"cpu": [], "memory": [], "disk": [], "network": []}
        
        # Organize data by server
        data_by_server = {}
        for row in rows:
            server_id = row[0]
            if server_id not in data_by_server:
                data_by_server[server_id] = {
                    "cpu": [],
                    "memory": [],
                    "disk": [],
                    "network_rx": [],
                    "network_tx": []
                }
            
            data_by_server[server_id]["cpu"].append(row[1])
            data_by_server[server_id]["memory"].append(row[2])
            data_by_server[server_id]["disk"].append(row[3])
            data_by_server[server_id]["network_rx"].append(row[4])
            data_by_server[server_id]["network_tx"].append(row[5])
        
        # Calculate averages
        avg_cpu = sum(sum(v["cpu"]) for v in data_by_server.values()) / sum(len(v["cpu"]) for v in data_by_server.values()) if data_by_server else 0
        avg_memory = sum(sum(v["memory"]) for v in data_by_server.values()) / sum(len(v["memory"]) for v in data_by_server.values()) if data_by_server else 0
        avg_disk = sum(sum(v["disk"]) for v in data_by_server.values()) / sum(len(v["disk"]) for v in data_by_server.values()) if data_by_server else 0
        
        return {
            "cpu": avg_cpu,
            "memory": avg_memory,
            "disk": avg_disk,
            "network_rx": sum(sum(v["network_rx"]) for v in data_by_server.values()) / 1024 / 1024,
            "network_tx": sum(sum(v["network_tx"]) for v in data_by_server.values()) / 1024 / 1024
        }
    finally:
        conn.close()


@router.get("/api/dashboard/status")
def get_dashboard_status():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get server counts
        online = conn.execute("SELECT COUNT(*) FROM servers WHERE last_status = ?", ("up",)).fetchone()[0]
        offline = conn.execute("SELECT COUNT(*) FROM servers WHERE last_status = ?", ("down",)).fetchone()[0]
        
        # Get disk usage stats
        cursor = conn.execute("SELECT AVG(disk_percent) as avg_disk, MAX(disk_percent) as max_disk FROM servers")
        disk_stats = cursor.fetchone()
        
        # Get network stats
        cursor = conn.execute("SELECT SUM(network_rx) as total_rx, SUM(network_tx) as total_tx FROM servers")
        network_stats = cursor.fetchone()
        
        return {
            "servers": {
                "online": online,
                "offline": offline,
                "total": online + offline
            },
            "disk": {
                "avg": disk_stats[0] if disk_stats[0] else 0,
                "max": disk_stats[1] if disk_stats[1] else 0
            },
            "network": {
                "rx": network_stats[0] / 1024 / 1024 if network_stats[0] else 0,
                "tx": network_stats[1] / 1024 / 1024 if network_stats[1] else 0
            }
        }
    finally:
        conn.close()


@router.get("/api/dashboard/trend")
def get_dashboard_trend():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get trend data for last 24 hours
        cursor = conn.execute("""
            SELECT 
                strftime('%H', timestamp) as hour,
                AVG(cpu_percent) as avg_cpu,
                AVG(memory_percent) as avg_memory,
                AVG(disk_percent) as avg_disk
            FROM metrics_history 
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """)
        
        rows = cursor.fetchall()
        if not rows:
            return {"hours": [], "cpu": [], "memory": [], "disk": []}
        
        return {
            "hours": [row[0] for row in rows],
            "cpu": [row[1] for row in rows],
            "memory": [row[2] for row in rows],
            "disk": [row[3] for row in rows]
        }
    finally:
        conn.close()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return HTMLResponse("".join([
        "<!DOCTYPE html>",
        "<html lang=\"en\"\u003e",
        "<head>",
        "<meta charset=\"UTF-8\"\u003e",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"\u003e",
        "<title\u003eServer Monitoring Dashboard</title>",
        "<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css\"\u003e",
        "<style\u003e",
        "* { margin: 0; padding: 0; box-sizing: border-box; }",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0e1116; color: #adbac1; line-height: 1.6; }",
        ".app { display: flex; height: 100vh; }",
        ".sidebar { width: 280px; background: #0e1116; border-right: 1px solid #1a1f26; }",
        ".logo { padding: 20px; border-bottom: 1px solid #1a1f26; text-align: center; }",
        ".logo h1 { color: #fff; margin-bottom: 5px; font-size: 24px; }",
        ".logo span { color: #6e7681; font-size: 12px; }",
        ".nav { padding: 20px 0; }",
        ".nav button { display: block; width: 100%; padding: 12px 20px; background: none; border: none; text-align: left; color: #adbac1; cursor: pointer; transition: all 0.2s; }",
        ".nav button:hover { background: #1a1f26; color: #fff; }",
        ".nav button.active { background: #1a1f26; color: #58a6ff; }",
        ".nav i { margin-right: 10px; width: 16px; }",
        ".sidebar-footer { padding: 20px; border-top: 1px solid #1a1f26; }",
        ".main { flex: 1; overflow-y: auto; }",
        ".header { padding: 20px; border-bottom: 1px solid #1a1f26; display: flex; justify-content: space-between; align-items: center; }",
        ".header h2 { color: #fff; font-size: 20px; }",
        ".header-actions { display: flex; gap: 10px; align-items: center; }",
        ".select { padding: 6px 12px; border: 1px solid #1a1f26; background: #0e1116; color: #adbac1; border-radius: 4px; }",
        ".select:focus { outline: none; border-color: #58a6ff; }",
        ".btn { padding: 6px 12px; background: #1a1f26; color: #adbac1; border: 1px solid #1a1f26; border-radius: 4px; cursor: pointer; transition: all 0.2s; }",
        ".btn:hover { background: #2a2f38; color: #fff; }",
        ".btn-secondary { background: #1a1f26; color: #adbac1; }",
        ".btn-secondary:hover { background: #2a2f38; }",
        ".stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 20px; }",
        ".stat-card { background: #1a1f26; border-radius: 8px; padding: 20px; text-align: center; transition: all 0.2s; }",
        ".stat-card:hover { background: #2a2f38; transform: translateY(-2px); }",
        ".stat-icon { font-size: 32px; margin-bottom: 12px; display: inline-block; border-radius: 8px; padding: 8px; }",
        ".stat-value { font-size: 24px; font-weight: bold; margin-bottom: 4px; }",
        ".stat-label { font-size: 14px; color: #6e7681; }",
        ".card { background: #1a1f26; border-radius: 8px; margin: 20px; }",
        ".card-header { padding: 16px 20px; border-bottom: 1px solid #1a1f26; display: flex; justify-content: space-between; align-items: center; }",
        ".card-title { color: #fff; font-size: 16px; }",
        ".card-title i { margin-right: 8px; }",
        ".card-body { padding: 20px; }",
        ".chart-container { height: 300px; position: relative; }",
        ".disk-chart { height: 200px; background: #1a1f26; border-radius: 8px; padding: 16px; margin-bottom: 16px; position: relative; overflow: hidden; }",
        ".disk-used { height: 100%; background: linear-gradient(90deg, #f85149, #ff6b6b); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; transition: width 0.3s ease; }",
        ".network-chart { height: 200px; background: #1a1f26; border-radius: 8px; padding: 16px; margin-bottom: 16px; position: relative; overflow: hidden; }",
        ".network-up { height: 50%; background: linear-gradient(180deg, #58a6ff, #4390ff); border-radius: 4px 4px 0 0; transition: height 0.3s ease; }",
        ".network-down { height: 50%; background: linear-gradient(0deg, #28a745, #20c997); border-radius: 0 0 4px 4px; transition: height 0.3s ease; }",
        ".server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }",
        ".server-card { background: #1a1f26; border-radius: 8px; padding: 16px; border-left: 4px solid #1a1f26; transition: all 0.2s; }",
        ".server-card.online { border-left-color: #28a745; }",
        ".server-card.offline { border-left-color: #dc3545; }",
        ".server-card:hover { background: #2a2f38; transform: translateY(-2px); }",
        ".server-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }",
        ".server-name { font-weight: bold; color: #fff; display: flex; align-items: center; gap: 8px; }",
        ".status-dot { width: 8px; height: 8px; border-radius: 50%; background: #dc3545; }",
        ".server-card.online .status-dot { background: #28a745; }",
        ".metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }",
        ".metric { text-align: center; padding: 8px; background: #2a2f38; border-radius: 4px; }",
        ".metric-label { font-size: 11px; color: #6e7681; margin-bottom: 4px; }",
        ".metric-value { font-size: 14px; font-weight: bold; color: #fff; }",
        ".disk-info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #6e7681; }",
        ".disk-info .disk-label { font-weight: 600; color: #fff; }",
        ".disk-info .disk-percent { font-weight: 600; }",
        ".network-info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #6e7681; }",
        ".network-info .network-label { font-weight: 600; color: #fff; }",
        ".network-info .network-value { font-weight: 600; }",
        ".empty-state { text-align: center; padding: 60px 20px; color: #6e7681; }",
        ".empty-state i { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }",
        ".hidden { display: none !important; }",
        ".view { }",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"app\"\u003e",
        "<aside class=\"sidebar\"\u003e",
        "<div class=\"logo\"\u003e",
        "<h1><i class=\"fas fa-chart-line\"\u003e</i> PyMon</h1>",
        "<span\u003eServer Monitoring</span>",
        "</div>",
        "<nav class=\"nav\"\u003e",
        "<button class=\"nav-item active\" onclick=\"loadDashboard()\"\u003e<i class=\"fas fa-th-large\"\u003e</i> Dashboard</button>",
        "<button class=\"nav-item\" onclick=\"loadServers()\"\u003e<i class=\"fas fa-server\"\u003e</i> Servers</button>",
        "<button class=\"nav-item\" onclick=\"loadAlerts()\"\u003e<i class=\"fas fa-bell\"\u003e</i> Alerts</button>",
        "<button class=\"nav-item\" onclick=\"loadSettings()\"\u003e<i class=\"fas fa-cog\"\u003e</i> Settings</button>",
        "</nav>",
        "<div class=\"sidebar-footer\"\u003e",
        "<button class=\"btn btn-secondary btn-sm\" onclick=\"logout()\" style=\"width: 100%;\"\u003e<i class=\"fas fa-sign-out-alt\"\u003e</i> Logout</button>",
        "</div>",
        "</aside>",
        "<main class=\"main\"\u003e",
        "<div id=\"view-dashboard\" class=\"view\"\u003e",
        "<div class=\"header\"\u003e",
        "<h2\u003eDashboard</h2>",
        "<div class=\"header-actions\"\u003e",
        "<select id=\"timeRange\" class=\"form-control\" style=\"width: auto;\" onchange=\"loadDashboard()\"\u003e",
        "<option value=\"5m\"\u003eLast 5 minutes</option>",
        "<option value=\"15m\"\u003eLast 15 minutes</option>",
        "<option value=\"1h\" selected\u003eLast 1 hour</option>",
        "<option value=\"6h\"\u003eLast 6 hours</option>",
        "<option value=\"24h\"\u003eLast 24 hours</option>",
        "</select>",
        "<button class=\"btn btn-secondary\" onclick=\"loadDashboard()\"\u003e<i class=\"fas fa-sync\"\u003e</i> Refresh</button>",
        "</div>",
        "</div>",
        "<div class=\"stats-grid\"\u003e",
        "<div class=\"stat-card\" onclick=\"loadServers()\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(63,185,80,0.2); color: var(--success);\"\u003e<i class=\"fas fa-check-circle\"\u003e</i></div>",
        "<div><div class=\"stat-value text-success\" id=\"stat-online\"\u003e0</div><div class=\"stat-label\"\u003eOnline</div></div>",
        "</div>",
        "<div class=\"stat-card\" onclick=\"loadServers()\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(248,81,73,0.2); color: var(--danger);\"\u003e<i class=\"fas fa-times-circle\"\u003e</i></div>",
        "<div><div class=\"stat-value text-danger\" id=\"stat-offline\"\u003e0</div><div class=\"stat-label\"\u003eOffline</div></div>",
        "</div>",
        "<div class=\"stat-card\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(88,166,255,0.2); color: var(--accent);\"\u003e<i class=\"fas fa-microchip\"\u003e</i></div>",
        "<div><div class=\"stat-value\" id=\"stat-cpu\"\u003e0%</div><div class=\"stat-label\"\u003eAvg CPU</div></div>",
        "</div>",
        "<div class=\"stat-card\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(210,153,34,0.2); color: var(--warning);\"\u003e<i class=\"fas fa-memory\"\u003e</i></div>",
        "<div><div class=\"stat-value\" id=\"stat-mem\"\u003e0%</div><div class=\"stat-label\"\u003eAvg Memory</div></div>",
        "</div>",
        "<div class=\"stat-card\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(210,153,34,0.2); color: var(--warning);\"\u003e<i class=\"fas fa-hdd\"\u003e</i></div>",
        "<div><div class=\"stat-value\" id=\"stat-disk\"\u003e0%</div><div class=\"stat-label\"\u003eAvg Disk</div></div>",
        "</div>",
        "<div class=\"stat-card\"\u003e",
        "<div class=\"stat-icon\" style=\"background: rgba(88,166,255,0.2); color: var(--accent);\"\u003e<i class=\"fas fa-network-wired\"\u003e</i></div>",
        "<div><div class=\"stat-value\" id=\"stat-net\"\u003e0/0 MB</div><div class=\"stat-label\"\u003eNetwork</div></div>",
        "</div>",
        "</div>",
        "<div class=\"grid-2\" id=\"charts-container\"\u003e</div>",
        "<div class=\"card\"\u003e",
        "<div class=\"card-header\"\u003e<span class=\"card-title\"><i class=\"fas fa-server\"\u003e</i> Servers</span></div>",
        "<div class=\"card-body\"\u003e",
        "<div class=\"server-grid\" id=\"server-grid\"\u003e</div>",
        "</div>",
        "</div>",
        "</div>",
        "<main>",
        "<div id=\"view-servers\" class=\"view hidden\"\u003e",
        "<div class=\"header\"\u003e",
        "<h2\u003eServers</h2>",
        "<button class=\"btn btn-primary\" onclick=\"loadServers()\"\u003e<i class=\"fas fa-sync\"\u003e</i> Refresh</button>",
        "</div>",
        "<div class=\"card\"\u003e",
        "<div class=\"card-body\" style=\"padding: 0;\"\u003e",
        "<table id=\"servers-table\" class=\"table\"\u003e",
        "<thead\u003e",
        "<tr\u003e",
        "<th\u003eStatus</th>",
        "<th>Name</th>",
        "<th>Host</th>",
        "<th>OS</th>",
        "<th>CPU</th>",
        "<th>Memory</th>",
        "<th>Disk</th>",
        "<th>Network</th>",
        "<th>Last Check</th>",
        "<th>Actions</th>",
        "</tr>",
        "</thead>",
        "<tbody\u003e</tbody>",
        "</table>",
        "</div>",
        "</div>",
        "<div id=\"view-alerts\" class=\"view hidden\"\u003e",
        "<div class=\"header\"\u003e",
        "<h2\u003eAlerts</h2>",
        "</div>",
        "<div class=\"card\"\u003e",
        "<div class=\"card-body\"\u003e<i class=\"fas fa-bell\"\u003e</i> Alert system</div>",
        "</div>",
        "<div id=\"view-settings\" class=\"view hidden\"\u003e",
        "<div class=\"header\"\u003e",
        "<h2\u003eSettings</h2>",
        "</div>",
        "<div class=\"card\"\u003e",
        "<div class=\"card-body\"\u003e<i class=\"fas fa-cog\"\u003e</i> Settings</div>",
        "</div>",
        "<script>",
        "</script>",
        "</body>",
        "</html>"
    ])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(router, host="0.0.0.0", port=8080)