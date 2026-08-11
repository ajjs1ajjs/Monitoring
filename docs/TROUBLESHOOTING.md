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
pymon server
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

Таблиці створюються автоматично при першому запуску сервера. Якщо БД пошкоджена — відновіть з резервної копії через API (`POST /api/v1/backup/restore`) або перейменуйте файл БД і перезапустіть.

---

## Аутентифікація

### Не можу увійти

```bash
# Пароль показується лише раз при першому запуску і автоматично видаляється
# після першого успішного входу (admin_password.txt). Якщо забули — скинути:
pymon reset-admin --config /etc/pymon/config.yml

# ...або задати конкретний пароль:
sudo PYMON_ADMIN_PASSWORD='NewStrongPass123' pymon reset-admin --config /etc/pymon/config.yml
```

### JWT помилка: `Invalid signature`

```bash
# JWT_SECRET змінився — потрібно залогінитись заново
# Встановити стабільний JWT_SECRET через env (файл .pymon_jwt_secret біля БД):
export JWT_SECRET="your-long-random-secret-here"
```

> ⚠️ Зміна `JWT_SECRET` також інвалідує розшифрування секретів нотифікацій,
> зашифрованих цим ключем (secret rotation вимагає повторного збереження налаштувань).

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
curl -X POST http://localhost:10000/api/v1/settings/config/import-prometheus \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"yaml_content": "<вміст prometheus.yml>"}'
```

---

## Docker

### Контейнер не стартує

```bash
docker compose logs pymon
# Переконатись що JWT_SECRET заданий:
docker compose run -e JWT_SECRET=test pymon pymon --version
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
# Секрети зберігаються зашифрованими у БД — після зміни JWT_SECRET перезбережіть їх
```

### Оновлення не застосовується

```bash
# Після git pull — перезібрати бінарник
go build -o pymon ./cmd/pymon
# та перезапустити службу
sudo systemctl restart pymon
```
