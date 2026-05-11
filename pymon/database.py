import sqlite3
import os
import logging
from pymon.config import load_config

logger = logging.getLogger(__name__)

def get_db_connection():
    config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
    db_path = config.storage.path
    
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode for better concurrency
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception as e:
        logger.warning(f"Could not set WAL mode: {e}")
        
    return conn

def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Servers table
    c.execute('''CREATE TABLE IF NOT EXISTS servers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  host TEXT NOT NULL,
                  agent_port INTEGER DEFAULT 9100,
                  server_group TEXT,
                  os_type TEXT DEFAULT 'linux',
                  enabled INTEGER DEFAULT 1,
                  last_status TEXT DEFAULT 'unknown',
                  last_check TEXT,
                  cpu_percent REAL DEFAULT 0,
                  memory_percent REAL DEFAULT 0,
                  disk_percent REAL DEFAULT 0,
                  exporter_version TEXT,
                  error_message TEXT,
                  is_maintenance INTEGER DEFAULT 0,
                  flapping_count INTEGER DEFAULT 0,
                  created_at TEXT)''')
    
    # Services table
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  target_url TEXT NOT NULL,
                  check_type TEXT DEFAULT 'http',
                  interval INTEGER DEFAULT 60,
                  enabled INTEGER DEFAULT 1,
                  status TEXT DEFAULT 'unknown',
                  last_check TEXT,
                  response_time_ms REAL DEFAULT 0,
                  created_at TEXT)''')

    # Metrics history
    c.execute('''CREATE TABLE IF NOT EXISTS metrics_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  server_id INTEGER,
                  cpu_percent REAL,
                  memory_percent REAL,
                  disk_percent REAL,
                  timestamp TEXT,
                  FOREIGN KEY(server_id) REFERENCES servers(id))''')
    
    # Alerts history
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  server_id INTEGER,
                  service_id INTEGER,
                  alert_type TEXT,
                  severity TEXT,
                  message TEXT,
                  timestamp TEXT,
                  resolved INTEGER DEFAULT 0,
                  resolved_at TEXT)''')

    conn.commit()
    conn.close()
    logger.info("Database initialized with WAL mode")
