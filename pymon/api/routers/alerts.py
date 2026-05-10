import os
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from pymon.auth import User, get_current_user
from pymon.api.deps import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertCreate(BaseModel):
    name: str
    metric: str
    condition: str
    threshold: float
    duration: int = 0
    severity: str = "warning"
    server_id: int | None = None
    notify_telegram: bool = False
    notify_discord: bool = False
    notify_slack: bool = False
    notify_email: bool = False
    notify_teams: bool = False
    description: str = ""
    enabled: bool = True

@router.get("")
async def list_alerts(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
        return {"alerts": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.post("")
async def create_alert(data: AlertCreate, current_user: User = Depends(get_current_user)):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO alerts (name, metric, condition, threshold, duration, severity, server_id, 
               notify_telegram, notify_discord, notify_slack, notify_email, notify_teams, description, enabled, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.name, data.metric, data.condition, data.threshold, data.duration, data.severity, data.server_id,
                int(data.notify_telegram), int(data.notify_discord), int(data.notify_slack), 
                int(data.notify_email), int(data.notify_teams), data.description, int(data.enabled),
                datetime.now(timezone.utc).isoformat()
            )
        )
        conn.commit()
        return {"status": "ok", "id": c.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
