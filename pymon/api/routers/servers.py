import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from pymon.api import models as api_models
from pymon.api.deps import get_db
from pymon.auth import User, get_admin_user, get_current_user
from pymon.constants import time_filter as _time_filter
from pymon.validation import validate_port, validate_server_host, validate_server_name

router = APIRouter(prefix="/servers", tags=["servers"])

class ServerCreate(BaseModel):
    name: str
    host: str
    os_type: str
    agent_port: int | None = None
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
def list_servers(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM servers ORDER BY name").fetchall()
        return {"servers": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("")
def create_server(data: ServerCreate, current_user: User = Depends(get_admin_user)):
    validate_server_name(data.name)
    host = validate_server_host(data.host)
    port = data.agent_port or (9182 if data.os_type == 'windows' else 9100)
    validate_port(port)
    conn = get_db()
    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO servers (name, host, agent_port, os_type, enabled, server_group, scrape_interval, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data.name, host, port, data.os_type, int(data.enabled), data.server_group, data.scrape_interval, now)
        )
        conn.commit()
        server_id = cursor.lastrowid
        return {"status": "ok", "id": server_id}
    finally:
        conn.close()


@router.get("/history")
def get_aggregated_history(
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    metric: str | None = Query(None, pattern="^(cpu|memory|disk|net)$"),
    current_user: User = Depends(get_current_user),
):
    """Aggregated metrics history for all servers."""
    time_filter = _time_filter(range)
    try:
        conn = get_db()
        try:
            servers = conn.execute("SELECT id, name, host FROM servers ORDER BY name").fetchall()
            # Single query for all servers (avoids an N+1 query-per-server fan-out).
            rows = conn.execute(
                """
                SELECT server_id, timestamp, cpu_percent, memory_percent, disk_percent,
                       network_rx, network_tx, disk_info
                FROM metrics_history
                WHERE timestamp > datetime('now', ?)
                ORDER BY server_id, timestamp
                """,
                (time_filter,),
            ).fetchall()
        finally:
            conn.close()

        history_by_server: dict[int, list] = {}
        for r in rows:
            dinfo = None
            try:
                if r[7]:
                    dinfo = json.loads(r[7])
            except Exception:
                pass
            item = {"timestamp": r[1]}
            if not metric or metric == "cpu":
                item["cpu"] = r[2]
            if not metric or metric == "memory":
                item["mem"] = r[3]
            if not metric or metric == "disk":
                item["disk"] = r[4]
                item["disk_info"] = dinfo
            if not metric or metric == "net":
                item["net_rx"] = r[5]
                item["net_tx"] = r[6]
            history_by_server.setdefault(r[0], []).append(item)

        servers_data = [
            {"id": srv["id"], "name": srv["name"], "host": srv["host"],
             "history": history_by_server.get(srv["id"], [])}
            for srv in servers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"range": range, "servers": servers_data}


@router.get("/{server_id}/history-detail")
def get_server_history_detail(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user),
):
    """Alias for /{server_id}/history to match test expectations."""
    return _server_history(server_id, range)


