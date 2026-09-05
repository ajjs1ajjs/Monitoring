package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/ajjs1ajjs/Monitoring/internal/config"
)

// TestConfigExportDoesNotMutateLiveConfigAndRedactsSecrets guards the fix for
// the export endpoint that used to overwrite the in-memory bot token / SMTP
// password with "***REDACTED***", silently breaking notifications.
func TestConfigExportDoesNotMutateLiveConfigAndRedactsSecrets(t *testing.T) {
	app, _ := newTestApp(t)
	app.Cfg.Notifications.Telegram = &config.TelegramNotify{Enabled: true, BotToken: "supersecret-bot-token", ChatID: "123"}
	app.Cfg.Notifications.Email = &config.EmailNotify{SMTPPass: "supersecret-smtp-pass"}
	app.Cfg.Notifications.Slack = &config.WebhookNotify{URL: "https://hooks.slack.com/services/T0000/B0000/supersecret-webhook"}
	h := app.Handler()
	token := loginToken(t, h)

	rec := doAuth(t, h, http.MethodGet, "/api/v1/settings/config/export", token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("export = %d: %s", rec.Code, rec.Body.String())
	}
	body := rec.Body.String()
	if strings.Contains(body, "supersecret-bot-token") ||
		strings.Contains(body, "supersecret-smtp-pass") ||
		strings.Contains(body, "supersecret-webhook") {
		t.Fatalf("export leaked a secret: %s", body)
	}
	if !strings.Contains(body, "***REDACTED***") {
		t.Fatalf("export did not redact secrets: %s", body)
	}

	// The live config must be untouched.
	if app.Cfg.Notifications.Telegram.BotToken != "supersecret-bot-token" {
		t.Fatalf("live bot token was mutated: %q", app.Cfg.Notifications.Telegram.BotToken)
	}
	if app.Cfg.Notifications.Email.SMTPPass != "supersecret-smtp-pass" {
		t.Fatalf("live smtp password was mutated: %q", app.Cfg.Notifications.Email.SMTPPass)
	}
	if app.Cfg.Notifications.Slack.URL != "https://hooks.slack.com/services/T0000/B0000/supersecret-webhook" {
		t.Fatalf("live slack webhook was mutated: %q", app.Cfg.Notifications.Slack.URL)
	}
}

// TestPushMetricRejectsInjection verifies a metric name carrying a newline
// cannot be pushed into the public Prometheus exposition.
func TestPushMetricRejectsInjection(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	for _, payload := range []string{
		`{"name":"evil\n# HELP injected 1","value":1}`,
		`{"name":"bad name","value":1}`,
		`{"name":"1bad","value":1}`,
		`{"name":"ok_name","value":1,"help_text":"line1\nline2"}`,
		`{"name":"ok_name","value":1,"labels":[{"name":"a\nb","value":"v"}]}`,
	} {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/metrics", bytes.NewBufferString(payload))
		req.Header.Set("Authorization", "Bearer "+token)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("payload %q = %d, want 400 (%s)", payload, rec.Code, rec.Body.String())
		}
	}

	// A valid push still works.
	req := httptest.NewRequest(http.MethodPost, "/api/v1/metrics", bytes.NewBufferString(`{"name":"valid_metric","value":7,"labels":[{"name":"host","value":"web-1"}]}`))
	req.Header.Set("Authorization", "Bearer "+token)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("valid push = %d: %s", rec.Code, rec.Body.String())
	}
}

// TestMetricRegistryCardinalityCap ensures the in-memory registry cannot grow
// without bound via unique label combinations (authenticated DoS).
func TestMetricRegistryCardinalityCap(t *testing.T) {
	r := &MetricRegistry{}
	for i := 0; i < maxRegistryEntries+100; i++ {
		r.Add(registryEntry{Name: "m", Labels: map[string]string{"i": itoa(int64(i))}})
	}
	if got := len(r.Snapshot()); got != maxRegistryEntries {
		t.Fatalf("registry size = %d, want %d", got, maxRegistryEntries)
	}
	// Updating an existing series must still work at the cap.
	r.Add(registryEntry{Name: "m", Labels: map[string]string{"i": "0"}, Value: 99})
	snap := r.Snapshot()
	for _, e := range snap {
		if e.Labels["i"] == "0" && e.Value != 99 {
			t.Fatalf("existing series was not updated at the cap")
		}
	}
}

