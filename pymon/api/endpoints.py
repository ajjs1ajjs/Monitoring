"""FastAPI API endpoints"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

    _PROM_METRICS_ENABLED = True
    _PROM_SERVER_COUNT = Gauge("pymon_servers_total", "Total number of servers")
except Exception:
    _PROM_METRICS_ENABLED = False

from fastapi import WebSocket, WebSocketDisconnect
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
    get_admin_user,
    get_current_user,
    list_api_keys,
)
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, MetricType
from pymon.storage import get_storage


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()

api = APIRouter()


@api.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


_limiter = Limiter(key_func=get_remote_address)


def get_db():
    """Get database connection - reads DB_PATH from environment each time"""
    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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


class ServerCreate(BaseModel):
    name: str
    host: str
    os_type: str
    agent_port: int = 9100
    enabled: bool = True
    server_group: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    os_type: str | None = None
    agent_port: int | None = None
    enabled: bool | None = None


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


@api.get("/auth/users")
async def list_users(current_user: User = Depends(get_admin_user)):
    from pymon.auth import list_users as _list_users

    return {"users": _list_users()}


@api.post("/auth/users")
async def create_user(data: dict, current_user: User = Depends(get_admin_user)):
    from pymon.auth import create_user as _create_user

    try:
        user = _create_user(
            username=data.get("username"),
            password=data.get("password", "changeme"),
            is_admin=data.get("is_admin", False),
        )
        return {"status": "ok", "user_id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.put("/auth/users/{user_id}")
async def update_user(user_id: int, data: dict, current_user: User = Depends(get_admin_user)):
    from pymon.auth import update_user as _update_user

    _update_user(user_id, is_admin=data.get("is_admin"), must_change_password=data.get("must_change_password"))
    return {"status": "ok"}


@api.delete("/auth/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_admin_user)):
    from fastapi import HTTPException

    from pymon.auth import delete_user as _delete_user

    try:
        _delete_user(user_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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

    labels = [Label(name=lbl["name"], value=lbl["value"]) for lbl in payload.labels]
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

        db_path = os.getenv("DB_PATH", "pymon.db")
        conn = sqlite3.connect(db_path)
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
    from datetime import datetime, timezone

    conn = get_db()
    c = conn.cursor()
    try:
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
        return {"status": "ok", "id": alert_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@api.get("/audit-log")
async def get_audit_log(limit: int = 100):
    """Return recent actions from the audit log"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        logs = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"logs": [dict(l) for l in logs]}
    finally:
        conn.close()


