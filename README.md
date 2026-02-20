# PyMon - Server Monitoring System

**Enterprise server monitoring for Linux and Windows (like Prometheus + node_exporter/windows_exporter)**

## Features

- **Server Monitoring** - Linux & Windows servers via agents
- **System Metrics** - CPU, Memory, Disk, Network, Processes
- **Agent-based** - Like node_exporter (Linux) and windows_exporter (Windows)
- **Web Dashboard** - Modern UI for managing servers and viewing metrics
- **Alerts** - Notifications via Telegram, Discord, Slack, Email
- **REST API** - Full API for integration
- **Prometheus-compatible** - /metrics endpoint on each agent
- **RAID Monitoring** - Linux mdadm, MegaRAID, HP Smart Array
- **Background Scraping** - Auto-collects metrics every 60 seconds

## Dashboard Features

- **Charts** - CPU, Memory, Disk, Network with real-time updates
- **Legend Sorting** - Click "Last" or "Max" to sort servers
- **Legend Filtering** - Click on server in legend to filter
- **Stat Cards** - Quick filters for Online/Offline/Linux/Windows
- **Auto-refresh** - Dashboard refreshes every 30 seconds
- **Manual Refresh** - Click refresh button to update immediately
- **Time Range** - 5m, 15m, 1h, 6h, 24h views

## Quick Start

### Install Server (Main monitoring server)

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

Or run locally:
```bash
pip install -r requirements.txt
python -m pymon.cli server
```

### Install Agent on Linux Servers

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash
```

Then edit the config:
```bash
sudo nano /etc/systemd/system/pymon-agent.service
# Set PYMON_SERVER and PYMON_API_KEY
sudo systemctl start pymon-agent
```

### Install Agent on Windows Servers

```powershell
# Run as Administrator
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-windows.ps1" -OutFile "install.ps1"
.\install.ps1 -ServerUrl "http://your-pymon-server:8090"
```

## Access

After installation:
- **Dashboard**: http://your-server:8090/dashboard/
- **API**: http://your-server:8090/api/v1/
- **Agent Metrics** (on each server): http://server-ip:9100/metrics

**Default credentials**: `admin` / `admin`

## How It Works

1. **Install PyMon Server** - Main monitoring hub
2. **Install Agents** on each server you want to monitor:
   - **Linux**: Uses psutil, collects like node_exporter
   - **Windows**: Uses WMI + psutil, collects like windows_exporter
3. **Server auto-discovers agents** - Background scraping every 60 seconds
4. **View metrics** in the web dashboard

## Agent Capabilities

### Linux Agent
- CPU usage and frequency
- Memory usage (total, available, used)
- Disk usage (all partitions)
- Network I/O (all interfaces)
- System load average
- Boot time
- RAID monitoring (mdadm, MegaRAID, HP Smart Array)
- SMART status for disks

### Windows Agent
- CPU usage
- Memory usage
- Disk usage (all drives)
- Network I/O
- Windows services status
- Process count
- OS info (version, name)
- RAID/Storage Spaces info

## Configuration

### Agent Environment Variables

```bash
PYMON_SERVER=http://your-server:8090    # PyMon server URL
PYMON_API_KEY=your-api-key              # API key for authentication
PYMON_AGENT_PORT=9100                   # Local HTTP port for /metrics
```

### Server Config

File: `config.yml`

```yaml
server:
  port: 8090
  host: 0.0.0.0

storage:
  backend: sqlite
  path: pymon.db

scrape_configs:
  - job_name: agents
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets: []

auth:
  admin_username: admin
  admin_password: admin
```

## API Examples

### Get All Servers
```bash
curl http://localhost:8090/api/servers \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Add Server
```bash
curl -X POST http://localhost:8090/api/servers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production DB",
    "host": "192.168.1.100",
    "os_type": "linux"
  }'
```

### Manual Scrape
```bash
curl -X POST http://localhost:8090/api/servers/1/scrape \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   PyMon Server  │◄--------│  Linux Agent    │
│   (this repo)   │  HTTP   │  (port 9100)    │
│                 │  /metrics                 │
│  - Dashboard    │         └──────────────────┘
│  - API          │         ┌──────────────────┐
│  - Alerts       │◄--------│  Windows Agent   │
│  - Storage      │  HTTP   │  (port 9100)     │
│  - Scraping     │  /metrics                 │
└─────────────────┘         └──────────────────┘
          ▲
          │
     Web Browser
```

## Management Commands

```bash
# Server
sudo systemctl status pymon
sudo systemctl restart pymon
sudo journalctl -u pymon -f

# Linux Agent
sudo systemctl status pymon-agent
sudo systemctl restart pymon-agent

# Windows Agent
Get-Service PyMonAgent
Start-Service PyMonAgent
Stop-Service PyMonAgent
```

## Update

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/update.sh | sudo bash
```

## License

MIT License

## Similar Tools

- **Prometheus** - We are compatible with /metrics format
- **node_exporter** - Our Linux agent works similarly
- **windows_exporter** - Our Windows agent works similarly
- **Grafana** - Our dashboard provides similar visualization

**Key difference**: PyMon is all-in-one (server + agents + dashboard) with easier setup.
