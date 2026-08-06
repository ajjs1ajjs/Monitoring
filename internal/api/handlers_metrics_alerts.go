package api

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

// --- metrics ---

func (a *App) handlePushMetric(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name   string   `json:"name"`
		Value  *float64 `json:"value"`
		Type   string   `json:"type"`
		Labels []struct {
			Name  string `json:"name"`
			Value string `json:"value"`
		} `json:"labels"`
		HelpText string `json:"help_text"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Value == nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	labelsMap := map[string]string{}
	for _, l := range body.Labels {
		labelsMap[l.Name] = l.Value
	}
	labelsJSON, _ := json.Marshal(labelsMap)
	if a.Metrics != nil {
		a.Metrics.Add(registryEntry{Name: body.Name, Type: body.Type, Help: body.HelpText, Value: *body.Value, Labels: labelsMap})
	}
	if err := a.Store.PushMetric(body.Name, string(labelsJSON), *body.Value); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleListMetrics(w http.ResponseWriter, r *http.Request) {
	metrics, err := a.Store.RecentMetrics(20)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"metrics": metrics})
}

func (a *App) handleMetricsTrend(w http.ResponseWriter, r *http.Request) {
	token := r.URL.Query().Get("range")
	if token == "" {
		token = "1h"
	}
	history, err := a.Store.AllServersHistory(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	// aggregate per timestamp bucket (already downsampled per server)
	type agg struct {
		Timestamp string  `json:"timestamp"`
		CPUAvg    float64 `json:"cpu_avg"`
		MemAvg    float64 `json:"mem_avg"`
		DiskAvg   float64 `json:"disk_avg"`
		NetRXAvg  float64 `json:"net_rx_avg"`
		NetTXAvg  float64 `json:"net_tx_avg"`
	}
	buckets := map[string]*struct {
		cpuSum, memSum, diskSum, rxSum, txSum float64
		cpuN, memN, diskN, rxN, txN           int
	}{}
	order := []string{}
	for _, pts := range history {
		for _, p := range pts {
			b, ok := buckets[p.Timestamp]
			if !ok {
				b = &struct {
					cpuSum, memSum, diskSum, rxSum, txSum float64
					cpuN, memN, diskN, rxN, txN           int
				}{}
				buckets[p.Timestamp] = b
				order = append(order, p.Timestamp)
			}
			if p.CPUPercent != nil {
				b.cpuSum += *p.CPUPercent
				b.cpuN++
			}
			if p.MemoryPercent != nil {
				b.memSum += *p.MemoryPercent
				b.memN++
			}
			if p.DiskPercent != nil {
				b.diskSum += *p.DiskPercent
				b.diskN++
			}
			if p.NetworkRX != nil {
				b.rxSum += *p.NetworkRX
				b.rxN++
			}
			if p.NetworkTX != nil {
				b.txSum += *p.NetworkTX
				b.txN++
			}
		}
	}
	avg := func(sum float64, n int) float64 {
		if n == 0 {
			return 0
		}
		return sum / float64(n)
	}
	out := make([]agg, 0, len(order))
	for _, ts := range order {
		b := buckets[ts]
		out = append(out, agg{ts, avg(b.cpuSum, b.cpuN), avg(b.memSum, b.memN),
			avg(b.diskSum, b.diskN), avg(b.rxSum, b.rxN), avg(b.txSum, b.txN)})
	}
	writeJSON(w, http.StatusOK, map[string]any{"history": out})
}

func (a *App) handleClearMetricHistory(w http.ResponseWriter, r *http.Request) {
	if _, err := a.Store.DB.Exec(`DELETE FROM metrics_history`); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "metrics_cleared", "Metric history cleared")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

// --- alerts ---

func (a *App) handleListAlerts(w http.ResponseWriter, r *http.Request) {
	alerts, err := a.Store.ListAlerts()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"alerts": alerts})
}

func (a *App) handleCreateAlert(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name           string  `json:"name"`
		Metric         string  `json:"metric"`
		Condition      string  `json:"condition"`
		Threshold      float64 `json:"threshold"`
		Duration       int     `json:"duration"`
		Severity       string  `json:"severity"`
		ServerID       int64   `json:"server_id"`
		ServiceID      int64   `json:"service_id"`
		NotifyTelegram bool    `json:"notify_telegram"`
		NotifyDiscord  bool    `json:"notify_discord"`
		NotifySlack    bool    `json:"notify_slack"`
		NotifyEmail    bool    `json:"notify_email"`
		NotifyTeams    bool    `json:"notify_teams"`
		Description    string  `json:"description"`
		Enabled        bool    `json:"enabled"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	sev := body.Severity
	if sev == "" {
		sev = "warning"
	}
	enabled := 1
	if !body.Enabled {
		enabled = 0
	}
	id, err := a.Store.CreateAlert(&storage.Alert{
		Name: body.Name, Metric: body.Metric, Condition: body.Condition,
		Threshold: body.Threshold, Duration: body.Duration, Severity: sev,
		ServerID: body.ServerID, ServiceID: body.ServiceID, Description: body.Description,
		Enabled: enabled,
	})
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "alert_created", "Alert '"+body.Name+"' created")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "id": id})
}

