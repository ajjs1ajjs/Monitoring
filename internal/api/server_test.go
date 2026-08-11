package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

func newTestApp(t *testing.T) (*App, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "test.db")
	db, abs, err := storage.Open(path)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	store := storage.NewStore(db, abs)
	t.Cleanup(func() { _ = store.DB.Close() })

	authn, err := auth.New("", 1)
	if err != nil {
		t.Fatalf("auth: %v", err)
	}
	// create admin
	hash, _ := auth.HashPassword("AdminPass123456")
	id, _ := store.CreateUser("admin", hash, 1)
	_ = store.UpdateUser(id, map[string]any{"must_change_password": 0})

	cfg := config.Default()
	app := &App{
		Cfg:       cfg,
		Store:     store,
		Auth:      authn,
		WS:        NewWSManager(),
		Metrics:   &MetricRegistry{},
		StartTime: time.Now(),
		Version:   Version{Version: "test"},
		LogPath:   path + ".log",
	}
	return app, "AdminPass123456"
}

func loginToken(t *testing.T, h http.Handler) string {
	t.Helper()
	body := bytes.NewBufferString(`{"username":"admin","password":"AdminPass123456"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", body)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("login status = %d: %s", rec.Code, rec.Body.String())
	}
	var res struct {
		AccessToken string `json:"access_token"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &res); err != nil {
		t.Fatalf("login parse: %v", err)
	}
	return res.AccessToken
}

func doAuth(t *testing.T, h http.Handler, method, path, token string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Authorization", "Bearer "+token)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/v1/health", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d", rec.Code)
	}
}

func TestUnauthorizedBlocked(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/v1/servers", nil))
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("unauthenticated /servers = %d, want 401", rec.Code)
	}
}

