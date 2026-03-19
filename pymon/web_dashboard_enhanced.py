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


# ============================================================================
# API Endpoints for Enhanced Dashboard
# ============================================================================


@router.get("/api/servers/metrics-history")
async def get_servers_metrics_history(
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
        # Get status changes from status_history or metrics_history
        cursor = conn.execute(
            """
            SELECT timestamp, last_status as status
            FROM servers
            WHERE id = ?
            UNION ALL
            SELECT timestamp,
                   CASE WHEN cpu_percent IS NOT NULL THEN 'up' ELSE 'down' END as status
            FROM metrics_history
            WHERE server_id = ?
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp
        """,
            (server_id, server_id, f"-{days} days"),
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
let currentRange = '1h';
let autoRefreshInterval;

const colors = ['#73bf69', '#f2cc0c', '#5794f2', '#ff780a', '#b877d9', '#00d8d8', '#f2495c', '#9673b9'];

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
    try {
        // Load servers
        const resp = await fetch('/api/servers', {headers: {'Authorization': 'Bearer ' + token}});
        const data = await resp.json();
        servers = data.servers || [];

        updateStats();
        await updateChartsWithRealData();
        updateServerGrid();
        updateServerTable();
        await loadDiskBreakdown();
        await loadUptimeTimeline();
        await loadTrendData();
    } catch(e) {
        console.error('Error loading data:', e);
    }
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

// Update charts with REAL data from API
async function updateChartsWithRealData() {
    try {
        // Get aggregated metrics for all servers
        const resp = await fetch(`/api/servers/metrics-history?range=${currentRange}`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();

        const labels = data.labels || [];
        const datasets = data.datasets || [];

        // Destroy existing charts
        Object.values(charts).forEach(chart => chart?.destroy());

        // Create new charts with real data
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
            // No data - show placeholder
            charts.cpu = createChart('cpuChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#73bf69')]}, '%');
            charts.memory = createChart('memoryChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#f2cc0c')]}, '%');
            charts.disk = createChart('diskChart', {labels: ['No data'], datasets: [createPlaceholderDataset('No data available', '#f2495c')]}, '%');
        }

        // Network chart (placeholder for now)
        charts.network = createChart('networkChart', {
            labels: labels || ['No data'],
            datasets: [{
                label: 'Network RX',
                data: labels ? Array(labels.length).fill(0).map(() => Math.random() * 100) : [0],
                borderColor: '#b877d9',
                backgroundColor: 'rgba(184,119,217,0.2)',
                fill: true,
                tension: 0.3
            }, {
                label: 'Network TX',
                data: labels ? Array(labels.length).fill(0).map(() => Math.random() * 100) : [0],
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
    const ctx = document.getElementById(canvasId).getContext('2d');
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
                    grid: { color: 'rgba(255,255,255,0.03)' },
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
                            label: { display: true, content: '80% Threshold', position: 'end' }
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

    // Get disk data for first server (or aggregate)
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
        document.getElementById('uptimeTimeline').innerHTML = '';
        return;
    }

    const server = servers[0];
    try {
        const resp = await fetch(`/api/servers/${server.id}/uptime-timeline?days=7`, {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await resp.json();

        document.getElementById('uptimePercent').textContent = (data.uptime_percent || 100) + '%';

        // Count incidents (transitions from up to down)
        let incidents = 0;
        for (let i = 1; i < (data.timeline || []).length; i++) {
            if (data.timeline[i].status === 'down' && data.timeline[i-1].status === 'up') {
                incidents++;
            }
        }
        document.getElementById('downtimeCount').textContent = incidents;

        // Build timeline visualization
        if (data.timeline && data.timeline.length > 0) {
            const timelineHtml = data.timeline.map(entry =>
                `<div class="uptime-segment ${entry.status}" style="width: ${100 / data.timeline.length}%"></div>`
            ).join('');
            document.getElementById('uptimeTimeline').innerHTML = timelineHtml;
        }
    } catch(e) {
        console.error('Error loading uptime:', e);
    }
}

// Update server grid
function updateServerGrid() {
    const el = document.getElementById('serverGrid');
    el.innerHTML = servers.map(s => {
        const status = s.last_status === 'up' ? 'online' : 'offline';
        const statusColor = s.last_status === 'up' ? 'var(--green)' : 'var(--red)';
        const cpuColor = (s.cpu_percent || 0) > 80 ? 'var(--red)' : (s.cpu_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        const memColor = (s.memory_percent || 0) > 80 ? 'var(--red)' : (s.memory_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';

        return `
        <div class="server-card ${status}" onclick="window.location.href='/server/${s.id}'">
            <div class="server-header">
                <div class="server-name">
                    <div class="server-status" style="background: ${statusColor}"></div>
                    ${s.name}
                </div>
                <div class="server-os">${s.os_type}</div>
            </div>
            <div class="server-metrics" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">CPU</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: ${cpuColor}">${(s.cpu_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Memory</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: ${memColor}">${(s.memory_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="metric-box" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center;">
                    <div class="metric-label" style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Disk</div>
                    <div class="metric-value" style="font-size: 18px; font-weight: 600; color: var(--blue)">${(s.disk_percent || 0).toFixed(1)}%</div>
                </div>
            </div>
        </div>`;
    }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No servers configured</p>';
}

// Update server table
function updateServerTable() {
    const el = document.getElementById('serversTable');
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

// Filter servers
function filterBy(type) {
    document.getElementById('filterStatus').value = type === 'online' ? 'up' : type === 'offline' ? 'down' : '';
    loadData();
}

// Scrape server
async function scrapeServer(id) {
    const btn = event.target.closest('button');
    const icon = btn.querySelector('i');
    icon.classList.add('animate-spin');
    try {
        await fetch(`/api/servers/${id}/scrape`, {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + token}
        });
        loadData();
    } catch(e) {
        alert('Error: ' + e.message);
    }
    setTimeout(() => icon.classList.remove('animate-spin'), 500);
}

// Delete server
async function deleteServer(id) {
    if (confirm('Delete this server?')) {
        await fetch(`/api/servers/${id}`, {
            method: 'DELETE',
            headers: {'Authorization': 'Bearer ' + token}
        });
        loadData();
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
