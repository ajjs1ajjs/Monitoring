package storage

import (
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	path := filepath.Join(t.TempDir(), "test.db")
	db, abs, err := Open(path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	st := NewStore(db, abs)
	t.Cleanup(func() { _ = st.DB.Close() })
	return st
}

func TestServerCRUD(t *testing.T) {
	st := newTestStore(t)
	s := &Server{Name: "web-01", Host: "192.168.1.10", AgentPort: 9100, OSType: "linux", Enabled: 1, Volumes: "[]", Labels: "{}"}
	id, err := st.CreateServer(s)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	got, err := st.GetServer(id)
	if err != nil || got == nil {
		t.Fatalf("get: %v", err)
	}
	if got.Name != "web-01" {
		t.Errorf("name = %q", got.Name)
	}
	if err := st.UpdateServer(id, map[string]any{"last_status": "up", "cpu_percent": 42.5}); err != nil {
		t.Fatalf("update: %v", err)
	}
	got2, _ := st.GetServer(id)
	if got2.LastStatus != "up" || got2.CPUPercent != 42.5 {
		t.Errorf("update not applied: %+v", got2)
	}
	if err := st.DeleteServer(id); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if g, _ := st.GetServer(id); g != nil {
		t.Errorf("expected deletion")
	}
}

func TestMetricPointAndHistory(t *testing.T) {
	st := newTestStore(t)
	s := &Server{Name: "db", Host: "h", AgentPort: 9100, Enabled: 1, Volumes: "[]", Labels: "{}"}
	id, _ := st.CreateServer(s)
	cpu := 55.0
	if err := st.InsertMetricPoint(id, &cpu, nil, nil, nil, nil, "{}"); err != nil {
		t.Fatalf("insert: %v", err)
	}
	hist, err := st.ServerHistory(id, "1h")
	if err != nil {
		t.Fatalf("history: %v", err)
	}
	if len(hist) != 1 {
		t.Fatalf("history len = %d, want 1", len(hist))
	}
	if hist[0].CPUPercent == nil || *hist[0].CPUPercent != 55 {
		t.Errorf("cpu = %v, want 55", hist[0].CPUPercent)
	}
}

func TestBackupRestore(t *testing.T) {
	st := newTestStore(t)
	dir := t.TempDir()
	s := &Server{Name: "a", Host: "h", AgentPort: 9100, Enabled: 1, Volumes: "[]", Labels: "{}"}
	id, _ := st.CreateServer(s)
	_ = st.InsertMetricPoint(id, ptr(10.0), nil, nil, nil, nil, "{}")

	name, err := st.BackupTo(dir)
	if err != nil {
		t.Fatalf("backup: %v", err)
	}
	if err := st.DeleteServer(id); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if g, _ := st.GetServer(id); g != nil {
		t.Fatalf("server should be gone")
	}
	if err := st.RestoreFrom(dir, name); err != nil {
		t.Fatalf("restore: %v", err)
	}
	if g, _ := st.GetServer(id); g == nil {
		t.Fatalf("server not restored")
	}
}

func TestUptimeTimeline(t *testing.T) {
	st := newTestStore(t)
	s := &Server{Name: "s", Host: "h", AgentPort: 9100, Enabled: 1, Volumes: "[]", Labels: "{}"}
	id, _ := st.CreateServer(s)
	cpu := 1.0
	_ = st.InsertMetricPoint(id, &cpu, nil, nil, nil, nil, "{}") // up
	_ = st.InsertMetricPoint(id, nil, nil, nil, nil, nil, "{}")  // down
	up, down, _, err := st.UptimeTimeline(id, 1)
	if err != nil {
		t.Fatalf("timeline: %v", err)
	}
	if up != 1 || down != 1 {
		t.Errorf("up/down = %d/%d, want 1/1", up, down)
	}
}

// TestNotificationSecretsEncryptedAtRest ensures notification secrets are
// stored encrypted and round-trip back to plaintext.
func TestNotificationSecretsEncryptedAtRest(t *testing.T) {
	st := newTestStore(t)

	// Without a key, values are stored as-is (provisioning/tests).
	cfg := `{"enabled":true,"smtp_pass":"s3cret","telegram_bot_token":"tok"}`
	if err := st.SaveNotifications(cfg, 1); err != nil {
		t.Fatalf("save: %v", err)
	}
	got, _ := st.GetNotifications()
	if got.Config != cfg {
		t.Fatalf("unencrypted round-trip mismatch: %q", got.Config)
	}

	// With a key, the stored value must be encrypted (enc: prefix) and reads
	// return the plaintext.
	st.SetEncryptionKey([]byte("some-stable-jwt-secret-for-testing-123456"))
	if err := st.SaveNotifications(cfg, 1); err != nil {
		t.Fatalf("save encrypted: %v", err)
	}
	var raw string
	_ = st.DB.QueryRow(`SELECT config FROM notifications WHERE channel='all'`).Scan(&raw)
	if len(raw) < 4 || raw[:4] != "enc:" {
		t.Fatalf("expected encrypted storage, got %q", raw)
	}
	got, err := st.GetNotifications()
	if err != nil {
		t.Fatalf("get encrypted: %v", err)
	}
	if got.Config != cfg {
		t.Fatalf("encrypted round-trip mismatch: %q", got.Config)
	}

	// A different key (rotated JWT secret) must fail loudly, not silently.
	st.SetEncryptionKey([]byte("a-different-secret-that-rotated-1234567"))
	if _, err := st.GetNotifications(); err == nil {
		t.Fatalf("expected decryption failure after key rotation")
	}
}

func ptr(f float64) *float64 { return &f }

// TestHistoryWindowExcludesOldRows guards against the 'T' vs ' ' separator
// bug where `timestamp >= datetime('now', ...)` (space separator) compared
// against stored ISO-8601 'T' timestamps wrongly included every row from the
// cutoff day regardless of time.
func TestHistoryWindowExcludesOldRows(t *testing.T) {
	st := newTestStore(t)
	s := &Server{Name: "s", Host: "h", AgentPort: 9100, Enabled: 1, Volumes: "[]", Labels: "{}"}
	id, _ := st.CreateServer(s)

	// Rows at roughly 0m, 30m, 90m and 25h in the past.
	cpu := 1.0
	for _, off := range []time.Duration{0, 30 * time.Minute, 90 * time.Minute, 25 * time.Hour} {
		if _, err := st.DB.Exec(`INSERT INTO metrics_history (server_id, cpu_percent, timestamp) VALUES (?,?,?)`,
			id, cpu, NowBefore(off)); err != nil {
			t.Fatalf("insert: %v", err)
		}
	}

	hist, err := st.ServerHistory(id, "1h")
	if err != nil {
		t.Fatalf("history: %v", err)
	}
	// Only rows within the last hour (0m and 30m) belong in a 1h window.
	if len(hist) != 2 {
		t.Fatalf("1h history rows = %d, want 2 (old cutoff-day rows leaked in)", len(hist))
	}
}

// TestTimestampsUseConsistentLayout ensures Now()/NowBefore() produce the same
// T-separated format so string comparisons are chronologically correct.
func TestTimestampsUseConsistentLayout(t *testing.T) {
	now := Now()
	before := NowBefore(time.Hour)
	if !strings.Contains(now, "T") || !strings.Contains(before, "T") {
		t.Fatalf("timestamps must use 'T' separator: now=%q before=%q", now, before)
	}
	beforeParsed, err := time.Parse(tsLayout, before)
	if err != nil {
		t.Fatalf("before not parseable: %v", err)
	}
	if !beforeParsed.Before(time.Now()) {
		t.Fatalf("NowBefore must be in the past")
	}
}
