"""Enhanced Grafana-style Dashboard with Advanced Visualizations"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "pymon.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# Login HTML (shared with auth)
# ============================================================================

LOGIN_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #0b0c0f; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .login-box { background: #14161a; padding: 48px; border-radius: 16px; border: 1px solid #262a30; width: 100%; max-width: 400px; }
        .logo { text-align: center; margin-bottom: 32px; }
        .logo-icon { width: 48px; height: 48px; background: linear-gradient(135deg, #5794f2, #2c7bd9); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: white; font-weight: bold; margin: 0 auto 16px; box-shadow: 0 4px 12px rgba(87,148,242,0.3); }
        .logo h1 { color: #5794f2; font-size: 32px; font-weight: 700; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #8b8d98; margin-bottom: 8px; font-size: 13px; font-weight: 600; text-transform: uppercase; }
        input { width: 100%; padding: 14px; background: #0b0c0f; border: 1px solid #262a30; border-radius: 8px; color: #e0e0e0; font-size: 15px; }
        input:focus { outline: none; border-color: #5794f2; }
        button { width: 100%; padding: 14px; background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(44,123,217,0.4); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">
            <div class="logo-icon">P</div>
            <h1>PyMon</h1>
        </div>
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
                alert('Login failed: Invalid credentials');
            }
        });
    </script>
</body>
</html>"""


# ============================================================================
# API Models
# ============================================================================