func TestServerLifecycle(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	// create
	rec := doAuth(t, h, http.MethodPost, "/api/v1/servers", token, map[string]any{
		"name": "web-01", "host": "192.168.1.10", "os_type": "linux",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("create server = %d: %s", rec.Code, rec.Body.String())
	}

	// list
	rec = doAuth(t, h, http.MethodGet, "/api/v1/servers", token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list = %d", rec.Code)
	}
	var list struct {
		Servers []storage.Server `json:"servers"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &list)
	if len(list.Servers) != 1 || list.Servers[0].Name != "web-01" {
		t.Fatalf("servers = %+v", list.Servers)
	}
	id := list.Servers[0].ID

	// summary
	rec = doAuth(t, h, http.MethodGet, "/api/v1/servers/summary/all", token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("summary = %d", rec.Code)
	}

	// delete
	rec = doAuth(t, h, http.MethodDelete, "/api/v1/servers/"+itoa(id), token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("delete = %d: %s", rec.Code, rec.Body.String())
	}
}

func TestNonAdminForbiddenOnAdminRoutes(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	// admin is admin, so this should work; create a non-admin user then login
	rec := doAuth(t, h, http.MethodPost, "/api/v1/auth/users", token, map[string]any{
		"username": "viewer", "password": "ViewerPass123456", "is_admin": false,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("create user = %d: %s", rec.Code, rec.Body.String())
	}
	var created struct {
		UserID int64 `json:"user_id"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &created)
	_ = app.Store.UpdateUser(created.UserID, map[string]any{"must_change_password": 0})
	body := bytes.NewBufferString(`{"username":"viewer","password":"ViewerPass123456"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", body)
	r2 := httptest.NewRecorder()
	h.ServeHTTP(r2, req)
	var login struct {
		AccessToken string `json:"access_token"`
	}
	_ = json.Unmarshal(r2.Body.Bytes(), &login)
	if login.AccessToken == "" {
		t.Fatalf("viewer login failed: %s", r2.Body.String())
	}

	// viewer can list servers
	rec = doAuth(t, h, http.MethodGet, "/api/v1/servers", login.AccessToken, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("viewer list = %d", rec.Code)
	}
	// viewer cannot create users
	rec = doAuth(t, h, http.MethodPost, "/api/v1/auth/users", login.AccessToken, map[string]any{
		"username": "x", "password": "Xx1234567890", "is_admin": false,
	})
	if rec.Code != http.StatusForbidden {
		t.Fatalf("viewer create user = %d, want 403", rec.Code)
	}
}

func TestPrometheusExport(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/metrics", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("metrics = %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "pymon_uptime_seconds") {
		t.Fatalf("metrics body missing uptime")
	}
}

func TestStaticAssetsServed(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	for _, tc := range []struct{ path, ctype string }{
		{"/static/css/dashboard.css", "text/css"},
		{"/static/js/dashboard.js", "text/javascript"},
		{"/static/manifest.json", "application/json"},
		{"/static/favicon.svg", "image/svg+xml"},
	} {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, tc.path, nil))
		if rec.Code != http.StatusOK {
			t.Errorf("%s = %d, want 200", tc.path, rec.Code)
			continue
		}
		if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, tc.ctype) {
			t.Errorf("%s content-type = %q, want prefix %q", tc.path, ct, tc.ctype)
		}
	}
	// dashboard page
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/dashboard/", nil))
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "PyMon") {
		t.Fatalf("dashboard = %d", rec.Code)
	}
}

func itoa(i int64) string {
	return fmtSprint(i)
}

func fmtSprint(i int64) string {
	return strings.TrimSpace(jsonNumber(i))
}

func jsonNumber(i int64) string {
	b, _ := json.Marshal(i)
	return string(b)
}

// TestEmptyListsAreArrays guards against nil slices being marshaled as JSON
// null (Go marshals nil slices to null, which the frontend's .forEach/.map
// calls cannot handle).
func TestEmptyListsAreArrays(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()
	token := loginToken(t, h)

	for _, tc := range []struct{ path, key string }{
		{"/api/v1/servers", `"servers"`},
		{"/api/v1/services", `"services"`},
		{"/api/v1/alerts", `"alerts"`},
		{"/api/v1/audit-log", `"logs"`},
		{"/api/v1/auth/api-keys", `"api_keys"`},
		{"/api/v1/metrics", `"metrics"`},
	} {
		rec := doAuth(t, h, http.MethodGet, tc.path, token, nil)
		if rec.Code != http.StatusOK {
			t.Errorf("%s = %d", tc.path, rec.Code)
			continue
		}
		body := rec.Body.String()
		if strings.Contains(body, tc.key+":null") {
			t.Errorf("%s returned null for %s (want [])", tc.path, tc.key)
		}
	}

	// /api/v1/auth/users (admin only)
	rec := doAuth(t, h, http.MethodGet, "/api/v1/auth/users", token, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("users = %d", rec.Code)
	}
	if strings.Contains(rec.Body.String(), `"users":null`) {
		t.Errorf("users returned null (want [])")
	}
}

// TestCookieSessionAuth verifies the SPA flow: login sets an HttpOnly
// SameSite=Strict cookie and authenticated requests work via the cookie alone
// (no token in localStorage).
func TestCookieSessionAuth(t *testing.T) {
	app, _ := newTestApp(t)
	h := app.Handler()

	body := bytes.NewBufferString(`{"username":"admin","password":"AdminPass123456"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", body)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("login = %d: %s", rec.Code, rec.Body.String())
	}
	var authCookie *http.Cookie
	for _, c := range rec.Result().Cookies() {
		if c.Name == authCookieName {
			authCookie = c
			if !c.HttpOnly {
				t.Fatalf("auth cookie must be HttpOnly")
			}
			if c.SameSite != http.SameSiteStrictMode {
				t.Fatalf("auth cookie must be SameSite=Strict")
			}
		}
	}
	if authCookie == nil {
		t.Fatalf("no auth cookie set on login")
	}

	// /me with the cookie only (no Authorization header)
	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	req2.AddCookie(authCookie)
	rec2 := httptest.NewRecorder()
	h.ServeHTTP(rec2, req2)
	if rec2.Code != http.StatusOK {
		t.Fatalf("me via cookie = %d: %s", rec2.Code, rec2.Body.String())
	}

	// logout clears the session
	req3 := httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", nil)
	req3.AddCookie(authCookie)
	rec3 := httptest.NewRecorder()
	h.ServeHTTP(rec3, req3)
	if rec3.Code != http.StatusOK {
		t.Fatalf("logout = %d", rec3.Code)
	}

	// a cleared/invalid cookie no longer authenticates
	req4 := httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	req4.AddCookie(&http.Cookie{Name: authCookieName, Value: "cleared"})
	rec4 := httptest.NewRecorder()
	h.ServeHTTP(rec4, req4)
	if rec4.Code != http.StatusUnauthorized {
		t.Fatalf("me after logout = %d, want 401", rec4.Code)
	}
}

// TestWebSocketOriginCheck guards against CSWSH: cross-site origins must be
// rejected while same-origin and explicitly allowed origins pass.
func TestWebSocketOriginCheck(t *testing.T) {
	app, _ := newTestApp(t)

	base := "http://localhost:10000"
	mk := func(origin string) *http.Request {
		r := httptest.NewRequest("GET", base+"/api/v1/ws/metrics", nil)
		r.Host = "localhost:10000"
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		return r
	}

	if !app.checkOrigin(mk(base)) {
		t.Fatalf("same-origin must be allowed")
	}
	if app.checkOrigin(mk("http://evil.example")) {
		t.Fatalf("cross-site origin must be rejected")
	}
	if !app.checkOrigin(mk("")) {
		t.Fatalf("non-browser client without Origin must be allowed")
	}

	app.Cfg.Server.AllowedOrigins = []string{"https://dash.example"}
	if !app.checkOrigin(mk("https://dash.example")) {
		t.Fatalf("configured allowed origin must be allowed")
	}
	if app.checkOrigin(mk("https://dash.example.evil")) {
		t.Fatalf("prefix-matching origin must be rejected")
	}
}
