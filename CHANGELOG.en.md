# Changelog

All notable changes to PyMon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2026-06-19

### 🔒 Security hardening & code audit

#### Security (critical)
- **Removed reversible admin-password storage** — dropped Fernet encryption, the
  per-startup cleartext print, and `credentials.txt`. The DB now holds only the
  bcrypt hash; the password is shown **once** on creation or `reset-admin`.
- **Removed the hardcoded weak default `291263`** — a strong random password is
  generated on first run when the config value is empty/weak (override with
  `PYMON_ADMIN_PASSWORD`).
- **Fixed broken access control** — server CRUD/maintenance, `/backup/*`, and
  audit/system-log/metric-history clears now require admin.
- **API keys can no longer perform admin actions** (ingest/read only; `403` otherwise).
- **Fixed stored XSS** — all server/service/user/log data is escaped in the
  dashboard; server host is validated against a strict character whitelist.
- **SSRF guard** — scrape/service checks refuse cloud-metadata addresses by
  default (`PYMON_ALLOW_METADATA` to opt out); private LAN ranges stay allowed.
- **Safe restore** — `/backup/restore` uses SQLite's online-backup API instead of
  overwriting the live DB file (WAL-safe).

#### Fixed
- SQLite connection leak in `_log_audit`; robust Prometheus label parsing;
  `_parse_duration` accepts floats; `delete_server` removes orphan alerts;
  `last_login` is updated on login; backup cron parser handles `*/n`, `a,b`,
  `a-b`; `reset-admin` resolves the DB path like the server.

#### Changed / Performance
- Removed N+1 queries in aggregated history, export-all, and compare.
- Extracted shared `TIME_RANGES` (`constants.py`) and `build_channels`
  (`notifications.py`); `uuid4` request ids.
- Replaced `show-password`/`restore-password` CLI commands with `reset-admin`.
- Reworked README and command/API docs; added `LICENSE`; bumped to 2.2.0.

---

## [2.1.0] - 2026-05-10

### 🏗️ Major Refactoring - Modular Architecture & Async Engine

#### Added
- **Modular API Architecture**: Decoupled monolithic `endpoints.py` into structured routers (`auth`, `servers`, `metrics`, `alerts`, etc.) under `pymon/api/routers/`.
- **Frontend/Backend Separation**: Extracted all HTML/JS/CSS into `pymon/templates/` and `pymon/static/`.
- **Async Scrape Manager**: Completely re-engineered the scraping engine using `asyncio` and `httpx.AsyncClient`, replacing legacy threading for high-performance monitoring.
- **Unified Database Layer**: Centralized database initialization and management in `pymon/database.py`.

#### Changed
- **CLI**: Modernized `cli.py` to support the new modular app structure and async lifespan events.
- **Agent Deployment**: Updated `node_exporter` and `windows_exporter` commands to latest 2026 versions in the dashboard.
- **Performance**: Optimized metric parsing and history storage with better CPU/RAM/Disk calculation logic for both Linux and Windows.

#### Removed
- Legacy "God Object" files: `web_dashboard.py`, `web_dashboard_enhanced.py`, `web_dashboard_simple.py`, and `web_ui.py`.

---

## [2.0.0] - 2026-03-19

### 🎉 Major Release - Enhanced Grafana-Style Dashboard

#### Added

##### Enhanced Dashboard
- **Grafana-style dark theme** - Professional enterprise-grade UI design
- **Real-time Chart.js visualizations** - Interactive charts with historical data
- **Time range selector** - 5m, 15m, 1h, 6h, 24h data ranges
- **Auto-refresh** - Dashboard updates every 30 seconds
- **Responsive design** - Mobile, tablet, and desktop support
- **Threshold indicators** - 80% warning lines on CPU/Memory/Disk charts
- **Export buttons** - Download chart data as CSV/JSON

##### New API Endpoints
- `GET /api/servers/metrics-history` - Historical metrics for charts
  - Query parameters: `server_id`, `range`, `metric`
  - Returns time-series data with labels and datasets
  
- `GET /api/servers/{id}/disk-breakdown` - Per-disk usage details
  - Shows C:, D:, E: volumes with size, used, free space
  - Returns percentage and GB values
  
- `GET /api/servers/{id}/uptime-timeline` - Uptime visualization data
  - 7-day default timeline (configurable 1-30 days)
  - Returns uptime percentage and status timeline
  
- `GET /api/servers/{id}/export` - Data export endpoint
  - Supports CSV and JSON formats
  - Configurable time ranges
  