func (a *App) handleDeleteAlert(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "alert_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid alert id")
		return
	}
	if err := a.Store.DeleteAlert(id); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "alert_deleted", "Alert deleted")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

// --- services ---

func (a *App) handleListServices(w http.ResponseWriter, r *http.Request) {
	services, err := a.Store.ListServices()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"services": services})
}

func (a *App) handleCreateService(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name           string `json:"name"`
		TargetURL      string `json:"target_url"`
		CheckType      string `json:"check_type"`
		Interval       int    `json:"interval"`
		Timeout        int    `json:"timeout"`
		ExpectedStatus int    `json:"expected_status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	if body.Name == "" || body.TargetURL == "" {
		writeErr(w, http.StatusBadRequest, "Name and target_url are required")
		return
	}
	if body.Interval < 5 {
		writeErr(w, http.StatusBadRequest, "Interval must be >= 5 seconds")
		return
	}
	if body.Timeout < 1 {
		writeErr(w, http.StatusBadRequest, "Timeout must be >= 1 second")
		return
	}
	switch body.CheckType {
	case "", "http", "tcp", "ping", "ssl":
	default:
		writeErr(w, http.StatusBadRequest, "Invalid check type")
		return
	}
	if body.CheckType == "" {
		body.CheckType = "http"
	}
	if body.ExpectedStatus == 0 {
		body.ExpectedStatus = 200
	}
	s := &storage.Service{
		Name: body.Name, TargetURL: body.TargetURL, CheckType: body.CheckType,
		Interval: body.Interval, Timeout: body.Timeout, ExpectedStatus: body.ExpectedStatus,
		Enabled: 1,
	}
	id, err := a.Store.CreateService(s)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "service_created", "Service "+body.Name+" created")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "id": id})
}

func (a *App) handleServicesHistory(w http.ResponseWriter, r *http.Request) {
	token := r.URL.Query().Get("range")
	if token == "" {
		token = "1h"
	}
	history, err := a.Store.ServiceHistory(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, history)
}

func (a *App) handleDeleteService(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "service_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid service id")
		return
	}
	if err := a.Store.DeleteService(id); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "service_deleted", "Service deleted")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

// --- audit logs ---

func (a *App) handleListAudit(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit < 1 || limit > 1000 {
		limit = 100
	}
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	logs, err := a.Store.ListAudit(limit, offset)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	total, err := a.Store.CountAudit()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"logs": logs, "total": total, "limit": limit, "offset": offset})
}

func (a *App) handleClearAudit(w http.ResponseWriter, r *http.Request) {
	if err := a.Store.ClearAudit(); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "audit_cleared", "Audit log cleared")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleSystemLogs(w http.ResponseWriter, r *http.Request) {
	lines := 200
	if v := r.URL.Query().Get("lines"); v != "" {
		if n, e := strconv.Atoi(v); e == nil && n >= 10 && n <= 5000 {
			lines = n
		}
	}
	content := tailLogFile(a.LogFilePath(), lines)
	writeJSON(w, http.StatusOK, map[string]any{"logs": strings.Split(strings.TrimRight(content, "\n"), "\n")})
}

func (a *App) handleClearSystemLogs(w http.ResponseWriter, r *http.Request) {
	_ = truncateLogFile(a.LogFilePath())
	a.audit(r, "system_logs_cleared", "System logs cleared")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}