@api.get("/notifications")
async def get_notifications():
    """Return notification channels configuration"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM notifications").fetchall()
        result = []
        for r in rows:
            cfg = json.loads(r["config"]) if r["config"] else {}
            result.append({"channel": r["channel"], "enabled": bool(r["enabled"]), "config": cfg})
        return {"notifications": result}
    finally:
        conn.close()


@api.put("/notifications/{channel}")
async def update_notification(channel: str, data: dict):
    """Update notification channel configuration"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE notifications SET enabled = ?, config = ? WHERE channel = ?",
            (int(data.get("enabled", 0)), json.dumps(data.get("config", {})), channel),
        )
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@api.get("/health")
async def health():
    db_status = "healthy"
    try:
        import sqlite3

        db_path = os.getenv("DB_PATH", "pymon.db")
        conn = sqlite3.connect(db_path, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "unhealthy"

    return {"status": "healthy", "database": db_status, "timestamp": datetime.now(timezone.utc).isoformat()}


@api.get("/healthz")
async def healthz():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Phase 2.9: Reinstate single history endpoint with proper typing (Phase 2.10 API contract)
@api.get("/servers/{server_id}/history-detail", response_model=api_models.HistoryResponse)
async def get_server_history(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|24h|7d)$"),
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
            "SELECT id, username, action, target, timestamp FROM audit_logs WHERE target LIKE ? ORDER BY timestamp DESC LIMIT ?",
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
    format: str = Query("json", pattern="^(json|csv)$"),
    range: str = Query("24h", pattern="^(5m|15m|1h|6h|24h|7d)$"),
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
            for row in data:  # type: ignore
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
    format: str = Query("json", pattern="^(json|csv)$"),
    range: str = Query("24h", pattern="^(5m|15m|1h|6h|24h|7d)$"),
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


# Phase 2.9: Reinstate single history endpoint with proper typing (Phase 2.10 API contract)
@api.get("/servers/history", response_model=api_models.HistoryAllResponse)
async def get_all_servers_metrics_history(
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|24h|7d)$"),
    metric: str | None = Query(None, pattern="^(cpu|memory|disk|network)$"),
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

        if not servers:
            return {"range": range, "servers": []}

        results = []
        # Whitelist of allowed column names to prevent SQL injection
        allowed_columns = {
            "cpu": "cpu_percent",
            "memory": "memory_percent",
            "disk": "disk_percent",
        }
        # Network requires special handling
        for s in servers:
            sid = s[0]
            if metric:
                if metric in allowed_columns:
                    col = allowed_columns[metric]
                    rows = conn.execute(
                        f"SELECT timestamp, {col} as value FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                        (sid, time_filter),
                    ).fetchall()
                elif metric == "network":
                    rows = conn.execute(
                        "SELECT timestamp, (network_rx + network_tx) / 2.0 as value FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                        (sid, time_filter),
                    ).fetchall()
                else:
                    col = "cpu_percent"
                    rows = conn.execute(
                        "SELECT timestamp, cpu_percent as value FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', ?) ORDER BY timestamp",
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
        return {"range": range, "servers": results}
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


@api.get("/servers/compare")
async def compare_time_ranges(
    server_id: int | None = Query(None),
    metric: str = Query("cpu", pattern="^(cpu|memory|disk|network)$"),
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|24h|7d)$"),
):
    """Compare current period vs previous period for trends"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    time_ranges = {"5m": 5, "15m": 15, "1h": 60, "6h": 360, "24h": 1440, "7d": 10080}
    minutes = time_ranges.get(range, 60)

    try:
        # Current period
        cursor = conn.execute(
            f"""
            SELECT AVG(cpu_percent) as cpu, AVG(memory_percent) as mem,
                   AVG(disk_percent) as disk, AVG(network_rx) as rx, AVG(network_tx) as tx
            FROM metrics_history
            WHERE (? IS NULL OR server_id = ?)
            AND timestamp > datetime('now', '-{minutes} minutes')
            AND timestamp <= datetime('now')
            """,
            (server_id, server_id),
        )
        current = cursor.fetchone()

        # Previous period
        cursor = conn.execute(
            f"""
            SELECT AVG(cpu_percent) as cpu, AVG(memory_percent) as mem,
                   AVG(disk_percent) as disk, AVG(network_rx) as rx, AVG(network_tx) as tx
            FROM metrics_history
            WHERE (? IS NULL OR server_id = ?)
            AND timestamp > datetime('now', '-{minutes * 2} minutes')
            AND timestamp <= datetime('now', '-{minutes} minutes')
            """,
            (server_id, server_id),
        )
        previous = cursor.fetchone()

        metric_cols = {"cpu": ["cpu"], "memory": ["mem"], "disk": ["disk"], "network": ["rx", "tx"]}
        target_cols = metric_cols.get(metric, ["cpu"])

        def get_avg_val(row, cols):
            if not row:
                return 0.0
            vals = []
            for col in cols:
                try:
                    val = row[col]
                    vals.append(float(val) if val is not None else 0.0)
                except (IndexError, KeyError, TypeError, ValueError):
                    vals.append(0.0)
            return sum(vals) / len(vals) if vals else 0.0

        current_val = get_avg_val(current, target_cols)
        previous_val = get_avg_val(previous, target_cols)

        delta = current_val - previous_val
        delta_percent = round((delta / previous_val * 100) if previous_val > 0 else 0, 2)

        return {
            "current": round(current_val, 2),
            "previous": round(previous_val, 2),
            "delta": round(delta, 2),
            "delta_percent": delta_percent,
            "trend": "up" if delta > 0.5 else "down" if delta < -0.5 else "stable",
        }
    except Exception as e:
        print(f"Error in compare_time_ranges: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zipname = f"pymon_backup_{ts}.zip"
    zippath = os.path.join(backup_dir, zipname)
    with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as zf:
        db_path = os.getenv("DB_PATH", "pymon.db")
        if os.path.exists(db_path):
            zf.write(db_path, arcname=os.path.basename(db_path))
        if os.path.exists("config.yml"):
            zf.write("config.yml", arcname="config.yml")
        if os.path.exists("config.example.yml"):
            zf.write("config.example.yml", arcname="config.example.yml")
    try:
        import sqlite3

        conn = sqlite3.connect(db_path)
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


@api.get("/servers")
async def list_servers_api():
    """List all monitored servers - unified endpoint for UI"""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
        return {"servers": [dict(r) for r in rows]}
    except Exception:
        return {"servers": []}
    finally:
        conn.close()


@api.post("/servers")
async def create_server(request: Request, data: ServerCreate, current_user: User = Depends(get_admin_user)):
    import sqlite3
    from datetime import datetime, timezone

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO servers (name, host, os_type, agent_port, enabled, last_status, cpu_percent, memory_percent, disk_percent, disk_info, last_check, created_at, server_group) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.name,
                data.host,
                data.os_type,
                data.agent_port,
                int(data.enabled),
                "unknown",
                0.0,
                0.0,
                0.0,
                "[]",
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                data.server_group or "default",
            ),
        )
        conn.commit()

        # Log action
        c.execute(
            "INSERT INTO audit_logs (username, action, target, timestamp) VALUES (?, ?, ?, ?)",
            (current_user.username, "Add Server", f"{data.name} ({data.host})", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

        server_id = c.lastrowid

        # Phase 2.11: Update ScrapeManager dynamically
        scrape_manager = getattr(request.app.state, "scrape_manager", None)
        if scrape_manager and data.enabled:
            row = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
            if row:
                server_dict = dict(row)
                scrape_manager.add_server_target(server_dict)
                if not scrape_manager._running:
                    scrape_manager.start()

        return {"status": "ok", "server_id": server_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@api.put("/servers/{server_id}")
async def update_server(
    server_id: int, request: Request, data: ServerUpdate, current_user: User = Depends(get_admin_user)
):
    conn = get_db()
    c = conn.cursor()
    try:
        # Check if exists
        server = c.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        updates = []
        params = []
        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.host is not None:
            updates.append("host = ?")
            params.append(data.host)
        if data.os_type is not None:
            updates.append("os_type = ?")
            params.append(data.os_type)
        if data.agent_port is not None:
            updates.append("agent_port = ?")
            params.append(data.agent_port)
        if data.enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if data.enabled else 0)

        if not updates:
            return {"status": "no_changes"}

        params.append(server_id)
        c.execute(f"UPDATE servers SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()

        # Update ScrapeManager dynamically
        scrape_manager = getattr(request.app.state, "scrape_manager", None)
        if scrape_manager:
            # Refresh targets from DB
            updated_server = c.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
            scrape_manager.remove_target("agents", f"{server['host']}:{server['agent_port']}")
            if updated_server["enabled"]:
                scrape_manager.add_server_target(dict(updated_server))

        return {"status": "ok"}
    finally:
        conn.close()


@api.delete("/servers/{server_id}")
async def delete_server(server_id: int, current_user: User = Depends(get_admin_user)):
    """Delete a monitored server and its historical metrics."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        # Also cleanup metrics
        conn.execute("DELETE FROM metrics WHERE labels LIKE ?", (f"%server_id={server_id}%",))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Server not found")
        return {"status": "ok"}
    finally:
        conn.close()


@api.get("/metrics/trend")
async def get_metrics_trend(current_user: User = Depends(get_current_user)):
    """Get aggregated metrics trend for the overview dashboard."""
    import sqlite3
    from datetime import datetime, timedelta, timezone

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Use metrics_history for more reliable structured data
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        query = """
            SELECT
                substr(timestamp, 1, 16) as ts,
                AVG(cpu_percent) as cpu_avg,
                AVG(memory_percent) as mem_avg,
                AVG(disk_percent) as disk_avg,
                SUM(network_rx) as net_rx,
                SUM(network_tx) as net_tx
            FROM metrics_history
            WHERE timestamp > ?
            GROUP BY ts
            ORDER BY ts ASC
            LIMIT 60
        """
        rows = conn.execute(query, (cutoff,)).fetchall()

        history = []
        for r in rows:
            history.append(
                {
                    "timestamp": r["ts"] + ":00Z",
                    "cpu_avg": round(r["cpu_avg"] or 0, 1),
                    "mem_avg": round(r["mem_avg"] or 0, 1),
                    "disk_avg": round(r["disk_avg"] or 0, 1),
                    "net_rx_avg": r["net_rx"] or 0,
                    "net_tx_avg": r["net_tx"] or 0,
                }
            )

        if not history:
            now = datetime.now(timezone.utc).isoformat()[:16] + ":00Z"
            history = [{"timestamp": now, "cpu_avg": 0, "mem_avg": 0, "net_rx_avg": 0, "net_tx_avg": 0}]

        return {"history": history}
    except Exception as e:
        return {"history": [], "error": str(e)}
    finally:
        conn.close()


@api.get("/alerts")
async def list_alerts_api(current_user: User = Depends(get_current_user)):
    """List all alert rules."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM alerts").fetchall()
        return {"alerts": [dict(r) for r in rows]}
    except Exception:
        return {"alerts": []}
    finally:
        conn.close()


@api.post("/alerts")
async def create_alert_api(data: AlertCreate, current_user: User = Depends(get_admin_user)):
    """Create a new alert rule."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO alerts (name, metric, condition, threshold, duration, severity, enabled) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.name, data.metric, data.condition, data.threshold, data.duration, data.severity, 1),
        )
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@api.delete("/alerts/{alert_id}")
async def delete_alert_api(alert_id: int, current_user: User = Depends(get_admin_user)):
    """Delete an alert rule."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@api.get("/audit-log")
async def list_audit_logs(limit: int = 50, current_user: User = Depends(get_current_user)):
    """List recent audit logs."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return {"logs": [dict(r) for r in rows]}
    except Exception:
        return {"logs": []}
    finally:
        conn.close()


