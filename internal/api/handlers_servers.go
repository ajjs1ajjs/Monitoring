package api

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

func hostNameRe(s string) bool {
	if s == "" {
		return false
	}
	for _, c := range s {
		if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
			(c >= '0' && c <= '9') || c == '.' || c == '_' ||
			c == '-' || c == ':' || c == '[' || c == ']') {
			return false
		}
	}
	return true
}

func validServerName(s string) bool {
	if s == "" || len(s) > 100 {
		return false
	}
	for _, c := range s {
		if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
			(c >= '0' && c <= '9') || c == '_' || c == '-' || c == ' ' ||
			c == '.' || (c >= 0x400 && c <= 0x4FF)) {
			return false
		}
	}
	return true
}

func (a *App) handleListServers(w http.ResponseWriter, r *http.Request) {
	servers, err := a.Store.ListServers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"servers": servers})
}

func (a *App) handleCreateServer(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name           string `json:"name"`
		Host           string `json:"host"`
		OSType         string `json:"os_type"`
		AgentPort      int    `json:"agent_port"`
		Enabled        *bool  `json:"enabled"`
		ServerGroup    string `json:"server_group"`
		ScrapeInterval int    `json:"scrape_interval"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	if !validServerName(body.Name) {
		writeErr(w, http.StatusBadRequest, "Invalid server name")
		return
	}
	if !hostNameRe(body.Host) {
		writeErr(w, http.StatusBadRequest, "Invalid host")
		return
	}
	port := body.AgentPort
	if port == 0 {
		if strings.EqualFold(body.OSType, "windows") {
			port = 9182
		} else {
			port = 9100
		}
	}
	osType := body.OSType
	if osType == "" {
		osType = "linux"
	}
	enabled := 1
	if body.Enabled != nil && !*body.Enabled {
		enabled = 0
	}
	s := &storage.Server{
		Name: body.Name, Host: body.Host, OSType: osType, AgentPort: port,
		Enabled: enabled, ServerGroup: body.ServerGroup, ScrapeInterval: body.ScrapeInterval,
		Volumes: "[]", Labels: "{}",
	}
	id, err := a.Store.CreateServer(s)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "server_created", "Server "+body.Name+" created")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "id": id})
}

func (a *App) handleGetServer(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	s, err := a.Store.GetServer(id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	if s == nil {
		writeErr(w, http.StatusNotFound, "Server not found")
		return
	}
	writeJSON(w, http.StatusOK, s)
}

func (a *App) handleUpdateServer(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	s, err := a.Store.GetServer(id)
	if err != nil || s == nil {
		writeErr(w, http.StatusNotFound, "Server not found")
		return
	}
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	fields := map[string]any{}
	for k, v := range body {
		switch k {
		case "name":
			name, _ := v.(string)
			if !validServerName(name) {
				writeErr(w, http.StatusBadRequest, "Invalid server name")
				return
			}
			fields["name"] = name
		case "host":
			host, _ := v.(string)
			if !hostNameRe(host) {
				writeErr(w, http.StatusBadRequest, "Invalid host")
				return
			}
			fields["host"] = host
		case "os_type":
			fields["os_type"] = v.(string)
		case "agent_port":
			fields["agent_port"] = int(v.(float64))
		case "enabled":
			n := 0
			if v.(bool) {
				n = 1
			}
			fields["enabled"] = n
		case "server_group":
			fields["server_group"] = v.(string)
		case "scrape_interval":
			fields["scrape_interval"] = int(v.(float64))
		}
	}
	if err := a.Store.UpdateServer(id, fields); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "server_updated", "Server "+s.Name+" updated")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleDeleteServer(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	s, _ := a.Store.GetServer(id)
	if err := a.Store.DeleteServer(id); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	if s != nil {
		a.audit(r, "server_deleted", "Server "+s.Name+" deleted")
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleServersHistory(w http.ResponseWriter, r *http.Request) {
	token := r.URL.Query().Get("range")
	if token == "" {
		token = "1h"
	}
	servers, err := a.Store.ListServers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	history, err := a.Store.AllServersHistory(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	out := make([]map[string]any, 0, len(servers))
	for _, s := range servers {
		out = append(out, map[string]any{
			"id": s.ID, "name": s.Name, "host": s.Host, "history": history[s.ID],
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"range": token, "servers": out})
}

func (a *App) handleServerHistory(w http.ResponseWriter, r *http.Request) {
	var id int64
	if v := r.PathValue("server_id"); v != "" {
		id, _ = strconv.ParseInt(v, 10, 64)
	} else {
		id, _ = pathInt(r, "id")
	}
	if id == 0 {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	token := r.URL.Query().Get("range")
	if token == "" {
		token = "1h"
	}
	history, err := a.Store.ServerHistory(id, token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"history": history})
}

func (a *App) handleDiskBreakdown(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	s, err := a.Store.GetServer(id)
	if err != nil || s == nil {
		writeErr(w, http.StatusNotFound, "Server not found")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"disks": s.Volumes})
}

func (a *App) handleUptimeTimeline(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	days := 7
	if v := r.URL.Query().Get("days"); v != "" {
		if n, e := strconv.Atoi(v); e == nil && n >= 1 && n <= 90 {
			days = n
		}
	}
	up, down, timeline, err := a.Store.UptimeTimeline(id, days)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	total := up + down
	uptime := 100.0
	if total > 0 {
		uptime = float64(up) / float64(total) * 100
	}
	type tlPoint struct {
		Timestamp string `json:"timestamp"`
		Status    string `json:"status"`
	}
	out := make([]tlPoint, 0, len(timeline))
	for _, p := range timeline {
		st := "down"
		if p.CPUPercent != nil {
			st = "up"
		}
		out = append(out, tlPoint{p.Timestamp, st})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"timeline": out, "uptime_percent": uptime,
	})
}

func (a *App) handleServerSummary(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	cpu, mem, disk, status, err := a.Store.ServerSummary(id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"server_id": id, "status": status,
		"avg_cpu": cpu, "avg_memory": mem, "avg_disk": disk,
	})
}

func (a *App) handleSummaryAll(w http.ResponseWriter, r *http.Request) {
	servers, err := a.Store.ListServers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	total := len(servers)
	online := 0
	var cpuSum, memSum, diskSum float64
	for _, s := range servers {
		if s.LastStatus == "up" {
			online++
		}
		cpuSum += s.CPUPercent
		memSum += s.MemoryPercent
		diskSum += s.DiskPercent
	}
	avg := func(sum float64, n int) float64 {
		if n == 0 {
			return 0
		}
		return sum / float64(n)
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"total": total, "online": online, "offline": total - online,
		"avg_cpu": avg(cpuSum, total), "avg_memory": avg(memSum, total),
		"avg_disk": avg(diskSum, total),
	})
}

func (a *App) handleSetMaintenance(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	var body struct {
		IsMaintenance bool `json:"is_maintenance"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	n := 0
	if body.IsMaintenance {
		n = 1
	}
	if err := a.Store.UpdateServer(id, map[string]any{"is_maintenance": n}); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "is_maintenance": body.IsMaintenance})
}

