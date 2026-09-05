package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
	"gopkg.in/yaml.v3"
)

// NotifyService sends test notifications over configured channels.
type NotifyService interface {
	Test(cfg map[string]any) (success, failed []string)
}

func (a *App) handleGetNotifications(w http.ResponseWriter, r *http.Request) {
	n, err := a.Store.GetNotifications()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	cfg := map[string]any{}
	if n != nil && n.Config != "" {
		_ = json.Unmarshal([]byte(n.Config), &cfg)
	}
	writeJSON(w, http.StatusOK, cfg)
}

func (a *App) handleSaveNotifications(w http.ResponseWriter, r *http.Request) {
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	enabled := 1
	if v, ok := body["enabled"].(bool); ok && !v {
		enabled = 0
	}
	b, _ := json.Marshal(body)
	if err := a.Store.SaveNotifications(string(b), enabled); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "settings_updated", "Notification settings updated")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleTestNotifications(w http.ResponseWriter, r *http.Request) {
	if a.Notify == nil {
		writeErr(w, http.StatusBadRequest, "Notifier not available")
		return
	}
	n, err := a.Store.GetNotifications()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	cfg := map[string]any{}
	if n != nil && n.Config != "" {
		_ = json.Unmarshal([]byte(n.Config), &cfg)
	}
	success, failed := a.Notify.Test(cfg)
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "success": success, "failed": failed})
}

func (a *App) handleExportConfig(w http.ResponseWriter, r *http.Request) {
	// Build a deep copy so redaction never mutates the live config that the
	// notifier and monitor keep using (a former bug replaced the bot token in
	// memory with "***REDACTED***", silently breaking Telegram/email alerts).
	cfg := a.Cfg.Clone()

	y := map[string]any{
		"server": map[string]any{
			"host": cfg.Server.Host, "port": cfg.Server.Port, "domain": cfg.Server.Domain,
		},
		"storage": map[string]any{
			"backend": cfg.Storage.Backend, "path": cfg.Storage.Path,
			"retention_hours": cfg.Storage.RetentionHours,
		},
		"auth": map[string]any{
			"admin_username": cfg.Auth.AdminUsername, "jwt_expire_hours": cfg.Auth.JWTExpireHours,
		},
		"alerting": cfg.Alerting,
		"backup":   cfg.Backup,
	}
	// redact secrets (on the copy)
	if cfg.Notifications.Telegram != nil && cfg.Notifications.Telegram.BotToken != "" {
		cfg.Notifications.Telegram.BotToken = "***REDACTED***"
	}
	if cfg.Notifications.Email != nil && cfg.Notifications.Email.SMTPPass != "" {
		cfg.Notifications.Email.SMTPPass = "***REDACTED***"
	}
	for _, wh := range []*config.WebhookNotify{
		cfg.Notifications.Discord, cfg.Notifications.Slack, cfg.Notifications.Teams,
	} {
		if wh != nil && wh.URL != "" {
			wh.URL = "***REDACTED***"
		}
	}
	y["notifications"] = cfg.Notifications
	b, err := yaml.Marshal(y)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Serialization failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"content": string(b)})
}

type promScrapeConfigs struct {
	ScrapeConfigs []struct {
		JobName        string `yaml:"job_name"`
		ScrapeInterval string `yaml:"scrape_interval"`
		ScrapeTimeout  string `yaml:"scrape_timeout"`
		MetricsPath    string `yaml:"metrics_path"`
		HonorLabels    bool   `yaml:"honor_labels"`
		StaticConfigs  []struct {
			Targets []string          `yaml:"targets"`
			Labels  map[string]string `yaml:"labels"`
		} `yaml:"static_configs"`
	} `yaml:"scrape_configs"`
}

func (a *App) handleImportPrometheus(w http.ResponseWriter, r *http.Request) {
	var body struct {
		YAMLContent string `json:"yaml_content"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	var cfg promScrapeConfigs
	if err := yaml.Unmarshal([]byte(body.YAMLContent), &cfg); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid YAML: "+err.Error())
		return
	}
	imported := 0
	for _, sc := range cfg.ScrapeConfigs {
		for _, ssc := range sc.StaticConfigs {
			for _, target := range ssc.Targets {
				t := strings.TrimSpace(target)
				if t == "" {
					continue
				}
				if strings.HasPrefix(t, "http://") || strings.HasPrefix(t, "https://") {
					// service
					if _, err := a.upsertServiceFromTarget(t, sc.JobName); err == nil {
						imported++
					}
				} else {
					// server host:port
					if _, err := a.upsertServerFromTarget(t, sc.JobName, ssc.Labels); err == nil {
						imported++
					}
				}
			}
		}
	}
	a.audit(r, "prometheus_import", fmt.Sprintf("Imported %d targets", imported))
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "imported": imported})
}

func (a *App) upsertServerFromTarget(target, job string, labels map[string]string) (int64, error) {
	host := target
	port := 0
	if idx := strings.LastIndex(target, ":"); idx > 0 {
		host = target[:idx]
		port, _ = parsePort(target[idx+1:])
	}
	if port == 0 {
		port = 9100
	}
	if !hostNameRe(host) {
		return 0, fmt.Errorf("invalid host %q", host)
	}
	osType := "linux"
	if port == 9182 || port == 1030 || port == 1035 {
		osType = "windows"
	}
	name := job
	if name == "" {
		name = target
	}
	// upsert by host+port
	servers, _ := a.Store.ListServers()
	for _, s := range servers {
		if s.Host == host && s.AgentPort == port {
			return s.ID, nil
		}
	}
	labelJSON, _ := json.Marshal(labels)
	s := &storage.Server{
		Name: name, Host: host, AgentPort: port, OSType: osType,
		Enabled: 1, Volumes: "[]", Labels: string(labelJSON),
	}
	return a.Store.CreateServer(s)
}

func (a *App) upsertServiceFromTarget(url, job string) (int64, error) {
	name := job
	if name == "" {
		name = url
	}
	services, _ := a.Store.ListServices()
	for _, s := range services {
		if s.TargetURL == url {
			return s.ID, nil
		}
	}
	s := &storage.Service{
		Name: name, TargetURL: url, CheckType: "http",
		Interval: 60, Timeout: 10, ExpectedStatus: 200, Enabled: 1,
	}
	return a.Store.CreateService(s)
}

func parsePort(s string) (int, error) {
	var p int
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, fmt.Errorf("invalid port")
		}
		p = p*10 + int(c-'0')
	}
	if p <= 0 || p > 65535 {
		return 0, fmt.Errorf("invalid port")
	}
	return p, nil
}
