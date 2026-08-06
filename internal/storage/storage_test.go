package storage

import (
	"path/filepath"
	"testing"
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

func ptr(f float64) *float64 { return &f }
