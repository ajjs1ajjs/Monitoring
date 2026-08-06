package monitor

import (
	"log"
	"strconv"
	"strings"
	"time"
)

// backupIfDue runs the scheduled backup at most once per hour.
func (m *Manager) backupIfDue() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if time.Since(m.lastBackup) < time.Hour {
		return
	}
	if m.Cfg == nil || !m.Cfg.Backup.Enabled {
		return
	}
	parts := strings.Fields(strings.TrimSpace(m.Cfg.Backup.Schedule))
	if len(parts) != 5 {
		return
	}
	now := time.Now()
	if hours := parseCronField(parts[1], 23); hours != nil && !containsInt(hours, now.Hour()) {
		return
	}
	minutes := parseCronField(parts[0], 59)
	if minutes != nil {
		min := int(^uint(0) >> 1)
		for v := range minutes {
			if v < min {
				min = v
			}
		}
		if now.Minute() < min {
			return
		}
	}
	m.lastBackup = time.Now()
	dir := m.Cfg.Backup.BackupDir
	if dir == "" {
		dir = "backups"
	}
	m.Store.SetMaxBackups(m.Cfg.Backup.MaxBackups)
	name, err := m.Store.BackupTo(dir)
	if err != nil {
		log.Printf("backup error: %v", err)
		return
	}
	log.Printf("Database backed up to %s/%s", dir, name)
}

// parseCronField supports '*', '*/n', 'a-b' and 'a,b,c'. Returns nil for '*'.
func parseCronField(field string, maxVal int) map[int]bool {
	field = strings.TrimSpace(field)
	if field == "*" {
		return nil
	}
	values := map[int]bool{}
	for _, part := range strings.Split(field, ",") {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		switch {
		case strings.HasPrefix(part, "*/"):
			step, err := strconv.Atoi(part[2:])
			if err != nil || step <= 0 {
				continue
			}
			for v := 0; v <= maxVal; v += step {
				values[v] = true
			}
		case strings.Contains(part, "-"):
			segs := strings.SplitN(part, "-", 2)
			lo, err1 := strconv.Atoi(segs[0])
			hi, err2 := strconv.Atoi(segs[1])
			if err1 != nil || err2 != nil {
				continue
			}
			for v := lo; v <= hi; v++ {
				if v >= 0 && v <= maxVal {
					values[v] = true
				}
			}
		default:
			v, err := strconv.Atoi(part)
			if err == nil && v >= 0 && v <= maxVal {
				values[v] = true
			}
		}
	}
	return values
}

func containsInt(set map[int]bool, v int) bool {
	_, ok := set[v]
	return ok
}
