# Changelog

All notable changes to PyMon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
