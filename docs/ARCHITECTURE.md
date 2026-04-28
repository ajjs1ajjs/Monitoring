Phase 3–4 Architecture Overview

- Overview
  - PyMon backend is a FastAPI service exposing REST APIs for monitoring data and control operations.
  - Data is stored in SQLite (default) with a Memory backend available for tests and small deployments. A future plan is PostgreSQL for scale.
  - The UI is a separate frontend integrated via Enhanced Dashboard (web_dashboard_enhanced.py). A legacy Dashboard Unified remains as a deprecated artifact.

- Key Components
  - API Layer (FastAPI)
    - Endpoints for servers, metrics history, exports, backups, alerts, and admin tasks.
    - History endpoints use a metrics_history table for time-series data.
  - Storage Layer
    - SQLiteStorage (async) for metrics history in prod-like usage.
    - MemoryStorage for tests or small-scale usage.
  - UI Layer
    - Enhanced Dashboard (web_dashboard_enhanced.py) – main UI.
    - Dashboard Unified (deprecated) – kept for historical reference and migration path.

- Data Flow
  - Collectors fetch metrics from exporters (node_exporter/windows_exporter/Telegraf) and push to metrics_history table via API endpoints and storage backends.
  - Frontend consumes API endpoints to render charts and dashboards (CPU/Memory/Disk/Network, uptime, disk breakdown, etc.).
  - Exports (CSV/JSON) provide data for reports.

- Security & Deployment
  - JWT-based authentication. Secrets via environment (JWT_SECRET) and possibly secret stores in future.
  - CORS configurable via PYMON_ALLOWED_ORIGINS.
  - Docker-based deployment via docker-compose and a multi-stage Dockerfile.

- Scaling Plan (Phase 4)
  - Move to PostgreSQL for persistency and scaling.
  - Fully asynchronous stack with asyncio-based storage adapters.
  - TLS termination behind an ingress, and secrets managed via CI/CD vault/secret manager.
