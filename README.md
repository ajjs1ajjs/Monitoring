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

## Quick Start

### Install Server (Main monitoring server)

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
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
3. **Agents send metrics** to the server every 15 seconds
4. **View metrics** in the web dashboard

## Agent Capabilities

### Linux Agent
- CPU usage and frequency
- Memory usage (total, available, used)
- Disk usage (all partitions)
- Network I/O (all interfaces)
- System load average
- Boot time

### Windows Agent
- CPU usage
- Memory usage
- Disk usage (all drives)
- Network I/O
- Windows services status
- Process count
- OS info (version, name)

## Configuration

### Agent Environment Variables

```bash
PYMON_SERVER=http://your-server:8090    # PyMon server URL
PYMON_API_KEY=your-api-key              # API key for authentication
PYMON_AGENT_PORT=9100                   # Local HTTP port for /metrics
```

### Server Config

File: `/etc/pymon/config.yml`

```yaml
server:
  port: 8090
  host: 0.0.0.0

storage:
  backend: sqlite
  path: /var/lib/pymon/pymon.db

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

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   PyMon Server  │◄────────│  Linux Agent     │
│   (this repo)   │  HTTP   │  (node_exporter  │
│                 │         │   style)         │
│  - Dashboard    │         └──────────────────┘
│  - API          │
│  - Alerts       │         ┌──────────────────┐
│  - Storage      │◄────────│  Windows Agent   │
└─────────────────┘  HTTP   │  (windows_exporter
         ▲                  │   style)         │
         │                  └──────────────────┘
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