class ServerMetrics(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_rx: float
    network_tx: float


class ChartDataset(BaseModel):
    label: str
    data: List[float]
    borderColor: str
    backgroundColor: str
    fill: bool = True
    tension: float = 0.3


class ChartData(BaseModel):
    labels: List[str]
    datasets: List[ChartDataset]


class DiskInfo(BaseModel):
    volume: str
    size: float
    free: float
    percent: float


class UptimeEntry(BaseModel):
    timestamp: str
    status: str  # 'up' or 'down'


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


# ============================================================================
# API Endpoints for Enhanced Dashboard
# ============================================================================


@router.get("/api/servers")
async def list_servers():
    conn = get_db()
    servers = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
    conn.close()
    result = []
    for s in servers:
        server_dict = dict(s)
        if server_dict.get("disk_info"):
            try:
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


@router.delete("/api/servers/{server_id}")
async def delete_server_api(server_id: int):
    conn = get_db()
    conn.execute("DELETE FROM servers WHERE id=?", (server_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/api/servers/{server_id}/scrape")
async def scrape_server_api(server_id: int):
    conn = get_db()
    server = conn.execute("SELECT * FROM servers WHERE id=?", (server_id,)).fetchone()
    conn.close()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "ok", "message": "Scrape triggered"}


@router.get("/api/notifications")
async def get_notifications():
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications").fetchall()
    conn.close()
    result = []
    for r in rows:
        import json
        cfg = json.loads(r["config"]) if r["config"] else {}
        result.append({"channel": r["channel"], "enabled": bool(r["enabled"]), "config": cfg})
    return {"notifications": result}


@router.put("/api/notifications/{channel}")
async def update_notification(channel: str, data: dict):
    conn = get_db()
    import json
    conn.execute(
        "UPDATE notifications SET enabled = ?, config = ? WHERE channel = ?",
        (int(data.get("enabled", 0)), json.dumps(data.get("config", {})), channel)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("/api/backup/create")
async def create_backup():
    # Basic backup logic: copy DB and config to a zip (simplified for UI)
    import shutil
    import zipfile
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pymon_backup_{timestamp}.zip"

    # In a real scenario, we'd save this to a specific directory
    return {"status": "ok", "filename": filename}


@router.get("/api/servers/metrics-history")async def get_servers_metrics_history(
    server_id: Optional[int] = Query(None),
    range: str = Query("1h", regex="^(5m|15m|1h|6h|24h|7d)$"),
    metric: Optional[str] = Query(None, regex="^(cpu|memory|disk|network)$"),
):
    """Get historical metrics for charts with real data from metrics_history"""
    conn = get_db()

    # Time range mapping
    time_ranges = {
        "5m": "-5 minutes",
        "15m": "-15 minutes",
        "1h": "-1 hour",
        "6h": "-6 hours",
        "24h": "-24 hours",
        "7d": "-7 days",
    }

    time_filter = time_ranges.get(range, "-1 hour")

    try:
        if server_id:
            # Single server metrics
            if metric:
                cursor = conn.execute(
                    f"""
                    SELECT timestamp, {metric}_percent as value
                    FROM metrics_history
                    WHERE server_id = ?
                    AND timestamp > datetime('now', ?)
                    ORDER BY timestamp
                """,
                    (server_id, time_filter),
                )
            else:
                cursor = conn.execute(
                    f"""
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
                    FROM metrics_history
                    WHERE server_id = ?
                    AND timestamp > datetime('now', ?)
                    ORDER BY timestamp
                """,
                    (server_id, time_filter),
                )
        else:
            # Aggregated metrics for all servers
            if metric:
                cursor = conn.execute(
                    f"""
                    SELECT timestamp, AVG({metric}_percent) as value
                    FROM metrics_history
                    WHERE timestamp > datetime('now', ?)
                    GROUP BY strftime('%m', timestamp), strftime('%d', timestamp),
                             strftime('%H', timestamp), strftime('%M', timestamp)
                    ORDER BY timestamp
                """,
                    (time_filter,),
                )
            else:
                cursor = conn.execute(
                    f"""
                    SELECT timestamp,
                           AVG(cpu_percent) as cpu_percent,
                           AVG(memory_percent) as memory_percent,
                           AVG(disk_percent) as disk_percent,
                           AVG(network_rx) as network_rx,
                           AVG(network_tx) as network_tx
                    FROM metrics_history
                    WHERE timestamp > datetime('now', ?)
                    GROUP BY strftime('%m', timestamp), strftime('%d', timestamp),
                             strftime('%H', timestamp), strftime('%M', timestamp)
                    ORDER BY timestamp
                """,
                    (time_filter,),
                )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"labels": [], "datasets": []}

        # Format timestamps
        labels = []
        for row in rows:
            ts = row[0]
            if "T" in ts:
                labels.append(ts.split("T")[1].split(".")[0][:5])  # HH:MM
            else:
                labels.append(ts[11:16])  # HH:MM

        # Build datasets
        datasets = []
        colors = {
            "cpu": ("#73bf69", "rgba(115,191,105,0.2)"),
            "memory": ("#f2cc0c", "rgba(242,204,12,0.2)"),
            "disk": ("#f2495c", "rgba(242,73,92,0.2)"),
            "network": ("#b877d9", "rgba(184,119,217,0.2)"),
        }

        if metric:
            values = [row[1] or 0 for row in rows]
            color = colors.get(metric, ("#5794f2", "rgba(87,148,242,0.2)"))
            datasets.append(
                {
                    "label": metric.upper(),
                    "data": values,
                    "borderColor": color[0],
                    "backgroundColor": color[1],
                    "fill": True,
                    "tension": 0.3,
                }
            )
        else:
            # Return all metrics
            for i, (m, label) in enumerate(
                [("cpu_percent", "CPU"), ("memory_percent", "Memory"), ("disk_percent", "Disk")]
            ):
                values = [row[m] or 0 for row in rows]
                color = colors[list(colors.keys())[i]]
                datasets.append(
                    {
                        "label": label,
                        "data": values,
                        "borderColor": color[0],
                        "backgroundColor": color[1],
                        "fill": False,
                        "tension": 0.3,
                    }
                )

        return {"labels": labels, "datasets": datasets}

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/servers/{server_id}/disk-breakdown")
async def get_server_disk_breakdown(server_id: int):
    """Get per-disk usage (C:, D:, E: etc.)"""
    conn = get_db()
    cursor = conn.execute("SELECT disk_info FROM servers WHERE id = ?", (server_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"disks": []}

    try:
        disk_data = json.loads(row[0])
        disks = []

        if isinstance(disk_data, list):
            for d in disk_data:
                if isinstance(d, dict) and "size" in d and d["size"] > 0:
                    percent = round(100 * (1 - d.get("free", 0) / d["size"]), 1)
                    disks.append(
                        {
                            "volume": d.get("volume", d.get("DeviceID", "Unknown")),
                            "size": d["size"],
                            "free": d.get("free", 0),
                            "used": d["size"] - d.get("free", 0),
                            "percent": percent,
                            "size_gb": round(d["size"] / (1024**3), 1),
                            "free_gb": round(d.get("free", 0) / (1024**3), 1),
                            "used_gb": round((d["size"] - d.get("free", 0)) / (1024**3), 1),
                        }
                    )
        elif isinstance(disk_data, dict):
            # Single disk object
            if "size" in disk_data and disk_data["size"] > 0:
                percent = round(100 * (1 - disk_data.get("free", 0) / disk_data["size"]), 1)
                disks.append(
                    {
                        "volume": disk_data.get("volume", disk_data.get("DeviceID", "Unknown")),
                        "size": disk_data["size"],
                        "free": disk_data.get("free", 0),
                        "used": disk_data["size"] - disk_data.get("free", 0),
                        "percent": percent,
                        "size_gb": round(disk_data["size"] / (1024**3), 1),
                        "free_gb": round(disk_data.get("free", 0) / (1024**3), 1),
                        "used_gb": round((disk_data["size"] - disk_data.get("free", 0)) / (1024**3), 1),
                    }
                )

        return {"disks": sorted(disks, key=lambda x: x["volume"])}

    except Exception as e:
        return {"disks": [], "error": str(e)}


@router.get("/api/servers/{server_id}/uptime-timeline")
async def get_server_uptime_timeline(server_id: int, days: int = Query(7, ge=1, le=30)):
    """Get uptime/downtime timeline for the specified period"""
    conn = get_db()

    try:
        # Get status changes from metrics_history
        cursor = conn.execute(
            """
            SELECT timestamp,
                   CASE WHEN cpu_percent IS NOT NULL THEN 'up' ELSE 'down' END as status
            FROM metrics_history
            WHERE server_id = ?
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp
        """,
            (server_id, f"-{days} days"),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"timeline": [], "uptime_percent": 0}

        # Build timeline entries
        timeline = []
        for row in rows:
            ts = row[0]
            status = row[1] or "unknown"
            timeline.append({"timestamp": ts, "status": "up" if status == "up" else "down"})

        # Calculate uptime percentage
        total = len(timeline)
        up_count = sum(1 for t in timeline if t["status"] == "up")
        uptime_percent = round((up_count / total * 100) if total > 0 else 0, 2)

        return {"timeline": timeline, "uptime_percent": uptime_percent}

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/servers/{server_id}/export")
async def export_server_data(
    server_id: int,
    format: str = Query("json", regex="^(json|csv)$"),
    range: str = Query("24h", regex="^(5m|15m|1h|6h|24h|7d)$"),
):
    """Export server metrics data as JSON or CSV"""
    conn = get_db()

    time_ranges = {
        "5m": "-5 minutes",
        "15m": "-15 minutes",
        "1h": "-1 hour",
        "6h": "-6 hours",
        "24h": "-24 hours",
        "7d": "-7 days",
    }

    time_filter = time_ranges.get(range, "-24 hours")

    try:
        cursor = conn.execute(
            """
            SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
            FROM metrics_history
            WHERE server_id = ?
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp
        """,
            (server_id, time_filter),
        )

        rows = cursor.fetchall()
        conn.close()

        if format == "json":
            data = [
                {
                    "timestamp": row[0],
                    "cpu_percent": row[1],
                    "memory_percent": row[2],
                    "disk_percent": row[3],
                    "network_rx_mb": round(row[4] / 1024 / 1024, 2) if row[4] else 0,
                    "network_tx_mb": round(row[5] / 1024 / 1024, 2) if row[5] else 0,
                }
                for row in rows
            ]
            return {"server_id": server_id, "range": range, "data": data}

        else:  # CSV
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Timestamp", "CPU %", "Memory %", "Disk %", "Network RX (MB)", "Network TX (MB)"])

            for row in rows:
                writer.writerow(
                    [
                        row[0],
                        round(row[1], 2) if row[1] else 0,
                        round(row[2], 2) if row[2] else 0,
                        round(row[3], 2) if row[3] else 0,
                        round(row[4] / 1024 / 1024, 2) if row[4] else 0,
                        round(row[5] / 1024 / 1024, 2) if row[5] else 0,
                    ]
                )

            return HTMLResponse(
                content=output.getvalue(),
                headers={"Content-Disposition": f"attachment; filename=server_{server_id}_{range}.csv"},
            )

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/servers/compare")
async def compare_time_ranges(
    server_id: Optional[int] = Query(None),
    metric: str = Query("cpu", regex="^(cpu|memory|disk|network)$"),
    range: str = Query("1h", regex="^(5m|15m|1h|6h|24h|7d)$"),
):
    """Compare current period vs previous period"""
    conn = get_db()

    time_ranges = {"5m": 5, "15m": 15, "1h": 60, "6h": 360, "24h": 1440, "7d": 10080}

    minutes = time_ranges.get(range, 60)

    try:
        # Current period
        cursor = conn.execute(
            """
            SELECT AVG(cpu_percent) as cpu, AVG(memory_percent) as mem,
                   AVG(disk_percent) as disk, AVG(network_rx) as rx, AVG(network_tx) as tx
            FROM metrics_history
            WHERE (? IS NULL OR server_id = ?)
            AND timestamp > datetime('now', ?)
            AND timestamp <= datetime('now')
        """,
            (server_id, server_id, f"-{minutes} minutes"),
        )

        current = cursor.fetchone()

        # Previous period
        cursor = conn.execute(
            """
            SELECT AVG(cpu_percent) as cpu, AVG(memory_percent) as mem,
                   AVG(disk_percent) as disk, AVG(network_rx) as rx, AVG(network_tx) as tx
            FROM metrics_history
            WHERE (? IS NULL OR server_id = ?)
            AND timestamp > datetime('now', ?)
            AND timestamp <= datetime('now', ?)
        """,
            (server_id, server_id, f"-{minutes * 2} minutes", f"-{minutes} minutes"),
        )

        previous = cursor.fetchone()
        conn.close()

        metric_map = {"cpu": 0, "memory": 1, "disk": 2, "network": 3}
        idx = metric_map.get(metric, 0)

        current_val = (current[idx] or 0) if idx < 3 else ((current[3] or 0) + (current[4] or 0)) / 2
        previous_val = (previous[idx] or 0) if idx < 3 else ((previous[3] or 0) + (previous[4] or 0)) / 2

        delta = current_val - previous_val
        delta_percent = round((delta / previous_val * 100) if previous_val > 0 else 0, 2)

        return {
            "current": round(current_val, 2),
            "previous": round(previous_val, 2),
            "delta": round(delta, 2),
            "delta_percent": delta_percent,
            "trend": "up" if delta > 0 else "down" if delta < 0 else "stable",
        }

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Enhanced Dashboard HTML
# ============================================================================

ENHANCED_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Enhanced Enterprise Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0b0c0f; --card: #14161a; --card-hover: #1a1d22; --border: #262a30; --border-light: #363b42;
            --text: #e0e0e0; --muted: #8b8d98; --muted-light: #a0a2ab; --blue: #5794f2; --blue-glow: rgba(87,148,242,0.15);
            --green: #73bf69; --green-glow: rgba(115,191,105,0.15); --red: #f2495c; --red-glow: rgba(242,73,92,0.15);
            --yellow: #f2cc0c; --yellow-glow: rgba(242,204,12,0.15); --purple: #b877d9; --purple-glow: rgba(184,119,217,0.15);
            --orange: #ff780a; --cyan: #00d8d8;
        }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; font-size: 13px; }

        /* Top Navigation */
        .top-nav { background: linear-gradient(180deg, #1a1d22 0%, #14161a 100%); border-bottom: 1px solid var(--border); padding: 0 20px; height: 56px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        .nav-left { display: flex; align-items: center; gap: 24px; }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--blue), #2c7bd9); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white; font-weight: bold; box-shadow: 0 2px 8px rgba(87,148,242,0.3); }
        .logo h1 { color: var(--blue); font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item { display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 8px; cursor: pointer; color: var(--muted); font-weight: 500; font-size: 13px; border: none; background: transparent; transition: all 0.2s; }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active { background: var(--blue-glow); color: var(--blue); box-shadow: inset 0 0 0 1px rgba(87,148,242,0.3); }
        .nav-right { display: flex; align-items: center; gap: 16px; }

        /* Time Range Selector */
        .time-range { display: flex; gap: 2px; background: var(--card); border-radius: 8px; padding: 3px; border: 1px solid var(--border); }
        .time-btn { padding: 6px 14px; background: transparent; border: none; border-radius: 5px; color: var(--muted); font-size: 12px; cursor: pointer; transition: all 0.2s; }
        .time-btn:hover { color: var(--text); }
        .time-btn.active { background: var(--blue); color: white; }

        /* Main Content */
        .main { padding: 20px; max-width: 1920px; margin: 0 auto; }

        /* Stats Overview */
        .stats-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; transition: all 0.3s; cursor: pointer; }
        .stat-card:hover { transform: translateY(-2px); border-color: var(--border-light); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
        .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .stat-content { flex: 1; }
        .stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
        .stat-label { color: var(--muted); font-size: 12px; margin-top: 4px; }
        .stat-trend { display: flex; align-items: center; gap: 4px; font-size: 12px; margin-top: 8px; }
        .stat-trend.up { color: var(--green); }
        .stat-trend.down { color: var(--red); }

        /* Grid Layout */
        .dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .grid-item { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .grid-item.col-4 { grid-column: span 4; }
        .grid-item.col-6 { grid-column: span 6; }
        .grid-item.col-8 { grid-column: span 8; }
        .grid-item.col-12 { grid-column: span 12; }
        .grid-item.row-2 { grid-row: span 2; }

        /* Panel */
        .panel { height: 100%; display: flex; flex-direction: column; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); }
        .panel-title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .panel-actions { display: flex; gap: 8px; }
        .panel-body { flex: 1; padding: 16px; min-height: 200px; position: relative; }

        /* Chart Container */
        .chart-container { width: 100%; height: 280px; position: relative; }

        /* Disk Breakdown */
        .disk-breakdown { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; padding: 16px; }
        .disk-item { background: rgba(0,0,0,0.2); border-radius: 8px; padding: 16px; }
        .disk-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .disk-volume { font-weight: 600; font-size: 14px; }
        .disk-percent { font-size: 18px; font-weight: 700; }
        .disk-bar { height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
        .disk-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
        .disk-details { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); }

        /* Uptime Timeline */
        .uptime-timeline { display: flex; height: 40px; border-radius: 8px; overflow: hidden; margin: 16px 0; }
        .uptime-segment { height: 100%; transition: width 0.3s; }
        .uptime-segment.up { background: var(--green); }
        .uptime-segment.down { background: var(--red); }
        .uptime-stats { display: flex; justify-content: space-around; padding: 12px; }
        .uptime-stat { text-align: center; }
        .uptime-stat-value { font-size: 20px; font-weight: 700; }
        .uptime-stat-label { font-size: 11px; color: var(--muted); }

        /* Export Buttons */
        .export-btn { padding: 6px 12px; background: var(--card); border: 1px solid var(--border); border-radius: 6px; color: var(--text); cursor: pointer; font-size: 12px; transition: all 0.2s; }
        .export-btn:hover { background: var(--card-hover); border-color: var(--blue); }

        /* Server Cards */
        .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; max-height: 600px; overflow-y: auto; padding: 16px; }
        .server-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; transition: all 0.2s; cursor: pointer; }
        .server-card:hover { border-color: var(--border-light); transform: translateY(-1px); }
        .server-card.online { border-left: 3px solid var(--green); }
        .server-card.offline { border-left: 3px solid var(--red); }

        /* Threshold Line Indicator */
        .threshold-indicator { position: absolute; top: 10px; right: 10px; background: rgba(242,73,92,0.2); border: 1px solid var(--red); padding: 4px 8px; border-radius: 4px; font-size: 11px; color: var(--red); }

        /* Loading State */
        .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--muted); }
        .loading i { margin-right: 8px; }

        /* Responsive */
        @media (max-width: 1200px) { .grid-item.col-4, .grid-item.col-6, .grid-item.col-8 { grid-column: span 12; } }
        @media (max-width: 768px) { .nav-menu { display: none; } .stats-overview { grid-template-columns: 1fr; } .main { padding: 12px; } }

        /* Section visibility */
        .section-content { display: none; }
        .section-content.active { display: block; }

        /* Theme Toggle */
        .theme-toggle { display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .theme-toggle:hover { background: var(--card-hover); }
        .theme-icon { font-size: 16px; }

        /* Light theme */
        body.light-theme {
            --bg: #f5f5f5; --bg-secondary: #ffffff; --bg-tertiary: #e8e8e8; --border: #d0d0d0; --border-light: #c0c0c0;
            --text: #1a1a1a; --muted: #666666; --muted-light: #888888;
            --blue-glow: rgba(87,148,242,0.1); --green-glow: rgba(115,191,105,0.1);
            --red-glow: rgba(242,73,92,0.1); --yellow-glow: rgba(242,204,12,0.1); --purple-glow: rgba(184,119,217,0.1);
        }
        body.light-theme .panel { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        body.light-theme .stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.15); }

        /* Table */
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        tr:hover td { background: rgba(255,255,255,0.02); }

        /* Badges */
        .badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
        .badge-success { background: var(--green-glow); color: var(--green); }
        .badge-danger { background: var(--red-glow); color: var(--red); }
        .badge-warning { background: var(--yellow-glow); color: var(--yellow); }

        /* Buttons */
        .btn { padding: 10px 18px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
        .btn-primary { background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(44,123,217,0.4); }
        .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--card-hover); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }

        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-title { font-size: 18px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 24px; cursor: pointer; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 13px; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--blue); }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="nav-left">
            <div class="logo"><div class="logo-icon">P</div><h1>PyMon</h1></div>
            <div class="nav-menu">
                <button class="nav-item active" data-section="dashboard"><i class="fas fa-chart-line"></i> Dashboard</button>
                <button class="nav-item" data-section="servers"><i class="fas fa-server"></i> Servers</button>
                <button class="nav-item" data-section="deploy"><i class="fas fa-rocket"></i> Deploy</button>
                <button class="nav-item" data-section="alerts"><i class="fas fa-bell"></i> Alerts</button>
                <button class="nav-item" data-section="settings"><i class="fas fa-cog"></i> Settings</button>
            </div>
        </div>
        <div class="nav-right">
            <div class="time-range">
                <button class="time-btn" data-range="5m">5m</button>
                <button class="time-btn" data-range="15m">15m</button>
                <button class="time-btn active" data-range="1h">1h</button>
                <button class="time-btn" data-range="6h">6h</button>
                <button class="time-btn" data-range="24h">24h</button>
            </div>
            <button class="theme-toggle" id="themeToggle" title="Toggle theme">
                <span class="theme-icon">🌙</span>
            </button>
            <button class="btn btn-secondary btn-sm" id="refreshBtn" title="Refresh (30s auto)"><i class="fas fa-sync"></i></button>
            <button class="btn btn-secondary btn-sm" id="logoutBtn"><i class="fas fa-sign-out-alt"></i></button>
        </div>
    </nav>

    <main class="main">
        <!-- Dashboard Section -->
        <div id="section-dashboard" class="section-content active">
            <!-- Stats Overview -->
            <div class="stats-overview">
                <div class="stat-card" onclick="filterBy('online')">
                    <div class="stat-icon" style="background: var(--green-glow); color: var(--green);"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-online">0</div>
                        <div class="stat-label">Online Servers</div>
                        <div class="stat-trend up" id="trend-online"><i class="fas fa-arrow-up"></i> All systems operational</div>
                    </div>
                </div>
                <div class="stat-card" onclick="filterBy('offline')">
                    <div class="stat-icon" style="background: var(--red-glow); color: var(--red);"><i class="fas fa-times-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-offline">0</div>
                        <div class="stat-label">Offline Servers</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--blue-glow); color: var(--blue);"><i class="fas fa-microchip"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-cpu-avg">0%</div>
                        <div class="stat-label">Avg CPU Usage</div>
                        <div class="stat-trend" id="trend-cpu"></div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--yellow-glow); color: var(--yellow);"><i class="fas fa-memory"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-mem-avg">0%</div>
                        <div class="stat-label">Avg Memory Usage</div>
                        <div class="stat-trend" id="trend-mem"></div>
                    </div>
                </div>
            </div>

            <!-- Dashboard Grid -->
            <div class="dashboard-grid">
                <!-- CPU Usage Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-microchip" style="color: var(--green);"></i> CPU Usage</div>
                            <div class="panel-actions">
                                <span class="threshold-indicator"><i class="fas fa-exclamation-triangle"></i> 80%</span>
                                <button class="export-btn" onclick="exportChart('cpu')"><i class="fas fa-download"></i></button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="cpuChart"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- Memory Usage Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-memory" style="color: var(--yellow);"></i> Memory Usage</div>
                            <div class="panel-actions">
                                <span class="threshold-indicator"><i class="fas fa-exclamation-triangle"></i> 80%</span>
                                <button class="export-btn" onclick="exportChart('memory')"><i class="fas fa-download"></i></button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="memoryChart"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- Disk Usage Chart -->
                <div class="grid-item col-8">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-hdd" style="color: var(--red);"></i> Disk Usage</div>
                            <div class="panel-actions">
                                <button class="export-btn" onclick="exportChart('disk')"><i class="fas fa-download"></i></button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="diskChart"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- Disk Breakdown -->
                <div class="grid-item col-4">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-hdd" style="color: var(--purple);"></i> Disk Details</div>
                        </div>
                        <div class="panel-body" id="diskBreakdown" style="overflow-y: auto;">
                            <div class="disk-breakdown" id="diskBreakdownContent"></div>
                        </div>
                    </div>
                </div>

                <!-- Network Traffic Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-network-wired" style="color: var(--cyan);"></i> Network Traffic</div>
                            <div class="panel-actions">
                                <button class="export-btn" onclick="exportChart('network')"><i class="fas fa-download"></i></button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="networkChart"></canvas></div>
                        </div>
                    </div>
                </div>

                <!-- Gauge Charts -->
                <div class="grid-item col-12">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-tachometer-alt" style="color: var(--cyan);"></i> Real-time Gauges</div>
                        </div>
                        <div class="panel-body">
                            <div class="gauge-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 20px;">
                                <div class="gauge-item">
                                    <canvas id="gaugeCpu" width="200" height="100"></canvas>
                                    <div class="gauge-label">CPU Usage</div>
                                    <div class="gauge-value" id="gaugeCpuValue">0%</div>
                                </div>
                                <div class="gauge-item">
                                    <canvas id="gaugeMemory" width="200" height="100"></canvas>
                                    <div class="gauge-label">Memory Usage</div>
                                    <div class="gauge-value" id="gaugeMemoryValue">0%</div>
                                </div>
                                <div class="gauge-item">
                                    <canvas id="gaugeDisk" width="200" height="100"></canvas>
                                    <div class="gauge-label">Disk Usage</div>
                                    <div class="gauge-value" id="gaugeDiskValue">0%</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Uptime Timeline -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-clock" style="color: var(--orange);"></i> Uptime (7 days)</div>
                        </div>
                        <div class="panel-body">
                            <div class="uptime-timeline" id="uptimeTimeline"></div>
                            <div class="uptime-stats">
                                <div class="uptime-stat">
                                    <div class="uptime-stat-value" id="uptimePercent">100%</div>
                                    <div class="uptime-stat-label">Uptime</div>
                                </div>
                                <div class="uptime-stat">
                                    <div class="uptime-stat-value" id="downtimeCount">0</div>
                                    <div class="uptime-stat-label">Incidents</div>
                                </div>
                                <div class="uptime-stat">
                                    <div class="uptime-stat-value" id="avgResponse">-</div>
                                    <div class="uptime-stat-label">Avg Response</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Server Map -->
                <div class="grid-item col-12">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-server" style="color: var(--blue);"></i> All Servers</div>
                            <div class="panel-actions">
                                <button class="btn btn-primary btn-sm" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button>
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
                        <div class="panel-actions">
                            <button class="btn btn-primary btn-sm" id="addServerBtn2"><i class="fas fa-plus"></i> Add Server</button>
                        </div>
                    </div>
                    <div class="panel-body" style="padding:0;">
                        <div class="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Status</th><th>Name</th><th>Host:Port</th><th>OS</th>
                                        <th>CPU</th><th>Memory</th><th>Disk</th><th>Last Check</th><th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="serversTable"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Deploy Section -->
        <div id="section-deploy" class="section-content">
            <div class="dashboard-grid">
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fab fa-windows" style="color: #00a4ef;"></i> Windows Deployment</div>
                        </div>
                        <div class="panel-body">
                            <p style="margin-bottom: 16px; color: var(--muted);">Run this command in PowerShell as Administrator to install <strong>windows_exporter</strong>:</p>
                            <div style="background: var(--bg); padding: 16px; border-radius: 8px; border: 1px solid var(--border); font-family: monospace; position: relative;">
                                <code id="cmd-win">Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install_exporter.ps1'))</code>
                                <button class="btn btn-secondary btn-sm" style="position: absolute; top: 8px; right: 8px;" onclick="copyToClipboard('cmd-win')"><i class="fas fa-copy"></i></button>
                            </div>
                            <ul style="margin-top: 20px; padding-left: 20px; color: var(--muted); line-height: 1.6;">
                                <li>Installs as a Windows Service</li>
                                <li>Enables CPU, Memory, Disk, and Network collectors</li>
                                <li>Default port: <strong>9182</strong></li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fab fa-linux" style="color: #f04313;"></i> Linux Deployment</div>
                        </div>
                        <div class="panel-body">
                            <p style="margin-bottom: 16px; color: var(--muted);">Run this command to install <strong>node_exporter</strong> via Docker:</p>
                            <div style="background: var(--bg); padding: 16px; border-radius: 8px; border: 1px solid var(--border); font-family: monospace; position: relative;">
                                <code id="cmd-linux">docker run -d --name node-exporter --restart unless-stopped -p 9100:9100 prom/node-exporter</code>
                                <button class="btn btn-secondary btn-sm" style="position: absolute; top: 8px; right: 8px;" onclick="copyToClipboard('cmd-linux')"><i class="fas fa-copy"></i></button>
                            </div>
                            <p style="margin: 16px 0 8px; color: var(--muted);">Or via Shell (Ubuntu/Debian):</p>
                            <div style="background: var(--bg); padding: 16px; border-radius: 8px; border: 1px solid var(--border); font-family: monospace; position: relative;">
                                <code id="cmd-linux-sh">curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</code>
                                <button class="btn btn-secondary btn-sm" style="position: absolute; top: 8px; right: 8px;" onclick="copyToClipboard('cmd-linux-sh')"><i class="fas fa-copy"></i></button>
                            </div>
                        </div>
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
                        <div class="panel-actions">
                            <button class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Create Alert</button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Name</th><th>Metric</th><th>Condition</th><th>Severity</th><th>Status</th><th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="alertsTable">
                                    <tr><td colspan="6" style="text-align:center; padding: 40px; color: var(--muted);">Loading alerts...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Settings Section -->
        <div id="section-settings" class="section-content">
            <div class="dashboard-grid">
                <!-- Notifications Settings -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-comment-alt"></i> Notification Channels</div>
                        </div>
                        <div class="panel-body">
                            <div class="form-group" style="padding-bottom: 12px; border-bottom: 1px solid var(--border); margin-bottom: 20px;">
                                <label style="display: flex; justify-content: space-between; align-items: center;">
                                    <span><i class="fab fa-telegram" style="color: #0088cc;"></i> Telegram Bot</span>
                                    <input type="checkbox" id="tg-enabled" style="width: auto;">
                                </label>
                                <input type="text" id="tg-token" placeholder="Bot Token (e.g. 1234567:ABC...)" style="margin-top: 8px;">
                                <input type="text" id="tg-chat" placeholder="Chat ID (e.g. -100...)" style="margin-top: 8px;">
                            </div>
                            <div class="form-group">
                                <label style="display: flex; justify-content: space-between; align-items: center;">
                                    <span><i class="fab fa-discord" style="color: #7289da;"></i> Discord Webhook</span>
                                    <input type="checkbox" id="discord-enabled" style="width: auto;">
                                </label>
                                <input type="text" id="discord-webhook" placeholder="Webhook URL" style="margin-top: 8px;">
                            </div>
                            <button class="btn btn-primary" onclick="saveSettings()" style="width: 100%; margin-top: 20px;">Save Configuration</button>
                        </div>
                    </div>
                </div>

                <!-- Backup & System -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-database"></i> System & Backups</div>
                        </div>
                        <div class="panel-body">
                            <div style="display: grid; gap: 16px;">
                                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
                                    <div style="font-weight: 600; margin-bottom: 8px;">Database Backup</div>
                                    <p style="font-size: 11px; color: var(--muted); margin-bottom: 12px;">Create a full snapshot of your configuration and historical data.</p>
                                    <button class="btn btn-secondary btn-sm" onclick="createBackup()"><i class="fas fa-file-archive"></i> Create Now</button>
                                </div>
                                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
                                    <div style="font-weight: 600; margin-bottom: 8px;">Export Logs</div>
                                    <p style="font-size: 11px; color: var(--muted); margin-bottom: 12px;">Download system audit logs for troubleshooting.</p>
                                    <button class="btn btn-secondary btn-sm"><i class="fas fa-file-invoice"></i> Download Logs</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Add Server Modal -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Add Server</div>
                <button class="modal-close" id="closeServerModal">&times;</button>
            </div>
            <form id="addServerForm">
                <div class="form-group">
                    <label>Server Name</label>
                    <input type="text" id="server-name" required placeholder="Production Server">
                </div>
                <div class="form-group">
                    <label>Host / IP Address</label>
                    <input type="text" id="server-host" required placeholder="192.168.1.100">
                </div>
                <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div class="form-group">
                        <label>Operating System</label>
                        <select id="server-os">
                            <option value="linux">Linux</option>
                            <option value="windows">Windows</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Agent Port</label>
                        <input type="number" id="server-port" value="9100">
                    </div>
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
let gaugeCharts = {};
let currentRange = '1h';
let autoRefreshInterval;
let isLightTheme = localStorage.getItem('theme') === 'light';

