import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from pymon.api.deps import get_db
from pymon.auth import User, get_current_user

router = APIRouter(prefix="/backup", tags=["backup"])

_config_cache = None

def _get_config():
    global _config_cache
    if _config_cache is None:
        from pymon.config import load_config
        _config_cache = load_config(os.getenv("CONFIG_PATH", "config.yml"))
    return _config_cache

def _get_backup_dir():
    return _get_config().backup.backup_dir


@router.get("/list")
async def list_backups(current_user: User = Depends(get_current_user)):
    backup_dir = _get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            backups.append({
                "filename": fname,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
    return {"backups": backups}


@router.post("/create")
async def create_backup(current_user: User = Depends(get_current_user)):
    config = _get_config()
    backup_dir = _get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    db_path = config.storage.path
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"pymon_backup_{timestamp}.db"
    dest = os.path.join(backup_dir, filename)
    try:
        conn = get_db()
        conn.close()
        shutil.copy2(db_path, dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(".db")],
        reverse=True,
    )
    max_backups = config.backup.max_backups
    for old in backups[max_backups:]:
        try:
            os.remove(os.path.join(backup_dir, old))
        except OSError:
            pass
    return {"status": "ok", "filename": filename}


@router.post("/restore")
async def restore_backup(data: dict, current_user: User = Depends(get_current_user)):
    config = _get_config()
    backup_dir = _get_backup_dir()
    filename = data.get("filename", "")
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    # Reject path traversal: only allow a bare filename inside backup_dir.
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    src = os.path.join(backup_dir, filename)
    if os.path.realpath(src) != os.path.join(os.path.realpath(backup_dir), filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.isfile(src):
        raise HTTPException(status_code=404, detail="Backup file not found")
    db_path = config.storage.path
    try:
        shutil.copy2(src, db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")
    return {"status": "ok", "restored_from": filename}
