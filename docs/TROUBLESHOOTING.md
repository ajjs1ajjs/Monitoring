# 🛠️ Усунення несправностей PyMon NOC

---

## Служба не запускається

```bash
# Linux
sudo systemctl status pymon
sudo journalctl -u pymon -n 50 --no-pager

# Windows
# Перевірити Task Scheduler → PyMon
# Або запустити вручну:
python -m pymon.cli server
```

### Помилка: `Port 10000 already in use`

```bash
# Знайти процес
sudo lsof -i :10000    # Linux
netstat -ano | findstr :10000  # Windows

# Зупинити
sudo kill -9 <PID>
# Або змінити порт в config.yml:
# server.port: 10001
```

---

## База даних

### Помилка: `database is locked`

```bash
# Переконатись що тільки один процес використовує БД
ps aux | grep pymon   # Linux
# Або перезапустити службу
sudo systemctl restart pymon
```

### Помилка: `no such table`

```bash
# Ініціалізувати таблиці
python -c "
from pymon.auth import init_auth_tables
from pymon.storage import init_storage
from pymon.database import init_database
init_storage()
init_auth_tables()
init_database()
print('Tables created')
"
```

---

## Аутентифікація

### Не можу увійти

```bash
# Пароль показується лише раз при першому запуску і НЕ зберігається у відкритому
# вигляді. Якщо забули — згенерувати новий випадковий (буде показано один раз):
python -m pymon.cli reset-admin

# ...або задати конкретний пароль:
PYMON_ADMIN_PASSWORD='NewStrongPass123' python -m pymon.cli reset-admin
```

### JWT помилка: `Invalid signature`

```bash
# JWT_SECRET змінився — потрібно залогінитись заново
# Встановити стабільний JWT_SECRET в .env:
echo "JWT_SECRET=your-secure-key-here" > .env
```

---

## Агенти / Збір метрик

### Метрики не збираються

```bash
# Перевірити доступність агента
curl http://IP_СЕРВЕРА:9100/metrics  # Linux (node_exporter)
curl http://IP_СЕРВЕРА:9182/metrics  # Windows (windows_exporter)

# Перевірити config.yml:
# scrape_configs:
#   - job_name: pymon_self
#     scrape_interval: 15s
```

### prometheus.yml імпорт не працює

```bash
# Переконатись що файл існує та має правильний формат
python -c "import yaml; yaml.safe_load(open('prometheus.yml')); print('OK')"
```

---

## Docker

### Контейнер не стартує

```bash
docker compose logs pymon
# Переконатись що JWT_SECRET заданий:
docker compose run -e JWT_SECRET=test pymon python -c "import os; print(os.getenv('JWT_SECRET'))"
```

---

## Network

### Немає доступу до dashboard

```bash
# Перевірити чи слухає порт
sudo ss -tulpn | grep 10000   # Linux
netstat -ano | findstr :10000  # Windows

# Перевірити firewall
sudo ufw status
sudo ufw allow 10000/tcp
```

---

## Інше

### Сповіщення не приходять

```bash
# Перевірити налаштування в розділі Settings → Notifications
# Переконатись що токени/вебхуки правильні
# Перевірити формат: webhook має починатись з https://
```

### Оновлення не застосовується

```bash
# Після git pull — оновити залежності
pip install -r requirements.txt -U

# Очистити кеш
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```
