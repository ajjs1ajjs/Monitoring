import os
import sqlite3
import aiosqlite
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Any

from pymon.auth import User, get_current_user
from pymon.api.deps import get_db, manager
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, MetricType, Metric
from pymon.storage import get_storage

router = APIRouter(prefix="/metrics", tags=["metrics"])

class MetricPayload(BaseModel):
    name: str
    value: float
    type: str = "gauge"
    labels: list[dict[str, str]] = []
    help_text: str = ""

@router.post("")
async def ingest_metric(payload: MetricPayload, current_user: User = Depends(get_current_user)):
    storage = get_storage()
    try:
        metric_type = MetricType(payload.type)
    except ValueError:
        metric_type = MetricType.GAUGE

    labels = [Label(name=lbl["name"], value=lbl["value"]) for lbl in payload.labels]
    registry.register(payload.name, metric_type, payload.help_text, labels)
    registry.set(payload.name, payload.value, labels)

    metric = Metric(
        name=payload.name, value=payload.value, metric_type=metric_type, labels=labels, help_text=payload.help_text
    )
    await storage.write(metric)
    return {"status": "ok"}

@router.get("")
async def list_metrics(current_user: User = Depends(get_current_user)):
    return {"metrics": [m.to_dict() for m in registry.get_all_metrics()]}

@router.get("/trend")
async def get_metrics_trend(
    range: str = Query("1h", pattern="^(5m|30m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user)
):
    """Aggregate trend for all servers"""
    time_ranges = {
        "5m": "-5 minutes", "30m": "-30 minutes", "1h": "-1 hour",
        "6h": "-6 hours", "12h": "-12 hours", "24h": "-24 hours",
        "3d": "-3 days", "7d": "-7 days", "15d": "-15 days", "30d": "-30 days"
    }
    time_filter = time_ranges.get(range, "-1 hour")
    db_path = os.getenv("DB_PATH", "pymon.db")
    
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                """
                SELECT timestamp, AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent), 
                       SUM(network_rx), SUM(network_tx)
                FROM metrics_history
                WHERE timestamp > datetime('now', ?)
                GROUP BY timestamp
                ORDER BY timestamp
                """,
                (time_filter,),
            )
            rows = await cursor.fetchall()
            history = [
                {
                    "timestamp": r[0],
                    "cpu_avg": r[1],
                    "mem_avg": r[2],
                    "disk_avg": r[3],
                    "net_rx_avg": r[4],
                    "net_tx_avg": r[5]
                }
                for r in rows
            ]
            return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{server_id}")
async def get_server_history_alias(server_id: int, range: str = "1h"):
    # Alias for servers router to maintain backward compatibility if needed
    from pymon.api.routers.servers import get_server_history
    return await get_server_history(server_id, range)

@router.delete("/history")
async def clear_metric_history(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM metrics_history")
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
