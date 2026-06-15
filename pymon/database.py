import logging
import sqlite3

from pymon.api.deps import get_db

logger = logging.getLogger(__name__)

def init_database():
    conn = get_db()
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
                   volumes TEXT DEFAULT '[]',
                   scrape_interval INTEGER DEFAULT 0,
                   created_at TEXT)''')
    try:
        c.execute("ALTER TABLE servers ADD COLUMN volumes TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE servers ADD COLUMN scrape_interval INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Services table
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  target_url TEXT NOT NULL,
                  check_type TEXT DEFAULT 'http',
                  interval INTEGER DEFAULT 60,
                  timeout INTEGER DEFAULT 10,
                  expected_status INTEGER DEFAULT 200,
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
                  network_rx REAL DEFAULT 0,
                  network_tx REAL DEFAULT 0,
                  disk_info TEXT DEFAULT '{}',
                  timestamp TEXT,
                  FOREIGN KEY(server_id) REFERENCES servers(id))''')

    try:
        c.execute("ALTER TABLE metrics_history ADD COLUMN disk_info TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        pass

    # Alerts history
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  server_id INTEGER,
                  service_id INTEGER,
                  alert_type TEXT,
                  severity TEXT DEFAULT 'warning',
                  message TEXT,
                  timestamp TEXT,
                  resolved INTEGER DEFAULT 0,
                  resolved_at TEXT,
                  name TEXT DEFAULT '',
                  metric TEXT DEFAULT '',
                  condition TEXT DEFAULT '',
                  threshold REAL DEFAULT 0,
                  duration INTEGER DEFAULT 0,
                  notify_telegram INTEGER DEFAULT 0,
                  notify_discord INTEGER DEFAULT 0,
                  notify_slack INTEGER DEFAULT 0,
                  notify_email INTEGER DEFAULT 0,
                  notify_teams INTEGER DEFAULT 0,
                  description TEXT DEFAULT '',
                  enabled INTEGER DEFAULT 1,
                  created_at TEXT)''')
    for col in ['name', 'metric', 'condition', 'description', 'created_at']:
        try:
            c.execute(f"ALTER TABLE alerts ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    for col in ['threshold']:
        try:
            c.execute(f"ALTER TABLE alerts ADD COLUMN {col} REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ['duration']:
        try:
            c.execute(f"ALTER TABLE alerts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ['enabled']:
        try:
            c.execute(f"ALTER TABLE alerts ADD COLUMN {col} INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
    for col in ['notify_telegram', 'notify_discord', 'notify_slack', 'notify_email', 'notify_teams']:
        try:
            c.execute(f"ALTER TABLE alerts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

    # Services history
    c.execute('''CREATE TABLE IF NOT EXISTS services_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  service_id INTEGER,
                  status TEXT,
                  latency_ms REAL,
                  timestamp TEXT)''')

    # Audit Log
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  details TEXT,
                  ip_address TEXT,
                  timestamp TEXT)''')

    # Notifications config
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (channel TEXT PRIMARY KEY,
                  enabled INTEGER DEFAULT 1,
                  config TEXT)''')

    conn.commit()
    conn.close()
    logger.info("Database initialized with WAL mode")
