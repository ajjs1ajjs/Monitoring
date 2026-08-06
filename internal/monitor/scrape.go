package monitor

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

type Broadcaster interface {
	Broadcast(event map[string]any)
}

type AlertSink interface {
	Dispatch(title, message string)
}

type Manager struct {
	Cfg    *config.Config
	Store  *storage.Store
	WS     Broadcaster
	Alerts AlertSink

	client *http.Client

	mu           sync.Mutex
	ruleState    map[[2]string]*ruleEpisode
	lastCleanup  time.Time
	vacuumedDate string
	lastBackup   time.Time
}

type ruleEpisode struct {
	started time.Time
	alerted bool
}

func New(cfg *config.Config, store *storage.Store, ws Broadcaster, alerts AlertSink) *Manager {
	return &Manager{
		Cfg: cfg, Store: store, WS: ws, Alerts: alerts,
		client:    &http.Client{Timeout: 10 * time.Second},
		ruleState: map[[2]string]*ruleEpisode{},
	}
}

func (m *Manager) ScrapeInterval() time.Duration {
	if m.Cfg != nil {
		if sec := m.Cfg.ScrapeIntervalSeconds(); sec > 0 {
			return time.Duration(sec) * time.Second
		}
	}
	return 15 * time.Second
}

func (m *Manager) Run(ctx context.Context) {
	go m.scrapeLoop(ctx)
	go m.checkLoop(ctx)
}

func (m *Manager) scrapeLoop(ctx context.Context) {
	time.Sleep(5 * time.Second)
	interval := m.ScrapeInterval()
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}
		if err := m.ScrapeAll(); err != nil {
			log.Printf("[ScrapeManager] error: %v", err)
		}
		m.cleanup()
		m.backupIfDue()
		select {
		case <-ctx.Done():
			return
		case <-time.After(interval):
		}
	}
}

func (m *Manager) cleanup() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if time.Since(m.lastCleanup) < time.Hour {
		return
	}
	m.lastCleanup = time.Now()
	retention := 168
	if m.Cfg != nil && m.Cfg.Storage.RetentionHours > 0 {
		retention = m.Cfg.Storage.RetentionHours
	}
	if err := m.Store.Cleanup(retention); err != nil {
		log.Printf("cleanup error: %v", err)
	}
	today := time.Now().Format("2006-01-02")
	if today != m.vacuumedDate && time.Now().Hour() == 3 {
		m.Store.Vacuum()
		m.vacuumedDate = today
	}
}

// ScrapeAll scrapes all enabled servers concurrently (semaphore 10).
func (m *Manager) ScrapeAll() error {
	servers, err := m.Store.EnabledServers()
	if err != nil {
		return err
	}
	if len(servers) == 0 {
		return nil
	}
	sem := make(chan struct{}, 10)
	var wg sync.WaitGroup
	for i := range servers {
		wg.Add(1)
		go func(s *storage.Server) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			m.scrapeOne(s)
		}(&servers[i])
	}
	wg.Wait()
	return nil
}

func (m *Manager) ForceScrape(serverID int64) error {
	s, err := m.Store.GetServer(serverID)
	if err != nil || s == nil {
		return fmt.Errorf("server not found")
	}
	up := m.scrapeOne(s)
	if !up {
		return fmt.Errorf("scrape failed (server down or unreachable)")
	}
	return nil
}

func (m *Manager) scrapeOne(s *storage.Server) bool {
	host := strings.TrimSpace(s.Host)
	scheme := "http"
	if strings.HasPrefix(host, "https://") {
		scheme = "https"
	}
	clean := host
	for _, p := range []string{"http://", "https://"} {
		clean = strings.TrimPrefix(clean, p)
	}
	clean = strings.SplitN(clean, "/", 2)[0]
	clean = strings.SplitN(clean, "?", 2)[0]
	port := s.AgentPort
	if port == 0 {
		port = 9100
	}
	url := fmt.Sprintf("%s://%s:%d/metrics", scheme, clean, port)

	now := storage.Now()
	text := ""
	up := false

	if IsBlockedOutboundHost(clean) {
		log.Printf("[ScrapeManager] refusing blocked metadata target %s for %s", clean, s.Name)
	} else {
		req, err := http.NewRequest(http.MethodGet, url, nil)
		if err == nil {
			resp, err := m.client.Do(req)
			if err == nil {
				defer resp.Body.Close()
				if resp.StatusCode == http.StatusOK {
					body, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
					text = string(body)
					up = true
				}
			} else {
				log.Printf("scrape HTTP error for %s (%s): %v", s.Name, url, err)
			}
		}
	}

	lastStatus := s.LastStatus
	if !up {
		return m.recordDowntime(s, now, lastStatus)
	}
	data, err := parseMetrics(text, s.Name)
	if err != nil {
		log.Printf("[ScrapeManager] parse error for %s: %v", s.Name, err)
		return m.recordDowntime(s, now, lastStatus)
	}
	return m.persistMetrics(s, data, text, lastStatus, now)
}

type scrapeResult struct {
	cpu     float64
	memory  float64
	disk    float64
	netRx   float64
	netTx   float64
	volumes []map[string]any // {volume,size_bytes,free_bytes,used_percent}
}

var buildInfoRe = regexp.MustCompile(`_build_info\{[^}]*version="([^"]+)"`)

