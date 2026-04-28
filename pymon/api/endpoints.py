"""FastAPI API endpoints"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import aiosqlite
from fastapi import Query, Request
from fastapi.responses import Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

    _PROM_METRICS_ENABLED = True
    _PROM_SERVER_COUNT = Gauge("pymon_servers_total", "Total number of servers")
except Exception:
    _PROM_METRICS_ENABLED = False
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from pymon.api import models as api_models
from pymon.auth import (
    APIKeyCreate,
    PasswordChange,
    Token,
    User,
    UserLogin,
    authenticate_user,
    change_password,
    create_api_key,
    delete_api_key,
    get_current_user,
    list_api_keys,
)
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, MetricType
from pymon.storage import get_storage

_limiter = Limiter(key_func=get_remote_address)

api = APIRouter()


class MetricPayload(BaseModel):
    name: str
    value: float
    type: str = "gauge"
    labels: list[dict[str, str]] = []
    help_text: str = ""


class QueryRequest(BaseModel):
    query: str
    start: datetime
    end: datetime
    step: int = 60


class AlertCreate(BaseModel):
    name: str
    metric: str
    condition: str
    threshold: int
    duration: int = 0
    severity: str = "warning"
    server_id: int | None = None
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False
    notify_teams: bool = False
    description: str = ""


@api.post("/auth/login", response_model=Token)
@_limiter.limit("10/minute")
async def login(request: Request, data: UserLogin):
    return authenticate_user(data.username, data.password)


@api.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@api.post("/auth/change-password")
async def change_pwd(data: PasswordChange, current_user: User = Depends(get_current_user)):
    change_password(current_user.id, data.current_password, data.new_password)
    return {"status": "ok"}


@api.post("/auth/api-keys")
async def create_key(data: APIKeyCreate, current_user: User = Depends(get_current_user)):
    key = create_api_key(current_user.id, data.name)
    return {"api_key": key, "name": data.name}


@api.get("/auth/api-keys")
async def list_keys(current_user: User = Depends(get_current_user)):
    return {"api_keys": list_api_keys(current_user.id)}


@api.delete("/auth/api-keys/{key_id}")
async def delete_key(key_id: int, current_user: User = Depends(get_current_user)):
    if delete_api_key(current_user.id, key_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="API key not found")


@api.post("/metrics")
async def ingest_metric(payload: MetricPayload, current_user: User = Depends(get_current_user)):
    storage = get_storage()
    try:
        metric_type = MetricType(payload.type)
    except ValueError:
        metric_type = MetricType.GAUGE

    labels = [Label(name=l["name"], value=l["value"]) for l in payload.labels]
    registry.register(payload.name, metric_type, payload.help_text, labels)
    registry.set(payload.name, payload.value, labels)

    from pymon.metrics.models import Metric

    metric = Metric(
        name=payload.name, value=payload.value, metric_type=metric_type, labels=labels, help_text=payload.help_text
    )
    await storage.write(metric)
    return {"status": "ok"}


@api.get("/metrics")
async def list_metrics(current_user: User = Depends(get_current_user)):
    return {"metrics": [m.to_dict() for m in registry.get_all_metrics()]}


@api.get("/query")
async def query_metrics(
    query: str,
    start: datetime | None = None,
    end: datetime | None = None,
    step: int = 60,
    current_user: User = Depends(get_current_user),
):
    storage = get_storage()
    end = end or datetime.now(timezone.utc)
    start = start or (end - timedelta(hours=1))
    points = await storage.read(query, start, end, step=step)
    return {
        "query": query,
        "result": [{"timestamp": p.timestamp.isoformat(), "value": p.value} for p in points],
    }


@api.get("/series")
async def list_series(current_user: User = Depends(get_current_user)):
    storage = get_storage()
    names = await storage.get_series_names()
    return {"series": names}


@api.get("/prometheus", include_in_schema=False)
def prometheus_metrics():
    if not _PROM_METRICS_ENABLED:
        raise HTTPException(status_code=503, detail="Prometheus metrics not enabled")
    try:
        import sqlite3

        conn = sqlite3.connect(os.getenv("DB_PATH", "pymon.db"))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM servers")
        count = cur.fetchone()[0]
        _PROM_SERVER_COUNT.set(count)
        conn.close()
    except Exception:
        pass
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@api.get("/alerts")
async def list_alerts(current_user: User = Depends(get_current_user)):
    import sqlite3

    conn = get_db()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, metric, condition, threshold, duration, severity, server_id, notify_telegram, notify_discord, notify_slack, notify_email, notify_teams, description, enabled, created_at FROM alerts ORDER BY id DESC"
        ).fetchall()
        return {"alerts": [dict(r) for r in rows]}
    finally:
        conn.close()


@api.post("/alerts")
async def create_alert(data: AlertCreate, current_user: User = Depends(get_current_user)):
    import sqlite3

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO alerts (name, metric, condition, threshold, duration, severity, server_id, notify_telegram, notify_discord, notify_slack, notify_email, notify_teams, description, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (
            data.name,
            data.metric,
            data.condition,
            data.threshold,
            data.duration,
            data.severity,
            data.server_id,
            int(data.notify_telegram),
            int(data.notify_discord),
            int(data.notify_slack),
            int(data.notify_email),
            int(data.notify_teams),
            data.description,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    alert_id = c.lastrowid
    conn.close()
    return {"status": "ok", "id": alert_id}


@api.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@api.get("/healthz")
async def healthz():
    # Lightweight alias for health checks in some environments
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Phase 2.9: Reinstate single history endpoint with proper typing (Phase 2.10 API contract)
@api.get("/servers/{server_id}/history", response_model=api_models.HistoryResponse)
async def get_server_history(
    server_id: int,
    range: str = Query("1h", regex="^(5m|15m|1h|6h|24h|7d)$"),
):
    """Return per-server historical metrics for UI history charts"""
    time_ranges = {
        "5m": "-5 minutes",
        "15m": "-15 minutes",
        "1h": "-1 hour",
        "6h": "-6 hours",
        "24h": "-24 hours",
        "7d": "-7 days",
    }
    time_filter = time_ranges.get(range, "-1 hour")
    db_path = os.getenv("DB_PATH", "pymon.db")
    history: list[dict] = []
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
                FROM metrics_history
                WHERE server_id = ?
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp
                """,
                (server_id, time_filter),
            )
            rows = await cursor.fetchall()
            history = [
                {
                    "timestamp": r[0],
                    "cpu_percent": r[1],
                    "memory_percent": r[2],
                    "disk_percent": r[3],
                    "network_rx": r[4],
                    "network_tx": r[5],
                }
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"history": history}


