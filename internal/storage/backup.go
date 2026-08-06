package storage

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

func (st *Store) BackupTo(dir string) (string, error) {
	st.mu.Lock()
	defer st.mu.Unlock()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	name := "pymon_backup_" + time.Now().Format("20060102_150405") + ".db"
	dst := filepath.Join(dir, name)
	if _, err := st.DB.Exec(fmt.Sprintf("VACUUM INTO %q", filepath.ToSlash(dst))); err != nil {
		return "", fmt.Errorf("backup: %w", err)
	}
	st.pruneBackups(dir)
	return name, nil
}

func (st *Store) pruneBackups(dir string) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasPrefix(e.Name(), "pymon_backup_") && strings.HasSuffix(e.Name(), ".db") {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)
	max := 10
	if st.maxBackups > 0 {
		max = st.maxBackups
	}
	for len(files) > max {
		_ = os.Remove(filepath.Join(dir, files[0]))
		files = files[1:]
	}
}

func (st *Store) SetMaxBackups(n int) { st.maxBackups = n }

func (st *Store) ListBackups(dir string) ([]map[string]any, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var out []map[string]any
	for _, e := range entries {
		if e.IsDir() || !strings.HasPrefix(e.Name(), "pymon_backup_") {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		out = append(out, map[string]any{
			"filename": e.Name(), "size": info.Size(),
			"created_at": info.ModTime().Format("2006-01-02T15:04:05"),
		})
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i]["filename"].(string) > out[j]["filename"].(string)
	})
	return out, nil
}

// RestoreFrom replaces the live DB file with a backup. Must be called when no
// concurrent queries are in flight (handlers serialize via mu).
func (st *Store) RestoreFrom(dir, filename string) error {
	if strings.Contains(filename, "..") || strings.ContainsAny(filename, `/\`) {
		return fmt.Errorf("invalid backup filename")
	}
	if !strings.HasPrefix(filename, "pymon_backup_") {
		return fmt.Errorf("invalid backup filename")
	}
	src := filepath.Join(dir, filename)
	if _, err := os.Stat(src); err != nil {
		return fmt.Errorf("backup not found: %w", err)
	}
	st.mu.Lock()
	defer st.mu.Unlock()
	if err := st.DB.Close(); err != nil {
		return err
	}
	b, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	// Ensure the backup is a valid SQLite DB before replacing.
	if len(b) < 16 || string(b[0:16]) != "SQLite format 3\x00" {
		return fmt.Errorf("not a valid SQLite database")
	}
	if err := os.WriteFile(st.DBPath, b, 0o644); err != nil {
		return err
	}
	newDB, abs, err := Open(st.DBPath)
	if err != nil {
		return fmt.Errorf("reopen after restore: %w", err)
	}
	st.DB = newDB
	st.DBPath = abs
	return nil
}