func (m *Manager) recordDowntime(s *storage.Server, now, lastStatus string) bool {
	if lastStatus == "up" && s.IsMaintenance == 0 {
		m.fireAlert("🔥 Server Down: "+s.Name,
			fmt.Sprintf("Server %s (%s) is offline or exporter is unreachable.", s.Name, s.Host))
	}
	_ = m.Store.InsertMetricPoint(s.ID, nil, nil, nil, nil, nil, "{}")
	_ = m.Store.UpdateServer(s.ID, map[string]any{"last_status": "down", "last_check": now})
	return false
}

func (m *Manager) persistMetrics(s *storage.Server, data *scrapeResult, text, lastStatus, now string) bool {
	exporterVersion := ""
	if match := buildInfoRe.FindStringSubmatch(text); len(match) > 1 {
		exporterVersion = match[1]
	}

	diskInfo, _ := json.Marshal(data.volumes)
	var volSummary []map[string]any
	for _, v := range data.volumes {
		volSummary = append(volSummary, map[string]any{
			"volume": v["volume"], "size": v["size_bytes"],
			"free": v["free_bytes"], "used_percent": v["used_percent"],
		})
	}
	volSummaryJSON, _ := json.Marshal(volSummary)

	if lastStatus == "down" && s.IsMaintenance == 0 {
		m.fireAlert("✅ Server Restored: "+s.Name,
			fmt.Sprintf("Server %s (%s) is back online.", s.Name, s.Host))
	}

	if s.IsMaintenance == 0 {
		m.evaluateCPUCondition(s.Name, data.cpu, s.CPUPercent, lastStatus)
		m.evaluateRules(s.Name, data.cpu, data.memory, data.disk)
	}

	cpu := data.cpu
	mem := data.memory
	disk := data.disk
	rx := data.netRx
	tx := data.netTx
	_ = m.Store.InsertMetricPoint(s.ID, &cpu, &mem, &disk, &rx, &tx, string(diskInfo))
	_ = m.Store.UpdateServer(s.ID, map[string]any{
		"last_status": "up", "last_check": now, "cpu_percent": cpu,
		"memory_percent": mem, "disk_percent": disk,
		"volumes": string(volSummaryJSON), "exporter_version": exporterVersion,
	})
	if m.WS != nil {
		m.WS.Broadcast(map[string]any{"type": "metrics_updated", "server_id": s.ID})
	}
	return true
}

func (m *Manager) fireAlert(title, message string) {
	if m.Alerts != nil {
		m.Alerts.Dispatch(title, message)
	}
}

func (m *Manager) evaluateCPUCondition(name string, cpu, lastCPU float64, lastStatus string) {
	// lastStatus == "unknown" means no successful scrape yet — skip the edge so
	// a transient reboot doesn't fire a false "High CPU" alert.
	if lastStatus == "unknown" {
		return
	}
	if cpu > 90 && lastCPU <= 90 {
		m.fireAlert(fmt.Sprintf("⚠️ High CPU: %s", name), fmt.Sprintf("Server %s CPU usage is high: %.1f%%.", name, cpu))
	} else if cpu <= 90 && lastCPU > 90 {
		m.fireAlert(fmt.Sprintf("✅ CPU Normal: %s", name), fmt.Sprintf("Server %s CPU usage returned to normal: %.1f%%.", name, cpu))
	}
}

func (m *Manager) evaluateRules(serverName string, cpu, memory, disk float64) {
	if m.Cfg == nil || !m.Cfg.Alerting.Enabled {
		return
	}
	now := time.Now()
	for i := range m.Cfg.Alerting.Rules {
		rule := &m.Cfg.Alerting.Rules[i]
		expr := strings.ToLower(rule.Expr)
		var val float64
		switch {
		case strings.Contains(expr, "cpu"):
			val = cpu
		case strings.Contains(expr, "memory") || strings.Contains(expr, "mem"):
			val = memory
		case strings.Contains(expr, "disk"):
			val = disk
		default:
			continue // e.g. exporter_available
		}
		cond := strings.ToLower(rule.Condition)
		fired := val > rule.Threshold
		if cond == "less_than" || cond == "lt" || cond == "lower_than" {
			fired = val < rule.Threshold
		}

		key := [2]string{serverName, rule.Name}
		m.mu.Lock()
		ep, ok := m.ruleState[key]
		if !ok {
			ep = &ruleEpisode{}
			m.ruleState[key] = ep
		}
		m.mu.Unlock()

		if !fired {
			m.mu.Lock()
			delete(m.ruleState, key)
			m.mu.Unlock()
			continue
		}
		if ep.started.IsZero() {
			ep.started = now
		}
		if ep.alerted {
			continue
		}
		duration := parseRuleDuration(rule.Duration)
		if now.Sub(ep.started) >= duration {
			msg := rule.Message
			if msg == "" {
				msg = fmt.Sprintf("%s: %.1f%% (threshold: %.1f%%)", rule.Name, val, rule.Threshold)
			}
			msg = strings.ReplaceAll(msg, "{{ value }}", fmt.Sprintf("%.1f", val))
			msg = strings.ReplaceAll(msg, "{{ server }}", serverName)
			sev := strings.ToUpper(rule.Severity)
			m.fireAlert(fmt.Sprintf("%s: %s on %s", sev, rule.Name, serverName), msg)
			ep.alerted = true
		}
	}
}

func parseRuleDuration(s string) time.Duration {
	if s == "" {
		return 0
	}
	if sec, err := config.ParseDuration(s); err == nil {
		return time.Duration(sec) * time.Second
	}
	return 0
}

func round1(f float64) float64 {
	return math.Round(f*10) / 10
}
