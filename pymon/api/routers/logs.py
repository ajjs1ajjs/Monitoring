import os

from fastapi import APIRouter, Depends, HTTPException, Query

from pymon.api.deps import get_db
from pymon.auth import User, get_current_user

router = APIRouter(prefix="/audit-log", tags=["logs"])


@router.get("")
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    conn = get_db()
    try:
        total_row = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()
        total = total_row[0] if total_row else 0
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return {"logs": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}
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

# System Logs (pymon.log)
@router.get("/system-logs")
async def get_system_logs(lines: int = Query(200, ge=10, le=5000), current_user: User = Depends(get_current_user)):
    log_path = os.path.join(".", "logs", "pymon.log")
    if not os.path.exists(log_path):
        return {"logs": ["Log file not found."]}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return {"logs": all_lines[-lines:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/system-logs")
async def clear_system_logs(current_user: User = Depends(get_current_user)):
    log_path = os.path.join(".", "logs", "pymon.log")
    try:
        if os.path.exists(log_path):
            # Open in write mode to truncate
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

