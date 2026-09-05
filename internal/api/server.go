package api

import (
	"embed"
	"encoding/json"
	"io/fs"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

type Version struct {
	Version string
	Commit  string
}

type Monitor interface {
	ForceScrape(serverID int64) error
}

type App struct {
	Cfg       *config.Config
	Store     *storage.Store
	Auth      *auth.Auth
	WS        *WSManager
	Monitor   Monitor
	Notify    NotifyService
	Metrics   *MetricRegistry
	StartTime time.Time
	Version   Version
	LogPath   string

	loginLimiter      *ipLimiter
	authActionLimiter *ipLimiter
}

//go:embed all:web
var webFS embed.FS

func (a *App) Handler() http.Handler {
	// Rate limiters are per-App so tests and multi-instance processes never
	// share (or exhaust) one another's budgets.
	if a.loginLimiter == nil {
		a.loginLimiter = newIPLimiter()
	}
	if a.authActionLimiter == nil {
		a.authActionLimiter = newIPLimiter()
	}
	mux := http.NewServeMux()

	// Unauthenticated
	mux.HandleFunc("GET /api/v1/health", a.handleHealth)
	mux.HandleFunc("POST /api/v1/auth/login", a.withRecovery(a.withRateLimit(a.handleLogin)))
	mux.HandleFunc("POST /api/v1/auth/logout", a.withRecovery(a.handleLogout))
	mux.HandleFunc("GET /api/v1/ws/metrics", a.handleWS)
	mux.HandleFunc("GET /metrics", a.handlePrometheusExport)

	// Authenticated API
	authed := func(h http.HandlerFunc) http.HandlerFunc { return a.withRecovery(a.withAuth(h)) }
	admin := func(h http.HandlerFunc) http.HandlerFunc { return a.withRecovery(a.withAuth(a.withAdmin(h))) }
	authedLimited := func(h http.HandlerFunc) http.HandlerFunc {
		return a.withRecovery(a.withAuth(a.withAuthActionRateLimit(h)))
	}

	mux.Handle("GET /api/v1/auth/me", authed(a.handleMe))
	mux.Handle("POST /api/v1/auth/change-password", authedLimited(a.handleChangePassword))
	mux.Handle("POST /api/v1/auth/api-keys", authedLimited(a.handleCreateAPIKey))
	mux.Handle("GET /api/v1/auth/api-keys", authed(a.handleListAPIKeys))
	mux.Handle("DELETE /api/v1/auth/api-keys/{key_id}", authed(a.handleDeleteAPIKey))

	mux.Handle("GET /api/v1/auth/users", admin(a.handleListUsers))
	mux.Handle("POST /api/v1/auth/users", admin(a.handleCreateUser))
	mux.Handle("PUT /api/v1/auth/users/{user_id}", admin(a.handleUpdateUser))
	mux.Handle("DELETE /api/v1/auth/users/{user_id}", admin(a.handleDeleteUser))

	mux.Handle("GET /api/v1/servers", authed(a.handleListServers))
	mux.Handle("POST /api/v1/servers", admin(a.handleCreateServer))
	mux.Handle("GET /api/v1/servers/history", authed(a.handleServersHistory))
	mux.Handle("GET /api/v1/servers/export", authed(a.handleServersExport))
	mux.Handle("GET /api/v1/servers/compare", authed(a.handleServersCompare))
	mux.Handle("GET /api/v1/servers/summary/all", authed(a.handleSummaryAll))
	mux.Handle("GET /api/v1/servers/{id}", authed(a.handleGetServer))
	mux.Handle("PUT /api/v1/servers/{id}", admin(a.handleUpdateServer))
	mux.Handle("DELETE /api/v1/servers/{id}", admin(a.handleDeleteServer))
	mux.Handle("GET /api/v1/servers/{id}/history", authed(a.handleServerHistory))
	mux.Handle("GET /api/v1/servers/{id}/history-detail", authed(a.handleServerHistory))
	mux.Handle("GET /api/v1/servers/{id}/disk-breakdown", authed(a.handleDiskBreakdown))
	mux.Handle("GET /api/v1/servers/{id}/uptime-timeline", authed(a.handleUptimeTimeline))
	mux.Handle("GET /api/v1/servers/{id}/export", authed(a.handleServerExport))
	mux.Handle("GET /api/v1/servers/{id}/summary", authed(a.handleServerSummary))
	mux.Handle("POST /api/v1/servers/{id}/maintenance", admin(a.handleSetMaintenance))
	mux.Handle("POST /api/v1/servers/{id}/scrape", admin(a.handleForceScrape))

	mux.Handle("POST /api/v1/metrics", authed(a.handlePushMetric))
	mux.Handle("GET /api/v1/metrics", authed(a.handleListMetrics))
	mux.Handle("GET /api/v1/metrics/trend", authed(a.handleMetricsTrend))
	mux.Handle("GET /api/v1/metrics/history/{server_id}", authed(a.handleServerHistory))
	mux.Handle("DELETE /api/v1/metrics/history", admin(a.handleClearMetricHistory))

	mux.Handle("GET /api/v1/alerts", authed(a.handleListAlerts))
	mux.Handle("POST /api/v1/alerts", admin(a.handleCreateAlert))
	mux.Handle("DELETE /api/v1/alerts/{alert_id}", admin(a.handleDeleteAlert))

	mux.Handle("GET /api/v1/services", authed(a.handleListServices))
	mux.Handle("POST /api/v1/services", admin(a.handleCreateService))
	mux.Handle("GET /api/v1/services/history", authed(a.handleServicesHistory))
	mux.Handle("DELETE /api/v1/services/{service_id}", admin(a.handleDeleteService))

	mux.Handle("GET /api/v1/settings/notifications", admin(a.handleGetNotifications))
	mux.Handle("POST /api/v1/settings/notifications", admin(a.handleSaveNotifications))
	mux.Handle("POST /api/v1/settings/notifications/test", admin(a.handleTestNotifications))
	mux.Handle("GET /api/v1/settings/config/export", admin(a.handleExportConfig))
	mux.Handle("POST /api/v1/settings/config/import-prometheus", admin(a.handleImportPrometheus))

	mux.Handle("GET /api/v1/audit-log", authed(a.handleListAudit))
	mux.Handle("DELETE /api/v1/audit-log", admin(a.handleClearAudit))
	mux.Handle("GET /api/v1/audit-log/system-logs", admin(a.handleSystemLogs))
	mux.Handle("DELETE /api/v1/audit-log/system-logs", admin(a.handleClearSystemLogs))

	mux.Handle("GET /api/v1/reports/server/{server_id}", authed(a.handleServerReport))

	mux.Handle("GET /api/v1/backup/list", admin(a.handleBackupList))
	mux.Handle("POST /api/v1/backup/create", admin(a.handleBackupCreate))
	mux.Handle("POST /api/v1/backup/restore", admin(a.handleBackupRestore))

	// Frontend
	web, _ := fs.Sub(webFS, "web")
	fileServer := http.FileServer(http.FS(web))
	// The embedded FS is rooted at internal/api/web, so the request path
	// /static/css/dashboard.css maps to static/css/dashboard.css directly.
	// Do NOT strip the /static/ prefix (that would look up css/... and 404).
	mux.Handle("/static/", fileServer)
	mux.HandleFunc("/dashboard/", func(w http.ResponseWriter, r *http.Request) {
		serveFile(w, r, web, "templates/dashboard.html")
	})
	mux.HandleFunc("/dashboard", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/dashboard/", http.StatusFound)
	})
	mux.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
		serveFile(w, r, web, "templates/login.html")
	})
	mux.HandleFunc("/favicon.ico", func(w http.ResponseWriter, r *http.Request) {
		serveFile(w, r, web, "static/favicon.svg")
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" {
			http.Redirect(w, r, "/dashboard/", http.StatusFound)
			return
		}
		http.NotFound(w, r)
	})

	return a.withSecurity(a.withLogging(mux))
}

func serveFile(w http.ResponseWriter, r *http.Request, fsys fs.FS, name string) {
	b, err := fs.ReadFile(fsys, name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	switch {
	case strings.HasSuffix(name, ".html"):
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
	case strings.HasSuffix(name, ".svg"):
		w.Header().Set("Content-Type", "image/svg+xml")
	}
	_, _ = w.Write(b)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]any{"detail": msg})
}

func pathInt(r *http.Request, name string) (int64, error) {
	return strconv.ParseInt(r.PathValue(name), 10, 64)
}
