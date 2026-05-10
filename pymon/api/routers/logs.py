import os
import sqlite3
from fastapi import APIRouter, Depends, Query
from pymon.auth import User, get_current_user
from pymon.api.deps import get_db

router = APIRouter(prefix="/audit-log", tags=["logs"])

@router.get("")
async def get_audit_logs(limit: int = Query(100, le=1000), current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"logs": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.delete("")
async def clear_audit_logs(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM audit_logs")
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
