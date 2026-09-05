package api

import (
	"encoding/json"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type WSManager struct {
	mu          sync.Mutex
	connections map[*websocket.Conn]struct{}
}

func NewWSManager() *WSManager {
	return &WSManager{connections: map[*websocket.Conn]struct{}{}}
}

func (m *WSManager) add(c *websocket.Conn) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.connections[c] = struct{}{}
}

func (m *WSManager) remove(c *websocket.Conn) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.connections, c)
}

// Broadcast sends a JSON event to all live connections.
func (m *WSManager) Broadcast(event map[string]any) {
	m.mu.Lock()
	conns := make([]*websocket.Conn, 0, len(m.connections))
	for c := range m.connections {
		conns = append(conns, c)
	}
	m.mu.Unlock()
	b, _ := json.Marshal(event)
	for _, c := range conns {
		if err := c.WriteMessage(websocket.TextMessage, b); err != nil {
			m.remove(c)
			_ = c.Close()
		}
	}
}

// wsUpgrader returns an upgrader whose CheckOrigin rejects cross-site WebSocket
// connections (CSWSH). Same-origin requests and explicitly configured allowed
// origins pass; everything else is refused. Non-browser clients that send no
// Origin header are accepted (the WS still requires a valid JWT in-band).
func (a *App) wsUpgrader() websocket.Upgrader {
	return websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin:     a.checkOrigin,
	}
}

func (a *App) checkOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true // non-browser client without an Origin header
	}
	u, err := url.Parse(origin)
	if err != nil {
		return false
	}
	// Same-origin: the Origin host matches the request Host.
	if u.Host == r.Host {
		return true
	}
	// Configured cross-origin allowlist (PYMON_ALLOWED_ORIGINS).
	for _, o := range a.Cfg.Server.AllowedOrigins {
		if strings.TrimRight(o, "/") == strings.TrimRight(origin, "/") {
			return true
		}
	}
	return false
}

// handleWS implements the /api/v1/ws/metrics protocol:
// client must send {"type":"auth","token":<JWT>} within 15s or gets closed 1008.
// The SPA is authenticated via its HttpOnly session cookie (no token in JS),
// so a valid cookie on the upgrade request skips the in-band token.
func (a *App) handleWS(w http.ResponseWriter, r *http.Request) {
	upgrader := a.wsUpgrader()
	// Cookie session (browser SPA).
	sessionOK := false
	if c, err := r.Cookie(authCookieName); err == nil && c.Value != "" {
		if _, err := a.Auth.ParseToken(c.Value); err == nil {
			sessionOK = true
		}
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	if !sessionOK {
		// 15s auth window
		_ = conn.SetReadDeadline(time.Now().Add(15 * time.Second))
		_, msg, err := conn.ReadMessage()
		if err != nil {
			_ = conn.WriteControl(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "auth timeout"), time.Now().Add(time.Second))
			return
		}
		var hello struct {
			Type  string `json:"type"`
			Token string `json:"token"`
		}
		if json.Unmarshal(msg, &hello) != nil || hello.Type != "auth" || hello.Token == "" {
			_ = conn.WriteControl(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "invalid auth"), time.Now().Add(time.Second))
			return
		}
		if _, err := a.Auth.ParseToken(hello.Token); err != nil {
			_ = conn.WriteControl(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "invalid token"), time.Now().Add(time.Second))
			return
		}
	}

	a.WS.add(conn)
	defer a.WS.remove(conn)

	// keepalive: on 60s of no inbound traffic, send an empty message to test
	// liveness (mirrors the original protocol).
	for {
		_ = conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		_, _, err := conn.ReadMessage()
		if err == nil {
			continue
		}
		if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
			if werr := conn.WriteMessage(websocket.TextMessage, []byte("")); werr != nil {
				return
			}
			continue
		}
		return
	}
}
