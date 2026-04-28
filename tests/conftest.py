"""Shared fixtures for all tests"""
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from pymon.cli import create_app


@pytest.fixture(scope="session")
def db_path():
    """Create a shared test database path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="session")
def init_database(db_path):
    """Initialize the test database with all required tables and test data"""
    os.environ["DB_PATH"] = db_path
    os.environ["STORAGE_BACKEND"] = "sqlite"

    # Initialize all tables
    from pymon.auth import init_auth_tables
    from pymon.storage import init_storage
    from pymon.web_dashboard import init_web_tables

    init_storage(backend="sqlite", db_path=db_path)
    init_auth_tables()
    init_web_tables()

    # Add test data
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)

    # Insert test servers
    conn.execute(
        "INSERT INTO servers (name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, disk_info, last_check, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("Test Server 1", "192.168.1.100", "linux", 9100, "up", 45.5, 62.3, 78.1,
         '[{"volume": "C:", "size": 500000000000, "free": 250000000000}, {"volume": "D:", "size": 1000000000000, "free": 600000000000}]',
         now.isoformat(), now.isoformat()),
    )
    conn.execute(
        "INSERT INTO servers (name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, disk_info, last_check, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("Test Server 2", "192.168.1.101", "windows", 9182, "up", 55.0, 72.0, 68.0,
         "[]", now.isoformat(), now.isoformat()),
    )

    # Insert metrics history for server 1
    for i in range(10):
        ts = (now - timedelta(minutes=i * 5)).isoformat()
        conn.execute(
            "INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 40 + i, 60 + i, 75 + i, 1000000 + i * 100000, 500000 + i * 50000, ts),
        )

    conn.commit()
    conn.close()

    yield

    # Cleanup is handled by db_path fixture


@pytest.fixture(scope="function")
def client(init_database, db_path):
    """Create test client with the shared database"""
    os.environ["DB_PATH"] = db_path
    app = create_app()
    with TestClient(app) as c:
        yield c
