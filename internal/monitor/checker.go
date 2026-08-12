package monitor

import (
	"context"
	"crypto/tls"
	"fmt"
	"log"
	"net"
	"net/http"
	"os/exec"
	"regexp"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

var pingTargetRe = regexp.MustCompile(`^[A-Za-z0-9._:\-\[\]]+$`)

// checkLoop runs every 5s and checks enabled services that are due.
func (m *Manager) checkLoop(ctx context.Context) {
	time.Sleep(10 * time.Second)
	lastChecked := map[int64]time.Time{}
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}
		if err := m.checkAll(lastChecked); err != nil {
			log.Printf("[ServiceChecker] error: %v", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(5 * time.Second):
		}
	}
}

func (m *Manager) checkAll(lastChecked map[int64]time.Time) error {
	services, err := m.Store.EnabledServices()
	if err != nil {
		return err
	}
	now := time.Now()
	var wg sync.WaitGroup
	sem := make(chan struct{}, 10)
	for i := range services {
		s := &services[i]
		interval := time.Duration(s.Interval) * time.Second
		if interval <= 0 {
			interval = 60 * time.Second
		}
		if last, ok := lastChecked[s.ID]; ok && now.Sub(last) < interval {
			continue
		}
		lastChecked[s.ID] = now
		wg.Add(1)
		go func(svc *storage.Service) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			m.checkOne(svc)
		}(s)
	}
	wg.Wait()
	return nil
}

func extractHostPort(url string, defaultPort int) (string, int) {
	host := strings.TrimSpace(url)
	port := defaultPort
	if strings.HasPrefix(host, "http://") || strings.HasPrefix(host, "https://") {
		h := strings.TrimPrefix(strings.TrimPrefix(host, "https://"), "http://")
		h = strings.SplitN(h, "/", 2)[0]
		h = strings.SplitN(h, "?", 2)[0]
		// Drop userinfo ("user:pass@host") — it is not part of the connect
		// target, and keeping it made the SSRF guard compare the wrong string
		// while the HTTP client still dialed the real (possibly localhost)
		// host.
		if at := strings.LastIndex(h, "@"); at >= 0 {
			h = h[at+1:]
		}
		if idx := strings.LastIndex(h, ":"); idx > 0 && !strings.Contains(h[idx+1:], "]") {
			if p, err := parsePort(h[idx+1:]); err == nil {
				port = p
			}
			h = h[:idx]
		}
		h = strings.Trim(h, "[] ")
		host = h
	} else {
		if idx := strings.LastIndex(host, ":"); idx > 0 {
			if p, err := parsePort(host[idx+1:]); err == nil {
				port = p
				host = strings.Trim(strings.TrimSpace(host[:idx]), "[] ")
			}
		}
	}
	return host, port
}

func parsePort(s string) (int, error) {
	var p int
	if s == "" {
		return 0, fmt.Errorf("empty port")
	}
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, fmt.Errorf("bad port")
		}
		p = p*10 + int(c-'0')
	}
	if p <= 0 || p > 65535 {
		return 0, fmt.Errorf("bad port")
	}
	return p, nil
}

func (m *Manager) checkOne(s *storage.Service) {
	timeout := time.Duration(s.Timeout) * time.Second
	if s.Timeout <= 0 {
		timeout = 10 * time.Second
	}
	expected := s.ExpectedStatus
	if expected == 0 {
		expected = 200
	}
	start := time.Now()
	status := "down"
	latency := 0.0

	chkHost, _ := extractHostPort(s.TargetURL, 443)
	if IsBlockedOutboundHost(chkHost) {
		status = "down"
	} else {
		switch s.CheckType {
		case "ping":
			status, latency = m.pingCheck(s.TargetURL, timeout, start)
		case "ssl":
			status, latency = m.sslCheck(s.TargetURL, timeout, start)
		default: // http, tcp (tcp falls through to HTTP like the original)
			status, latency = m.httpCheck(s.TargetURL, timeout, expected, start)
		}
	}

	// transition alerts
	last := s.Status
	transitioned := (status == "down" && (last == "up" || last == "degraded")) ||
		(status == "degraded" && last == "up" && s.CheckType == "ssl") ||
		(status == "up" && (last == "down" || last == "degraded"))
	if transitioned && m.shouldSuppressTransition(fmt.Sprintf("%d", s.ID), s.Name, status) {
		// flapping detected — the suppressor emits one combined notice and
		// suppresses the per-transition spam.
	} else if status == "down" && (last == "up" || last == "degraded") {
		m.fireAlert(fmt.Sprintf("🔥 Service Down: %s", s.Name),
			fmt.Sprintf("Service %s (%s) is down. Type: %s", s.Name, s.TargetURL, s.CheckType))
	} else if status == "degraded" && last == "up" && s.CheckType == "ssl" {
		m.fireAlert(fmt.Sprintf("⚠️ SSL Expiring: %s", s.Name),
			fmt.Sprintf("SSL certificate for %s (%s) expires in less than 14 days.", s.Name, s.TargetURL))
	} else if status == "up" && (last == "down" || last == "degraded") {
		m.fireAlert(fmt.Sprintf("✅ Service Restored: %s", s.Name),
			fmt.Sprintf("Service %s (%s) is back online.", s.Name, s.TargetURL))
	}

	now := storage.Now()
	for attempt := 0; attempt < 3; attempt++ {
		err1 := m.Store.UpdateService(s.ID, map[string]any{
			"status": status, "last_check": now, "response_time_ms": latency,
		})
		err2 := m.Store.InsertServiceHistory(s.ID, status, latency)
		if err1 == nil && err2 == nil {
			return
		}
		time.Sleep(200 * time.Millisecond)
	}
	log.Printf("[ServiceChecker] DB error for %s (%s)", s.Name, s.TargetURL)
}