@router.get("/{server_id}/disk-breakdown")
def get_disk_breakdown(
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
            size = v.get("size")
            free = v.get("free")
            size_gb = round(size / (1024**3), 2) if isinstance(size, (int, float)) else 0
            free_gb = round(free / (1024**3), 2) if isinstance(free, (int, float)) else 0
            used_gb = round(max(0.0, size_gb - free_gb), 2)
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
def get_uptime_timeline(
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
def export_server(
    server_id: int,
    range: str = Query("24h", pattern="^(1h|6h|12h|24h|3d|7d)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
):
    """Export server metrics as JSON or CSV."""
    time_filter = _time_filter(range, default="-24 hours")
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
def export_all_servers(
    range: str = Query("24h", pattern="^(1h|6h|12h|24h|3d|7d)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
):
    """Export all servers' metrics."""
    time_filter = _time_filter(range, default="-24 hours")
    conn = get_db()
    try:
        servers = conn.execute("SELECT id, name, host FROM servers ORDER BY name").fetchall()
        # Single query for all servers instead of one query per server (N+1).
        all_rows = conn.execute(
            """
            SELECT server_id, timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx
            FROM metrics_history
            WHERE timestamp > datetime('now', ?)
            ORDER BY server_id, timestamp
            """,
            (time_filter,),
        ).fetchall()
        data_by_server: dict[int, list] = {}
        for r in all_rows:
            data_by_server.setdefault(r["server_id"], []).append({
                "timestamp": r["timestamp"], "cpu": r["cpu_percent"],
                "memory": r["memory_percent"], "disk": r["disk_percent"],
                "network_rx": r["network_rx"], "network_tx": r["network_tx"],
            })
        result = [
            {"id": s["id"], "name": s["name"], "host": s["host"],
             "data": data_by_server.get(s["id"], [])}
            for s in servers
        ]
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["server_id", "server_name", "host", "timestamp", "cpu", "memory", "disk", "network_rx", "network_tx"])
            for srv in result:
                for d in srv["data"]:
                    writer.writerow([srv["id"], srv["name"], srv["host"], d["timestamp"], d["cpu"], d["memory"], d["disk"], d["network_rx"], d["network_tx"]])
            return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=all_servers_{range}.csv"})
        return {"range": range, "servers": result}
    finally:
        conn.close()


@router.get("/compare")
def compare_servers(
    metric: str = Query("cpu", pattern="^(cpu|memory|disk)$"),
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d)$"),
    current_user: User = Depends(get_current_user),
):
    """Compare a metric across all servers."""
    # Column name comes from a fixed whitelist, so it's safe to interpolate.
    col = {"cpu": "cpu_percent", "memory": "memory_percent", "disk": "disk_percent"}.get(metric, "cpu_percent")
    time_filter = _time_filter(range)
    conn = get_db()
    try:
        servers = conn.execute("SELECT id, name FROM servers ORDER BY name").fetchall()
        # Full SQL templates keyed by column name — no interpolation needed.
        _QUERIES = {
            "cpu_percent": """
                SELECT server_id, AVG(cpu_percent), MIN(cpu_percent), MAX(cpu_percent), COUNT(cpu_percent)
                FROM metrics_history
                WHERE timestamp > datetime('now', ?) AND cpu_percent IS NOT NULL
                GROUP BY server_id
            """,
            "memory_percent": """
                SELECT server_id, AVG(memory_percent), MIN(memory_percent), MAX(memory_percent), COUNT(memory_percent)
                FROM metrics_history
                WHERE timestamp > datetime('now', ?) AND memory_percent IS NOT NULL
                GROUP BY server_id
            """,
            "disk_percent": """
                SELECT server_id, AVG(disk_percent), MIN(disk_percent), MAX(disk_percent), COUNT(disk_percent)
                FROM metrics_history
                WHERE timestamp > datetime('now', ?) AND disk_percent IS NOT NULL
                GROUP BY server_id
            """,
        }
        agg_rows = conn.execute(
            _QUERIES[col],
            (time_filter,),
        ).fetchall()
        agg = {r[0]: r for r in agg_rows}
        result = []
        for s in servers:
            a = agg.get(s["id"])
            count = a[4] if a else 0
            result.append({
                "server_id": s["id"],
                "server_name": s["name"],
                "metric": metric,
                "average": round(a[1], 2) if count else 0,
                "min": round(a[2], 2) if count else 0,
                "max": round(a[3], 2) if count else 0,
                "data_points": count,
            })
        return {"metric": metric, "range": range, "servers": result}
    finally:
        conn.close()


@router.get("/{server_id}")
def get_server(server_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Server not found")
        return dict(row)
    finally:
        conn.close()

@router.put("/{server_id}")
def update_server(server_id: int, data: ServerUpdate, current_user: User = Depends(get_admin_user)):
    if data.host is not None:
        data.host = validate_server_host(data.host)
    if data.agent_port is not None:
        validate_port(data.agent_port)
    if data.name is not None:
        validate_server_name(data.name)
    conn = get_db()
    try:
        fields = []
        params = []
        # Defense-in-depth: only allow known model columns to be built into SQL.
        allowed_columns = set(ServerUpdate.model_fields)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field not in allowed_columns:
                continue
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
def delete_server(server_id: int, current_user: User = Depends(get_admin_user)):
    conn = get_db()
    try:
        # Clean up dependent rows too, so deleting a server leaves no orphans.
        conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        conn.execute("DELETE FROM metrics_history WHERE server_id = ?", (server_id,))
        conn.execute("DELETE FROM alerts WHERE server_id = ?", (server_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

@router.post("/{server_id}/maintenance")
def toggle_maintenance(server_id: int, data: api_models.MaintenanceToggle, current_user: User = Depends(get_admin_user)):
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

def _server_history(server_id: int, range: str) -> dict:
    """Core history query, callable directly (no DI) so route aliases can reuse it."""
    time_filter = _time_filter(range)
    history = []
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, disk_info
                FROM metrics_history
                WHERE server_id = ?
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp
                """,
                (server_id, time_filter),
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            dinfo = None
            try:
                if r[6]:
                    dinfo = json.loads(r[6])
            except Exception:
                pass
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


@router.get("/{server_id}/history", response_model=api_models.HistoryResponse)
def get_server_history(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user),
):
    return _server_history(server_id, range)

@router.get("/{server_id}/summary")
def get_server_summary(server_id: int, current_user: User = Depends(get_current_user)):
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
def get_all_servers_summary(current_user: User = Depends(get_current_user)):
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