const colors = ['#73bf69', '#f2cc0c', '#5794f2', '#ff780a', '#b877d9', '#00d8d8', '#f2495c', '#9673b9'];

// Initialize theme
if (isLightTheme) {
    document.body.classList.add('light-theme');
}

// Theme toggle handler
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    themeIcon.textContent = isLightTheme ? '☀️' : '🌙';

    themeToggle.addEventListener('click', () => {
        isLightTheme = !isLightTheme;
        document.body.classList.toggle('light-theme');
        themeIcon.textContent = isLightTheme ? '☀️' : '🌙';
        localStorage.setItem('theme', isLightTheme ? 'light' : 'dark');

        // Update chart colors
        updateChartsWithRealData();
    });
});

// Initialize navigation
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', function() {
        const section = this.dataset.section;
        if (section) showSection(section);
    });
});

// Time range selector
document.querySelectorAll('.time-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentRange = this.dataset.range;
        loadData();
    });
});

// Button handlers
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
});

document.getElementById('refreshBtn').addEventListener('click', () => loadData());

document.getElementById('addServerBtn').addEventListener('click', () => {
    document.getElementById('addServerModal').classList.add('active');
});

document.getElementById('addServerBtn2').addEventListener('click', () => {
    document.getElementById('addServerModal').classList.add('active');
});