@api.get("/servers/{server_id}/events")
async def get_server_events(server_id: int, limit: int = 50):
    """Return recent events for a server from the audit log"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT id, username, action, target, timestamp FROM audit_log WHERE target LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{server_id}%", limit),
        )
        rows = cursor.fetchall()
        events = [dict(r) for r in rows]
        return {"events": events}
    finally:
        conn.close()


@api.get("/servers/{server_id}/summary")
async def get_server_summary(server_id: int):
    """Return a lightweight summary for a server (online/offline and recent averages)"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        last_status = conn.execute("SELECT last_status FROM servers WHERE id = ?", (server_id,)).fetchone()
        online = 1 if last_status and last_status[0] == "up" else 0
        offline = 1 - online

        # compute averages for last 1 hour if data exists
        cursor = conn.execute(
            "SELECT AVG(cpu_percent) as cpu, AVG(memory_percent) as mem, AVG(disk_percent) as disk FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', '-1 hour')",
            (server_id,),
        )
        row = cursor.fetchone()
        avg_cpu = float(row[0] or 0)
        avg_mem = float(row[1] or 0)
        avg_disk = float(row[2] or 0)
        return {
            "server_id": server_id,
            "online": online,
            "offline": offline,
            "avg_cpu": avg_cpu,
            "avg_memory": avg_mem,
            "avg_disk": avg_disk,
        }
    finally:
        conn.close()