- `GET /api/servers/compare` - Time range comparison
  - Compare current vs previous period
  - Returns delta, delta_percent, and trend (up/down/stable)

##### Visualizations
- **Disk Breakdown Panel** - Per-volume usage with progress bars
- **Uptime Timeline** - Visual 7-day up/down history
- **Trend Indicators** - Show comparison with previous period
- **Server Cards** - Improved grid with color-coded metrics
- **Stats Overview** - Online/Offline counts, average CPU/Memory

##### Documentation
- Complete API documentation in `docs/API.md`
- Updated README.md with new features
- SDK examples for Python, cURL, and JavaScript

#### Changed

- **Dashboard** - Replaced legacy dashboard with enhanced Grafana-style version
- **CLI** - Updated to use `web_dashboard_enhanced.py` by default
- **Login Page** - Modern design matching dashboard theme
- **Navigation** - Improved top navigation bar
- **Server Grid** - Enhanced cards with better metrics display

#### Improved

- **Chart Configuration** - Better Chart.js options with annotations
- **Color Coding** - Consistent threshold colors (green < 60% < yellow < 80% < red)
- **Performance** - Optimized data loading and rendering
- **Mobile Experience** - Responsive breakpoints for all screen sizes

#### Technical

- New file: `pymon/web_dashboard_enhanced.py` (1,400+ lines)
- Updated: `pymon/cli.py` - Integration with enhanced dashboard
- Updated: `.gitignore` - Better Python/IDE exclusions
- Chart.js upgraded to 4.4.1 with annotation plugin

---

## [1.5.0] - 2026-02-15

### Added

- RAID monitoring support via Telegraf
- Backup and restore functionality
- API key management
- Audit logging
- Maintenance windows

### Changed

- Improved alert notification system
- Enhanced security with JWT tokens
- Better error handling

---

## [1.4.0] - 2026-01-20

### Added

- Multi-channel notifications (Telegram, Discord, Slack, Email)
- Alert rules configuration
- Server groups support

### Changed

- Updated dashboard UI
- Improved metrics collection

---

## [1.3.0] - 2025-12-10

### Added

- Windows Server support with windows_exporter
- Linux support with node_exporter
- Basic REST API

### Changed

- Migrated to FastAPI framework
- SQLite database backend

---

## [1.2.0] - 2025-11-05

### Added

- Web dashboard
- Server monitoring (CPU, Memory, Disk)
- Basic authentication

---

## [1.1.0] - 2025-10-15

### Added

- Metrics collection from Prometheus exporters
- Command-line interface
- Configuration file support

---

## [1.0.0] - 2025-09-01

### Initial Release

- Basic server monitoring
- SQLite storage
- Simple web interface

---

## Version History

| Version | Date | Key Features |
|---------|------|--------------|
| 2.1.0 | 2026-05-10 | Modular architecture, Async scrape engine, Frontend/Backend decoupling |
| 2.0.0 | 2026-03-19 | Enhanced Grafana-style dashboard, real-time charts, disk breakdown |
| 1.5.0 | 2026-02-15 | RAID monitoring, backups, API keys |
| 1.4.0 | 2026-01-20 | Multi-channel notifications, alert rules |
| 1.3.0 | 2025-12-10 | Windows/Linux support, FastAPI migration |
| 1.2.0 | 2025-11-05 | Web dashboard, basic auth |
| 1.1.0 | 2025-10-15 | Metrics collection, CLI |
| 1.0.0 | 2025-09-01 | Initial release |

---

## Upcoming Features (Roadmap)

### v2.1.0 (Planned)
- [ ] Dark/Light theme toggle
- [ ] Real-time WebSocket updates
- [ ] Alert sounds and notifications
- [ ] Server groups and tags

### v2.2.0 (Planned)
- [ ] Public status page
- [ ] Custom dashboards
- [ ] Advanced reporting
- [ ] Multi-user support with roles

### v3.0.0 (Future)
- [ ] PostgreSQL support
- [ ] Clustering/HA
- [ ] Machine learning anomaly detection
- [ ] Mobile app

---

## Contributing

To contribute to PyMon:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update CHANGELOG.md
6. Submit a pull request

---

## Support

- **Issues**: https://github.com/ajjs1ajjs/Monitoring/issues
- **Discussions**: https://github.com/ajjs1ajjs/Monitoring/discussions
- **Documentation**: https://github.com/ajjs1ajjs/Monitoring/tree/main/docs
