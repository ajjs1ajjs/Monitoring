package notify

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/smtp"
	"strings"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

// Service reads notification settings from the DB and dispatches alerts.
type Service struct {
	Store *storage.Store
	HTTP  *http.Client
}

func New(store *storage.Store) *Service {
	return &Service{
		Store: store,
		HTTP:  &http.Client{Timeout: 15 * time.Second},
	}
}

// LoadCfg fetches the flat notification config stored in the DB.
func (s *Service) LoadCfg() map[string]any {
	n, err := s.Store.GetNotifications()
	if err != nil || n == nil || n.Config == "" {
		return map[string]any{}
	}
	cfg := map[string]any{}
	_ = json.Unmarshal([]byte(n.Config), &cfg)
	return cfg
}

// BuildChannels returns an enabled-channel map from a flat config dict.
func BuildChannels(data map[string]any) map[string]map[string]any {
	ch := map[string]map[string]any{}
	if getStr(data, "telegram_bot_token") != "" && getStr(data, "telegram_chat_id") != "" {
		ch["telegram"] = map[string]any{
			"bot_token": getStr(data, "telegram_bot_token"),
			"chat_id":   getStr(data, "telegram_chat_id"),
		}
	}
	if getStr(data, "discord_webhook_url") != "" {
		ch["discord"] = map[string]any{"webhook_url": getStr(data, "discord_webhook_url")}
	}
	if getStr(data, "slack_webhook_url") != "" {
		ch["slack"] = map[string]any{"webhook_url": getStr(data, "slack_webhook_url")}
	}
	if getStr(data, "teams_webhook_url") != "" {
		ch["teams"] = map[string]any{"webhook_url": getStr(data, "teams_webhook_url")}
	}
	if getStr(data, "smtp_server") != "" && getStr(data, "email_to") != "" {
		ch["email"] = map[string]any{
			"smtp_server": getStr(data, "smtp_server"),
			"smtp_port":   getNum(data, "smtp_port", 587),
			"smtp_user":   getStr(data, "smtp_user"),
			"smtp_pass":   getStr(data, "smtp_pass"),
			"email_to":    getStr(data, "email_to"),
			"use_tls":     getBool(data, "use_tls"),
		}
	}
	return ch
}

// Dispatch sends an alert using the stored settings.
func (s *Service) Dispatch(title, message string) {
	cfg := s.LoadCfg()
	if v, ok := cfg["enabled"].(bool); ok && !v {
		return
	}
	channels := BuildChannels(cfg)
	if len(channels) == 0 {
		return
	}
	s.dispatch(title, message, channels)
}

func (s *Service) dispatch(title, message string, channels map[string]map[string]any) {
	if c, ok := channels["telegram"]; ok {
		_ = s.sendTelegram(buildTelegramAlert(title, message), getStr(c, "bot_token"), getStr(c, "chat_id"))
	}
	if c, ok := channels["discord"]; ok {
		_ = s.sendDiscord(message, getStr(c, "webhook_url"))
	}
	if c, ok := channels["slack"]; ok {
		_ = s.sendSlack(title, message, getStr(c, "webhook_url"))
	}
	if c, ok := channels["teams"]; ok {
		_ = s.sendTeams(message, getStr(c, "webhook_url"))
	}
	if c, ok := channels["email"]; ok {
		_ = s.sendEmail(htmlEscape(title)+"\n\n"+htmlEscape(message), fmt.Sprintf("PyMon Alert: %s", title), c)
	}
}

func htmlEscape(v string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;")
	return r.Replace(v)
}

// Test sends a test message over all configured channels; returns success/failed.
func (s *Service) Test(cfg map[string]any) (success, failed []string) {
	channels := BuildChannels(cfg)
	msg := "✅ Test notification from PyMon"
	res := map[string]bool{}
	if c, ok := channels["telegram"]; ok {
		res["telegram"] = s.sendTelegram(buildTelegramAlert("🧪 Test Alert", msg), getStr(c, "bot_token"), getStr(c, "chat_id"))
	}
	if c, ok := channels["discord"]; ok {
		res["discord"] = s.sendDiscord(msg, getStr(c, "webhook_url"))
	}
	if c, ok := channels["slack"]; ok {
		res["slack"] = s.sendSlack("Test Alert", msg, getStr(c, "webhook_url"))
	}
	if c, ok := channels["teams"]; ok {
		res["teams"] = s.sendTeams(msg, getStr(c, "webhook_url"))
	}
	if c, ok := channels["email"]; ok {
		res["email"] = s.sendEmail(msg, "PyMon Test Alert", c)
	}
	for name, ok := range res {
		if ok {
			success = append(success, name)
		} else {
			failed = append(failed, name)
		}
	}
	return success, failed
}

func (s *Service) postJSON(url string, payload any) bool {
	b, err := json.Marshal(payload)
	if err != nil {
		return false
	}
	resp, err := s.HTTP.Post(url, "application/json", bytes.NewReader(b))
	if err != nil {
		log.Printf("notify: %v", err)
		return false
	}
	defer resp.Body.Close()
	_, _ = io.Copy(io.Discard, resp.Body)
	return resp.StatusCode >= 200 && resp.StatusCode < 300
}

func (s *Service) sendTelegram(message, botToken, chatID string) bool {
	if botToken == "" || chatID == "" {
		return false
	}
	return s.postJSON(fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", botToken), map[string]any{
		"chat_id": chatID, "text": message, "parse_mode": "HTML",
	})
}

// buildTelegramAlert renders a readable HTML alert and escapes user-supplied
// text so special characters can't break Telegram's HTML markup.
func buildTelegramAlert(title, message string) string {
	esc := func(v string) string {
		r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;")
		return r.Replace(v)
	}
	return "<b>🚨 " + esc(title) + "</b>\n\n" + esc(message)
}

