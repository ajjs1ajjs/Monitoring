# PyMon API Documentation

Complete API reference for PyMon Enterprise Server Monitoring.

**Base URL:** `http://localhost:8090`

**Authentication:** All API endpoints (except `/api/v1/auth/login`) require JWT token in header:
```
Authorization: Bearer <your_token>
```

---

## Table of Contents

1. [Authentication](#authentication)
2. [Servers](#servers)
3. [Enhanced Dashboard APIs](#enhanced-dashboard-apis)
4. [Metrics](#metrics)
5. [Alerts](#alerts)
6. [Backups](#backups)
7. [System](#system)

---

## Authentication

### Login

Get JWT access token.

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true,
    "must_change_password": true
  }
}
```

---

### Get Current User

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "is_admin": true,
  "must_change_password": false
}
```

---

### Change Password

**Endpoint:** `POST /api/v1/auth/change-password`

**Request:**
```json
{
  "current_password": "admin",
  "new_password": "NewSecure123"
}
```

---

### API Keys

Create and manage API keys for programmatic access.

**Create API Key:**
```bash
POST /api/v1/auth/api-keys
{
  "name": "Monitoring Script"
}
```

**Response:**
```json
{
  "api_key": "pymon_abc123xyz...",
  "name": "Monitoring Script"
}
```

**List API Keys:**
```bash
GET /api/v1/auth/api-keys
```

**Delete API Key:**
```bash
DELETE /api/v1/auth/api-keys/{key_id}
```

---

## Servers

### List All Servers

**Endpoint:** `GET /api/servers`

**Response:**
```json
{
  "servers": [
    {
      "id": 1,
      "name": "Production Web",
      "host": "192.168.1.100",
      "os_type": "linux",
      "agent_port": 9100,
      "last_status": "up",
      "cpu_percent": 45.2,
      "memory_percent": 62.5,
      "disk_percent": 78.3,
      "last_check": "2026-03-19T10:30:00"
    }
  ]
}
```

---

### Add Server

**Endpoint:** `POST /api/servers`

**Request:**
```json
{
  "name": "Production DB",
  "host": "192.168.1.101",
  "os_type": "windows",
  "agent_port": 9182
}
```

**Response:**
```json
{
  "id": 2,
  "message": "Server added"
}
```

---

### Get Server Details

**Endpoint:** `GET /api/servers/{server_id}`

**Response:**
```json
{
  "id": 1,
  "name": "Production Web",
  "host": "192.168.1.100",
  "os_type": "linux",
  "agent_port": 9100,
  "enabled": true,
  "last_status": "up",
  "cpu_percent": 45.2,
  "memory_percent": 62.5,
  "disk_percent": 78.3,
  "network_rx": 1024000,
  "network_tx": 512000,
  "last_check": "2026-03-19T10:30:00"
}
```

---

### Update Server

**Endpoint:** `PUT /api/servers/{server_id}`

**Request:**
```json
{
  "name": "Updated Server Name",
  "enabled": true
}
```

---

### Delete Server

**Endpoint:** `DELETE /api/servers/{server_id}`

**Response:**
```json
{
  "message": "Server deleted"
}
```

---

### Manual Scrape

Trigger immediate metrics collection.

**Endpoint:** `POST /api/servers/{server_id}/scrape`

**Response:**
```json
{
  "message": "Scrape triggered"
}
```

---

## Enhanced Dashboard APIs

### Get Historical Metrics

Get time-series data for charts.

**Endpoint:** `GET /api/servers/metrics-history`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_id` | int | null | Specific server ID (null = all servers aggregated) |
| `range` | string | "1h" | Time range: `5m`, `15m`, `1h`, `6h`, `24h`, `7d` |
| `metric` | string | null | Specific metric: `cpu`, `memory`, `disk`, `network` (null = all) |

**Example:**
```bash
GET /api/servers/metrics-history?range=1h&metric=cpu
```

**Response:**
```json
{
  "labels": ["10:00", "10:05", "10:10", "10:15", "10:20", "10:25"],
  "datasets": [
    {
      "label": "CPU",
      "data": [42.5, 45.2, 48.1, 43.7, 46.3, 44.9],
      "borderColor": "#73bf69",
      "backgroundColor": "rgba(115,191,105,0.2)",
      "fill": true,
      "tension": 0.3
    }
  ]
}
```

---

### Get Disk Breakdown

Get per-disk usage for a server (C:, D:, E: etc.).

**Endpoint:** `GET /api/servers/{server_id}/disk-breakdown`

**Example:**
```bash
GET /api/servers/1/disk-breakdown
```

**Response:**
```json
{
  "disks": [
    {
      "volume": "C:",
      "size": 536870912000,
      "size_gb": 500.0,
      "free": 134217728000,
      "free_gb": 125.0,
      "used_gb": 375.0,
      "percent": 75.0
    },
    {
      "volume": "D:",
      "size": 1099511627776,
      "size_gb": 1024.0,
      "free": 549755813888,
      "free_gb": 512.0,
      "used_gb": 512.0,
      "percent": 50.0
    }
  ]
}
```

---

### Get Uptime Timeline

Get server uptime/downtime timeline.

**Endpoint:** `GET /api/servers/{server_id}/uptime-timeline`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days (1-30) |

**Example:**
```bash
GET /api/servers/1/uptime-timeline?days=7
```

**Response:**
```json
{
  "timeline": [
    {"timestamp": "2026-03-12T10:00:00", "status": "up"},
    {"timestamp": "2026-03-13T15:30:00", "status": "down"},
    {"timestamp": "2026-03-13T16:00:00", "status": "up"},
    {"timestamp": "2026-03-19T10:00:00", "status": "up"}
  ],
  "uptime_percent": 99.5
}
```

---

### Export Server Data

Export metrics data as CSV or JSON.

**Endpoint:** `GET /api/servers/{server_id}/export`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "json" | Export format: `json`, `csv` |
| `range` | string | "24h" | Time range: `5m`, `15m`, `1h`, `6h`, `24h`, `7d` |

**Example (JSON):**
```bash
GET /api/servers/1/export?format=json&range=24h
```

**Response (JSON):**
```json
{
  "server_id": 1,
  "range": "24h",
  "data": [
    {
      "timestamp": "2026-03-18T10:00:00",
      "cpu_percent": 42.5,
      "memory_percent": 61.2,
      "disk_percent": 78.3,
      "network_rx_mb": 1024.5,
      "network_tx_mb": 512.3
    }
  ]
}
```

**Response (CSV):**
```csv
Timestamp,CPU %,Memory %,Disk %,Network RX (MB),Network TX (MB)
2026-03-18T10:00:00,42.5,61.2,78.3,1024.5,512.3
2026-03-18T10:15:00,45.2,62.5,78.5,1156.2,623.1
```

---

### Compare Time Ranges

Compare current period vs previous period with trend analysis.

**Endpoint:** `GET /api/servers/compare`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_id` | int | null | Specific server (null = all servers) |
| `metric` | string | "cpu" | Metric: `cpu`, `memory`, `disk`, `network` |
| `range` | string | "1h" | Time range: `5m`, `15m`, `1h`, `6h`, `24h`, `7d` |

**Example:**
```bash
GET /api/servers/compare?metric=cpu&range=1h
```

**Response:**
```json
{
  "current": 45.2,
  "previous": 42.1,
  "delta": 3.1,
  "delta_percent": 7.36,
  "trend": "up"
}
```

**Trend Values:**
- `up` - Metric increased
- `down` - Metric decreased
- `stable` - No significant change

---

## Metrics

### List All Metrics

**Endpoint:** `GET /api/v1/metrics`

**Response:**
```json
{
  "metrics": [
    {
      "name": "system_cpu_usage_percent",
      "type": "gauge",
      "value": 45.2,
      "labels": [{"name": "server", "value": "prod-01"}]
    }
  ]
}
```

---

### Ingest Metric

Push custom metrics.

**Endpoint:** `POST /api/v1/metrics`

**Request:**
```json
{
  "name": "custom_metric",
  "value": 123.45,
  "type": "gauge",
  "labels": [{"name": "server", "value": "prod-01"}],
  "help_text": "Custom metric description"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### Query Metrics

Query time-series data.

**Endpoint:** `GET /api/v1/query`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Metric name |
| `start` | datetime | Start time (ISO 8601) |
| `end` | datetime | End time (ISO 8601) |
| `step` | int | Step in seconds (default: 60) |

**Example:**
```bash
GET /api/v1/query?query=cpu&start=2026-03-19T09:00:00&end=2026-03-19T10:00:00&step=60
```

**Response:**
```json
{
  "query": "cpu",
  "result": [
    {"timestamp": "2026-03-19T09:00:00", "value": 42.5},
    {"timestamp": "2026-03-19T09:01:00", "value": 43.1}
  ]
}
```

---

### List Series Names

**Endpoint:** `GET /api/v1/series`

**Response:**
```json
{
  "series": ["cpu", "memory", "disk", "network_rx", "network_tx"]
}
```

---

## Alerts

### List Alerts

**Endpoint:** `GET /api/alerts`

**Response:**
```json
{
  "alerts": [
    {
      "id": 1,
      "name": "High CPU",
      "metric": "cpu",
      "condition": "greater_than",
      "threshold": 90,
      "severity": "critical",
      "enabled": true
    }
  ]
}
```

---

### Create Alert

**Endpoint:** `POST /api/alerts`

**Request:**
```json
{
  "name": "High CPU Usage",
  "metric": "cpu",
  "condition": "greater_than",
  "threshold": 90,
  "duration": 300,
  "severity": "critical",
  "notify_telegram": true,
  "notify_email": true,
  "enabled": true
}
```

---

### Update Alert

**Endpoint:** `PUT /api/alerts/{id}`

**Request:**
```json
{
  "threshold": 95,
  "enabled": false
}
```

---

### Delete Alert

**Endpoint:** `DELETE /api/alerts/{id}`

---

## Backups

### Get Backup Config

**Endpoint:** `GET /api/backup/config`

**Response:**
```json
{
  "auto": true,
  "time": "02:00",
  "path": "/backups",
  "keep_days": 30
}
```

---

### Update Backup Config

**Endpoint:** `POST /api/backup/config`

**Request:**
```json
{
  "auto": true,
  "time": "03:00",
  "path": "/backups",
  "keep_days": 60
}
```

---

### Create Backup

**Endpoint:** `POST /api/backup/create`

**Request:**
```json
{
  "path": "/backups"
}
```

**Response:**
```json
{
  "status": "ok",
  "file": "/backups/pymon_full_20260319.zip"
}
```

---

### Restore Backup

**Endpoint:** `POST /api/backup/restore`

**Request:**
```json
{
  "file": "/backups/pymon_full_20260319.zip",
  "restore_db": true,
  "restore_config": true,
  "restore_settings": true
}
```

---

### List Backups

**Endpoint:** `GET /api/backup/list`

**Response:**
```json
{
  "files": [
    {
      "filename": "pymon_full_20260319.zip",
      "size": 1048576,
      "created": "2026-03-19T02:00:00"
    }
  ]
}
```

---

### Delete Backup

**Endpoint:** `DELETE /api/backup/file`

**Request:**
```json
{
  "filename": "pymon_full_20260319.zip"
}
```

---

## System

### Health Check

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-19T10:30:00"
}
```

---

### Factory Reset

⚠️ **WARNING:** This will delete all data!

**Endpoint:** `POST /api/system/reset`

---

### Clear Metrics

**Endpoint:** `POST /api/system/clear-metrics`

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request body"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

### 404 Not Found
```json
{
  "detail": "Server not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message here"
}
```

---

## Rate Limiting

API requests are rate-limited to:
- **100 requests per minute** per IP address
- **1000 requests per hour** per user

Exceeding limits returns `429 Too Many Requests`.

---

## SDK Examples

### Python

```python
import requests

# Login
resp = requests.post('http://localhost:8090/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin'
})
token = resp.json()['access_token']

# Get servers
headers = {'Authorization': f'Bearer {token}'}
resp = requests.get('http://localhost:8090/api/servers', headers=headers)
servers = resp.json()['servers']

# Get metrics history
resp = requests.get(
    'http://localhost:8090/api/servers/metrics-history?range=1h&metric=cpu',
    headers=headers
)
metrics = resp.json()
```

### cURL

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# Get servers
curl -X GET http://localhost:8090/api/servers \
  -H "Authorization: Bearer $TOKEN"

# Get metrics history
curl -X GET "http://localhost:8090/api/servers/metrics-history?range=1h" \
  -H "Authorization: Bearer $TOKEN"
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

// Login
const { data } = await axios.post('http://localhost:8090/api/v1/auth/login', {
  username: 'admin',
  password: 'admin'
});
const token = data.access_token;

// Get servers
const servers = await axios.get('http://localhost:8090/api/servers', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get metrics history
const metrics = await axios.get(
  'http://localhost:8090/api/servers/metrics-history?range=1h',
  { headers: { 'Authorization': `Bearer ${token}` } }
);
```

---

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/ajjs1ajjs/Monitoring/issues
- **Discussions**: https://github.com/ajjs1ajjs/Monitoring/discussions
---

## Additional Endpoints (Phase 2.8+)

- Export All Servers
  - Endpoint: GET /servers/export
  - Query params: format=json|csv, range=5m|15m|1h|6h|24h|7d
  - Description: Exports metrics for all servers aggregated into a list per server. Returns JSON or CSV attachment.

- Aggregate Metrics History (All Servers)
  - Endpoint: GET /servers/metrics/history
  - Query params: range=5m|15m|1h|6h|24h|7d, metric (cpu|memory|disk|network) optional
  - Description: Returns aggregated history data across all servers. If metric is provided, returns series per metric; else returns per-server histories for CPU/Memory/Disk/Network.

- Server Summary (All Servers)
  - Endpoint: GET /servers/summary
  - Description: Returns a high-level summary across all monitored servers: total, online, offline, avg_cpu, avg_memory, avg_disk.

- Micro Endpoints for Admin/Backups
  - GET /backup/list: List available backups
  - POST /backup/create: Create a new backup (zip)

- Admin Events
  - GET /servers/{server_id}/events: Recent audit events for a server
