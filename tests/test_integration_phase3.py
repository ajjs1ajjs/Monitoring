import os
import sqlite3
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


def setup_test_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, host TEXT, os_type TEXT, agent_port INTEGER, last_status TEXT, cpu_percent REAL, memory_percent REAL, disk_percent REAL, disk_info TEXT, last_check TEXT)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS metrics_history (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, cpu_percent REAL, memory_percent REAL, disk_percent REAL, network_rx REAL, network_tx REAL, timestamp TEXT)"
    )
    cur.execute("DELETE FROM servers; DELETE FROM metrics_history;")
    cur.execute("INSERT INTO servers (id, name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, disk_info, last_check) VALUES (1, 'Test Server', '127.0.0.1', 'linux', 9100, 'up', 40.0, 50.0, 60.0, '[]', ?)", (datetime.now(timezone.utc).isoformat(),))
    now = datetime.now(timezone.utc)
    for i in range(5):
        ts = (now - timedelta(minutes=i*5)).isoformat()
        cur.execute("INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (1, 40+i, 50+i, 60+i, 1000+i*100, 500+i*50, ts))
    conn.commit()
    conn.close()


from pymon.api.endpoints import api
from fastapi import FastAPI


@pytest.fixture
def app():
    os.environ['DB_PATH'] = os.environ.get('DB_PATH', 'test_pymon.db')
    # Create a fresh temp DB
    db_path = os.environ['DB_PATH']
    if os.path.exists(db_path):
        os.remove(db_path)
    setup_test_db(db_path)
    from pymon.api.endpoints import api as api_router
    app = FastAPI()
    app.include_router(api_router, prefix='/api/v1')
    return app


def test_history_endpoint(app):
    client = TestClient(app)
    resp = client.get('/api/v1/servers/1/history?range=1h')
    assert resp.status_code == 200
    data = resp.json()
    assert 'history' in data
    assert isinstance(data['history'], list)
