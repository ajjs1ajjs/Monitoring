# PyMon - Python Monitoring System

**Open-source альтернатива Prometheus + Grafana на чистому Python**

## Можливості

- **Збір метрик** - Counter, Gauge, Histogram (як Prometheus)
- **Scrape Manager** - Автоматичний збір з targets (Prometheus-style YAML config)
- **Часові ряди** - In-memory та SQLite зберігання
- **Візуалізація** - Web Dashboard з графіками (як Grafana)
- **REST API** - Повний API для інтеграції
- **Алертинг** - Правила та сповіщення
- **Авторизація** - JWT + API Keys
- **Prometheus-сумісність** - Експорт у форматі Prometheus

## Швидкий старт

### Linux (curl)

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

### Docker

```bash
docker run -d -p 8090:8090 \
  -v pymon-data:/data \
  -v pymon-config:/config \
  -e JWT_SECRET=your-secret-key \
  ghcr.io/ajjs1ajjs/Monitoring:latest
```

### pip

```bash
pip install pymon
pymon server --port 8090
```

## Доступ

Після встановлення:
- **URL**: http://your-server:8090
- **Dashboard**: http://your-server:8090/dashboard/
- **API**: http://your-server:8090/api/v1/
- **Prometheus Export**: http://your-server:8090/metrics

**Default credentials**: `admin` / `admin` (змініть після першого входу!)

## Конфігурація

Файл: `/etc/pymon/config.yml`

```yaml
# Server settings
server:
  port: 8090
  host: 0.0.0.0
  domain: your-server

# Storage
storage:
  backend: sqlite
  path: /var/lib/pymon/pymon.db
  retention_hours: 168

# Authentication
auth:
  admin_username: admin
  admin_password: admin
  jwt_expire_hours: 24

# Scrape configuration (Prometheus-style)
scrape_configs:
  - job_name: pymon_self
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets:
          - localhost:8090
        labels:
          env: production

  - job_name: web_services
    scrape_interval: 30s
    static_configs:
      - targets:
          - https://example.com
          - https://api.example.com/health
        labels:
          type: http

# Alerting rules
alerting:
  enabled: true
  evaluation_interval: 30s
  rules:
    - name: HighCPU
      expr: system_cpu_usage_percent
      threshold: 80
      duration: 60s
      severity: warning
      message: "CPU usage is {{ value }}%"

# Backup
backup:
  enabled: true
  max_backups: 10
  backup_dir: /etc/pymon/backups
```

### Зміна конфігурації

```bash
# Редагування конфігу
sudo nano /etc/pymon/config.yml

# Перезапуск після змін
sudo systemctl restart pymon

# Або використання скрипта
sudo /opt/pymon/scripts/config.sh --list
sudo /opt/pymon/scripts/config.sh --get server.port
sudo /opt/pymon/scripts/config.sh --set server.port 9000
```

## API

### Авторизація

```bash
# Отримати токен
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Використання токену
curl http://localhost:8090/api/v1/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Метрики

```bash
# Надіслати метрику
curl -X POST http://localhost:8090/api/v1/metrics \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "http_requests_total",
    "value": 42,
    "type": "counter",
    "labels": [{"name": "method", "value": "GET"}],
    "help_text": "Total HTTP requests"
  }'

# Запит даних
curl "http://localhost:8090/api/v1/query?query=http_requests_total" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### API Keys

```bash
# Створити API ключ
curl -X POST http://localhost:8090/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'

# Використання API ключа
curl http://localhost:8090/api/v1/metrics \
  -H "X-API-Key: pymon_YOUR_API_KEY"
```

## Python SDK

```python
from pymon.client import PyMonClient

async with PyMonClient("http://localhost:8090") as client:
    # Авторизація
    await client.login("admin", "admin")
    
    # Надіслати метрику
    await client.push(
        "requests_total", 
        42, 
        labels={"service": "api", "env": "prod"}
    )
    
    # Запит даних
    data = await client.query("requests_total", hours=1)
    
    # Створити API ключ
    api_key = await client.create_api_key("my-service")
```

### Локальне використання

```python
from pymon.metrics.collector import Counter, Gauge, Histogram
from pymon.metrics.models import Label

# Створення метрик
requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labels=[Label("method", "GET")]
)

memory_usage = Gauge("memory_bytes", "Memory usage in bytes")
request_duration = Histogram("request_duration_seconds", "Request duration")

# Використання
requests_total.inc()
memory_usage.set(1024 * 1024 * 100)
request_duration.observe(0.15)

# Prometheus експорт
print(requests_total.registry.export_prometheus())
```

## Керування сервісом

```bash
# Статус
sudo systemctl status pymon

# Перезапуск
sudo systemctl restart pymon

# Зупинка
sudo systemctl stop pymon

# Логи
sudo journalctl -u pymon -f

# Оновлення
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/update.sh | sudo bash
```

## Docker Compose

```yaml
version: '3.8'
services:
  pymon:
    image: ghcr.io/ajjs1ajjs/Monitoring:latest
    ports:
      - "8090:8090"
    volumes:
      - pymon-data:/data
      - pymon-config:/config
    environment:
      - JWT_SECRET=your-secret-key-change-me
    restart: unless-stopped

volumes:
  pymon-data:
  pymon-config:
```

## Ліцензія

MIT License
