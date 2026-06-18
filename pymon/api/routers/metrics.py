
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from pymon.api.deps import get_db
from pymon.auth import User, get_current_user
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, Metric, MetricType
from pymon.storage import get_storage

router = APIRouter(prefix="/metrics", tags=["metrics"])

class LabelPayload(BaseModel):
    name: str
    value: str

class MetricPayload(BaseModel):
    name: str
    value: float
    type: str = "gauge"
    labels: list[LabelPayload] = []
    help_text: str = ""

@router.post("")
async def ingest_metric(payload: MetricPayload, current_user: User = Depends(get_current_user)):
    storage = get_storage()
    try:
        metric_type = MetricType(payload.type)
    except ValueError:
        metric_type = MetricType.GAUGE

    labels = [Label(name=lbl.name, value=lbl.value) for lbl in payload.labels]
    registry.register(payload.name, metric_type, payload.help_text, labels)
    registry.set(payload.name, payload.value, labels)

    metric = Metric(
        name=payload.name, value=payload.value, metric_type=metric_type, labels=labels, help_text=payload.help_text
    )
    await storage.write(metric)
    return {"status": "ok"}

@router.get("")
async def list_metrics(current_user: User = Depends(get_current_user)):
    registry_metrics = [m.to_dict() for m in registry.get_all_metrics()]

    if registry_metrics:
        return {"metrics": registry_metrics}

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT mh.server_id, s.name, mh.cpu_percent, mh.memory_percent,
                   mh.disk_percent, mh.network_rx, mh.network_tx, mh.timestamp
            FROM metrics_history mh
            JOIN servers s ON s.id = mh.server_id
            WHERE mh.timestamp = (SELECT MAX(timestamp) FROM metrics_history)
            ORDER BY mh.timestamp DESC LIMIT 20
        """)
        rows = cursor.fetchall()
        conn.close()
        return {"metrics": [
            {
                "server_id": r[0], "server_name": r[1],
                "cpu_percent": r[2], "memory_percent": r[3],
                "disk_percent": r[4], "network_rx": r[5],
                "network_tx": r[6], "timestamp": r[7]
            } for r in rows
        ]}
    except Exception:
        return {"metrics": registry_metrics}

@router.get("/trend")
async def get_metrics_trend(
    range: str = Query("1h", pattern="^(5m|15m|30m|1h|6h|12h|24h|3d|7d|15d|30d)$"),
    current_user: User = Depends(get_current_user)
):
    """Aggregate trend for all servers"""
    time_ranges = {
        "5m": "-5 minutes", "15m": "-15 minutes", "30m": "-30 minutes", "1h": "-1 hour",
        "6h": "-6 hours", "12h": "-12 hours", "24h": "-24 hours",
        "3d": "-3 days", "7d": "-7 days", "15d": "-15 days", "30d": "-30 days"
    }
    time_filter = time_ranges.get(range, "-1 hour")

    try:
        conn = get_db()
        cursor = conn.execute(
            """
            SELECT MAX(timestamp), AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent),
                   SUM(network_rx), SUM(network_tx)
            FROM metrics_history
            WHERE timestamp > datetime('now', ?)
            GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
            ORDER BY 1
            """,
            (time_filter,),
        )
        rows = cursor.fetchall()
        conn.close()
        history = [
            {
                "timestamp": r[0],
                "cpu_avg": round(r[1], 1) if r[1] is not None else None,
                "mem_avg": round(r[2], 1) if r[2] is not None else None,
                "disk_avg": round(r[3], 1) if r[3] is not None else None,
                "net_rx_avg": round(r[4], 1) if r[4] is not None else None,
                "net_tx_avg": round(r[5], 1) if r[5] is not None else None
            }
            for r in rows
        ]
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{server_id}")
async def get_server_history_alias(
    server_id: int,
    range: str = "1h",
    current_user: User = Depends(get_current_user),
):
    # Alias for servers router to maintain backward compatibility if needed
    from pymon.api.routers.servers import get_server_history
    return await get_server_history(server_id, range, current_user)

@router.delete("/history")
async def clear_metric_history(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM metrics_history")
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
