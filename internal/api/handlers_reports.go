package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

func (a *App) handleHealth(w http.ResponseWriter, r *http.Request) {
	status := "ok"
	if a.Store == nil {
		status = "degraded"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":         status,
		"version":        a.Version.Version,
		"uptime_seconds": int64(time.Since(a.StartTime).Seconds()),
		"time":           time.Now().Format(time.RFC3339),
	})
}

func (a *App) handleServerReport(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "server_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid server id")
		return
	}
	s, err := a.Store.GetServer(id)
	if err != nil || s == nil {
		writeErr(w, http.StatusNotFound, "Server not found")
		return
	}
	history, err := a.Store.ServerHistory(id, "24h")
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	type pt struct {
		Timestamp string   `json:"timestamp"`
		CPU       *float64 `json:"cpu"`
		Memory    *float64 `json:"memory"`
	}
	var cpuPts, memPts []pt
	for _, h := range history {
		cpuPts = append(cpuPts, pt{h.Timestamp, h.CPUPercent, nil})
		memPts = append(memPts, pt{h.Timestamp, nil, h.MemoryPercent})
	}
	cpuJSON, _ := json.Marshal(cpuPts)
	memJSON, _ := json.Marshal(memPts)
	gen := time.Now().Format("2006-01-02 15:04")

	const head = `<!DOCTYPE html>
<html lang="uk"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report: %TITLE%</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>body{font-family:system-ui,sans-serif;margin:24px;color:#0f172a}table{border-collapse:collapse;width:100%;margin:16px 0}
th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}.chart{max-width:100%;margin:24px 0}h2{color:#334155}
button{padding:10px 16px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer}
@media print { button{display:none} }</style>
</head><body>
<h1>Server Report: %TITLE%</h1>
<p>Generated: %GEN%</p>
<h2>Status</h2>
<table><tr><th>Host</th><th>Status</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last check</th></tr>
<tr><td>%HOST%</td><td>%STATUS%</td><td>%CPU%</td><td>%MEM%</td><td>%DISK%</td><td>%LAST%</td></tr></table>
<h2>CPU (24h)</h2><div class="chart"><canvas id="cpuChart"></canvas></div>
<h2>Memory (24h)</h2><div class="chart"><canvas id="memChart"></canvas></div>
<button onclick="window.print()">Print / PDF</button>
<script>
const cpu = %CPUJSON%; const mem = %MEMJSON%;
function mk(id,label,data,color){new Chart(document.getElementById(id),{type:'line',data:{labels:data.map(p=>p.timestamp),
datasets:[{label:label,data:data.map(p=>p.cpu??p.memory??null),borderColor:color,fill:true,tension:0.3}]},
options:{scales:{y:{beginAtZero:true}},plugins:{legend:{display:false}}}});}
mk('cpuChart','CPU %',cpu,'#2563eb'); mk('memChart','Memory %',mem,'#16a34a');
</script></body></html>`

	cpuPct := fmt.Sprintf("%.1f%%", s.CPUPercent)
	memPct := fmt.Sprintf("%.1f%%", s.MemoryPercent)
	diskPct := fmt.Sprintf("%.1f%%", s.DiskPercent)

	replacer := strings.NewReplacer(
		"%TITLE%", escapeHTML(s.Name),
		"%GEN%", gen,
		"%HOST%", escapeHTML(s.Host),
		"%STATUS%", escapeHTML(s.LastStatus),
		"%CPU%", cpuPct,
		"%MEM%", memPct,
		"%DISK%", diskPct,
		"%LAST%", escapeHTML(s.LastCheck),
		"%CPUJSON%", string(cpuJSON),
		"%MEMJSON%", string(memJSON),
	)
	html := replacer.Replace(head)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write([]byte(html))
}

func escapeHTML(s string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", "\"", "&quot;", "'", "&#39;")
	return r.Replace(s)
}
