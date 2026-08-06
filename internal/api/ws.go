package api

import (
	"encoding/json"
	"log"
	"net"
	"net/http"
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

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin:     func(r *http.Request) bool { return true },
}

// handleWS implements the /api/v1/ws/metrics protocol:
// client must send {"type":"auth","token":<JWT>} within 15s or gets closed 1008.
func (a *App) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

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

var _ = log.Printf