func (s *Service) sendDiscord(message, webhookURL string) bool {
	if webhookURL == "" {
		return false
	}
	return s.postJSON(webhookURL, map[string]any{
		"content": nil,
		"embeds":  []map[string]any{{"title": "PyMon Alert", "description": message, "color": 15158332}},
	})
}

func (s *Service) sendSlack(title, message, webhookURL string) bool {
	if webhookURL == "" {
		return false
	}
	return s.postJSON(webhookURL, map[string]any{
		"text":       fmt.Sprintf("*%s*\n%s", title, message),
		"username":   "PyMon",
		"icon_emoji": ":rotating_light:",
	})
}

func (s *Service) sendTeams(message, webhookURL string) bool {
	if webhookURL == "" {
		return false
	}
	return s.postJSON(webhookURL, map[string]any{
		"type": "message",
		"attachments": []map[string]any{
			{
				"contentType": "application/vnd.microsoft.card.adaptive",
				"content": map[string]any{
					"type": "AdaptiveCard",
					"body": []map[string]any{
						{"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": "PyMon Alert"},
						{"type": "TextBlock", "text": message, "wrap": true},
					},
					"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
					"version": "1.0",
				},
			},
		},
	})
}

func (s *Service) sendEmail(message, subject string, cfg map[string]any) bool {
	server := getStr(cfg, "smtp_server")
	to := getStr(cfg, "email_to")
	if server == "" || to == "" {
		return false
	}
	port := int(getNum(cfg, "smtp_port", 587))
	user := getStr(cfg, "smtp_user")
	pass := getStr(cfg, "smtp_pass")
	useTLS := getBool(cfg, "use_tls")

	addr := net.JoinHostPort(server, fmt.Sprintf("%d", port))
	var conn net.Conn
	var err error
	if useTLS {
		conn, err = tls.DialWithDialer(&net.Dialer{Timeout: 15 * time.Second}, "tcp", addr,
			&tls.Config{ServerName: server})
	} else {
		conn, err = net.DialTimeout("tcp", addr, 15*time.Second)
	}
	if err != nil {
		log.Printf("notify email dial: %v", err)
		return false
	}
	defer conn.Close()
	// bound the whole SMTP conversation, not just the dial
	_ = conn.SetDeadline(time.Now().Add(30 * time.Second))

	client, err := smtp.NewClient(conn, server)
	if err != nil {
		return false
	}
	defer client.Close()

	if !useTLS {
		if ok, _ := client.Extension("STARTTLS"); ok {
			if err := client.StartTLS(&tls.Config{ServerName: server}); err != nil {
				log.Printf("notify email starttls: %v", err)
				return false
			}
		}
	}
	if pass != "" {
		if err := authSMTP(client, server, user, pass); err != nil {
			log.Printf("notify email auth: %v", err)
			return false
		}
	}
	if err := client.Mail(user); err != nil {
		return false
	}
	if err := client.Rcpt(to); err != nil {
		return false
	}
	w, err := client.Data()
	if err != nil {
		return false
	}
	body := buildMIME(user, to, subject, message)
	_, _ = w.Write([]byte(body))
	_ = w.Close()
	return client.Quit() == nil
}

func buildMIME(from, to, subject, body string) string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("From: %s\r\n", from))
	b.WriteString(fmt.Sprintf("To: %s\r\n", to))
	b.WriteString(fmt.Sprintf("Subject: %s\r\n", subject))
	b.WriteString("MIME-Version: 1.0\r\n")
	b.WriteString("Content-Type: text/html; charset=UTF-8\r\n")
	b.WriteString("\r\n")
	b.WriteString(body)
	return b.String()
}

// authSMTP picks an AUTH mechanism the server actually advertises. Exchange
// often only supports LOGIN/NTLM, so PLAIN (the only one Go's smtp.PlainAuth
// can do) would time out. Prefer PLAIN when available, otherwise fall back to
// LOGIN.
func authSMTP(c *smtp.Client, server, user, pass string) error {
	if ok, mechs := c.Extension("AUTH"); ok {
		if strings.Contains(strings.ToUpper(mechs), "LOGIN") {
			return c.Auth(&loginAuth{user: user, password: pass})
		}
	}
	return c.Auth(smtp.PlainAuth("", user, pass, server))
}

// loginAuth implements SMTP AUTH LOGIN (base64 user/password exchange).
type loginAuth struct {
	user, password string
}

func (a *loginAuth) Start(_ *smtp.ServerInfo) (string, []byte, error) {
	return "LOGIN", nil, nil
}

func (a *loginAuth) Next(fromServer []byte, more bool) ([]byte, error) {
	if !more {
		return nil, nil
	}
	switch strings.ToLower(strings.TrimSpace(string(fromServer))) {
	case "username:":
		return []byte(a.user), nil
	case "password:":
		return []byte(a.password), nil
	default:
		return nil, fmt.Errorf("unexpected server challenge: %q", string(fromServer))
	}
}

// --- config dict helpers ---

func getStr(m map[string]any, key string) string {
	if m == nil {
		return ""
	}
	switch v := m[key].(type) {
	case string:
		return v
	case float64:
		return fmt.Sprintf("%.0f", v)
	default:
		return ""
	}
}

func getNum(m map[string]any, key string, def float64) float64 {
	if m == nil {
		return def
	}
	switch v := m[key].(type) {
	case float64:
		return v
	case int:
		return float64(v)
	case string:
		f := 0.0
		if _, err := fmt.Sscanf(v, "%f", &f); err == nil {
			return f
		}
	}
	return def
}

func getBool(m map[string]any, key string) bool {
	if m == nil {
		return false
	}
	v, ok := m[key].(bool)
	return ok && v
}
