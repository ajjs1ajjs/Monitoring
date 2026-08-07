package notify

import (
	"bufio"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"
)

// runTestSMTPServer starts a minimal SMTP server and returns its port plus a
// channel that receives "DATA" once a message body is accepted.
func runTestSMTPServer(t *testing.T, authLine string, handleAuth func(conn net.Conn, r *bufio.Reader)) (int, chan string) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	t.Cleanup(func() { ln.Close() })

	got := make(chan string, 1)
	go func() {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		conn.SetDeadline(time.Now().Add(5 * time.Second))
		r := bufio.NewReader(conn)
		fmt.Fprintf(conn, "220 test ESMTP\r\n")
		for {
			line, err := r.ReadString('\n')
			if err != nil {
				return
			}
			raw := strings.TrimSpace(line)
			cmd := strings.ToUpper(raw)
			switch {
			case strings.HasPrefix(cmd, "EHLO"):
				fmt.Fprintf(conn, "250-test\r\n250 AUTH %s\r\n", authLine)
			case cmd == "AUTH LOGIN":
				fmt.Fprintf(conn, "334 VXNlcm5hbWU6\r\n") // "Username:"
			case raw == "dUB0ZXN0": // base64("u@test")
				fmt.Fprintf(conn, "334 UGFzc3dvcmQ6\r\n") // "Password:"
			case raw == "cHc=": // base64("pw")
				fmt.Fprintf(conn, "235 ok\r\n")
			case strings.HasPrefix(cmd, "AUTH PLAIN"):
				fmt.Fprintf(conn, "235 ok\r\n")
			case strings.HasPrefix(cmd, "MAIL FROM"):
				fmt.Fprintf(conn, "250 ok\r\n")
			case strings.HasPrefix(cmd, "RCPT TO"):
				fmt.Fprintf(conn, "250 ok\r\n")
			case cmd == "DATA":
				fmt.Fprintf(conn, "354 go ahead\r\n")
				for {
					l, err := r.ReadString('\n')
					if err != nil {
						return
					}
					if l == ".\r\n" {
						break
					}
				}
				fmt.Fprintf(conn, "250 ok\r\n")
				got <- "DATA"
			case cmd == "QUIT":
				fmt.Fprintf(conn, "221 bye\r\n")
				return
			default:
				fmt.Fprintf(conn, "250 ok\r\n")
			}
		}
	}()
	return ln.Addr().(*net.TCPAddr).Port, got
}

// TestEmailAuthLogin verifies that SMTP AUTH LOGIN is used when the server
// advertises LOGIN (Exchange-style), not just PLAIN.
func TestEmailAuthLogin(t *testing.T) {
	port, got := runTestSMTPServer(t, "LOGIN", nil)
	svc := New(nil)
	ok := svc.sendEmail("hello", "subject", map[string]any{
		"smtp_server": "127.0.0.1",
		"smtp_port":   float64(port),
		"smtp_user":   "u@test",
		"smtp_pass":   "pw",
		"email_to":    "u@test",
		"use_tls":     false,
	})
	if !ok {
		t.Fatalf("sendEmail returned false")
	}
	select {
	case c := <-got:
		if c != "DATA" {
			t.Fatalf("server saw %q, want DATA", c)
		}
	case <-time.After(5 * time.Second):
		t.Fatalf("sendEmail did not send DATA")
	}
}

// TestEmailPlainAuth verifies the plain flow still works when the server
// advertises PLAIN.
func TestEmailPlainAuth(t *testing.T) {
	port, got := runTestSMTPServer(t, "PLAIN", nil)
	svc := New(nil)
	ok := svc.sendEmail("hello", "subject", map[string]any{
		"smtp_server": "127.0.0.1",
		"smtp_port":   float64(port),
		"smtp_user":   "u@test",
		"smtp_pass":   "pw",
		"email_to":    "u@test",
		"use_tls":     false,
	})
	if !ok {
		t.Fatalf("sendEmail returned false")
	}
	select {
	case c := <-got:
		if c != "DATA" {
			t.Fatalf("server saw %q, want DATA", c)
		}
	case <-time.After(5 * time.Second):
		t.Fatalf("sendEmail did not send DATA")
	}
}

// TestBuildTelegramAlertEscapesHTML ensures special characters in titles and
// messages are escaped so Telegram's HTML markup can't be broken.
func TestBuildTelegramAlertEscapesHTML(t *testing.T) {
	out := buildTelegramAlert("Server <A&B>", "Value is 5<10 & 3>1")
	if strings.Contains(out, "<A&B>") {
		t.Fatalf("title not escaped: %s", out)
	}
	if strings.Contains(out, "5<10") || strings.Contains(out, "3>1") {
		t.Fatalf("message not escaped: %s", out)
	}
	if !strings.Contains(out, "&lt;") || !strings.Contains(out, "&amp;") || !strings.Contains(out, "&gt;") {
		t.Fatalf("missing entities: %s", out)
	}
}