// TestUpdateServerRejectsBadTypes ensures PUT /servers/{id} with a wrong JSON
// type returns 400 instead of panicking (the old code used bare type
// assertions, so `"enabled": 1` crashed the request).
func TestUpdateServerRejectsBadTypes(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	rec := doAuth(t, h, http.MethodPost, "/api/v1/servers", token, map[string]any{
		"name": "web-01", "host": "192.168.1.10", "os_type": "linux",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("create = %d: %s", rec.Code, rec.Body.String())
	}
	id := serverIDFromCreate(t, h, token)

	for _, body := range []map[string]any{
		{"enabled": 1},               // number instead of bool
		{"agent_port": "abc"},        // string instead of number
		{"agent_port": 70000},        // out-of-range port
		{"agent_port": -5},           // negative port
		{"scrape_interval": "fast"},  // string instead of number
		{"os_type": 42},              // number instead of string
		{"name": 123},                // number instead of string
	} {
		rec := doAuth(t, h, http.MethodPut, "/api/v1/servers/"+itoa(id), token, body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("PUT with %v = %d, want 400 (%s)", body, rec.Code, rec.Body.String())
		}
	}
}

func serverIDFromCreate(t *testing.T, h http.Handler, token string) int64 {
	t.Helper()
	rec := doAuth(t, h, http.MethodGet, "/api/v1/servers", token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list = %d", rec.Code)
	}
	var list struct {
		Servers []struct {
			ID int64 `json:"id"`
		} `json:"servers"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &list); err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(list.Servers) != 1 {
		t.Fatalf("servers = %d", len(list.Servers))
	}
	return list.Servers[0].ID
}

// TestClientIPDoesNotTrustSpoofedXFF ensures the per-IP rate limit cannot be
// bypassed by sending a random X-Forwarded-For header from a public address.
func TestClientIPDoesNotTrustSpoofedXFF(t *testing.T) {
	app, _ := newTestApp(t)

	// Public peer (default RemoteAddr in httptest): XFF must be ignored.
	r := httptest.NewRequest(http.MethodGet, "/", nil)
	r.Header.Set("X-Forwarded-For", "203.0.113.9")
	if got := app.clientIP(r); got != "192.0.2.1" {
		t.Fatalf("public peer clientIP = %q, want 192.0.2.1", got)
	}

	// Local proxy peer: XFF is trusted so the real client IP is used.
	r2 := httptest.NewRequest(http.MethodGet, "/", nil)
	r2.RemoteAddr = "127.0.0.1:5678"
	r2.Header.Set("X-Forwarded-For", "203.0.113.10")
	if got := app.clientIP(r2); got != "203.0.113.10" {
		t.Fatalf("local proxy clientIP = %q, want 203.0.113.10", got)
	}
}

// TestCSPAllowsDashboardCDNs guards against regressions where the CSP blocks
// the Chart.js/Lucide/fonts CDN hosts the dashboard depends on.
func TestCSPAllowsDashboardCDNs(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/login", nil))
	csp := rec.Header().Get("Content-Security-Policy")
	if csp == "" {
		t.Fatalf("no CSP header")
	}
	for _, need := range []string{"https://cdn.jsdelivr.net", "https://unpkg.com", "https://fonts.googleapis.com", "https://fonts.gstatic.com"} {
		if !strings.Contains(csp, need) {
			t.Errorf("CSP missing %s: %s", need, csp)
		}
	}
	// Inline handlers must remain blocked (no 'unsafe-inline' in script-src).
	if strings.Contains(csp, "script-src 'self' 'unsafe-inline'") || strings.Contains(csp, "'unsafe-inline' 'self'") {
		t.Errorf("CSP must not allow unsafe-inline scripts: %s", csp)
	}
}

// TestReportPageUsesNonceCSP verifies the report page ships its own nonce-based
// CSP (the global CSP would otherwise block the inline chart script).
func TestReportPageUsesNonceCSP(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	rec := doAuth(t, h, http.MethodPost, "/api/v1/servers", token, map[string]any{
		"name": "report-host", "host": "192.168.1.50", "os_type": "linux",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("create = %d", rec.Code)
	}
	id := serverIDFromCreate(t, h, token)

	rec = doAuth(t, h, http.MethodGet, "/api/v1/reports/server/"+itoa(id), token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("report = %d: %s", rec.Code, rec.Body.String())
	}
	csp := rec.Header().Get("Content-Security-Policy")
	if !strings.Contains(csp, "'nonce-") {
		t.Fatalf("report CSP missing nonce: %s", csp)
	}
	if !strings.Contains(rec.Body.String(), `nonce="`) {
		t.Fatalf("report HTML missing nonce attribute")
	}
}
