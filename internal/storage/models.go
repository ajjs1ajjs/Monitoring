package storage

type Server struct {
	ID              int64   `json:"id"`
	Name            string  `json:"name"`
	Host            string  `json:"host"`
	AgentPort       int     `json:"agent_port"`
	ServerGroup     string  `json:"server_group"`
	OSType          string  `json:"os_type"`
	Enabled         int     `json:"enabled"`
	LastStatus      string  `json:"last_status"`
	LastCheck       string  `json:"last_check"`
	CPUPercent      float64 `json:"cpu_percent"`
	MemoryPercent   float64 `json:"memory_percent"`
	DiskPercent     float64 `json:"disk_percent"`
	ExporterVersion string  `json:"exporter_version"`
	ErrorMessage    string  `json:"error_message"`
	IsMaintenance   int     `json:"is_maintenance"`
	FlappingCount   int     `json:"flapping_count"`
	Volumes         string  `json:"volumes"`
	ScrapeInterval  int     `json:"scrape_interval"`
	Labels          string  `json:"labels"`
	CreatedAt       string  `json:"created_at"`
}

type Service struct {
	ID             int64   `json:"id"`
	Name           string  `json:"name"`
	TargetURL      string  `json:"target_url"`
	CheckType      string  `json:"check_type"`
	Interval       int     `json:"interval"`
	Timeout        int     `json:"timeout"`
	ExpectedStatus int     `json:"expected_status"`
	Enabled        int     `json:"enabled"`
	Status         string  `json:"status"`
	LastCheck      string  `json:"last_check"`
	ResponseTimeMS float64 `json:"response_time_ms"`
	CreatedAt      string  `json:"created_at"`
}

type MetricPoint struct {
	ID            int64    `json:"id"`
	ServerID      int64    `json:"server_id"`
	CPUPercent    *float64 `json:"cpu"`
	MemoryPercent *float64 `json:"mem"`
	DiskPercent   *float64 `json:"disk"`
	NetworkRX     *float64 `json:"net_rx"`
	NetworkTX     *float64 `json:"net_tx"`
	DiskInfo      string   `json:"disk_info"`
	Timestamp     string   `json:"timestamp"`
}

type ServiceHistory struct {
	ID        int64   `json:"id"`
	ServiceID int64   `json:"service_id"`
	Status    string  `json:"status"`
	LatencyMS float64 `json:"latency_ms"`
	Timestamp string  `json:"timestamp"`
}

type Alert struct {
	ID             int64   `json:"id"`
	ServerID       int64   `json:"server_id"`
	ServiceID      int64   `json:"service_id"`
	AlertType      string  `json:"alert_type"`
	Severity       string  `json:"severity"`
	Message        string  `json:"message"`
	Timestamp      string  `json:"timestamp"`
	Resolved       int     `json:"resolved"`
	ResolvedAt     string  `json:"resolved_at"`
	Name           string  `json:"name"`
	Metric         string  `json:"metric"`
	Condition      string  `json:"condition"`
	Threshold      float64 `json:"threshold"`
	Duration       int     `json:"duration"`
	NotifyTelegram int     `json:"notify_telegram"`
	NotifyDiscord  int     `json:"notify_discord"`
	NotifySlack    int     `json:"notify_slack"`
	NotifyEmail    int     `json:"notify_email"`
	NotifyTeams    int     `json:"notify_teams"`
	Description    string  `json:"description"`
	Enabled        int     `json:"enabled"`
	CreatedAt      string  `json:"created_at"`
}

type AuditLog struct {
	ID        int64  `json:"id"`
	UserID    int64  `json:"user_id"`
	Action    string `json:"action"`
	Details   string `json:"details"`
	IPAddress string `json:"ip_address"`
	Timestamp string `json:"timestamp"`
}

type User struct {
	ID                 int64  `json:"id"`
	Username           string `json:"username"`
	PasswordHash       string `json:"-"`
	IsAdmin            int    `json:"is_admin"`
	MustChangePassword int    `json:"must_change_password"`
	CreatedAt          string `json:"created_at"`
	LastLogin          string `json:"last_login"`
}

type APIKey struct {
	ID        int64  `json:"id"`
	UserID    int64  `json:"user_id"`
	KeyHash   string `json:"-"`
	KeySHA256 string `json:"-"`
	Name      string `json:"name"`
	CreatedAt string `json:"created_at"`
	LastUsed  string `json:"last_used"`
}

type Notification struct {
	Channel string `json:"channel"`
	Enabled int    `json:"enabled"`
	Config  string `json:"config"`
}

type Metric struct {
	ID        int64   `json:"id"`
	Name      string  `json:"name"`
	Labels    string  `json:"labels"`
	Value     float64 `json:"value"`
	Timestamp string  `json:"timestamp"`
}

type Volume struct {
	Volume  string  `json:"volume"`
	SizeGB  float64 `json:"size_gb"`
	FreeGB  float64 `json:"free_gb"`
	UsedGB  float64 `json:"used_gb"`
	Percent float64 `json:"percent"`
}

type DiskBreakdown struct {
	Volume  string  `json:"volume"`
	SizeGB  float64 `json:"size_gb"`
	FreeGB  float64 `json:"free_gb"`
	UsedGB  float64 `json:"used_gb"`
	Percent float64 `json:"percent"`
}