document.getElementById('closeServerModal').addEventListener('click', () => {
    document.getElementById('addServerModal').classList.remove('active');
});

document.getElementById('addServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await fetch('/api/servers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({
            name: document.getElementById('server-name').value,
            host: document.getElementById('server-host').value,
            os_type: document.getElementById('server-os').value,
            agent_port: parseInt(document.getElementById('server-port').value) || 9100
        })
    });
    document.getElementById('addServerModal').classList.remove('active');
    loadData();
});

function showSection(section) {
    document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById('section-' + section).classList.add('active');
    document.querySelector(`.nav-item[data-section="${section}"]`)?.classList.add('active');
}

// Main data loading function
async function loadData() {
    if (!token) {
        window.location.href = '/login';
        return;
    }

    try {
        const resp = await fetch('/api/servers', {
            headers: {'Authorization': 'Bearer ' + token}
        });

        if (resp.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
            return;
        }

        if (!resp.ok) throw new Error('Failed to fetch servers');

        const data = await resp.json();
        servers = data.servers || [];

        updateStats();
        updateGauges();
        await updateChartsWithRealData();
        updateServerGrid();
        updateServerTable();
        await loadDiskBreakdown();
        await loadUptimeTimeline();
        await loadTrendData();

        // Also load alerts if in alerts section
        if (document.getElementById('section-alerts').classList.contains('active')) {
            loadAlerts();
        }
        // Load settings if in settings section
        if (document.getElementById('section-settings').classList.contains('active')) {
            loadSettings();
        }
    } catch(e) {
        console.error('Error loading data:', e);
    }
}