func (a *App) handleForceScrape(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	if a.Monitor == nil {
		writeErr(w, http.StatusInternalServerError, "Monitor not available")
		return
	}
	if err := a.Monitor.ForceScrape(id); err != nil {
		writeErr(w, http.StatusInternalServerError, fmt.Sprintf("Scrape failed: %v", err))
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "success"})
}

// --- export ---

func (a *App) handleServersExport(w http.ResponseWriter, r *http.Request) {
	token := r.URL.Query().Get("range")
	format := r.URL.Query().Get("format")
	if token == "" {
		token = "1h"
	}
	servers, err := a.Store.ListServers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	history, err := a.Store.AllServersHistory(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	if format == "csv" {
		writeCSVServers(w, servers, history)
		return
	}
	type srv struct {
		ID   int64          `json:"id"`
		Name string         `json:"name"`
		Host string         `json:"host"`
		Data []metricExport `json:"data"`
	}
	out := make([]srv, 0, len(servers))
	for _, s := range servers {
		out = append(out, srv{s.ID, s.Name, s.Host, toMetricExport(history[s.ID])})
	}
	writeJSON(w, http.StatusOK, map[string]any{"range": token, "servers": out})
}

func (a *App) handleServerExport(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid id")
		return
	}
	token := r.URL.Query().Get("range")
	format := r.URL.Query().Get("format")
	if token == "" {
		token = "1h"
	}
	s, err := a.Store.GetServer(id)
	if err != nil || s == nil {
		writeErr(w, http.StatusNotFound, "Server not found")
		return
	}
	history, err := a.Store.ServerHistory(id, token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	if format == "csv" {
		writeCSVServer(w, s.Name, toMetricExport(history))
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"server": s, "range": token, "data": toMetricExport(history),
	})
}

