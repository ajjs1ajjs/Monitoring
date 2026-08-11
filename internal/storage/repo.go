package storage

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

type Store struct {
	StoreCore
	maxBackups int
	secretKey  []byte
}

func NewStore(db *sql.DB, path string) *Store {
	return &Store{StoreCore: StoreCore{DB: db, DBPath: path}}
}

func scanServer(row interface{ Scan(...any) error }) (*Server, error) {
	var s Server
	var group, osType, exporter, errMsg, volumes, labels sql.NullString
	var lastCheck, createdAt sql.NullString
	var cpu, mem, disk sql.NullFloat64
	err := row.Scan(&s.ID, &s.Name, &s.Host, &s.AgentPort, &group, &osType,
		&s.Enabled, &s.LastStatus, &lastCheck, &cpu, &mem, &disk,
		&exporter, &errMsg, &s.IsMaintenance, &s.FlappingCount, &volumes, &s.ScrapeInterval,
		&labels, &createdAt)
	if err != nil {
		return nil, err
	}
	s.ServerGroup = group.String
	s.OSType = osType.String
	s.LastCheck = lastCheck.String
	s.CPUPercent = cpu.Float64
	s.MemoryPercent = mem.Float64
	s.DiskPercent = disk.Float64
	s.ExporterVersion = exporter.String
	s.ErrorMessage = errMsg.String
	s.Volumes = volumes.String
	s.Labels = labels.String
	s.CreatedAt = createdAt.String
	if s.Volumes == "" {
		s.Volumes = "[]"
	}
	if s.Labels == "" {
		s.Labels = "{}"
	}
	return &s, nil
}

const serverCols = `id, name, host, agent_port, server_group, os_type, enabled, last_status,
 last_check, cpu_percent, memory_percent, disk_percent, exporter_version, error_message,
 is_maintenance, flapping_count, volumes, scrape_interval, labels, created_at`

