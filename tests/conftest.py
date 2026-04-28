import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


def create_test_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, host TEXT NOT NULL, os_type TEXT DEFAULT 'linux', agent_port INTEGER DEFAULT 9100, last_status TEXT DEFAULT 'unknown', cpu_percent REAL, memory_percent REAL, disk_percent REAL, disk_info TEXT, created_at TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS metrics_history (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER NOT NULL, cpu_percent REAL, memory_percent REAL, disk_percent REAL, network_rx REAL, network_tx REAL, timestamp TEXT)"
    )
    c.execute("INSERT INTO servers (id, name, host, os_type, agent_port, last_status) VALUES (1, 'Test Server', '127.0.0.1', 'linux', 9100, 'up')")
    now = datetime.now(timezone.utc)
    for i in range(6):
        ts = (now - timedelta(minutes=i*5)).isoformat()
        c.execute("INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (1, 40+i, 50+i, 60+i, 1000+i*100, 500+i*50, ts))
    # Add a second server for aggregation tests
    c.execute("INSERT INTO servers (id, name, host, os_type, agent_port, last_status) VALUES (2, 'Test Server 2', '127.0.0.2', 'linux', 9101, 'up')")
    now2 = now
    for i in range(3):
        ts2 = (now2 - timedelta(minutes=i*7)).isoformat()
        c.execute("INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (2, 25+i, 35+i, 45+i, 800+i*120, 300+i*50, ts2))
    conn.commit()
    conn.close()


@pytest.fixture
def test_app():
    # Prepare a temporary DB for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_pymon.db"
        create_test_db(str(db_path))
        os.environ["DB_PATH"] = str(db_path)
        from pymon.api.endpoints import api as api_router
        app = FastAPI()
        app.include_router(api_router, prefix="/api/v1")
        from fastapi.testclient import TestClient
        client = TestClient(app)
        yield client