@api.get("/servers/{server_id}/export", response_model=api_models.AllServersExportResponse)
async def export_server_data_json(
    server_id: int,
    format: str = Query("json", regex="^(json|csv)$"),
    range: str = Query("24h", regex="^(5m|15m|1h|6h|24h|7d)$"),
    current_user: User = Depends(get_current_user),
):
    """Export server metrics as JSON or CSV for a given range"""
    import csv
    import io

    time_ranges = {
        "5m": "-5 minutes",
        "15m": "-15 minutes",
        "1h": "-1 hour",
        "6h": "-6 hours",
        "24h": "-24 hours",
        "7d": "-7 days",
    }
    time_filter = time_ranges.get(range, "-24 hours")
    db_path = os.getenv("DB_PATH", "pymon.db")
    import aiosqlite

    data = []
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                "SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                (server_id, time_filter),
            )
            rows = await cursor.fetchall()
            for row in rows:
                data.append(
                    {
                        "timestamp": row[0],
                        "cpu_percent": row[1],
                        "memory_percent": row[2],
                        "disk_percent": row[3],
                        "network_rx": row[4],
                        "network_tx": row[5],
                    }
                )
        if format == "json":
            # Align with AllServersExportResponse schema
            return {"range": range, "servers": data}
        else:
            import csv as _csv

            output = io.StringIO()
            writer = _csv.writer(output)
            writer.writerow(["Timestamp", "CPU %", "Memory %", "Disk %", "Network RX (MB)", "Network TX (MB)"])
            for row in data:
                writer.writerow(
                    [
                        row["timestamp"],
                        row["cpu_percent"] or 0,
                        row["memory_percent"] or 0,
                        row["disk_percent"] or 0,
                        round((row["network_rx"] or 0) / (1024 * 1024), 2),
                        round((row["network_tx"] or 0) / (1024 * 1024), 2),
                    ]
                )
            from fastapi.responses import PlainTextResponse

            return PlainTextResponse(
                output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=server_{server_id}_{range}.csv"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/servers/export")
async def export_all_servers(
    format: str = Query("json", regex="^(json|csv)$"),
    range: str = Query("24h", regex="^(5m|15m|1h|6h|24h|7d)$"),
    current_user: User = Depends(get_current_user),
):
    """Export metrics for all servers (aggregated per-server data)"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        time_ranges = {
            "5m": "-5 minutes",
            "15m": "-15 minutes",
            "1h": "-1 hour",
            "6h": "-6 hours",
            "24h": "-24 hours",
            "7d": "-7 days",
        }
        time_filter = time_ranges.get(range, "-24 hours")

        servers = conn.execute("SELECT id FROM servers").fetchall()
        data = []
        for s in servers:
            sid = s[0]
            cur = conn.execute(
                "SELECT MAX(cpu_percent) as max_cpu, MAX(memory_percent) as max_memory, MAX(disk_percent) as max_disk, SUM(network_rx) as total_rx, SUM(network_tx) as total_tx FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?)",
                (sid, time_filter),
            )
            row = cur.fetchone()
            data.append(
                {
                    "server_id": sid,
                    "cpu": row[0] or 0,
                    "memory": row[1] or 0,
                    "disk": row[2] or 0,
                    "network_rx_mb": (row[3] or 0) / 1024 / 1024,
                    "network_tx_mb": (row[4] or 0) / 1024 / 1024,
                }
            )

        if format == "json":
            return {"range": range, "servers": data}
        else:
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["server_id", "cpu", "memory", "disk", "network_rx_mb", "network_tx_mb"])
            for row in data:
                writer.writerow(
                    [
                        row["server_id"],
                        row["cpu"],
                        row["memory"],
                        row["disk"],
                        row["network_rx_mb"],
                        row["network_tx_mb"],
                    ]
                )
            from fastapi.responses import PlainTextResponse

            return PlainTextResponse(
                output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=servers_export_{range}.csv"},
            )
    finally:
        conn.close()


@api.get("/servers/metrics/history", response_model=api_models.HistoryAllResponse)
async def get_all_servers_metrics_history(
    range: str = Query("1h", regex="^(5m|15m|1h|6h|24h|7d)$"),
    metric: str | None = Query(None, regex="^(cpu|memory|disk|network)$"),
):
    """Aggregate metrics history across all servers per server"""
    db_path = os.getenv("DB_PATH", "pymon.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        time_ranges = {
            "5m": "-5 minutes",
            "15m": "-15 minutes",
            "1h": "-1 hour",
            "6h": "-6 hours",
            "24h": "-24 hours",
            "7d": "-7 days",
        }
        time_filter = time_ranges.get(range, "-1 hour")

        servers = conn.execute("SELECT id FROM servers").fetchall()
        results = []
        for s in servers:
            sid = s[0]
            if metric:
                col = {
                    "cpu": "cpu_percent",
                    "memory": "memory_percent",
                    "disk": "disk_percent",
                    "network": "(network_rx + network_tx) / 2.0",
                }.get(metric, "cpu_percent")
                rows = conn.execute(
                    f"SELECT timestamp, {col} as value FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                    (sid, time_filter),
                ).fetchall()
                values = [r[1] for r in rows]
                results.append(
                    {"server_id": sid, "metric": metric.upper(), "data": values, "labels": [r[0] for r in rows]}
                )
            else:
                rows = conn.execute(
                    "SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                    (sid, time_filter),
                ).fetchall()
                results.append(
                    {
                        "server_id": sid,
                        "cpu": [r[1] for r in rows],
                        "memory": [r[2] for r in rows],
                        "disk": [r[3] for r in rows],
                        "network_rx": [r[4] for r in rows],
                        "network_tx": [r[5] for r in rows],
                        "labels": [r[0] for r in rows],
                    }
                )
        return {"servers": results}
    finally:
        conn.close()


@api.get("/servers/summary")
async def get_all_servers_summary():
    """Aggregate summary for all monitored servers"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN last_status = 'up' THEN 1 ELSE 0 END) as online,
                SUM(CASE WHEN last_status = 'down' THEN 1 ELSE 0 END) as offline,
                AVG(COALESCE(cpu_percent, 0)) as avg_cpu,
                AVG(COALESCE(memory_percent, 0)) as avg_memory,
                AVG(COALESCE(disk_percent, 0)) as avg_disk
            FROM servers
            """
        )
        row = cursor.fetchone()
        if not row:
            return {"summary": {"total": 0, "online": 0, "offline": 0, "avg_cpu": 0, "avg_memory": 0, "avg_disk": 0}}
        return {
            "summary": {
                "total": row[0],
                "online": row[1],
                "offline": row[2],
                "avg_cpu": float(row[3] or 0),
                "avg_memory": float(row[4] or 0),
                "avg_disk": float(row[5] or 0),
            }
        }
    finally:
        conn.close()


@api.get("/servers/{server_id}/uptime-timeline")
async def get_server_uptime_timeline_endpoint(
    server_id: int,
    days: int = Query(7, ge=1, le=30),
):
    """Return uptime timeline for a server over the last N days"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
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
        if not rows:
            return {"timeline": [], "uptime_percent": 0}
        timeline = [{"timestamp": r[0], "status": (r[1] if r[1] else "down")} for r in rows]
        total = len(timeline)
        up_count = sum(1 for t in timeline if t["status"] == "up")
        uptime_percent = round((up_count / total * 100) if total > 0 else 0, 2)
        return {"timeline": timeline, "uptime_percent": uptime_percent}
    finally:
        conn.close()


