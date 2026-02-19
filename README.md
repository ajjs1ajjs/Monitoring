# PyMon - Python Monitoring System

**Open-source альтернатива Prometheus + Grafana на чистому Python**

## Можливості

- **Збір метрик** - Counter, Gauge, Histogram (як Prometheus)
- **Часові ряди** - In-memory та SQLite зберігання
- **Візуалізація** - Web Dashboard з графіками (як Grafana)
- **REST API** - Повний API для інтеграції
- **Алертинг** - Правила та сповіщення
- **Авторизація** - JWT + API Keys
- **Prometheus-сумісність** - Експорт у форматі Prometheus

## Швидкий старт

### Linux (curl)

```bash
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Project2/main/install.sh | sudo bash
```

### Docker

```bash
docker run -d -p 8000:8000 \
  -v pymon-data:/data \
  -v pymon-config:/config \
  -e JWT_SECRET=your-secret-key \
  ghcr.io/ajjs1ajjs/Project2:latest
```

### pip

```bash
pip install pymon
pymon server --port 8000
```

## Доступ

Після встановлення:
- **URL**: http://your-server:8000
- **Dashboard**: http://your-server:8000/dashboard/
- **API**: http://your-server:8000/api/v1/
- **Prometheus Export**: http://your-server:8000/metrics

**Default credentials**: `admin` / `admin` (змініть після першого входу!)

## API

### Авторизація

```bash
# Отримати токен
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Використання токену
curl http://localhost:8000/api/v1/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Метрики

```bash
# Надіслати метрику
curl -X POST http://localhost:8000/api/v1/metrics \
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
curl "http://localhost:8000/api/v1/query?query=http_requests_total" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### API Keys

```bash
# Створити API ключ
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'

# Використання API ключа
curl http://localhost:8000/api/v1/metrics \
  -H "X-API-Key: pymon_YOUR_API_KEY"
```

## Python SDK

```python
from pymon.client import PyMonClient

async with PyMonClient("http://localhost:8000") as client:
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

# Логи
sudo journalctl -u pymon -f

# Оновлення
curl -fsSL https://raw.githubusercontent.com/ajjs1ajjs/Project2/main/update.sh | sudo bash
```

## Конфігурація

Файл: `/etc/pymon/config.json`

```json
{
  "server": {
    "port": 8000,
    "host": "0.0.0.0"
  },
  "storage": {
    "backend": "sqlite",
    "path": "/var/lib/pymon/pymon.db"
  },
  "auth": {
    "admin_username": "admin",
    "admin_password": "admin",
    "jwt_expire_hours": 24
  },
  "retention_hours": 168
}
```

## Docker Compose

```yaml
version: '3.8'
services:
  pymon:
    image: ghcr.io/ajjs1ajjs/Project2:latest
    ports:
      - "8000:8000"
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
