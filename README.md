# PyMon - Enterprise Server Monitoring

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

**Professional server monitoring dashboard with real-time metrics, alerts, and RAID monitoring.**

<p align="center">
  <img src="https://img.shields.io/badge/Servers-300+-blue" alt="Servers">
  <img src="https://img.shields.io/badge/Features-20+-green" alt="Features">
  <img src="https://img.shields.io/badge/Alerts-Telegram%20%7C%20Discord%20%7C%20Slack%20%7C%20Email-orange" alt="Alerts">
</p>

---

## Features

| Category | Features |
|----------|----------|
| **Monitoring** | CPU, Memory, Disk, Network, Uptime |
| **OS Support** | Windows Server, Linux (all distros) |
| **RAID** | Hardware RAID monitoring via Telegraf |
| **Alerts** | Telegram, Discord, Slack, Email |
| **Dashboard** | Real-time charts, filtering, sorting |
| **API** | Full REST API with authentication |
| **Backup** | Automatic backups with restore |

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────┐
│  PyMon Dashboard                                    [Logout] │
├─────────────────────────────────────────────────────────────┤
│  Dashboard  │  Servers  │  Alerts  │  Settings              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  309    │  │   5     │  │  257    │  │   52    │        │
│  │ Online  │  │ Offline │  │ Windows │  │  Linux  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ CPU Usage Chart                          [5m][1h][24h]│  │
│  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ SQL2019        77.4%  Max: 82%  │  │
│  │ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░ APPSRV7        54.6%  Max: 61%  │  │
│  │ ▓▓▓▓▓▓▓▓▓░░░░░░░░░░ APPSRV6        51.6%  Max: 58%  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  RAID Status: 6 servers | 21 arrays | 2 degraded           │
│  HOST-VM: RAID5 281GB ✓ RAID6 15258GB ✗ RAID6 3814GB ✓    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- pip package manager

### Installation

```bash
# Clone repository
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux

# Install dependencies
pip install -r requirements.txt

# Start server
python -m pymon.cli server
```

Access dashboard: **http://localhost:8090/dashboard/**

Default credentials: `admin` / `admin`

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

auth:
  admin_username: admin
  admin_password: admin

scrape_configs:
  - job_name: servers
    scrape_interval: 60
    scrape_timeout: 10
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

### Import from Prometheus

If you have existing `prometheus.yml`:

```bash
python scripts/import_prometheus.py prometheus.yml
```

---

## API Reference

### Authentication

```bash
# Login
POST /api/v1/auth/login
Body: {"username": "admin", "password": "admin"}
Response: {"access_token": "..."}

# All requests need header:
Authorization: Bearer <token>
```

### Servers

```bash
GET    /api/servers              # List all servers
POST   /api/servers              # Add server
GET    /api/servers/{id}         # Get server details
PUT    /api/servers/{id}         # Update server
DELETE /api/servers/{id}         # Delete server
POST   /api/servers/{id}/scrape  # Manual scrape
```

### Alerts

```bash
GET    /api/alerts               # List alerts
POST   /api/alerts               # Create alert
PUT    /api/alerts/{id}          # Update alert
DELETE /api/alerts/{id}          # Delete alert
```

### RAID Status

```bash
GET    /api/raid-status          # Get all RAID arrays
```

### Backups

```bash
GET    /api/backup/config        # Backup settings
POST   /api/backup/config        # Update settings
POST   /api/backup/create        # Create full backup
POST   /api/backup/restore       # Restore from backup
GET    /api/backup/list          # List backup files
DELETE /api/backup/file          # Delete backup file
```

### System

```bash
GET    /api/health               # Health check
POST   /api/system/reset         # Factory reset (dangerous!)
POST   /api/system/clear-metrics # Clear all metrics
```

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
| Notify | Telegram, Discord, Slack, Email |

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

### Auto Backup Settings

```bash
curl -X POST http://localhost:8090/api/backup/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "auto": true,
    "time": "02:00",
    "path": "D:/backups",
    "keep_days": 30
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

## Dashboard Features

### Servers Tab

- **Search**: Filter by name or host
- **Status Filter**: Online / Offline
- **OS Filter**: Windows / Linux
- **Metric Filters**: CPU/Memory/Disk thresholds
- **Sorting**: Name, Status, CPU, Memory, Disk
- **Disk Details**: Shows C:, D:, E: with percentages

### Alert Metrics

| Metric | Description |
|--------|-------------|
| `cpu` | CPU usage percentage |
| `memory` | Memory usage percentage |
| `disk` | Disk usage percentage |
| `network` | Network I/O |
| `exporter` | Exporter availability |
| `raid` | RAID array health |

---

## Directory Structure

```
Monitoring/
├── pymon/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration
│   ├── web_dashboard.py    # Dashboard + API
│   ├── api/
│   │   └── endpoints.py    # API endpoints
│   ├── auth.py             # Authentication
│   ├── storage.py          # Database storage
│   └── scrape.py           # Metrics scraping
├── config.yml              # Configuration file
├── pymon.db                # SQLite database
├── backups/                # Backup storage
├── requirements.txt        # Dependencies
└── README.md
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

### Metrics not updating

```bash
# Manual scrape test
curl -X POST http://localhost:8090/api/servers/1/scrape \
  -H "Authorization: Bearer $TOKEN"

# Check scrape interval in config.yml
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
| Dashboard | Built-in | Requires Grafana |
| Alerts | Built-in | Requires AlertManager |
| Database | SQLite (no setup) | Requires configuration |
| Learning curve | Low | Medium-High |
| RAID monitoring | Built-in | Custom setup |

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ajjs1ajjs/Monitoring/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ajjs1ajjs/Monitoring/discussions)

---

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLite](https://sqlite.org/) - Database
- [httpx](https://www.python-httpx.org/) - HTTP client
- [Chart.js](https://chartjs.org/) - Charts

Compatible with:
- [windows_exporter](https://github.com/prometheus-community/windows_exporter)
- [node_exporter](https://github.com/prometheus/node_exporter)
- [Telegraf](https://github.com/influxdata/telegraf)
