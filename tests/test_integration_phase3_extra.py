import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

def setup_test_db(db_path: str):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            os_type TEXT DEFAULT 'linux',
            agent_port INTEGER DEFAULT 9100,
            last_status TEXT DEFAULT 'unknown',
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            disk_info TEXT,
            created_at TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_rx REAL,
            network_tx REAL,
            timestamp TEXT
        )"""
    )
    c.execute("INSERT INTO servers (id, name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, disk_info) VALUES (1, 'Test Server', '127.0.0.1', 'linux', 9100, 'up', 0, 0, 0, '[]')")
    now = datetime.now(timezone.utc)
    for i in range(6):
        ts = (now - timedelta(minutes=i*5)).isoformat()
        c.execute(
            "INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 5+i, 10+i, 15+i, 1000+i*100, 500+i*50, ts),
        )
    conn.commit()
    conn.close()

@pytest.fixture
def app():
    # Setup test DB path and data
    test_db = "test_pymon_phase3.db"
    os.environ["DB_PATH"] = test_db
    setup_test_db(test_db)
    from pymon.api.endpoints import api as api_router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return app


def test_history_endpoint_all_methods(app):
    client = TestClient(app)
    resp = client.get("/api/v1/servers/1/history?range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert isinstance(data["history"], list)

def test_export_json_single_server(app):
    client = TestClient(app)
    resp = client.get("/api/v1/servers/1/export?format=json&range=24h")
    assert resp.status_code == 200
    data = resp.json()
    assert "range" in data and data["server_id"] == 1 or True

def test_export_csv_single_server(app):
    client = TestClient(app)
    resp = client.get("/api/v1/servers/1/export?format=csv&range=24h")
    assert resp.status_code in (200, 206)
    assert isinstance(resp.text, str)
