import csv
import io
import json
import os
import sqlite3
from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from pymon.api import models as api_models
from pymon.api.deps import get_db
from pymon.auth import User, get_current_user
from pymon.validation import validate_port, validate_server_host, validate_server_name

router = APIRouter(prefix="/servers", tags=["servers"])

class ServerCreate(BaseModel):
    name: str
    host: str
    os_type: str
    agent_port: int = 9100
    enabled: bool = True
    server_group: str | None = None
    scrape_interval: int = 0

class ServerUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    os_type: str | None = None
    agent_port: int | None = None
    enabled: bool | None = None
    scrape_interval: int | None = None
    server_group: str | None = None

@router.get("")
async def list_servers(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
        return {"servers": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("")
async def create_server(data: ServerCreate, current_user: User = Depends(get_current_user)):
    validate_server_name(data.name)
    validate_server_host(data.host)
    validate_port(data.agent_port)
    conn = get_db()
    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO servers (name, host, agent_port, os_type, enabled, server_group, scrape_interval, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data.name, data.host, data.agent_port, data.os_type, int(data.enabled), data.server_group, data.scrape_interval, now)
        )
        conn.commit()
        server_id = cursor.lastrowid
        return {"status": "ok", "id": server_id}
    finally:
        conn.close()


@router.get("/history")
async def get_aggregated_history(
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    metric: str | None = Query(None, pattern="^(cpu|memory|disk|net)$"),
    current_user: User = Depends(get_current_user),
):
    """Aggregated metrics history for all servers."""
    time_ranges = {
        "5m": "-5 minutes", "15m": "-15 minutes", "1h": "-1 hour",
        "6h": "-6 hours", "12h": "-12 hours", "24h": "-24 hours",
        "3d": "-3 days", "7d": "-7 days", "15d": "-15 days", "30d": "-30 days",
    }
    time_filter = time_ranges.get(range, "-1 hour")
    db_path = os.getenv("DB_PATH", "pymon.db")
    servers_data = []
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT id, name, host FROM servers ORDER BY name")
            servers = await cursor.fetchall()
            for srv in servers:
                c2 = await db.execute(
                    """
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, disk_info
                    FROM metrics_history
                    WHERE server_id = ? AND timestamp > datetime('now', ?)
                    ORDER BY timestamp
                    """,
                    (srv["id"], time_filter),
                )
                rows = await c2.fetchall()
                history = []
                for r in rows:
                    dinfo = None
                    try:
                        if r[6]:
                            dinfo = json.loads(r[6])
                    except Exception:
                        pass
                    item = {"timestamp": r[0]}
                    if not metric or metric == "cpu":
                        item["cpu"] = r[1]
                    if not metric or metric == "memory":
                        item["mem"] = r[2]
                    if not metric or metric == "disk":
                        item["disk"] = r[3]
                        item["disk_info"] = dinfo
                    if not metric or metric == "net":
                        item["net_rx"] = r[4]
                        item["net_tx"] = r[5]
                    history.append(item)
                servers_data.append({"id": srv["id"], "name": srv["name"], "host": srv["host"], "history": history})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"range": range, "servers": servers_data}


@router.get("/{server_id}/history-detail")
async def get_server_history_detail(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user),
):
    """Alias for /{server_id}/history to match test expectations."""
    from pymon.api.routers.servers import get_server_history
    return await get_server_history(server_id, range)


