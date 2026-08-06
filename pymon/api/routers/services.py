
from fastapi import APIRouter, Depends, HTTPException, Query

from pymon.api import models as api_models
from pymon.api.deps import get_db
from pymon.auth import User, get_admin_user, get_current_user

router = APIRouter(prefix="/services", tags=["services"])

@router.get("")
def list_services(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM services ORDER BY name").fetchall()
        return {"services": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.post("")
def create_service(data: api_models.ServiceCreate, current_user: User = Depends(get_admin_user)):
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Service name is required")
    if len(data.name) > 100:
        raise HTTPException(status_code=400, detail="Service name must be less than 100 characters")
    if not data.target_url or not data.target_url.strip():
        raise HTTPException(status_code=400, detail="target_url is required")
    if data.check_type not in ("http", "tcp", "ping", "ssl"):
        raise HTTPException(status_code=400, detail="check_type must be one of: http, tcp, ping, ssl")
    if data.interval is not None and data.interval < 5:
        raise HTTPException(status_code=400, detail="interval must be at least 5 seconds")
    if data.timeout is not None and data.timeout < 1:
        raise HTTPException(status_code=400, detail="timeout must be at least 1 second")
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO services (name, target_url, check_type, interval, timeout, enabled) VALUES (?, ?, ?, ?, ?, ?)",
            (data.name.strip(), data.target_url.strip(), data.check_type, data.interval, data.timeout, 1)
        )
        conn.commit()
        return {"status": "ok", "id": c.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/history")
def get_all_services_history(
    range: str = Query("1h", pattern=r"^\d+[mhd]$"),
    current_user: User = Depends(get_current_user),
):
    conn = get_db()
    try:
        h: float = 1.0
        if range.endswith('h'):
            h = float(range[:-1])
        elif range.endswith('d'):
            h = float(range[:-1]) * 24
        elif range.endswith('m'):
            h = float(range[:-1]) / 60
        rows = conn.execute("SELECT * FROM services_history WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC", (f'-{h} hours',)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.delete("/{service_id}")
def delete_service(service_id: int, current_user: User = Depends(get_admin_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
