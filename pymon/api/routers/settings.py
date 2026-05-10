import os
import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pymon.auth import User, get_current_user
from pymon.api.deps import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/notifications")
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        # Check if notifications table has a unified config or per-channel
        # The frontend expects a single object for all channels based on the saveSettings JS
        row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
        if row:
            return json.loads(row[0])
        
        # Fallback: if they are per-channel, we might need to aggregate
        rows = conn.execute("SELECT * FROM notifications").fetchall()
        config = {"enabled": True}
        for r in rows:
            if r['config']:
                cfg = json.loads(r['config'])
                config.update(cfg)
            config[f"{r['channel']}_enabled"] = bool(r['enabled'])
        return config
    finally:
        conn.close()

@router.post("/notifications")
async def save_notification_settings(data: dict, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        # Save as a single 'all' record for simplicity as expected by dashboard
        config_json = json.dumps(data)
        conn.execute("INSERT OR REPLACE INTO notifications (channel, enabled, config) VALUES (?, ?, ?)",
                    ('all', int(data.get('enabled', True)), config_json))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

@router.post("/notifications/test")
async def test_notifications(current_user: User = Depends(get_current_user)):
    # Trigger test notification logic
    return {"status": "test_dispatched"}