type metricExport struct {
	Timestamp string   `json:"timestamp"`
	CPU       *float64 `json:"cpu"`
	Memory    *float64 `json:"memory"`
	Disk      *float64 `json:"disk"`
	NetworkRX *float64 `json:"network_rx"`
	NetworkTX *float64 `json:"network_tx"`
}

func toMetricExport(points []storage.MetricPoint) []metricExport {
	out := make([]metricExport, 0, len(points))
	for _, p := range points {
		out = append(out, metricExport{
			Timestamp: p.Timestamp, CPU: p.CPUPercent, Memory: p.MemoryPercent,
			Disk: p.DiskPercent, NetworkRX: p.NetworkRX, NetworkTX: p.NetworkTX,
		})
	}
	return out
}

func writeCSVServers(w http.ResponseWriter, servers []storage.Server, history map[int64][]storage.MetricPoint) {
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	writer := csv.NewWriter(w)
	_ = writer.Write([]string{"server_id", "server_name", "timestamp", "cpu", "memory", "disk", "network_rx", "network_tx"})
	for _, s := range servers {
		for _, p := range history[s.ID] {
			_ = writer.Write([]string{
				strconv.FormatInt(s.ID, 10), s.Name, p.Timestamp,
				formatPtr(p.CPUPercent), formatPtr(p.MemoryPercent), formatPtr(p.DiskPercent),
				formatPtr(p.NetworkRX), formatPtr(p.NetworkTX),
			})
		}
	}
	writer.Flush()
}

func writeCSVServer(w http.ResponseWriter, name string, points []metricExport) {
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	writer := csv.NewWriter(w)
	_ = writer.Write([]string{"server_name", "timestamp", "cpu", "memory", "disk", "network_rx", "network_tx"})
	for _, p := range points {
		_ = writer.Write([]string{name, p.Timestamp, formatPtr(p.CPU), formatPtr(p.Memory),
			formatPtr(p.Disk), formatPtr(p.NetworkRX), formatPtr(p.NetworkTX)})
	}
	writer.Flush()
}

func formatPtr(f *float64) string {
	if f == nil {
		return ""
	}
	return fmt.Sprintf("%.2f", *f)
}

func (a *App) handleServersCompare(w http.ResponseWriter, r *http.Request) {
	metric := r.URL.Query().Get("metric")
	token := r.URL.Query().Get("range")
	if metric == "" {
		metric = "cpu"
	}
	if token == "" {
		token = "1h"
	}
	servers, err := a.Store.ListServers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	history, err := a.Store.AllServersHistory(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	out := []map[string]any{}
	for _, s := range servers {
		points := history[s.ID]
		var sum, min, max float64
		var n int
		haveMin := false
		for _, p := range points {
			var v *float64
			switch metric {
			case "cpu":
				v = p.CPUPercent
			case "memory", "mem":
				v = p.MemoryPercent
			case "disk":
				v = p.DiskPercent
			}
			if v == nil {
				continue
			}
			sum += *v
			if !haveMin || *v < min {
				min = *v
			}
			if !haveMin || *v > max {
				max = *v
			}
			haveMin = true
			n++
		}
		avg := 0.0
		if n > 0 {
			avg = sum / float64(n)
		}
		out = append(out, map[string]any{
			"server_id": s.ID, "server_name": s.Name, "metric": metric,
			"average": avg, "min": min, "max": max, "data_points": n,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"metric": metric, "range": token, "servers": out})
}
