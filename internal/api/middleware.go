package api

import (
	"bufio"
	"context"
	"errors"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

type principal struct {
	UserID             int64
	Username           string
	IsAdmin            bool
	MustChangePassword bool
	AuthMethod         string
}

type ctxKey int

const principalKey ctxKey = 0

// withAuth extracts either a Bearer JWT or an X-API-Key and sets the principal.
// Users with must_change_password are blocked except for change-password/me.
func (a *App) withAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		authz := r.Header.Get("Authorization")
		apiKey := r.Header.Get("X-API-Key")

		var p *principal
		if apiKey != "" {
			sha := auth.SHA256Hex(apiKey)
			key, err := a.Store.GetAPIKeyBySHA(sha)
			if err != nil || key == nil {
				writeErr(w, http.StatusUnauthorized, "Invalid API key")
				return
			}
			if !auth.VerifyPassword(key.KeyHash, apiKey) {
				writeErr(w, http.StatusUnauthorized, "Invalid API key")
				return
			}
			a.Store.TouchAPIKey(key.ID)
			p = &principal{UserID: key.UserID, IsAdmin: false, AuthMethod: "api_key"}
		} else if strings.HasPrefix(authz, "Bearer ") {
			claims, err := a.Auth.ParseToken(strings.TrimPrefix(authz, "Bearer "))
			if err != nil {
				writeErr(w, http.StatusUnauthorized, "Invalid or expired token")
				return
			}
			p = a.principalFromClaims(claims)
		} else if c, err := r.Cookie(authCookieName); err == nil && c.Value != "" {
			// HttpOnly session cookie set by the SPA login.
			claims, err := a.Auth.ParseToken(c.Value)
			if err != nil {
				writeErr(w, http.StatusUnauthorized, "Invalid or expired session")
				return
			}
			p = a.principalFromClaims(claims)
		} else {
			writeErr(w, http.StatusUnauthorized, "Not authenticated")
			return
		}

		if p == nil {
			writeErr(w, http.StatusUnauthorized, "User not found")
			return
		}
		// Users with must_change_password are blocked except for
		// change-password/me.
		if p.MustChangePassword && p.AuthMethod == "jwt" &&
			!strings.HasSuffix(r.URL.Path, "/change-password") &&
			r.URL.Path != "/api/v1/auth/me" {
			writeJSON(w, http.StatusForbidden, map[string]any{
				"detail": "You must change your password before continuing",
			})
			return
		}

		// API keys are never admins (read/ingest only).
		next(w, r.WithContext(context.WithValue(r.Context(), principalKey, p)))
	}
}

func (a *App) principalFromClaims(claims *auth.Claims) *principal {
	// Load fresh user state from the DB (must_change_password and role
	// changes take effect immediately, like the original Python version).
	u, err := a.Store.GetUserByID(claims.UserID)
	if err != nil || u == nil {
		return nil
	}
	return &principal{
		UserID: u.ID, Username: u.Username,
		IsAdmin:            u.IsAdmin == 1,
		MustChangePassword: u.MustChangePassword == 1,
		AuthMethod:         "jwt",
	}
}

// withAdmin requires the principal to be an admin. API-key principals can never
// be admins.
func (a *App) withAdmin(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		p := a.principal(r)
		if p == nil || !p.IsAdmin || p.AuthMethod == "api_key" {
			writeErr(w, http.StatusForbidden, "Admin access required")
			return
		}
		next(w, r)
	}
}

func (a *App) principal(r *http.Request) *principal {
	if v, ok := r.Context().Value(principalKey).(*principal); ok {
		return v
	}
	return nil
}

// clientIP returns the client address used for rate limiting. The
// X-Forwarded-For header is only honored when the immediate peer is a local
// proxy (loopback/private address); otherwise it is attacker-controlled and
// would trivially defeat the per-IP rate limits.
func (a *App) clientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		host = r.RemoteAddr
	}
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" && isTrustedPeer(host) {
		return strings.TrimSpace(strings.Split(xff, ",")[0])
	}
	return host
}

