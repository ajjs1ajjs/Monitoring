package storage

import (
	"fmt"
	"io"
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
	out := []map[string]any{}
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
// concurrent queries are in flight (handlers serialize via mu). The backup is
// streamed to a temp file and atomically renamed into place, so the old DB
// survives if the copy fails, and multi-GB backups don't need to be loaded
// into memory.
func (st *Store) RestoreFrom(dir, filename string) error {
	if strings.Contains(filename, "..") || strings.ContainsAny(filename, `/\`) {
		return fmt.Errorf("invalid backup filename")
	}
	if !strings.HasPrefix(filename, "pymon_backup_") {
		return fmt.Errorf("invalid backup filename")
	}
	src := filepath.Join(dir, filename)
	in, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("backup not found: %w", err)
	}
	defer in.Close()

	// Validate the SQLite magic header without loading the whole file.
	var magic [16]byte
	if _, err := io.ReadFull(in, magic[:]); err != nil {
		return fmt.Errorf("invalid backup: %w", err)
	}
	if string(magic[:]) != "SQLite format 3\x00" {
		return fmt.Errorf("not a valid SQLite database")
	}
	// Rewind so the copy includes the header bytes we just read.
	if _, err := in.Seek(0, io.SeekStart); err != nil {
		return err
	}

	st.mu.Lock()
	defer st.mu.Unlock()

	// Copy to a temp file, then swap it into place.
	tmp := st.DBPath + ".restore.tmp"
	tf, err := os.Create(tmp)
	if err != nil {
		return err
	}
	committed := false
	defer func() {
		if !committed {
			_ = os.Remove(tmp)
		}
	}()
	if _, err := io.Copy(tf, in); err != nil {
		_ = tf.Close()
		return err
	}
	if err := tf.Sync(); err != nil {
		_ = tf.Close()
		return err
	}
	if err := tf.Close(); err != nil {
		return err
	}

	if err := st.DB.Close(); err != nil {
		return err
	}
	if err := os.Rename(tmp, st.DBPath); err != nil {
		return err
	}
	committed = true

	newDB, abs, err := Open(st.DBPath)
	if err != nil {
		return fmt.Errorf("reopen after restore: %w", err)
	}
	st.DB = newDB
	st.DBPath = abs
	return nil
}