func (st *Store) ListServers() ([]Server, error) {
	rows, err := st.DB.Query(`SELECT ` + serverCols + ` FROM servers ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Server{}
	for rows.Next() {
		s, err := scanServer(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *s)
	}
	return out, rows.Err()
}

func (st *Store) GetServer(id int64) (*Server, error) {
	row := st.DB.QueryRow(`SELECT `+serverCols+` FROM servers WHERE id = ?`, id)
	s, err := scanServer(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	return s, err
}

func (st *Store) CreateServer(s *Server) (int64, error) {
	res, err := st.DB.Exec(`INSERT INTO servers (name, host, agent_port, server_group, os_type,
	  enabled, cpu_percent, memory_percent, disk_percent, is_maintenance, volumes, scrape_interval, labels, created_at)
	  VALUES (?,?,?,?,?,?,0,0,0,0,?,?,?,?)`,
		s.Name, s.Host, s.AgentPort, s.ServerGroup, s.OSType, s.Enabled, s.Volumes, s.ScrapeInterval, s.Labels, Now())
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (st *Store) UpdateServer(id int64, fields map[string]any) error {
	if len(fields) == 0 {
		return nil
	}
	var sets []string
	var args []any
	for k, v := range fields {
		sets = append(sets, k+" = ?")
		args = append(args, v)
	}
	args = append(args, id)
	_, err := st.DB.Exec(`UPDATE servers SET `+strings.Join(sets, ", ")+` WHERE id = ?`, args...)
	return err
}

func (st *Store) DeleteServer(id int64) error {
	tx, err := st.DB.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for _, q := range []string{
		`DELETE FROM metrics_history WHERE server_id = ?`,
		`DELETE FROM alerts WHERE server_id = ?`,
		`DELETE FROM servers WHERE id = ?`,
	} {
		if _, err := tx.Exec(q, id); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (st *Store) EnabledServers() ([]Server, error) {
	rows, err := st.DB.Query(`SELECT ` + serverCols + ` FROM servers WHERE enabled = 1`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Server{}
	for rows.Next() {
		s, err := scanServer(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *s)
	}
	return out, rows.Err()
}

func (st *Store) InsertMetricPoint(serverID int64, cpu, mem, disk, rx, tx *float64, diskInfo string) error {
	_, err := st.DB.Exec(`INSERT INTO metrics_history (server_id, cpu_percent, memory_percent,
	  disk_percent, network_rx, network_tx, disk_info, timestamp) VALUES (?,?,?,?,?,?,?,?)`,
		serverID, cpu, mem, disk, rx, tx, diskInfo, Now())
	return err
}

// HistoryRange maps a token (5m,15m,1h,6h,12h,24h,3d,7d,15d,30d) to a SQLite
// datetime modifier and a downsample bucket size in seconds.
func HistoryRange(token string) (modifier string, bucketSec int) {
	switch token {
	case "5m":
		return "-5 minutes", 60
	case "15m":
		return "-15 minutes", 60
	case "30m":
		return "-30 minutes", 60
	case "1h":
		return "-1 hours", 60
	case "6h":
		return "-6 hours", 60
	case "12h":
		return "-12 hours", 60
	case "24h":
		return "-24 hours", 60
	case "3d":
		return "-3 days", 60
	case "7d":
		return "-7 days", 3600
	case "15d":
		return "-15 days", 3600
	case "30d":
		return "-30 days", 3600
	}
	return "-1 hours", 60
}

func bucketExpr(bucketSec int) string {
	if bucketSec >= 3600 {
		return "strftime('%Y-%m-%dT%H:00', timestamp)"
	}
	return "strftime('%Y-%m-%dT%H:%M', timestamp)"
}

// ServerHistory returns downsampled history points for a server.
func (st *Store) ServerHistory(serverID int64, token string) ([]MetricPoint, error) {
	mod, bucket := HistoryRange(token)
	q := fmt.Sprintf(`SELECT id, server_id, cpu_percent, memory_percent, disk_percent,
	  network_rx, network_tx, disk_info, timestamp FROM (
	    SELECT *, ROW_NUMBER() OVER (PARTITION BY %s ORDER BY id DESC) AS rn
	    FROM metrics_history
	    WHERE server_id = ? AND timestamp >= datetime('now', ?)
	  ) WHERE rn = 1 ORDER BY timestamp ASC`, bucketExpr(bucket))
	rows, err := st.DB.Query(q, serverID, mod)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []MetricPoint{}
	for rows.Next() {
		var m MetricPoint
		var cpu, mem, disk, rx, tx sql.NullFloat64
		var diskInfo sql.NullString
		var ts sql.NullString
		if err := rows.Scan(&m.ID, &m.ServerID, &cpu, &mem, &disk, &rx, &tx, &diskInfo, &ts); err != nil {
			return nil, err
		}
		m.CPUPercent = floatPtr(cpu)
		m.MemoryPercent = floatPtr(mem)
		m.DiskPercent = floatPtr(disk)
		m.NetworkRX = floatPtr(rx)
		m.NetworkTX = floatPtr(tx)
		m.DiskInfo = diskInfo.String
		m.Timestamp = ts.String
		out = append(out, m)
	}
	return out, rows.Err()
}

// AllServersHistory is the same downsampling across all servers (used by
// /servers/history and /metrics/trend).
func (st *Store) AllServersHistory(token string) (map[int64][]MetricPoint, error) {
	mod, bucket := HistoryRange(token)
	q := fmt.Sprintf(`SELECT id, server_id, cpu_percent, memory_percent, disk_percent,
	  network_rx, network_tx, disk_info, timestamp FROM (
	    SELECT *, ROW_NUMBER() OVER (PARTITION BY server_id, %s ORDER BY id DESC) AS rn
	    FROM metrics_history
	    WHERE timestamp >= datetime('now', ?)
	  ) WHERE rn = 1 ORDER BY timestamp ASC`, bucketExpr(bucket))
	rows, err := st.DB.Query(q, mod)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[int64][]MetricPoint{}
	for rows.Next() {
		var m MetricPoint
		var cpu, mem, disk, rx, tx sql.NullFloat64
		var diskInfo sql.NullString
		var ts sql.NullString
		if err := rows.Scan(&m.ID, &m.ServerID, &cpu, &mem, &disk, &rx, &tx, &diskInfo, &ts); err != nil {
			return nil, err
		}
		m.CPUPercent = floatPtr(cpu)
		m.MemoryPercent = floatPtr(mem)
		m.DiskPercent = floatPtr(disk)
		m.NetworkRX = floatPtr(rx)
		m.NetworkTX = floatPtr(tx)
		m.DiskInfo = diskInfo.String
		m.Timestamp = ts.String
		out[m.ServerID] = append(out[m.ServerID], m)
	}
	return out, rows.Err()
}

func floatPtr(n sql.NullFloat64) *float64 {
	if !n.Valid {
		return nil
	}
	f := n.Float64
	return &f
}

// UptimeTimeline counts non-NULL cpu rows as "up".
func (st *Store) UptimeTimeline(serverID int64, days int) (up int, down int, timeline []MetricPoint, err error) {
	mod := fmt.Sprintf("-%d days", days)
	rows, err := st.DB.Query(`SELECT id, server_id, cpu_percent, memory_percent, disk_percent,
	  network_rx, network_tx, disk_info, timestamp FROM metrics_history
	  WHERE server_id = ? AND timestamp >= datetime('now', ?) ORDER BY timestamp ASC`, serverID, mod)
	if err != nil {
		return 0, 0, nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var m MetricPoint
		var cpu, mem, disk, rx, tx sql.NullFloat64
		var diskInfo sql.NullString
		var ts sql.NullString
		if err := rows.Scan(&m.ID, &m.ServerID, &cpu, &mem, &disk, &rx, &tx, &diskInfo, &ts); err != nil {
			return 0, 0, nil, err
		}
		m.CPUPercent = floatPtr(cpu)
		m.MemoryPercent = floatPtr(mem)
		m.DiskPercent = floatPtr(disk)
		m.NetworkRX = floatPtr(rx)
		m.NetworkTX = floatPtr(tx)
		m.DiskInfo = diskInfo.String
		m.Timestamp = ts.String
		status := "down"
		if cpu.Valid {
			status = "up"
			up++
		} else {
			down++
		}
		_ = status
		timeline = append(timeline, m)
	}
	return up, down, timeline, rows.Err()
}

// ParseVolumes decodes the volumes JSON column.
func ParseVolumes(raw string) ([]Volume, error) {
	var vols []Volume
	if raw == "" {
		return vols, nil
	}
	if err := json.Unmarshal([]byte(raw), &vols); err != nil {
		// Python stored shape: [{volume, size, free, used_percent}]
		var alt []map[string]any
		if err2 := json.Unmarshal([]byte(raw), &alt); err2 == nil {
			for _, v := range alt {
				vols = append(vols, Volume{
					Volume:  str(v["volume"]),
					SizeGB:  num(v["size"]) / (1 << 30),
					FreeGB:  num(v["free"]) / (1 << 30),
					UsedGB:  num(v["used_percent"]) / (1 << 30),
					Percent: num(v["used_percent"]),
				})
			}
			return vols, nil
		}
		return nil, err
	}
	return vols, nil
}

func str(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func num(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int64:
		return float64(n)
	case int:
		return float64(n)
	case json.Number:
		f, _ := n.Float64()
		return f
	}
	return 0
}

// --- Services ---

func scanService(row interface{ Scan(...any) error }) (*Service, error) {
	var s Service
	var ts, lc sql.NullString
	err := row.Scan(&s.ID, &s.Name, &s.TargetURL, &s.CheckType, &s.Interval,
		&s.Timeout, &s.ExpectedStatus, &s.Enabled, &s.Status, &lc, &s.ResponseTimeMS, &ts)
	if err != nil {
		return nil, err
	}
	s.LastCheck = lc.String
	s.CreatedAt = ts.String
	return &s, nil
}

const serviceCols = `id, name, target_url, check_type, interval, timeout, expected_status,
 enabled, status, last_check, response_time_ms, created_at`

func (st *Store) ListServices() ([]Service, error) {
	rows, err := st.DB.Query(`SELECT ` + serviceCols + ` FROM services ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Service{}
	for rows.Next() {
		s, err := scanService(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *s)
	}
	return out, rows.Err()
}

func (st *Store) GetService(id int64) (*Service, error) {
	row := st.DB.QueryRow(`SELECT `+serviceCols+` FROM services WHERE id = ?`, id)
	s, err := scanService(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	return s, err
}

func (st *Store) CreateService(s *Service) (int64, error) {
	res, err := st.DB.Exec(`INSERT INTO services (name, target_url, check_type, interval, timeout,
	  expected_status, enabled, status, response_time_ms, created_at)
	  VALUES (?,?,?,?,?,?,?,?,?,?)`,
		s.Name, s.TargetURL, s.CheckType, s.Interval, s.Timeout, s.ExpectedStatus,
		s.Enabled, "unknown", 0, Now())
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (st *Store) UpdateService(id int64, fields map[string]any) error {
	if len(fields) == 0 {
		return nil
	}
	var sets []string
	var args []any
	for k, v := range fields {
		sets = append(sets, k+" = ?")
		args = append(args, v)
	}
	args = append(args, id)
	_, err := st.DB.Exec(`UPDATE services SET `+strings.Join(sets, ", ")+` WHERE id = ?`, args...)
	return err
}

func (st *Store) DeleteService(id int64) error {
	tx, err := st.DB.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for _, q := range []string{
		`DELETE FROM services_history WHERE service_id = ?`,
		`DELETE FROM services WHERE id = ?`,
	} {
		if _, err := tx.Exec(q, id); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (st *Store) EnabledServices() ([]Service, error) {
	rows, err := st.DB.Query(`SELECT ` + serviceCols + ` FROM services WHERE enabled = 1`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Service{}
	for rows.Next() {
		s, err := scanService(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *s)
	}
	return out, rows.Err()
}

func (st *Store) InsertServiceHistory(serviceID int64, status string, latency float64) error {
	_, err := st.DB.Exec(`INSERT INTO services_history (service_id, status, latency_ms, timestamp)
	  VALUES (?,?,?,?)`, serviceID, status, latency, Now())
	return err
}

func (st *Store) ServiceHistory(token string) ([]ServiceHistory, error) {
	mod, _ := HistoryRange(token)
	rows, err := st.DB.Query(`SELECT id, service_id, status, latency_ms, timestamp
	  FROM services_history WHERE timestamp >= datetime('now', ?) ORDER BY id ASC`, mod)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []ServiceHistory{}
	for rows.Next() {
		var h ServiceHistory
		var ts sql.NullString
		if err := rows.Scan(&h.ID, &h.ServiceID, &h.Status, &h.LatencyMS, &ts); err != nil {
			return nil, err
		}
		h.Timestamp = ts.String
		out = append(out, h)
	}
	return out, rows.Err()
}

// --- Alerts ---

func (st *Store) ListAlerts() ([]Alert, error) {
	rows, err := st.DB.Query(`SELECT id, server_id, service_id, alert_type, severity, message,
	  timestamp, resolved, resolved_at, name, metric, condition, threshold, duration,
	  notify_telegram, notify_discord, notify_slack, notify_email, notify_teams,
	  description, enabled, created_at FROM alerts ORDER BY id DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Alert{}
	for rows.Next() {
		var a Alert
		var serverID, serviceID sql.NullInt64
		var sev, msg, ts, resolvedAt, name, metric, cond, desc, createdAt sql.NullString
		var threshold sql.NullFloat64
		var duration sql.NullInt64
		if err := rows.Scan(&a.ID, &serverID, &serviceID, &a.AlertType, &sev, &msg,
			&ts, &a.Resolved, &resolvedAt, &name, &metric, &cond, &threshold, &duration,
			&a.NotifyTelegram, &a.NotifyDiscord, &a.NotifySlack, &a.NotifyEmail, &a.NotifyTeams,
			&desc, &a.Enabled, &createdAt); err != nil {
			return nil, err
		}
		a.ServerID = serverID.Int64
		a.ServiceID = serviceID.Int64
		a.Severity = sev.String
		a.Message = msg.String
		a.Timestamp = ts.String
		a.ResolvedAt = resolvedAt.String
		a.Name = name.String
		a.Metric = metric.String
		a.Condition = cond.String
		a.Threshold = threshold.Float64
		a.Duration = int(duration.Int64)
		a.Description = desc.String
		a.CreatedAt = createdAt.String
		out = append(out, a)
	}
	return out, rows.Err()
}

func (st *Store) CreateAlert(a *Alert) (int64, error) {
	ts := Now()
	res, err := st.DB.Exec(`INSERT INTO alerts (server_id, service_id, alert_type, severity,
	  message, timestamp, resolved, resolved_at, name, metric, condition, threshold, duration,
	  notify_telegram, notify_discord, notify_slack, notify_email, notify_teams,
	  description, enabled, created_at) VALUES (?,?,?,?,?,?,0,NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		nullID(a.ServerID), nullID(a.ServiceID), a.AlertType, a.Severity, a.Message, ts,
		a.Name, a.Metric, a.Condition, a.Threshold, a.Duration,
		a.NotifyTelegram, a.NotifyDiscord, a.NotifySlack, a.NotifyEmail, a.NotifyTeams,
		a.Description, a.Enabled, ts)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (st *Store) DeleteAlert(id int64) error {
	_, err := st.DB.Exec(`DELETE FROM alerts WHERE id = ?`, id)
	return err
}

func nullID(id int64) any {
	if id == 0 {
		return nil
	}
	return id
}

// --- Audit log ---

func (st *Store) AddAudit(userID int64, action, details, ip string) error {
	_, err := st.DB.Exec(`INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp)
	  VALUES (?,?,?,?,?)`, nullID(userID), action, details, ip, Now())
	return err
}

func (st *Store) ListAudit(limit, offset int) ([]AuditLog, error) {
	rows, err := st.DB.Query(`SELECT id, user_id, action, details, ip_address, timestamp
	  FROM audit_logs ORDER BY id DESC LIMIT ? OFFSET ?`, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []AuditLog{}
	for rows.Next() {
		var a AuditLog
		var uid sql.NullInt64
		var action, details, ip, ts sql.NullString
		if err := rows.Scan(&a.ID, &uid, &action, &details, &ip, &ts); err != nil {
			return nil, err
		}
		a.UserID = uid.Int64
		a.Action = action.String
		a.Details = details.String
		a.IPAddress = ip.String
		a.Timestamp = ts.String
		out = append(out, a)
	}
	return out, rows.Err()
}

func (st *Store) CountAudit() (int, error) {
	var n int
	err := st.DB.QueryRow(`SELECT COUNT(*) FROM audit_logs`).Scan(&n)
	return n, err
}

func (st *Store) ClearAudit() error {
	_, err := st.DB.Exec(`DELETE FROM audit_logs`)
	return err
}

// --- Users ---

func (st *Store) GetUserByUsername(username string) (*User, error) {
	row := st.DB.QueryRow(`SELECT id, username, password_hash, is_admin, must_change_password,
	  created_at, last_login FROM users WHERE username = ?`, username)
	return scanUser(row)
}

func (st *Store) GetUserByID(id int64) (*User, error) {
	row := st.DB.QueryRow(`SELECT id, username, password_hash, is_admin, must_change_password,
	  created_at, last_login FROM users WHERE id = ?`, id)
	return scanUser(row)
}

func scanUser(row interface{ Scan(...any) error }) (*User, error) {
	var u User
	var admin, mustChange sql.NullInt64
	var created, lastLogin sql.NullString
	err := row.Scan(&u.ID, &u.Username, &u.PasswordHash, &admin, &mustChange, &created, &lastLogin)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	u.IsAdmin = int(admin.Int64)
	u.MustChangePassword = int(mustChange.Int64)
	u.CreatedAt = created.String
	u.LastLogin = lastLogin.String
	return &u, nil
}

func (st *Store) ListUsers() ([]User, error) {
	rows, err := st.DB.Query(`SELECT id, username, password_hash, is_admin, must_change_password,
	  created_at, last_login FROM users ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []User{}
	for rows.Next() {
		u, err := scanUser(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *u)
	}
	return out, rows.Err()
}

func (st *Store) CreateUser(username, hash string, isAdmin int) (int64, error) {
	res, err := st.DB.Exec(`INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at)
	  VALUES (?,?,?,1,?)`, username, hash, isAdmin, Now())
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (st *Store) UpdateUser(id int64, fields map[string]any) error {
	var sets []string
	var args []any
	for k, v := range fields {
		sets = append(sets, k+" = ?")
		args = append(args, v)
	}
	args = append(args, id)
	_, err := st.DB.Exec(`UPDATE users SET `+strings.Join(sets, ", ")+` WHERE id = ?`, args...)
	return err
}

func (st *Store) DeleteUser(id int64) error {
	_, err := st.DB.Exec(`DELETE FROM users WHERE id = ?`, id)
	return err
}

func (st *Store) CountAdmins() (int, error) {
	var n int
	err := st.DB.QueryRow(`SELECT COUNT(*) FROM users WHERE is_admin = 1`).Scan(&n)
	return n, err
}

// --- API keys ---

func (st *Store) GetAPIKeyBySHA(sha string) (*APIKey, error) {
	row := st.DB.QueryRow(`SELECT id, user_id, key_hash, key_sha256, name, created_at, last_used
	  FROM api_keys WHERE key_sha256 = ?`, sha)
	return scanAPIKey(row)
}

func scanAPIKey(row interface{ Scan(...any) error }) (*APIKey, error) {
	var k APIKey
	var uid sql.NullInt64
	var hash, name, created, lastUsed sql.NullString
	err := row.Scan(&k.ID, &uid, &hash, &k.KeySHA256, &name, &created, &lastUsed)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	k.UserID = uid.Int64
	k.KeyHash = hash.String
	k.Name = name.String
	k.CreatedAt = created.String
	k.LastUsed = lastUsed.String
	return &k, nil
}

func (st *Store) CreateAPIKey(userID int64, hash, sha, name string) (int64, error) {
	res, err := st.DB.Exec(`INSERT INTO api_keys (user_id, key_hash, key_sha256, name, created_at)
	  VALUES (?,?,?,?,?)`, userID, hash, sha, name, Now())
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (st *Store) ListAPIKeys(userID int64) ([]APIKey, error) {
	rows, err := st.DB.Query(`SELECT id, user_id, key_hash, key_sha256, name, created_at, last_used
	  FROM api_keys WHERE user_id = ? ORDER BY id`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []APIKey{}
	for rows.Next() {
		k, err := scanAPIKey(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *k)
	}
	return out, rows.Err()
}

func (st *Store) DeleteAPIKey(id int64) error {
	_, err := st.DB.Exec(`DELETE FROM api_keys WHERE id = ?`, id)
	return err
}

func (st *Store) TouchAPIKey(id int64) {
	_, _ = st.DB.Exec(`UPDATE api_keys SET last_used = ? WHERE id = ?`, Now(), id)
}

// --- Notifications ---

func (st *Store) GetNotifications() (*Notification, error) {
	row := st.DB.QueryRow(`SELECT channel, enabled, config FROM notifications WHERE channel = 'all'`)
	var n Notification
	var enabled sql.NullInt64
	var config sql.NullString
	if err := row.Scan(&n.Channel, &enabled, &config); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	n.Enabled = int(enabled.Int64)
	if config.Valid && config.String != "" {
		dec, err := st.decryptText(config.String)
		if err != nil {
			return nil, err
		}
		n.Config = dec
	} else {
		n.Config = ""
	}
	return &n, nil
}

func (st *Store) SaveNotifications(config string, enabled int) error {
	enc, err := st.encryptText(config)
	if err != nil {
		return err
	}
	_, err = st.DB.Exec(`INSERT INTO notifications (channel, enabled, config) VALUES ('all',?,?)
	  ON CONFLICT(channel) DO UPDATE SET enabled=excluded.enabled, config=excluded.config`,
		enabled, enc)
	return err
}

// --- Push metrics ---

func (st *Store) PushMetric(name, labels string, value float64) error {
	_, err := st.DB.Exec(`INSERT INTO metrics (name, labels, value, timestamp) VALUES (?,?,?,?)`,
		name, labels, value, Now())
	return err
}

func (st *Store) RecentMetrics(limit int) ([]Metric, error) {
	if limit <= 0 {
		limit = 20
	}
	rows, err := st.DB.Query(`SELECT id, name, labels, value, timestamp FROM metrics
	  ORDER BY id DESC LIMIT ?`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Metric{}
	for rows.Next() {
		var m Metric
		var labels, ts sql.NullString
		if err := rows.Scan(&m.ID, &m.Name, &labels, &m.Value, &ts); err != nil {
			return nil, err
		}
		m.Labels = labels.String
		m.Timestamp = ts.String
		out = append(out, m)
	}
	return out, rows.Err()
}

// --- Retention / maintenance ---

func (st *Store) Cleanup(retentionHours int) error {
	mod := fmt.Sprintf("-%d hours", retentionHours)
	tables := []string{"metrics_history", "services_history", "alerts", "metrics"}
	for _, t := range tables {
		if _, err := st.DB.Exec(fmt.Sprintf(`DELETE FROM %s WHERE timestamp < datetime('now', ?)`, t), mod); err != nil {
			return err
		}
	}
	return nil
}

func (st *Store) Vacuum() {
	_, _ = st.DB.Exec(`VACUUM`)
}

func (st *Store) ServerLastTimestamp(serverID int64) string {
	var ts string
	_ = st.DB.QueryRow(`SELECT MAX(timestamp) FROM metrics_history WHERE server_id = ?`, serverID).Scan(&ts)
	return ts
}

// SlowDirtyUptimePercent returns uptime % for last 1h based on non-NULL cpu rows.
func (st *Store) ServerSummary(serverID int64) (avgCPU, avgMem, avgDisk float64, status string, err error) {
	rows, err := st.DB.Query(`SELECT cpu_percent, memory_percent, disk_percent FROM metrics_history
	  WHERE server_id = ? AND timestamp >= datetime('now','-1 hours')`, serverID)
	if err != nil {
		return 0, 0, 0, "", err
	}
	defer rows.Close()
	var cpuN, memN, diskN, up int
	for rows.Next() {
		var c, m, d sql.NullFloat64
		if err := rows.Scan(&c, &m, &d); err != nil {
			return 0, 0, 0, "", err
		}
		if c.Valid {
			cpuN++
			avgCPU += c.Float64
			up++
		}
		if m.Valid {
			memN++
			avgMem += m.Float64
		}
		if d.Valid {
			diskN++
			avgDisk += d.Float64
		}
	}
	if cpuN > 0 {
		avgCPU = avgCPU / float64(cpuN)
	}
	if memN > 0 {
		avgMem = avgMem / float64(memN)
	}
	if diskN > 0 {
		avgDisk = avgDisk / float64(diskN)
	}
	status = "down"
	if up > 0 {
		status = "up"
	}
	return avgCPU, avgMem, avgDisk, status, nil
}

func (st *Store) CountAllServers() (int, error) {
	var n int
	err := st.DB.QueryRow(`SELECT COUNT(*) FROM servers`).Scan(&n)
	return n, err
}

func (st *Store) TotalOnline() (int, error) {
	var n int
	err := st.DB.QueryRow(`SELECT COUNT(*) FROM servers WHERE last_status = 'up'`).Scan(&n)
	return n, err
}

var _ = time.Now