func (m *Manager) httpCheck(url string, timeout time.Duration, expected int, start time.Time) (string, float64) {
	client := &http.Client{Timeout: timeout}
	resp, err := client.Get(url)
	latency := float64(time.Since(start).Milliseconds())
	if err != nil {
		return "down", latency
	}
	defer resp.Body.Close()
	if resp.StatusCode == expected {
		return "up", latency
	}
	return "degraded", latency
}

func (m *Manager) pingCheck(url string, timeout time.Duration, start time.Time) (string, float64) {
	host, _ := extractHostPort(url, 0)
	if !pingTargetRe.MatchString(host) || strings.HasPrefix(host, "-") {
		return "down", float64(time.Since(start).Milliseconds())
	}
	// Windows: -n 1 -w <ms>; Unix: -c 1 -W <sec>
	args := []string{"-n", "1", "-w", fmt.Sprintf("%d", timeout.Milliseconds())}
	sep := "--"
	if !isWindows() {
		args = []string{"-c", "1", "-W", fmt.Sprintf("%d", int(timeout.Seconds()))}
		sep = "--"
	}
	args = append(args, sep, host)
	ok, err := execPing(args)
	latency := float64(time.Since(start).Milliseconds())
	if err != nil {
		return "down", latency
	}
	if ok {
		return "up", latency
	}
	return "down", latency
}

func (m *Manager) sslCheck(url string, timeout time.Duration, start time.Time) (string, float64) {
	host, port := extractHostPort(url, 443)
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, fmt.Sprintf("%d", port)), timeout)
	latency := float64(time.Since(start).Milliseconds())
	if err != nil {
		return "down", latency
	}
	defer conn.Close()
	cfg := &tls.Config{ServerName: host}
	tlsConn := tls.Client(conn, cfg)
	if err := tlsConn.Handshake(); err != nil {
		// verification failure -> degraded (like SSLCertVerificationError)
		if _, ok := err.(*tls.CertificateVerificationError); ok {
			return "degraded", latency
		}
		return "down", latency
	}
	defer tlsConn.Close()
	state := tlsConn.ConnectionState()
	var notAfter time.Time
	for _, cert := range state.PeerCertificates {
		if cert == nil {
			continue
		}
		if time.Now().After(cert.NotBefore) && time.Now().Before(cert.NotAfter) {
			notAfter = cert.NotAfter
			break
		}
	}
	if notAfter.IsZero() {
		return "down", latency
	}
	daysLeft := int(time.Until(notAfter).Hours() / 24)
	if daysLeft < 14 {
		return "degraded", latency
	}
	return "up", latency
}

func isWindows() bool { return runtime.GOOS == "windows" }

func execPing(args []string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "ping", args...)
	err := cmd.Run()
	if err != nil {
		if ctx.Err() != nil {
			return false, err
		}
		return false, nil // non-zero exit = ping failed
	}
	return true, nil
}

// flapInfo tracks recent status transitions for one service.
type flapInfo struct {
	transitions []time.Time
	lastStatus  string
	flapping    bool
}

// shouldSuppressTransition detects flapping services (>= 5 transitions within
// 10 minutes) and suppresses per-transition alerts. A single combined notice is
// emitted the first time flapping is detected, then suppression kicks in until
// the service stabilizes.
func (m *Manager) shouldSuppressTransition(svcKey, name, status string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	info, ok := m.serviceFlap[svcKey]
	if !ok {
		info = &flapInfo{}
		m.serviceFlap[svcKey] = info
	}
	now := time.Now()
	cut := now.Add(-10 * time.Minute)
	kept := info.transitions[:0]
	for _, t := range info.transitions {
		if t.After(cut) {
			kept = append(kept, t)
		}
	}
	info.transitions = kept
	if info.lastStatus != status {
		info.transitions = append(info.transitions, now)
		info.lastStatus = status
	}
	if len(info.transitions) >= 5 {
		if !info.flapping {
			info.flapping = true
			m.fireAlert(fmt.Sprintf("🔄 Service Flapping: %s", name),
				fmt.Sprintf("Service %s is flapping (frequent state changes); alerts are being suppressed.", name))
		}
		return true
	}
	info.flapping = false
	return false
}
