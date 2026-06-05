"""Shared fixtures for all tests"""
import os
import sqlite3
import tempfile
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
    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture(scope="session")
def test_config(db_path):
    """Create a temporary config.yml that points to the test database"""
    import yaml
    config_path = os.path.join(tempfile.gettempdir(), "pymon_test_config.yml")
    config = {
        "server": {"host": "127.0.0.1", "port": 10000, "domain": "localhost"},
        "storage": {"backend": "sqlite", "path": db_path, "retention_hours": 168},
        "auth": {"admin_username": "admin", "admin_password": "testpass123", "jwt_expire_hours": 24},
        "scrape_configs": [],
        "notifications": {},
        "prometheus": {"enabled": False},
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    os.environ["CONFIG_PATH"] = config_path
    yield config_path
    if os.path.exists(config_path):
        os.unlink(config_path)


@pytest.fixture(scope="session")
def init_database(db_path, test_config):
    """Initialize the test database with all required tables and test data"""
    from pymon.auth import init_auth_tables
    from pymon.database import init_database
    from pymon.storage import init_storage

    init_storage(backend="sqlite", db_path=db_path)
    init_auth_tables()
    init_database()

    # Add test data
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)

    # Insert test servers (matching actual database.py schema)
    conn.execute(
        "INSERT INTO servers (name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, volumes, last_check, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("Test Server 1", "192.168.1.100", "linux", 9100, "up", 45.5, 62.3, 78.1,
         '[{"volume": "C:", "size": 500000000000, "free": 250000000000}, {"volume": "D:", "size": 1000000000000, "free": 600000000000}]',
         now.isoformat(), now.isoformat()),
    )
    conn.execute(
        "INSERT INTO servers (name, host, os_type, agent_port, last_status, cpu_percent, memory_percent, disk_percent, volumes, last_check, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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


@pytest.fixture(scope="function")
def auth_client(client, init_database):
    """Create test client that is already authenticated"""
    from pymon.auth import create_token
    token = create_token(user_id=1, username="admin", is_admin=True, must_change=False)
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
