package storage

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

var Schema = `
CREATE TABLE IF NOT EXISTS servers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  labels TEXT DEFAULT '{}',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS metrics_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  server_id INTEGER NOT NULL,
  cpu_percent REAL,
  memory_percent REAL,
  disk_percent REAL,
  network_rx REAL DEFAULT 0,
  network_tx REAL DEFAULT 0,
  disk_info TEXT DEFAULT '{}',
  timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_mh_server ON metrics_history(server_id);
CREATE INDEX IF NOT EXISTS idx_mh_ts ON metrics_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_mh_server_ts ON metrics_history(server_id, timestamp);

CREATE TABLE IF NOT EXISTS services_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id INTEGER NOT NULL,
  status TEXT,
  latency_ms REAL,
  timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_sh_service ON services_history(service_id);
CREATE INDEX IF NOT EXISTS idx_sh_ts ON services_history(timestamp);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_server ON alerts(server_id);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  action TEXT,
  details TEXT,
  ip_address TEXT,
  timestamp TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
  channel TEXT PRIMARY KEY,
  enabled INTEGER DEFAULT 1,
  config TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin INTEGER DEFAULT 0,
  must_change_password INTEGER DEFAULT 1,
  created_at TEXT,
  last_login TEXT
);

CREATE TABLE IF NOT EXISTS api_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  key_hash TEXT NOT NULL,
  key_sha256 TEXT,
  name TEXT,
  created_at TEXT,
  last_used TEXT
);
CREATE INDEX IF NOT EXISTS idx_apikeys_sha ON api_keys(key_sha256);

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  labels TEXT DEFAULT '{}',
  value REAL,
  timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp);
`

func Open(path string) (*sql.DB, string, error) {
	if path == "" {
		path = "pymon.db"
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		abs = path
	}
	if dir := filepath.Dir(abs); dir != "." && dir != "" {
		_ = os.MkdirAll(dir, 0o755)
	}
	dsn := fmt.Sprintf("file:%s?_pragma=journal_mode(WAL)&_pragma=busy_timeout(30000)&_pragma=synchronous(NORMAL)", abs)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, abs, err
	}
	db.SetMaxOpenConns(10)
	if _, err := db.Exec(Schema); err != nil {
		return nil, abs, fmt.Errorf("apply schema: %w", err)
	}
	return db, abs, nil
}

// tsLayout is the storage format for all timestamps. It deliberately uses the
// ISO-8601 'T' separator (matching the Python v2 data) and is stored as UTC.
// SQLite datetime()/strftime() can parse this format, and lexicographic
// comparison between two identical-formatted strings is chronologically
// correct — which is why cutoffs are formatted with tsLayout too instead of
// being compared against datetime('now', ...) output (space separator).
const tsLayout = "2006-01-02T15:04:05"

func Now() string {
	return time.Now().UTC().Format(tsLayout)
}

// NowBefore returns the storage-format UTC timestamp d before now.
func NowBefore(d time.Duration) string {
	return time.Now().UTC().Add(-d).Format(tsLayout)
}

// Store holds a *sql.DB plus the resolved DB path (for backup/restore).
type StoreCore struct {
	DB     *sql.DB
	DBPath string
	mu     sync.Mutex
}

func NewStoreCore(db *sql.DB, path string) *StoreCore {
	return &StoreCore{DB: db, DBPath: path}
}
