import os
import json
import sqlite3
import aiosqlite
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any
from pydantic import BaseModel

from pymon.auth import User, get_current_user
from pymon.api.deps import get_db
from pymon.api import models as api_models

router = APIRouter(prefix="/servers", tags=["servers"])

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
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO servers (name, host, os_type, agent_port, enabled, server_group, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data.name,
                data.host,
                data.os_type,
                data.agent_port,
                int(data.enabled),
                data.server_group,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        server_id = c.lastrowid
        return {"status": "ok", "id": server_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
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
    conn = get_db()
    try:
        fields = []
        params = []
        for field, value in data.dict(exclude_unset=True).items():
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

@router.post("/{server_id}/scrape")
async def force_scrape_server(server_id: int, current_user: User = Depends(get_current_user)):
    # This usually triggers a scrape job in ScrapeManager
    # For now we'll just return OK, or we can import ScrapeManager if needed
    return {"status": "scrape_queued"}

@router.get("/{server_id}/history", response_model=api_models.HistoryResponse)
async def get_server_history(
    server_id: int,
    range: str = Query("1h", pattern="^(5m|15m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
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
async def get_server_summary(server_id: int):
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
async def get_all_servers_summary():
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
