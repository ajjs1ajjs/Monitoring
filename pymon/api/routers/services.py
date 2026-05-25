
from fastapi import APIRouter, Depends, HTTPException

from pymon.api import models as api_models
from pymon.api.deps import get_db
from pymon.auth import User, get_current_user

router = APIRouter(prefix="/services", tags=["services"])

@router.get("")
async def list_services(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM services ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("")
async def create_service(data: api_models.ServiceCreate, current_user: User = Depends(get_current_user)):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO services (name, target_url, check_type, interval, timeout, enabled) VALUES (?, ?, ?, ?, ?, ?)",
            (data.name, data.target_url, data.check_type, data.interval, data.timeout, 1)
        )
        conn.commit()
        return {"status": "ok", "id": c.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/history")
async def get_all_services_history(range: str = "1h", current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        h: float = 1.0
        if range.endswith('h'): h = float(range[:-1])
        elif range.endswith('d'): h = float(range[:-1]) * 24
        elif range.endswith('m'): h = float(range[:-1]) / 60
        rows = conn.execute("SELECT * FROM services_history WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC", (f'-{h} hours',)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.delete("/{service_id}")
async def delete_service(service_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