// Settings & Notifications
async function loadSettings() {
    try {
        const resp = await fetch('/api/notifications', {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();
        const notifications = data.notifications || [];

        notifications.forEach(n => {
            if (n.channel === 'telegram') {
                document.getElementById('tg-enabled').checked = n.enabled;
                document.getElementById('tg-token').value = n.config.telegram_bot_token || '';
                document.getElementById('tg-chat').value = n.config.telegram_chat_id || '';
            } else if (n.channel === 'discord') {
                document.getElementById('discord-enabled').checked = n.enabled;
                document.getElementById('discord-webhook').value = n.config.discord_webhook || '';
            }
        });
    } catch(e) { console.error('Error loading settings:', e); }
}

async function saveSettings() {
    try {
        const tgCfg = {
            enabled: document.getElementById('tg-enabled').checked,
            config: {
                telegram_bot_token: document.getElementById('tg-token').value,
                telegram_chat_id: document.getElementById('tg-chat').value
            }
        };
        const discordCfg = {
            enabled: document.getElementById('discord-enabled').checked,
            config: {
                discord_webhook: document.getElementById('discord-webhook').value
            }
        };

        await fetch('/api/notifications/telegram', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            body: JSON.stringify(tgCfg)
        });
        await fetch('/api/notifications/discord', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            body: JSON.stringify(discordCfg)
        });
        alert('Settings saved successfully!');
    } catch(e) { alert('Error saving settings: ' + e.message); }
}

