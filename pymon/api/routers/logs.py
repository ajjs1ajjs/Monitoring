from fastapi import APIRouter, Depends, Query

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