func isTrustedPeer(host string) bool {
	ip := net.ParseIP(strings.Trim(host, "[]"))
	if ip == nil {
		return false
	}
	return ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast()
}

// --- rate limiting (per IP, fixed window) ---

type ipLimiter struct {
	mu   sync.Mutex
	seen map[string][]time.Time
}

func newIPLimiter() *ipLimiter {
	l := &ipLimiter{seen: map[string][]time.Time{}}
	go l.cleanup()
	return l
}

// cleanup periodically drops IPs with no recent activity so the map cannot
// grow without bound under a DDoS with rotating source IPs.
func (l *ipLimiter) cleanup() {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		l.mu.Lock()
		now := time.Now()
		for ip, ts := range l.seen {
			if len(ts) == 0 || now.Sub(ts[len(ts)-1]) > time.Hour {
				delete(l.seen, ip)
			}
		}
		l.mu.Unlock()
	}
}

func (l *ipLimiter) allow(ip string, max int, window time.Duration) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := time.Now()
	cut := now.Add(-window)
	l.seen[ip] = filterTimes(l.seen[ip], cut)
	if len(l.seen[ip]) >= max {
		return false
	}
	l.seen[ip] = append(l.seen[ip], now)
	return true
}

func filterTimes(t []time.Time, cut time.Time) []time.Time {
	out := t[:0]
	for _, x := range t {
		if x.After(cut) {
			out = append(out, x)
		}
	}
	return out
}

func (a *App) withRateLimit(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !a.loginLimiter.allow(a.clientIP(r), 10, time.Minute) {
			writeErr(w, http.StatusTooManyRequests, "Too many login attempts. Try again later.")
			return
		}
		next(w, r)
	}
}

// withAuthActionRateLimit slows down password changes and API-key creation
// (credential/abuse surface) without sharing the tight login budget.
func (a *App) withAuthActionRateLimit(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !a.authActionLimiter.allow(a.clientIP(r), 30, time.Minute) {
			writeErr(w, http.StatusTooManyRequests, "Too many requests. Try again later.")
			return
		}
		next(w, r)
	}
}

// --- recovery ---

func (a *App) withRecovery(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("panic: %v", rec)
				writeErr(w, http.StatusInternalServerError, "Internal server error")
			}
		}()
		next(w, r)
	}
}

// --- security headers ---

// withSecurity sets defensive headers. The dashboard loads Chart.js, Lucide
// and the Outfit/JetBrains Mono fonts from CDNs, so those hosts must be
// allow-listed (script-src/style-src/font-src). Inline event-handler
// attributes and inline <script> blocks remain blocked.
func (a *App) withSecurity(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("Content-Security-Policy",
			"default-src 'self'; "+
				"script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "+
				"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "+
				"img-src 'self' data:; "+
				"font-src 'self' data: https://fonts.gstatic.com; "+
				"connect-src 'self' ws: wss:; "+
				"frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
		next.ServeHTTP(w, r)
	})
}

func (a *App) withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w, status: 200}
		next.ServeHTTP(sw, r)
		log.Printf("%s %s -> %d (%s)", r.Method, r.URL.Path, sw.status, time.Since(start).Round(time.Millisecond))
	})
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

// Hijack lets gorilla/websocket upgrade the connection through the logging
// wrapper (without it the WS upgrade fails because the writer isn't hijackable).
func (w *statusWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	hj, ok := w.ResponseWriter.(http.Hijacker)
	if !ok {
		return nil, nil, errors.New("response writer does not support hijacking")
	}
	return hj.Hijack()
}

func (w *statusWriter) Flush() {
	if f, ok := w.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

func (w *statusWriter) ReadFrom(r io.Reader) (int64, error) {
	if rf, ok := w.ResponseWriter.(io.ReaderFrom); ok {
		return rf.ReadFrom(r)
	}
	return io.Copy(w.ResponseWriter, r)
}

// audit helpers
func (a *App) audit(r *http.Request, action, details string) {
	var uid int64
	if p := a.principal(r); p != nil {
		uid = p.UserID
	}
	_ = a.Store.AddAudit(uid, action, details, a.clientIP(r))
}

var _ = storage.Now
