import os
import sqlite3
from datetime import datetime, timezone

def get_db_conn():
    db_path = os.getenv("DB_PATH", "pymon.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize all required database tables"""
    conn = get_db_conn()
    c = conn.cursor()
    
    # Servers table
    c.execute("""CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        host TEXT NOT NULL,
        os_type TEXT DEFAULT 'linux',
        agent_port INTEGER DEFAULT 9100,
        enabled BOOLEAN DEFAULT 1,
        server_group TEXT,
        created_at TEXT,
        last_check TEXT,
        last_status TEXT DEFAULT 'unknown',
        error_message TEXT,
        cpu_percent REAL DEFAULT 0,
        memory_percent REAL DEFAULT 0,
        disk_percent REAL DEFAULT 0,
        network_rx REAL DEFAULT 0,
        network_tx REAL DEFAULT 0,
        uptime TEXT,
        disk_info TEXT,
        exporter_version TEXT,
        is_maintenance BOOLEAN DEFAULT 0,
        flapping_count INTEGER DEFAULT 0,
        last_flapping_change TEXT
    )""")
    
    # Metrics history table
    c.execute("""CREATE TABLE IF NOT EXISTS metrics_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id INTEGER,
        cpu_percent REAL,
        memory_percent REAL,
        disk_percent REAL,
        network_rx REAL,
        network_tx REAL,
        disk_info TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (server_id) REFERENCES servers(id)
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metrics_history_server_ts ON metrics_history(server_id, timestamp)")
    
    # Alerts table
    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        metric TEXT NOT NULL,
        condition TEXT NOT NULL,
        threshold REAL NOT NULL,
        duration INTEGER DEFAULT 0,
        severity TEXT DEFAULT 'warning',
        server_id INTEGER,
        notify_telegram BOOLEAN DEFAULT 0,
        notify_discord BOOLEAN DEFAULT 0,
        notify_slack BOOLEAN DEFAULT 0,
        notify_email BOOLEAN DEFAULT 0,
        notify_teams BOOLEAN DEFAULT 0,
        description TEXT,
        enabled BOOLEAN DEFAULT 1,
        created_at TEXT,
        FOREIGN KEY (server_id) REFERENCES servers(id)
    )""")
    
    # Services table (HTTP/TCP Monitoring)
    c.execute("""CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_url TEXT NOT NULL,
        check_type TEXT DEFAULT 'http', -- http, tcp
        interval INTEGER DEFAULT 60,
        timeout INTEGER DEFAULT 5,
        enabled BOOLEAN DEFAULT 1,
        is_maintenance BOOLEAN DEFAULT 0,
        last_status TEXT DEFAULT 'unknown',
        last_check TEXT,
        last_response_time REAL,
        error_message TEXT,
        created_at TEXT
    )""")
    
    # Audit logs table
    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT NOT NULL,
        target TEXT,
        details TEXT,
        timestamp TEXT NOT NULL
    )""")
    
    # Backups table
    c.execute("""CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        size_bytes INTEGER,
        created_at TEXT NOT NULL
    )""")
    
    # Notifications table
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        channel TEXT PRIMARY KEY,
        enabled BOOLEAN DEFAULT 0,
        config TEXT
    )""")
    
    # Default notification config if not exists
    c.execute("SELECT 1 FROM notifications WHERE channel = 'all'")
    if not c.fetchone():
        import json
        default_config = json.dumps({"enabled": False, "telegram_enabled": False, "discord_enabled": False})
        c.execute("INSERT INTO notifications (channel, enabled, config) VALUES (?, ?, ?)", 
                  ('all', 0, default_config))
        
    conn.commit()
    conn.close()