class NotificationSettings(BaseModel):
    enabled: bool
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""


@api.get("/settings/notifications")
async def get_notif_settings(current_user: User = Depends(get_admin_user)):
    """Get notification settings from config.yml"""
    from pymon.config import load_config

    config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
    return config.notifications


@api.post("/settings/notifications")
async def update_notif_settings(data: NotificationSettings, current_user: User = Depends(get_admin_user)):
    """Update notification settings in config.yml"""
    import yaml

    config_path = os.getenv("CONFIG_PATH", "config.yml")

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f) or {}

    if "notifications" not in config_data:
        config_data["notifications"] = {}

    config_data["notifications"]["enabled"] = data.enabled
    config_data["notifications"]["telegram_bot_token"] = data.telegram_bot_token
    config_data["notifications"]["telegram_chat_id"] = data.telegram_chat_id
    config_data["notifications"]["discord_webhook_url"] = data.discord_webhook_url

    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)

    return {"status": "ok"}


@api.post("/servers/{server_id}/scrape")
async def force_scrape_server(server_id: int, request: Request, current_user: User = Depends(get_admin_user)):
    """Manually trigger a scrape for a specific server."""
    import sqlite3

    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        server = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        scrape_manager = getattr(request.app.state, "scrape_manager", None)
        if not scrape_manager:
            raise HTTPException(status_code=503, detail="ScrapeManager not available")

        # Find the target in the manager
        target_str = f"{server['host']}:{server['agent_port']}"
        target = None
        for t in scrape_manager.targets:
            if t.server_id == server_id or t.target == target_str:
                target = t
                break

        if not target:
            # Try to add it if missing
            target = scrape_manager.add_server_target(dict(server))

        # Trigger immediate scrape
        await scrape_manager.execute_scrape(target)

        return {"status": "ok", "message": "Scrape triggered successfully"}
    finally:
        conn.close()
