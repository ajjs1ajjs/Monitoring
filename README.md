<div align="center">
  <h1>PyMon NOC</h1>
  <p><b>Enterprise Infrastructure Monitoring & NOC Dashboard</b></p>
  
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

  <img src="https://img.shields.io/badge/Status-Production_Ready-success" alt="Production Ready">
</div>

---

**PyMon NOC** is a self-hosted, lightweight, and extremely fast infrastructure monitoring platform designed for both Linux and Windows environments. It features a modern, responsive Grafana-style dashboard, real-time metrics scraping, and integrated alerting rules.

## ✨ Features

- **Real-Time NOC Dashboard**: Beautiful dark-themed dashboard with live metrics, dynamic charts, and detailed Grid/List views.
- **Cross-Platform Agents**: Support for standard Prometheus exporters (`node_exporter` for Linux, `windows_exporter` for Windows).
- **Smart Alerting**: Configure critical thresholds for CPU, RAM, and Disk to receive instant notifications via Telegram or Discord.
- **Role-Based Access Control**: Secure JWT authentication and user management built-in.
- **Audit Logging**: Comprehensive tracking of all system events and user actions.
- **Zero-Dependency Core**: Built on Python, SQLite/PostgreSQL, and Vanilla JS for maximum portability and speed.

## 🚀 Quick Start

### Installing the Management Server

**Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

**Windows Server:**
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1'))
```

Once installed, the dashboard will be available at: `http://localhost:10000/dashboard/`  
**Default Login:** `admin` / `changeme` *(Please change immediately after logging in)*

### Deploying Agents to Target Nodes

PyMon uses standard Prometheus exporters. You can deploy them easily to your servers:

**Linux Node (node_exporter):**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash
```

**Windows Node (windows_exporter):**
```powershell
iwr -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install_exporter.ps1' | iex
```

## 🛠️ Manual Installation & Development

```bash
# Clone the repository
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package and dependencies
pip install -e .

# Start the server
pymon server
```

## ⚙️ Configuration

PyMon uses a `config.yml` file located in the root directory. You can configure:
- **Server**: Host, port, and domain.
- **Storage**: Choose between SQLite (default) or PostgreSQL for massive scalability.
- **Auth**: JWT expiration times and secrets.
- **Scraping**: Polling intervals and timeout settings.

## 📚 Documentation

Detailed documentation can be found in the `docs/` folder:
- [API Reference](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Database Migration Guide](docs/MIGRATION.md)

## 🛡️ Security Best Practices

- Secure the dashboard behind a reverse proxy (Nginx/Traefik) with TLS.
- Restrict agent ports (9100/9182) to only allow traffic from your PyMon server IP via firewall.
- Regularly rotate your `JWT_SECRET`.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