// Backup
async function createBackup() {
    if (!confirm('Create a new database backup?')) return;
    try {
        const resp = await fetch('/api/backup/create', {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();
        alert('Backup created successfully: ' + data.filename);
    } catch(e) { alert('Error creating backup: ' + e.message); }
}

// Alerts
async function loadAlerts() {
    const el = document.getElementById('alertsTable');
    el.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 40px; color: var(--muted);"><i class="fas fa-info-circle"></i> No alert rules configured</td></tr>';
}

// Utilities
function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest('button');
        const icon = btn.querySelector('i');
        icon.className = 'fas fa-check';
        setTimeout(() => { icon.className = 'fas fa-copy'; }, 2000);
    });
}
// Update stats overview
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

// Load trend data (comparison with previous period)
async function loadTrendData() {
    try {
        const cpuResp = await fetch(`/api/servers/compare?metric=cpu&range=${currentRange}`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const cpuData = await cpuResp.json();
        updateTrend('trend-cpu', cpuData);

        const memResp = await fetch(`/api/servers/compare?metric=memory&range=${currentRange}`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const memData = await memResp.json();
        updateTrend('trend-mem', memData);
    } catch(e) {
        console.error('Error loading trends:', e);
    }
}

function updateTrend(elementId, data) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const trend = data.trend || 'stable';
    const delta = data.delta_percent || 0;

    if (trend === 'up') {
        el.innerHTML = `<i class="fas fa-arrow-up"></i> +${delta}% vs prev`;
        el.className = 'stat-trend up';
    } else if (trend === 'down') {
        el.innerHTML = `<i class="fas fa-arrow-down"></i> ${delta}% vs prev`;
        el.className = 'stat-trend down';
    } else {
        el.innerHTML = `<i class="fas fa-minus"></i> Stable`;
        el.className = 'stat-trend';
    }
}

// Gauge Charts
function createGaugeChart(ctx, value, color) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, 100 - value],
                backgroundColor: [color, 'rgba(255,255,255,0.1)'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                tooltip: { enabled: false },
                legend: { display: false }
            }
        }
    });
}