@api.get("/servers/{server_id}/disk-breakdown")
async def get_server_disk_breakdown_endpoint(server_id: int):
    """Return per-disk breakdown for a server"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT disk_info FROM servers WHERE id = ?", (server_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return {"disks": []}
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
    finally:
        conn.close()


@api.get("/backup/list")
async def list_backups_endpoint():
    db_path = os.getenv("DB_PATH", "pymon.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT filename, size_bytes, created_at FROM backups ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        return {"backups": [{"filename": r[0], "size": r[1], "created_at": r[2]} for r in rows]}
    finally:
        conn.close()


@api.post("/backup/create")
async def create_backup_endpoint():
    # Lightweight backup creation: zip DB and config if present
    import zipfile
    from datetime import datetime

    backup_dir = os.path.join(os.path.dirname(os.getenv("DB_PATH", "pymon.db")), "backups")
    import os

    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zipname = f"pymon_backup_{ts}.zip"
    zippath = os.path.join(backup_dir, zipname)
    import shutil

    with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(os.getenv("DB_PATH", "pymon.db")):
            zf.write(os.getenv("DB_PATH"), arcname=os.path.basename(os.getenv("DB_PATH")))
        if os.path.exists("config.yml"):
            zf.write("config.yml", arcname="config.yml")
        if os.path.exists("config.example.yml"):
            zf.write("config.example.yml", arcname="config.example.yml")
    try:
        import sqlite3

        conn = sqlite3.connect(os.getenv("DB_PATH", "pymon.db"))
        c = conn.cursor()
        c.execute(
            "INSERT INTO backups (filename, size_bytes, created_at) VALUES (?, ?, ?)",
            (zipname, os.path.getsize(zippath), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return {"status": "ok", "filename": zipname}