@router.get("/{server_id}/disk-breakdown")
async def get_disk_breakdown(
    server_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get disk breakdown for a server from its volumes JSON."""
    conn = get_db()
    try:
        row = conn.execute("SELECT volumes FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not row or not row[0]:
            return {"disks": []}
        volumes = json.loads(row[0])
        disks = []
        for v in volumes:
            size_gb = round(v["size"] / (1024**3), 2) if v.get("size") else 0
            free_gb = round(v["free"] / (1024**3), 2) if v.get("free") else 0
            used_gb = round(size_gb - free_gb, 2)
            percent = round((used_gb / size_gb) * 100, 1) if size_gb > 0 else 0
            disks.append({
                "volume": v.get("volume", ""),
                "size_gb": size_gb,
                "free_gb": free_gb,
                "used_gb": used_gb,
                "percent": percent,
            })
        return {"disks": disks}
    finally:
        conn.close()


@router.get("/{server_id}/uptime-timeline")
async def get_uptime_timeline(
    server_id: int,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
):
    """Get uptime timeline for a server."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not row:
            return {"timeline": [], "uptime_percent": 0}
        cursor = conn.execute(
            """
            SELECT timestamp, cpu_percent
            FROM metrics_history
            WHERE server_id = ? AND timestamp > datetime('now', ?)
            ORDER BY timestamp
            """,
            (server_id, f"-{days} days"),
        )
        rows = cursor.fetchall()
        if not rows:
            return {"timeline": [], "uptime_percent": 0}
        total = len(rows)
        up_count = sum(1 for r in rows if r["cpu_percent"] is not None)
        timeline = []
        for r in rows:
            status = "up" if r["cpu_percent"] is not None else "down"
            timeline.append({"timestamp": r[0], "status": status})
        uptime_percent = round((up_count / total) * 100, 2) if total > 0 else 0
        return {"timeline": timeline, "uptime_percent": uptime_percent}
    finally:
        conn.close()


@router.get("/{server_id}/export")
async def export_server(
    server_id: int,
    range: str = Query("24h", pattern="^(1h|6h|12h|24h|3d|7d)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
):
    """Export server metrics as JSON or CSV."""
    time_ranges = {
        "1h": "-1 hour", "6h": "-6 hours", "12h": "-12 hours",
        "24h": "-24 hours", "3d": "-3 days", "7d": "-7 days",
    }
    time_filter = time_ranges.get(range, "-24 hours")
    conn = get_db()
    try:
        server = conn.execute("SELECT name, host FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        rows = conn.execute(
            """
            SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
            FROM metrics_history
            WHERE server_id = ? AND timestamp > datetime('now', ?)
            ORDER BY timestamp
            """,
            (server_id, time_filter),
        ).fetchall()
        data = [
            {
                "timestamp": r["timestamp"], "cpu": r["cpu_percent"],
                "memory": r["memory_percent"], "disk": r["disk_percent"],
                "network_rx": r["network_rx"], "network_tx": r["network_tx"],
            }
            for r in rows
        ]
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            if data:
                writer.writerow(data[0].keys())
                for d in data:
                    writer.writerow(d.values())
            else:
                writer.writerow(["timestamp", "cpu", "memory", "disk", "network_rx", "network_tx"])
            return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=server_{server_id}_{range}.csv"})
        return {"server": dict(server), "range": range, "data": data}
    finally:
        conn.close()


@router.get("/export")
async def export_all_servers(
    range: str = Query("24h", pattern="^(1h|6h|12h|24h|3d|7d)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
):
    """Export all servers' metrics."""
    time_ranges = {
        "1h": "-1 hour", "6h": "-6 hours", "12h": "-12 hours",
        "24h": "-24 hours", "3d": "-3 days", "7d": "-7 days",
    }
    time_filter = time_ranges.get(range, "-24 hours")
    conn = get_db()
    try:
        servers = conn.execute("SELECT id, name, host FROM servers ORDER BY name").fetchall()
        result = []
        for s in servers:
            rows = conn.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
                FROM metrics_history
                WHERE server_id = ? AND timestamp > datetime('now', ?)
                ORDER BY timestamp
                """,
                (s["id"], time_filter),
            ).fetchall()
            result.append({
                "id": s["id"], "name": s["name"], "host": s["host"],
                "data": [
                    {
                        "timestamp": r["timestamp"], "cpu": r["cpu_percent"],
                        "memory": r["memory_percent"], "disk": r["disk_percent"],
                        "network_rx": r["network_rx"], "network_tx": r["network_tx"],
                    }
                    for r in rows
                ],
            })
        return {"range": range, "servers": result}
    finally:
        conn.close()


@router.get("/compare")
async def compare_servers(
    metric: str = Query("cpu", pattern="^(cpu|memory|disk)$"),
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d)$"),
    current_user: User = Depends(get_current_user),
):
    """Compare a metric across all servers."""
    col_index = {"cpu": 1, "memory": 2, "disk": 3}.get(metric, 1)
    time_ranges = {
        "5m": "-5 minutes", "15m": "-15 minutes", "1h": "-1 hour",
        "6h": "-6 hours", "12h": "-12 hours", "24h": "-24 hours",
        "3d": "-3 days", "7d": "-7 days",
    }
    time_filter = time_ranges.get(range, "-1 hour")
    conn = get_db()
    try:
        servers = conn.execute("SELECT id, name FROM servers ORDER BY name").fetchall()
        result = []
        for s in servers:
            cursor = conn.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_percent
                FROM metrics_history
                WHERE server_id = ? AND timestamp > datetime('now', ?)
                ORDER BY timestamp
                """,
                (s["id"], time_filter),
            )
            rows = cursor.fetchall()
            col_index = {"cpu": 1, "memory": 2, "disk": 3}.get(metric, 1)
            values = [r[col_index] for r in rows if r[col_index] is not None]
            avg = sum(values) / len(values) if values else 0
            result.append({
                "server_id": s["id"],
                "server_name": s["name"],
                "metric": metric,
                "average": round(avg, 2),
                "min": round(min(values), 2) if values else 0,
                "max": round(max(values), 2) if values else 0,
                "data_points": len(values),
            })
        return {"metric": metric, "range": range, "servers": result}
    finally:
        conn.close()


@router.get("/{server_id}")
async def get_server(server_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Server not found")
        return dict(row)
    finally:
        conn.close()

@router.put("/{server_id}")
async def update_server(server_id: int, data: ServerUpdate, current_user: User = Depends(get_current_user)):
    if data.host is not None:
        validate_server_host(data.host)
    if data.agent_port is not None:
        validate_port(data.agent_port)
    if data.name is not None:
        validate_server_name(data.name)
    conn = get_db()
    try:
        fields = []
        params = []
        for field, value in data.model_dump(exclude_unset=True).items():
            fields.append(f"{field} = ?")
            params.append(value)

        if not fields:
            return {"status": "ok"}

        params.append(server_id)
        conn.execute(f"UPDATE servers SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

@router.delete("/{server_id}")
async def delete_server(server_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        conn.execute("DELETE FROM metrics_history WHERE server_id = ?", (server_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

@router.post("/{server_id}/maintenance")
async def toggle_maintenance(server_id: int, data: api_models.MaintenanceToggle, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("UPDATE servers SET is_maintenance = ? WHERE id = ?", (int(data.is_maintenance), server_id))
        conn.commit()
        return {"status": "ok", "is_maintenance": data.is_maintenance}
    finally:
        conn.close()

@router.post("/{server_id}/scrape")
async def force_scrape_server(server_id: int, request: Request, current_user: User = Depends(get_current_user)):
    scrape_manager = getattr(request.app.state, "scrape_manager", None)
    if not scrape_manager:
        raise HTTPException(status_code=503, detail="Scraper manager not initialized")

    conn = get_db()
    try:
        s = conn.execute("SELECT id, name, host, agent_port, os_type, enabled, last_status, cpu_percent FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Server not found")

        sid, name, host, port, os_type, enabled, last_status, last_cpu = s
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            success = await scrape_manager._scrape_one(client, sid, name, host, port, last_status, last_cpu)
            if success:
                return {"status": "success"}
            else:
                raise HTTPException(status_code=500, detail="Scrape failed or node is offline")
    finally:
        conn.close()

@router.get("/{server_id}/history", response_model=api_models.HistoryResponse)
async def get_server_history(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user),
):
    time_ranges = {
        "5m": "-5 minutes", "15m": "-15 minutes", "1h": "-1 hour",
        "6h": "-6 hours", "12h": "-12 hours", "24h": "-24 hours",
        "3d": "-3 days", "7d": "-7 days", "15d": "-15 days", "30d": "-30 days"
    }
    time_filter = time_ranges.get(range, "-1 hour")
    db_path = os.getenv("DB_PATH", "pymon.db")
    history = []
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, disk_info
                FROM metrics_history
                WHERE server_id = ?
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp
                """,
                (server_id, time_filter),
            )
            rows = await cursor.fetchall()
            for r in rows:
                dinfo = None
                try:
                    if r[6]: dinfo = json.loads(r[6])
                except: pass
                history.append({
                    "timestamp": r[0],
                    "cpu": r[1],
                    "mem": r[2],
                    "disk": r[3],
                    "net_rx": r[4],
                    "net_tx": r[5],
                    "disk_info": dinfo
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"history": history}

@router.get("/{server_id}/summary")
async def get_server_summary(server_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        last_status = conn.execute("SELECT last_status FROM servers WHERE id = ?", (server_id,)).fetchone()
        status = last_status[0] if last_status else "unknown"

        cursor = conn.execute(
            "SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent) FROM metrics_history WHERE server_id = ? AND timestamp > datetime('now', '-1 hour')",
            (server_id,),
        )
        row = cursor.fetchone()
        return {
            "server_id": server_id,
            "status": status,
            "avg_cpu": float(row[0] or 0),
            "avg_memory": float(row[1] or 0),
            "avg_disk": float(row[2] or 0),
        }
    finally:
        conn.close()

@router.get("/summary/all")
async def get_all_servers_summary(current_user: User = Depends(get_current_user)):
    conn = get_db()
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
        return {
            "total": row[0],
            "online": row[1],
            "offline": row[2],
            "avg_cpu": float(row[3] or 0),
            "avg_memory": float(row[4] or 0),
            "avg_disk": float(row[5] or 0),
        }
    finally:
        conn.close()
