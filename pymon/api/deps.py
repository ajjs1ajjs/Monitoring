import os
import sqlite3

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

_db_path_cache = None

def _resolve_db_path() -> str:
    global _db_path_cache
    if _db_path_cache is None:
        from pymon.config import load_config
        cfg = load_config(os.getenv("CONFIG_PATH", "config.yml"))
        _db_path_cache = cfg.storage.path
    return _db_path_cache

def get_db():
    """Get database connection with WAL mode enabled for concurrency"""
    db_path = _resolve_db_path()
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    return conn

async def get_async_db():
    """Get async database connection with aiosqlite"""
    import aiosqlite
    db_path = _resolve_db_path()
    conn = await aiosqlite.connect(db_path, timeout=30.0)
    conn.row_factory = aiosqlite.Row
    try:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return conn