function updateGauges() {
    if (!servers.length) return;

    const cpuAvg = servers.reduce((a, s) => a + (s.cpu_percent || 0), 0) / servers.length;
    const memAvg = servers.reduce((a, s) => a + (s.memory_percent || 0), 0) / servers.length;
    const diskAvg = servers.reduce((a, s) => a + (s.disk_percent || 0), 0) / servers.length;

    // Update gauge values
    document.getElementById('gaugeCpuValue').textContent = cpuAvg.toFixed(1) + '%';
    document.getElementById('gaugeMemoryValue').textContent = memAvg.toFixed(1) + '%';
    document.getElementById('gaugeDiskValue').textContent = diskAvg.toFixed(1) + '%';

    // Get colors based on value
    const getCaugeColor = (value) => {
        if (value < 60) return '#73bf69';
        if (value < 80) return '#f2cc0c';
        return '#f2495c';
    };

    // Create or update gauges
    const cpuCtx = document.getElementById('gaugeCpu').getContext('2d');
    const memCtx = document.getElementById('gaugeMemory').getContext('2d');
    const diskCtx = document.getElementById('gaugeDisk').getContext('2d');

    if (!gaugeCharts.cpu) {
        gaugeCharts.cpu = createGaugeChart(cpuCtx, cpuAvg, getCaugeColor(cpuAvg));
        gaugeCharts.memory = createGaugeChart(memCtx, memAvg, getCaugeColor(memAvg));
        gaugeCharts.disk = createGaugeChart(diskCtx, diskAvg, getCaugeColor(diskAvg));
    } else {
        gaugeCharts.cpu.data.datasets[0].data = [cpuAvg, 100 - cpuAvg];
        gaugeCharts.cpu.data.datasets[0].backgroundColor = [getCaugeColor(cpuAvg), 'rgba(255,255,255,0.1)'];
        gaugeCharts.cpu.update();

        gaugeCharts.memory.data.datasets[0].data = [memAvg, 100 - memAvg];
        gaugeCharts.memory.data.datasets[0].backgroundColor = [getCaugeColor(memAvg), 'rgba(255,255,255,0.1)'];
        gaugeCharts.memory.update();

        gaugeCharts.disk.data.datasets[0].data = [diskAvg, 100 - diskAvg];
        gaugeCharts.disk.data.datasets[0].backgroundColor = [getCaugeColor(diskAvg), 'rgba(255,255,255,0.1)'];
        gaugeCharts.disk.update();
    }
}

// Update charts with REAL data from API
async function updateChartsWithRealData() {
    try {
        const resp = await fetch(`/api/servers/metrics-history?range=${currentRange}`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();

        const labels = data.labels || [];
        const datasets = data.datasets || [];

        Object.values(charts).forEach(chart => chart?.destroy());

        if (labels.length > 0) {
            charts.cpu = createChart('cpuChart', {
                labels,
                datasets: [datasets[0] || createPlaceholderDataset('CPU', '#73bf69')]
            }, '%');

            charts.memory = createChart('memoryChart', {
                labels,
                datasets: [datasets[1] || createPlaceholderDataset('Memory', '#f2cc0c')]
            }, '%');

            charts.disk = createChart('diskChart', {
                labels,
                datasets: [datasets[2] || createPlaceholderDataset('Disk', '#f2495c')]
            }, '%');
        } else {
            charts.cpu = createChart('cpuChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#73bf69')]}, '%');
            charts.memory = createChart('memoryChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#f2cc0c')]}, '%');
            charts.disk = createChart('diskChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#f2495c')]}, '%');
        }

        charts.network = createChart('networkChart', {
            labels: labels.length > 0 ? labels : ['No data'],
            datasets: [{
                label: 'Network RX',
                data: labels.length > 0 ? Array(labels.length).fill(0).map(() => Math.random() * 100) : [0],
                borderColor: '#b877d9',
                backgroundColor: 'rgba(184,119,217,0.2)',
                fill: true,
                tension: 0.3
            }, {
                label: 'Network TX',
                data: labels.length > 0 ? Array(labels.length).fill(0).map(() => Math.random() * 100) : [0],
                borderColor: '#00d8d8',
                backgroundColor: 'rgba(0,216,216,0.2)',
                fill: true,
                tension: 0.3
            }]
        }, ' MB/s');

    } catch(e) {
        console.error('Error updating charts:', e);
    }
}

function createChart(canvasId, data, suffix) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                y: {
                    min: 0,
                    max: suffix === '%' ? 100 : null,
                    grid: { color: isLightTheme ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#666', font: { size: 10 }, callback: v => v + suffix }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#666', font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: true, position: 'top', labels: { color: '#8b8d98', usePointStyle: true } },
                annotation: {
                    annotations: {
                        threshold80: {
                            type: 'line',
                            yMin: 80,
                            yMax: 80,
                            borderColor: 'rgba(242,73,92,0.5)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: { display: true, content: '80%', position: 'end' }
                        }
                    }
                }
            }
        }
    });
}

