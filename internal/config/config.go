package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

type Server struct {
	Host   string `yaml:"host"`
	Port   int    `yaml:"port"`
	Domain string `yaml:"domain"`
	// AllowedOrigins restricts cross-origin access to the API and WebSocket
	// (CSWSH protection). Empty = same-origin only. Populated from the
	// PYMON_ALLOWED_ORIGINS env var (comma-separated) or the YAML list.
	AllowedOrigins []string `yaml:"allowed_origins"`
}

type Storage struct {
	Backend        string `yaml:"backend"`
	Path           string `yaml:"path"`
	RetentionHours int    `yaml:"retention_hours"`
}

type Auth struct {
	AdminUsername  string `yaml:"admin_username"`
	AdminPassword  string `yaml:"admin_password"`
	JWTExpireHours int    `yaml:"jwt_expire_hours"`
}

type StaticTarget struct {
	Targets []string          `yaml:"targets"`
	Labels  map[string]string `yaml:"labels"`
}

type ScrapeConfig struct {
	JobName        string         `yaml:"job_name"`
	ScrapeInterval string         `yaml:"scrape_interval"`
	ScrapeTimeout  string         `yaml:"scrape_timeout"`
	MetricsPath    string         `yaml:"metrics_path"`
	StaticConfigs  []StaticTarget `yaml:"static_configs"`
}

type AlertRule struct {
	Name      string  `yaml:"name"`
	Expr      string  `yaml:"expr"`
	Threshold float64 `yaml:"threshold"`
	Duration  string  `yaml:"duration"`
	Severity  string  `yaml:"severity"`
	Message   string  `yaml:"message"`
	Condition string  `yaml:"condition"`
}

type Alerting struct {
	Enabled            bool        `yaml:"enabled"`
	EvaluationInterval string      `yaml:"evaluation_interval"`
	Rules              []AlertRule `yaml:"rules"`
}

type Notifications struct {
	Enabled  bool            `yaml:"enabled"`
	Email    *EmailNotify    `yaml:"email"`
	Telegram *TelegramNotify `yaml:"telegram"`
	Discord  *WebhookNotify  `yaml:"discord"`
	Slack    *WebhookNotify  `yaml:"slack"`
	Teams    *WebhookNotify  `yaml:"teams"`
}

type EmailNotify struct {
	Enabled  bool   `yaml:"enabled"`
	SMTPHost string `yaml:"smtp_server"`
	SMTPPort int    `yaml:"smtp_port"`
	SMTPUser string `yaml:"smtp_user"`
	SMTPPass string `yaml:"smtp_pass"`
	To       string `yaml:"to"`
	From     string `yaml:"from"`
	UseTLS   bool   `yaml:"use_tls"`
}

type TelegramNotify struct {
	Enabled   bool   `yaml:"enabled"`
	BotToken  string `yaml:"bot_token"`
	ChatID    string `yaml:"chat_id"`
	ParseMode string `yaml:"parse_mode"`
}

type WebhookNotify struct {
	Enabled  bool   `yaml:"enabled"`
	URL      string `yaml:"webhook_url"`
	Username string `yaml:"username"`
	Channel  string `yaml:"channel"`
}

type Backup struct {
	Enabled    bool   `yaml:"enabled"`
	Schedule   string `yaml:"schedule"`
	MaxBackups int    `yaml:"max_backups"`
	BackupDir  string `yaml:"path"`
}

type Config struct {
	Server        Server         `yaml:"server"`
	Storage       Storage        `yaml:"storage"`
	Auth          Auth           `yaml:"auth"`
	ScrapeConfigs []ScrapeConfig `yaml:"scrape_configs"`
	Alerting      Alerting       `yaml:"alerting"`
	Notifications Notifications  `yaml:"notifications"`
	Backup        Backup         `yaml:"backup"`
}

func Default() *Config {
	return &Config{
		Server:   Server{Host: "0.0.0.0", Port: 10000, Domain: "localhost"},
		Storage:  Storage{Backend: "sqlite", Path: "pymon.db", RetentionHours: 168},
		Auth:     Auth{AdminUsername: "admin", JWTExpireHours: 24},
		Alerting: Alerting{Enabled: true, EvaluationInterval: "30s"},
		Backup:   Backup{Enabled: true, Schedule: "0 2 * * *", MaxBackups: 10, BackupDir: "backups"},
	}
}

// Load reads a YAML/JSON config from path. If path is empty, tries CONFIG_PATH
// env then ./config.yml. Returns default config when nothing found.
func Load(path string) (*Config, error) {
	cfg := Default()
	if path == "" {
		path = os.Getenv("CONFIG_PATH")
	}
	if path == "" {
		for _, candidate := range []string{"config.yml", "config.yaml", "config.json"} {
			if _, err := os.Stat(candidate); err == nil {
				path = candidate
				break
			}
		}
	}
	if path == "" {
		return cfg, nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config %s: %w", path, err)
	}
	// Environment override for the cross-origin allowlist.
	if env := strings.TrimSpace(os.Getenv("PYMON_ALLOWED_ORIGINS")); env != "" {
		cfg.Server.AllowedOrigins = nil
		for _, o := range strings.Split(env, ",") {
			if o = strings.TrimSpace(o); o != "" {
				cfg.Server.AllowedOrigins = append(cfg.Server.AllowedOrigins, o)
			}
		}
	}
	return cfg, nil
}

func (c *Config) ScrapeIntervalSeconds() int {
	for _, sc := range c.ScrapeConfigs {
		if sec := parseDurationSeconds(sc.ScrapeInterval); sec > 0 {
			return sec
		}
	}
	return 15
}

func (c *Config) AdminEnabled() bool { return true }

func parseDurationSeconds(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	mult := 1.0
	switch {
	case strings.HasSuffix(s, "ms"):
		mult = 0.001
		s = strings.TrimSuffix(s, "ms")
	case strings.HasSuffix(s, "s"):
		mult = 1
		s = strings.TrimSuffix(s, "s")
	case strings.HasSuffix(s, "m"):
		mult = 60
		s = strings.TrimSuffix(s, "m")
	case strings.HasSuffix(s, "h"):
		mult = 3600
		s = strings.TrimSuffix(s, "h")
	}
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	// ParseFloat rejects any trailing garbage (e.g. "5xyzs"), so malformed
	// values are never silently accepted.
	n, err := strconv.ParseFloat(s, 64)
	if err != nil || n <= 0 {
		return 0
	}
	sec := int(n * mult)
	if sec < 1 {
		return 0
	}
	return sec
}

func ParseDuration(s string) (int, error) {
	if sec := parseDurationSeconds(s); sec > 0 {
		return sec, nil
	}
	return 0, fmt.Errorf("invalid duration %q", s)
}
