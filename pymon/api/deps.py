from fastapi import WebSocket

from pymon.database import get_db_connection


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
        # Iterate over a snapshot: broadcast is awaited concurrently from many
        # scrape tasks, and mutating the live list during iteration (on a failed
        # send or a concurrent connect/disconnect) would corrupt the loop.
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

def get_db():
    """Get database connection with WAL mode enabled for concurrency"""
    return get_db_connection()

async def get_async_db():
    """Get async database connection with aiosqlite"""
    import aiosqlite
    from pymon.config import resolve_db_path
    db_path = resolve_db_path()
    conn = await aiosqlite.connect(db_path, timeout=30.0)
    conn.row_factory = aiosqlite.Row
    try:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return conn
