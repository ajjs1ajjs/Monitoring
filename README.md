# PyMon - Enterprise Server Monitoring

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/ajjs1ajjs/Monitoring/blob/main/LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Version](https://img.shields.io/badge/Version-0.1.0-orange.svg)]()

**Professional server monitoring dashboard with Grafana-style visualizations, real-time metrics, and alerts.**

<p align="center">
  <img src="https://img.shields.io/badge/Dashboard-Grafana--style-blue" alt="Dashboard">
  <img src="https://img.shields.io/badge/Features-20+-green" alt="Features">
  <img src="https://img.shields.io/badge/Alerts-Telegram%20%7C%20Discord%20%7C%20Slack%20%7C%20Email-orange" alt="Alerts">
</p>

---

## Quick Start

### Windows

```powershell
# PowerShell (as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1'))
```

### Linux

```bash
# Bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

### Manual

```bash
# Clone repository
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring

# Create virtual environment
python -m venv .venv

# Activate
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m pymon server
```

**Access:** http://localhost:8090/dashboard/

**Default credentials:** `admin` / `changeme`

> &#9888;&#65039; Change password after first login!

---

## Features

| Category | Features |
|----------|----------|
| **Monitoring** | CPU, Memory, Disk, Network, Uptime |
| **Dashboard** | Grafana-style dark theme, real-time charts, auto-refresh |
| **Visualizations** | Line charts, disk breakdown, uptime timeline |
| **OS Support** | Windows Server, Linux (all distros) |
| **Alerts** | Telegram, Discord, Slack, Email |
| **API** | Full REST API with JWT authentication |
| **Export** | CSV, JSON data export |

---

## Configuration

### config.yml

```yaml
server:
  host: 0.0.0.0
  port: 8090
  domain: localhost

storage:
  backend: sqlite
  path: pymon.db
  retention_hours: 168

auth:
  admin_username: admin
  admin_password: changeme  # &#9888;&#65039; CHANGE THIS!
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

### Windows Server

```powershell
# Install windows_exporter (PowerShell as Admin)
msiexec /i windows_exporter.msi ENABLED_COLLECTORS="cpu,cs,memory,net,logical_disk"

# Or via script
iwr -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install_exporter.ps1' | iex
```

**Port:** 9182

### Linux Server

```bash
# Install node_exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz
./node_exporter
```

**Port:** 9100

---

## API Reference

### Authentication

```bash
# Login
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme"}'

# Response:
# {"access_token":"...","token_type":"bearer","user":{"id":1,"username":"admin"...}}
```

### Add Server

```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8090/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production","host":"192.168.1.100","os_type":"windows","agent_port":9182}'
```

### Get Metrics

```bash
# Historical metrics across servers
curl "http://localhost:8090/api/v1/servers/history?range=1h&metric=cpu"

# Disk breakdown
curl "http://localhost:8090/api/v1/servers/1/disk-breakdown"

# Export data
curl "http://localhost:8090/api/v1/servers/1/export?format=csv&range=24h"
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | sqlite | Storage type |
| `DB_PATH` | pymon.db | Database path |
| `CONFIG_PATH` | config.yml | Config file |
| `TLS_ENABLED` | false | Enable TLS |
| `TLS_CERT` | - | TLS certificate |
| `TLS_KEY` | - | TLS key |
| `JWT_SECRET` | auto-generated | JWT secret |

---

## Directory Structure

```
Monitoring/
&#9500;&#9472;&#9472; pymon/
&#9474;   &#9500;&#9472;&#9472; __init__.py          # Package init
&#9474;   &#9500;&#9472;&#9472; cli.py               # CLI entry point
&#9474;   &#9500;&#9472;&#9472; config.py            # Configuration
&#9474;   &#9500;&#9472;&#9472; auth.py              # JWT Authentication
&#9474;   &#9500;&#9472;&#9472; scrape.py            # Metrics scraping
&#9474;   &#9500;&#9472;&#9472; middleware.py        # Error handling
&#9474;   &#9500;&#9472;&#9472; validation.py        # Input validation
&#9474;   &#9500;&#9472;&#9472; web_dashboard.py     # Legacy DB/table helpers
&#9474;   &#9500;&#9472;&#9472; web_dashboard_enhanced.py  # Active dashboard UI
&#9474;   &#9500;&#9472;&#9472; api/
&#9474;   &#9474;   &#9492;&#9472;&#9472; endpoints.py     # API endpoints
&#9474;   &#9500;&#9472;&#9472; metrics/             # Metrics modules
&#9474;   &#9500;&#9472;&#9472; storage/             # Storage backends
&#9474;   &#9492;&#9472;&#9472; storage/db_utils.py   # DB utilities
&#9500;&#9472;&#9472; config.yml              # Configuration
&#9500;&#9472;&#9472; requirements.txt        # Dependencies
&#9500;&#9472;&#9472; run.sh                 # Linux start script
&#9500;&#9472;&#9472; run.bat                # Windows start script
&#9500;&#9472;&#9472; install.sh             # Linux installer
&#9492;&#9472;&#9472; install.ps1            # Windows installer
```

---

## Troubleshooting

### Port in use

```bash
# Linux
sudo lsof -i :8090
# or
sudo netstat -tulpn | grep 8090

# Windows
netstat -ano | findstr :8090
```

### Charts no data

```bash
# Check exporter
curl http://server:9182/metrics  # Windows
curl http://server:9100/metrics  # Linux

# Check scrape status in dashboard
```

---

## Security

- &#9888;&#65039; Change default password immediately
- &#128274; Use TLS in production
- &#128273; Use API keys for integrations
- &#128221; Review audit logs

---

## Credits

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLite](https://sqlite.org/) - Database
- [Chart.js](https://chartjs.org/) - Charts
- [windows_exporter](https://github.com/prometheus-community/windows_exporter)
- [node_exporter](https://github.com/prometheus/node_exporter)

---

## License

MIT - See [LICENSE](LICENSE)

---

**&#11088; Star if useful!**
