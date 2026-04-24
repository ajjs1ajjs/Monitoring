# PyMon - Enterprise Server Monitoring

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Version](https://img.shields.io/badge/Version-2.0.0-orange.svg)]()

**Professional server monitoring dashboard with Grafana-style visualizations, real-time metrics, alerts, and RAID monitoring.**

<p align="center">
  <img src="https://img.shields.io/badge/Servers-300+-blue" alt="Servers">
  <img src="https://img.shields.io/badge/Features-25+-green" alt="Features">
  <img src="https://img.shields.io/badge/Alerts-Telegram%20%7C%20Discord%20%7C%20Slack%20%7C%20Email-orange" alt="Alerts">
</p>

---

## 🌟 New in v2.0.0 - Enhanced Dashboard

![Enhanced Dashboard](https://img.shields.io/badge/Dashboard-Grafana--style-blue)

- 🎨 **Grafana-style Dark Theme** - Professional enterprise-grade UI
- 📊 **Real-time Charts** - Chart.js with historical data
- 💾 **Disk Breakdown** - Per-volume usage (C:, D:, E:)
- ⏱️ **Uptime Timeline** - 7-day visual history
- 📤 **Data Export** - CSV/JSON export for reports
- 🔄 **Auto-refresh** - Every 30 seconds
- 📱 **Responsive Design** - Mobile, tablet, desktop
- 📈 **Trend Analysis** - Compare current vs previous periods

---

## Features

| Category | Features |
|----------|----------|
| **Monitoring** | CPU, Memory, Disk, Network, Uptime, RAID |
| **Dashboard** | Grafana-style dark theme, real-time charts, auto-refresh |
| **Visualizations** | Line charts, disk breakdown, uptime timeline, trend indicators |
| **OS Support** | Windows Server, Linux (all distros) |
| **RAID** | Hardware RAID monitoring via Telegraf |
| **Alerts** | Telegram, Discord, Slack, Email, Teams |
| **API** | Full REST API with JWT authentication |
| **Export** | CSV, JSON data export |
| **Backup** | Automatic backups with restore |

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip package manager

### Windows Quick Start

```batch
# Clone and run
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring
.\run.bat  # For PowerShell, or just 'run.bat' for CMD
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux

# Install dependencies
pip install -r requirements.txt

# Install PyMon in editable mode
pip install -e . --no-deps

# Start server
python -m pymon.cli server
```

**Access dashboard:** http://localhost:8090/dashboard/

**Default credentials:** `admin` / `admin`

⚠️ **Change password after first login!**

---

## 🎨 Dashboard Features

### Stats Overview

| Card | Description |
|------|-------------|
| **Online Servers** | Count of servers with status=up |
| **Offline Servers** | Count of servers with status=down |
| **Avg CPU Usage** | Average CPU across all servers |
| **Avg Memory Usage** | Average memory across all servers |

### Charts

| Chart | Type | Features |
|-------|------|----------|
| **CPU Usage** | Line chart | Real-time data, 80% threshold line |
| **Memory Usage** | Line chart | Real-time data, 80% threshold line |
| **Disk Usage** | Line chart | Real-time data, 80% threshold line |
| **Disk Breakdown** | Progress bars | Per-volume (C:, D:, E:) usage |
| **Network Traffic** | Line chart | RX/TX metrics |
| **Uptime Timeline** | Bar segments | 7-day up/down visualization |

### Time Range Selector

Choose data range: **5m**, **15m**, **1h**, **6h**, **24h**

### Server Grid

- Status indicators (green=online, red=offline)
- CPU/Memory/Disk metrics per server
- Color-coded thresholds (green < 60% < yellow < 80% < red)
- Click to navigate to server details

---

## Configuration

### config.yml

```yaml
server:
  host: 0.0.0.0
  port: 8090

storage:
  backend: sqlite
  path: pymon.db
  retention_hours: 168  # 7 days

auth:
  admin_username: admin
  admin_password: admin
  jwt_expire_hours: 24

scrape_configs:
  - job_name: servers
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets:
          - 192.168.1.100:9182  # Windows
          - 192.168.1.101:9100  # Linux
```

---

## Data Sources

PyMon collects metrics from industry-standard exporters:

### Windows Servers

**[windows_exporter](https://github.com/prometheus-community/windows_exporter)**

```powershell
# Download and install
msiexec /i windows_exporter.msi ENABLED_COLLECTORS="cpu,cs,memory,net,logical_disk"

# Default port: 9182
# Metrics: http://server:9182/metrics
```

### Linux Servers

**[node_exporter](https://github.com/prometheus/node_exporter)**

```bash
# Download
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz

# Run
./node_exporter

# Default port: 9100
# Metrics: http://server:9100/metrics
```

### RAID Monitoring

**[Telegraf](https://github.com/influxdata/telegraf)** with MegaRAID/SMART plugins

```toml
# /etc/telegraf/telegraf.conf
[[inputs.prometheus]]
  urls = ["http://localhost:9273/metrics"]

[[outputs.prometheus_client]]
  listen = ":9273"
```

| Server Type | Exporter | Port | Metrics |
|-------------|----------|------|---------|
| Windows | windows_exporter | 9182 | CPU, Memory, Disk, Network |
| Linux | node_exporter | 9100 | CPU, Memory, Disk, Network |
| RAID | Telegraf | 9273 | RAID status, disk health |

---

## Adding Servers

### Via Dashboard

1. Go to **Servers** tab
2. Click **Add Server**
3. Fill in: Name, Host/IP, OS Type, Port
4. Click **Add**

### Via API

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# Add server
curl -X POST http://localhost:8090/api/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production SQL",
    "host": "192.168.1.100",
    "os_type": "windows",
    "agent_port": 9182
  }'
```

---

## 🔌 API Reference

### Authentication

```bash
# Login
POST /api/v1/auth/login
Body: {"username": "admin", "password": "admin"}
Response: {"access_token": "...", "token_type": "bearer"}

# All requests need header:
Authorization: Bearer <token>
```

### Enhanced Dashboard APIs (NEW!)

#### Get Historical Metrics

```bash
# Get metrics history for charts
GET /api/servers/metrics-history?range=1h&metric=cpu
# Returns: { "labels": ["10:00", "10:05", ...], "datasets": [...] }

# Metrics: cpu, memory, disk, network
# Ranges: 5m, 15m, 1h, 6h, 24h, 7d
```

#### Get Disk Breakdown

```bash
# Get per-disk usage (C:, D:, E:)
GET /api/servers/{server_id}/disk-breakdown
# Returns: { "disks": [{"volume": "C:", "size_gb": 500, "used_gb": 375, "percent": 75}] }
```

#### Get Uptime Timeline

```bash
# Get 7-day uptime visualization
GET /api/servers/{server_id}/uptime-timeline?days=7
# Returns: { "timeline": [...], "uptime_percent": 99.5 }
```

#### Export Data

```bash
# Export server metrics as CSV or JSON
GET /api/servers/{server_id}/export?format=csv&range=24h
# Returns: CSV file download
```

#### Compare Time Ranges

```bash
# Compare current vs previous period
GET /api/servers/compare?metric=cpu&range=1h
# Returns: { "current": 45.2, "previous": 42.1, "delta": 3.1, "trend": "up" }
```

### Servers API

```bash
GET    /api/servers              # List all servers
POST   /api/servers              # Add server
GET    /api/servers/{id}         # Get server details
PUT    /api/servers/{id}         # Update server
DELETE /api/servers/{id}         # Delete server
POST   /api/servers/{id}/scrape  # Manual scrape
```

### Alerts API

```bash
GET    /api/alerts               # List alerts
POST   /api/alerts               # Create alert
PUT    /api/alerts/{id}          # Update alert
DELETE /api/alerts/{id}          # Delete alert
```

### Full API Documentation

See [docs/API.md](docs/API.md) for complete API reference.

---

## Alerts Configuration

### Create Alert Rule

| Parameter | Values |
|-----------|--------|
| Metric | cpu, memory, disk, network, exporter, raid |
| Condition | greater_than, less_than, equals |
| Threshold | Numeric value (0-100) |
| Duration | Seconds to trigger |
| Severity | critical, warning, info |
| Notify | Telegram, Discord, Slack, Email, Teams |

### Example: High CPU Alert

```json
{
  "name": "High CPU Usage",
  "metric": "cpu",
  "condition": "greater_than",
  "threshold": 90,
  "duration": 300,
  "severity": "critical",
  "notify_telegram": true,
  "notify_email": true
}
```

---

## 📤 Data Export

### Export Chart Data

Click the **download icon** on any chart to export data.

### Via API

```bash
# Export as JSON
curl -X GET "http://localhost:8090/api/servers/1/export?format=json&range=24h" \
  -H "Authorization: Bearer $TOKEN"

# Export as CSV
curl -X GET "http://localhost:8090/api/servers/1/export?format=csv&range=24h" \
  -H "Authorization: Bearer $TOKEN" \
  --output server_metrics.csv
```

---

## Backup & Restore

### Create Backup

```bash
# Via API
curl -X POST http://localhost:8090/api/backup/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "D:/backups"}'

# Backup contains:
# - pymon.db (database)
# - config.yml (configuration)
# - settings.json (all settings)
```

### Restore Backup

```bash
curl -X POST http://localhost:8090/api/backup/restore \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file": "D:/backups/pymon_full_20260222.zip",
    "restore_db": true,
    "restore_config": true,
    "restore_settings": true
  }'
```

---

## Update

```bash
# Stop server
# Ctrl+C or:
sudo systemctl stop pymon  # Linux

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Start server
python -m pymon.cli server
```

---

## Troubleshooting

### Server won't start

```bash
# Check port is free
netstat -an | findstr :8090    # Windows
netstat -tulpn | grep 8090     # Linux

# Check logs
python -m pymon.cli server 2>&1 | tee server.log
```

### Charts not showing data

```bash
# Check if metrics_history table has data
# Data is collected every 15-60 seconds based on scrape_interval
# Wait a few minutes after adding servers

# Manual scrape test
curl -X POST http://localhost:8090/api/servers/1/scrape \
  -H "Authorization: Bearer $TOKEN"
```

### Can't connect to exporter

```bash
# Test exporter directly
curl http://server-ip:9182/metrics     # Windows
curl http://server-ip:9100/metrics     # Linux
curl http://server-ip:9273/metrics     # Telegraf

# Check firewall
# Windows: Allow port 9182 in Windows Firewall
# Linux: sudo ufw allow 9100
```

---

## Security Recommendations

1. **Change default password** immediately
2. **Use HTTPS** in production
3. **Restrict API access** with firewall rules
4. **Enable backup encryption** for sensitive data
5. **Use API keys** for integrations
6. **Review audit logs** regularly

---

## Comparison

| Feature | PyMon | Prometheus + Grafana |
|---------|-------|---------------------|
| Setup | Single command | Multiple components |
| Dashboard | Built-in (Grafana-style) | Requires Grafana |
| Alerts | Built-in | Requires AlertManager |
| Database | SQLite (no setup) | Requires configuration |
| Learning curve | Low | Medium-High |
| RAID monitoring | Built-in | Custom setup |
| Export | CSV/JSON | Requires plugins |

---

## Directory Structure

```
Monitoring/
├── pymon/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── config.py               # Configuration
│   ├── web_dashboard.py        # Legacy dashboard
│   ├── web_dashboard_enhanced.py  # NEW: Enhanced Grafana-style dashboard
│   ├── api/
│   │   └── endpoints.py        # API endpoints
│   ├── auth.py                 # JWT Authentication
│   ├── scrape.py               # Metrics scraping
│   ├── metrics/
│   │   ├── collector.py        # Metric registry
│   │   └── models.py           # Data models
│   └── storage/
│       └── backend.py          # Database backend
├── docs/
│   └── API.md                  # Full API documentation
├── examples/
│   ├── basic_usage.py          # Basic usage examples
│   └── api_examples.py         # API usage examples
├── config.yml                  # Configuration file
├── requirements.txt            # Dependencies
└── README.md
```

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ajjs1ajjs/Monitoring/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ajjs1ajjs/Monitoring/discussions)
- **Documentation**: [docs/API.md](docs/API.md)

---

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLite](https://sqlite.org/) - Database
- [httpx](https://www.python-httpx.org/) - HTTP client
- [Chart.js](https://chartjs.org/) - Charts
- [Font Awesome](https://fontawesome.com/) - Icons

Compatible with:
- [windows_exporter](https://github.com/prometheus-community/windows_exporter)
- [node_exporter](https://github.com/prometheus/node_exporter)
- [Telegraf](https://github.com/influxdata/telegraf)

---

## 📊 Quick Reference

### Default Ports

| Service | Port |
|---------|------|
| PyMon Dashboard | 8090 |
| windows_exporter | 9182 |
| node_exporter | 9100 |
| Telegraf | 9273 |

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/servers` | List all servers |
| `GET /api/servers/metrics-history?range=1h` | Historical metrics |
| `GET /api/servers/{id}/disk-breakdown` | Per-disk usage |
| `GET /api/servers/{id}/uptime-timeline` | Uptime history |
| `GET /api/servers/{id}/export?format=csv` | Export data |
| `GET /api/servers/compare?metric=cpu` | Trend comparison |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `R` | Refresh dashboard |
| `?` | Show keyboard shortcuts |

---

**⭐ Star this repo if you find it useful!**

**📢 Questions? Open an issue or join the discussion!**
