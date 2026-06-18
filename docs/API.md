# Документація API PyMon

Повна довідка REST API для PyMon Enterprise Server Monitoring.

**Базова URL:** `http://localhost:10000`

**Автентифікація:** Всі API ендпоінти (крім `/api/v1/auth/login`) вимагають JWT токен в заголовку:
```
Authorization: Bearer <your_token>
```

---

## Зміст

1. [Автентифікація](#автентифікація)
2. [Сервери](#сервери)
3. [Розширені API дашборду](#розширені-api-дашборду)
4. [Метрики](#метрики)
5. [Сповіщення](#сповіщення)
6. [Бекапи](#бекапи)
7. [Система](#система)

---

## Автентифікація

### Логін

Отримати JWT токен доступу.

**POST** `/api/v1/auth/login`

**Body:**
```json
{
    "username": "admin",
    "password": "<your-password>"
}
```

**Відповідь:**
```json
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "admin",
        "is_admin": true,
        "must_change_password": false
    }
}
```

### Зміна пароля

**POST** `/api/v1/auth/change-password`

**Body:**
```json
{
    "current_password": "oldpass",
    "new_password": "NewSecurePass123"
}
```

### API ключі

**Створення:** `POST /api/v1/auth/api-keys`
```json
{"name": "my-key"}
```

**Список:** `GET /api/v1/auth/api-keys`

### Користувачі

**Список:** `GET /api/v1/auth/users` (admin only)

**Створення:** `POST /api/v1/auth/users` (admin only)
```json
{"username": "user1", "password": "SecurePass123", "is_admin": false}
```

**Оновлення:** `PUT /api/v1/auth/users/{userId}` (admin only)

**Видалення:** `DELETE /api/v1/auth/users/{userId}` (admin only, крім admin)

**Поточний користувач:** `GET /api/v1/auth/me`

---

## Сервери

### Список серверів

**GET** `/api/v1/servers`

**Відповідь:**
```json
{
    "servers": [
        {
            "id": 1,
            "name": "Web Server 1",
            "host": "192.168.1.100",
            "agent_port": 9100,
            "os_type": "linux",
            "enabled": 1,
            "last_status": "up",
            "cpu_percent": 45.5,
            "memory_percent": 62.3,
            "disk_percent": 78.1
        }
    ]
}
```

### Створення сервера

**POST** `/api/v1/servers`

```json
{
    "name": "New Server",
    "host": "192.168.1.200",
    "os_type": "linux",
    "agent_port": 9100,
    "enabled": true,
    "server_group": "Production",
    "scrape_interval": 0
}
```

### Отримання сервера

**GET** `/api/v1/servers/{server_id}`

### Оновлення сервера

**PUT** `/api/v1/servers/{server_id}`

### Видалення сервера

**DELETE** `/api/v1/servers/{server_id}`

### Примусовий збір метрик

**POST** `/api/v1/servers/{server_id}/scrape`

### Режим обслуговування

**POST** `/api/v1/servers/{server_id}/maintenance`
```json
{"is_maintenance": true}
```

### Історія метрик

**GET** `/api/v1/servers/{server_id}/history?range=1h`

Параметри range: `5m`, `15m`, `1h`, `6h`, `12h`, `24h`, `3d`, `7d`, `15d`, `30d`

### Детальна історія

**GET** `/api/v1/servers/{server_id}/history-detail?range=1h`

### Дисковий breakdown

**GET** `/api/v1/servers/{server_id}/disk-breakdown`

### Uptime Timeline

**GET** `/api/v1/servers/{server_id}/uptime-timeline?days=7`

### Експорт

**GET** `/api/v1/servers/{server_id}/export?format=json&range=24h`
**GET** `/api/v1/servers/{server_id}/export?format=csv&range=24h`

### Експорт всіх серверів

**GET** `/api/v1/servers/export?format=json&range=24h`

### Порівняння

**GET** `/api/v1/servers/compare?metric=cpu&range=1h`

Параметри metric: `cpu`, `memory`, `disk`

### Загальна статистика

**GET** `/api/v1/servers/summary/all`

---

## Розширені API дашборду

### Агрегована історія (всі сервери)

**GET** `/api/v1/servers/history?range=1h&metric=cpu`

### Зведення сервера

**GET** `/api/v1/servers/{server_id}/summary`

---

## Метрики

### Відправити метрику

**POST** `/api/v1/metrics`

```json
{
    "name": "cpu_usage",
    "value": 45.2,
    "type": "gauge",
    "labels": [{"name": "host", "value": "server1"}],
    "help_text": "CPU usage percentage"
}
```

### Список метрик

**GET** `/api/v1/metrics`

### Тренд метрик

**GET** `/api/v1/metrics/trend?range=1h`

### Очистити історію

**DELETE** `/api/v1/metrics/history`

### Prometheus експорт

**GET** `/metrics`

---

## Сповіщення

### Список сповіщень

**GET** `/api/v1/alerts`

### Створення правила

**POST** `/api/v1/alerts`

```json
{
    "name": "High CPU",
    "metric": "cpu_percent",
    "condition": ">",
    "threshold": 90,
    "duration": 300,
    "severity": "critical",
    "server_id": 1,
    "description": "CPU above 90%"
}
```

### Видалення

**DELETE** `/api/v1/alerts/{alert_id}`

---

## Налаштування

### Отримати налаштування сповіщень

**GET** `/api/v1/settings/notifications`

### Зберегти налаштування

**POST** `/api/v1/settings/notifications`

### Тест сповіщення

**POST** `/api/v1/settings/notifications/test`

### Експорт конфігурації

**GET** `/api/v1/settings/config/export`

### Імпорт Prometheus

**POST** `/api/v1/settings/config/import-prometheus`

```json
{
    "yaml_content": "scrape_configs:\n  - job_name: 'node'\n    static_configs:\n      - targets: ['localhost:9100']"
}
```

---

## Сервіси

### Список

**GET** `/api/v1/services`

### Створення

**POST** `/api/v1/services`

```json
{
    "name": "My Website",
    "target_url": "https://example.com",
    "check_type": "http",
    "interval": 60,
    "timeout": 10
}
```

### Історія

**GET** `/api/v1/services/history?range=1h`

### Видалення

**DELETE** `/api/v1/services/{service_id}`

---

## Бекапи

### Список бекапів

**GET** `/api/v1/backup/list`

### Створення

**POST** `/api/v1/backup/create`

### Відновлення

**POST** `/api/v1/backup/restore`
```json
{"filename": "pymon_backup_20240101_120000.db"}
```

---

## Логи

### Аудит логи

**GET** `/api/v1/audit-log?limit=100&offset=0`

### Очистити аудит

**DELETE** `/api/v1/audit-log`

### Системні логи

**GET** `/api/v1/audit-log/system-logs?lines=200`

### Очистити системні логи

**DELETE** `/api/v1/audit-log/system-logs`

---

## Звіти

### Згенерувати звіт

**GET** `/api/v1/reports/server/{server_id}`

Повертає HTML звіт з графіками Chart.js.

---

## Здоров'я системи

**GET** `/api/v1/health`

```json
{"status": "healthy"}
```

---

## WebSocket

**ws** `/api/v1/ws/metrics`

Підключення для отримання оновлень метрик в реальному часі.

---

## Приклади використання

### Python

```python
import httpx

async with httpx.AsyncClient() as client:
    # Логін
    resp = await client.post("http://localhost:10000/api/v1/auth/login",
        json={"username": "admin", "password": "<your-password>"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Список серверів
    servers = await client.get("http://localhost:10000/api/v1/servers",
        headers=headers)
    print(servers.json())
```

### cURL

```bash
TOKEN=$(curl -s -X POST http://localhost:10000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password": "<your-password>"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:10000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN"
```