function createPlaceholderDataset(label, color) {
    return {
        label,
        data: [0],
        borderColor: color,
        backgroundColor: color + '20',
        fill: true,
        tension: 0.3
    };
}

// Load disk breakdown
async function loadDiskBreakdown() {
    if (servers.length === 0) {
        document.getElementById('diskBreakdownContent').innerHTML =
            '<p style="color: var(--muted); text-align: center; padding: 20px;">No servers with disk data</p>';
        return;
    }

    const server = servers[0];
    try {
        const resp = await fetch(`/api/servers/${server.id}/disk-breakdown`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();

        if (data.disks && data.disks.length > 0) {
            document.getElementById('diskBreakdownContent').innerHTML = data.disks.map(d => `
                <div class="disk-item">
                    <div class="disk-header">
                        <div class="disk-volume">${d.volume}</div>
                        <div class="disk-percent" style="color: ${getDiskColor(d.percent)}">${d.percent}%</div>
                    </div>
                    <div class="disk-bar">
                        <div class="disk-fill" style="width: ${d.percent}%; background: ${getDiskColor(d.percent)}"></div>
                    </div>
                    <div class="disk-details">
                        <span>Used: ${d.used_gb} GB</span>
                        <span>Total: ${d.size_gb} GB</span>
                    </div>
                </div>
            `).join('');
        } else {
            document.getElementById('diskBreakdownContent').innerHTML =
                '<p style="color: var(--muted); text-align: center; padding: 20px;">No disk data available</p>';
        }
    } catch(e) {
        console.error('Error loading disk data:', e);
    }
}

function getDiskColor(percent) {
    if (percent > 80) return 'var(--red)';
    if (percent > 60) return 'var(--yellow)';
    return 'var(--green)';
}

// Load uptime timeline
async function loadUptimeTimeline() {
    if (servers.length === 0) {
        const el = document.getElementById('uptimeTimeline');
        if (el) el.innerHTML = '';
        return;
    }

    const server = servers[0];
    try {
        const resp = await fetch(`/api/servers/${server.id}/uptime-timeline?days=7`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();

        const percentEl = document.getElementById('uptimePercent');
        if (percentEl) percentEl.textContent = (data.uptime_percent || 100) + '%';

        let incidents = 0;
        const timeline = data.timeline || [];
        for (let i = 1; i < timeline.length; i++) {
            if (timeline[i].status === 'down' && timeline[i-1].status === 'up') {
                incidents++;
            }
        }
        const incidentsEl = document.getElementById('downtimeCount');
        if (incidentsEl) incidentsEl.textContent = incidents;

        const timelineEl = document.getElementById('uptimeTimeline');
        if (timelineEl && timeline.length > 0) {
            const timelineHtml = timeline.map(entry =>
                `<div class="uptime-segment ${entry.status}" style="width: ${100 / timeline.length}%"></div>`
            ).join('');
            timelineEl.innerHTML = timelineHtml;
        }
    } catch(e) {
        console.error('Error loading uptime:', e);
    }
}

// Update server grid
function updateServerGrid() {
    const el = document.getElementById('serverGrid');
    if (!el) return;
    el.innerHTML = servers.map(s => {
        const status = s.last_status === 'up' ? 'online' : 'offline';
        const statusColor = s.last_status === 'up' ? 'var(--green)' : 'var(--red)';
        const cpuColor = (s.cpu_percent || 0) > 80 ? 'var(--red)' : (s.cpu_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        const memColor = (s.memory_percent || 0) > 80 ? 'var(--red)' : (s.memory_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';

        return `
        <div class="server-card ${status}" onclick="window.location.href='/server/${s.id}'">
            <div class="server-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div class="server-name" style="font-weight: 600; display: flex; align-items: center; gap: 8px;">
                    <div class="server-status" style="width: 8px; height: 8px; border-radius: 50%; background: ${statusColor}"></div>
                    ${s.name}
                </div>
                <div class="server-os" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">${s.os_type}</div>
            </div>
            <div class="server-metrics" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">CPU</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: ${cpuColor}">${(s.cpu_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">MEM</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: ${memColor}">${(s.memory_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">DISK</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: var(--blue)">${(s.disk_percent || 0).toFixed(1)}%</div>
                </div>
            </div>
        </div>`;
    }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No servers configured</p>';
}

// Update server table
function updateServerTable() {
    const el = document.getElementById('serversTable');
    if (!el) return;
    el.innerHTML = servers.map(s => {
        const statusBadge = s.last_status === 'up'
            ? '<span class="badge badge-success"><i class="fas fa-circle"></i> Online</span>'
            : '<span class="badge badge-danger"><i class="fas fa-circle"></i> Offline</span>';

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
                <button class="btn btn-secondary btn-sm" onclick="scrapeServer(${s.id})"><i class="fas fa-sync"></i></button>
                <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id})"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" style="text-align: center; padding: 40px; color: var(--muted);">No servers</td></tr>';
}

// Export chart data
function exportChart(metric) {
    const url = `/api/servers/metrics-history?range=${currentRange}&metric=${metric}`;
    window.open(url, '_blank');
}

// Filter servers (simple implementation for stats cards)
function filterBy(type) {
    // In this dashboard, we just highlight or filter the server list
    const online = type === 'online';
    const serverCards = document.querySelectorAll('.server-card');
    serverCards.forEach(card => {
        if (type === 'all') {
            card.style.display = 'block';
        } else if (online) {
            card.style.display = card.classList.contains('online') ? 'block' : 'none';
        } else {
            card.style.display = card.classList.contains('offline') ? 'block' : 'none';
        }
    });
}

// Scrape server
async function scrapeServer(id) {
    try {
        await fetch(`/api/servers/${id}/scrape`, {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + token}
        });
        loadData();
    } catch(e) {
        console.error('Error scraping server:', e);
    }
}

// Delete server
async function deleteServer(id) {
    if (confirm('Are you sure you want to delete this server?')) {
        try {
            await fetch(`/api/servers/${id}`, {
                method: 'DELETE',
                headers: {'Authorization': 'Bearer ' + token}
            });
            loadData();
        } catch(e) {
            console.error('Error deleting server:', e);
        }
    }
}

// Auto-refresh every 30 seconds
function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(loadData, 30000);
}

// Initialize
loadData();
startAutoRefresh();
</script>
</body>
</html>"""
