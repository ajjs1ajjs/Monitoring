# 📋 Довідник команд PyMon NOC

Повний список команд для керування PyMon NOC.

---

## 🔧 Service Management (Linux systemd)

```bash
# Встановлення служби
sudo ./deploy.sh

# Або вручну:
sudo ./deploy.sh --user pymon --port 10000

# Управління
sudo systemctl start pymon
sudo systemctl stop pymon
sudo systemctl restart pymon
sudo systemctl status pymon

# Логи
sudo journalctl -u pymon -f
sudo journalctl -u pymon -n 100 --no-pager

# Видалення служби
sudo ./deploy.sh --remove
```

---

## 🪟 Service Management (Windows)

```powershell
# Встановлення служби (через Task Scheduler)
.\install.ps1 -Service

# Або вручну:
.\install.ps1

# Запуск в консолі (для тестування)
python -m pymon.cli server

# Зупинка
# Через Task Scheduler або Ctrl+C в консолі

# Видалення
# Через Task Scheduler: видалити задачу "PyMonServer"
```

---

## 📦 Update (Оновлення)

### Linux
```bash
sudo ./update.sh
```

### Windows
```powershell
# Зупинити, оновити код, запустити
cd \шлях\до\Monitoring
git pull
python -m pymon.cli server
```

---

## 🎯 Direct Run (без служби)

### Linux
```bash
# З віртуальним оточенням
cd /opt/pymon
./venv/bin/python -m pymon.cli server

# Без venv
python -m pymon.cli server --config config.yml
```

### Windows
```powershell
python -m pymon.cli server
```

---

## ⚙️ Configuration

```bash
# Редагувати конфіг
sudo nano /etc/pymon/config.yml
# або: config.yml в директорії проекту

# Перевірити синтаксис
python -c "import yaml; yaml.safe_load(open('config.yml')); print('OK')"

# Використати кастомний шлях
python -m pymon.cli server --config /шлях/до/config.yml

# Змінні середовища:
export CONFIG_PATH=/etc/pymon/config.yml
export JWT_SECRET=ваш-секретний-ключ-мін-32-символи
export PYMON_ALLOWED_ORIGINS=http://localhost:10000
export PYMON_ADMIN_PASSWORD=ВашСильнийПароль123   # необов'язково
export PYMON_ALLOW_METADATA=false                 # SSRF-захист (cloud metadata)
```

---

## 🔐 Authentication

```bash
# Отримати токен (через API)
curl -X POST http://localhost:10000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<ваш-пароль>"}'

# Зміна пароля (мін. 12 символів, upper+lower+digit)
curl -X POST http://localhost:10000/api/v1/auth/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"current_password": "oldpass", "new_password": "NewSecurePass789"}'
```

---

## 🔑 Скидання пароля адміна

Пароль показується **лише один раз** при створенні і ніколи не зберігається у
відкритому вигляді. Якщо його втрачено — згенеруйте новий:

```bash
# Локально (БД у поточній директорії або через DB_PATH)
python -m pymon.cli reset-admin

# Задати конкретний пароль
PYMON_ADMIN_PASSWORD='NewStrongPass123' python -m pymon.cli reset-admin

# На проді (systemd) — вказати конфіг, щоб знайти живу БД
sudo -u <user> CONFIG_PATH=/etc/pymon/config.yml /opt/pymon/venv/bin/pymon reset-admin
```

> Перезапуск служби не потрібен — користувачі читаються з БД на кожен запит.

### API-ключі

API-ключі (заголовок `X-API-Key`) призначені **лише для інжесту метрик та
читання** — адмін-дії через них заборонені (повертають `403`). Створення/перегляд
ключів — через `POST/GET /api/v1/auth/api-keys` (потрібен JWT-логін).

---

## 📊 API

Повний API reference: [docs/API.md](API.md)

```bash
# Health check
curl http://localhost:10000/api/v1/health

# Список серверів
curl http://localhost:10000/api/v1/servers

# Метрики
curl http://localhost:10000/api/v1/metrics

# Prometheus сумісний endpoint
curl http://localhost:10000/metrics
```

---

## 🔄 Backup

Автоматичні бекапи виконуються за розкладом `backup.schedule` (cron) з `config.yml`.
Керувати можна і з дашборду (**Settings → Backup**) або через API:

```bash
# Створити бекап (адмін)
curl -X POST http://localhost:10000/api/v1/backup/create \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# Список бекапів
curl http://localhost:10000/api/v1/backup/list -H "Authorization: Bearer <ADMIN_TOKEN>"

# Відновлення (безпечно: онлайн-backup API SQLite, без зупинки служби)
curl -X POST http://localhost:10000/api/v1/backup/restore \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"filename": "pymon_backup_20260101_020000.db"}'
```

```bash
# Ручне копіювання БД (служба може бути запущена — SQLite у WAL-режимі)
cp /var/lib/pymon/pymon.db /backup/pymon-$(date +%Y%m%d).db

# Через скрипт
sudo ./scripts/backup.sh
```

---

## 🧪 Tests

```bash
# Всі тести
python -m pytest tests/ -v

# Конкретний модуль
python -m pytest tests/test_auth.py -v

# З coverage
python -m pytest tests/ --cov=pymon --cov-report=html
```

---

## 🐳 Docker

```bash
# Збірка
docker build -t pymon .

# Запуск
docker compose up -d

# Перевірка
curl http://localhost:10000/api/v1/health

# Логи
docker compose logs -f
```

---

## 🧹 Cleanup / Видалення

### Linux (повне видалення)
```bash
# 1. Backup (якщо треба зберегти дані)
sudo cp /var/lib/pymon/pymon.db /tmp/pymon.db.backup
sudo cp /etc/pymon/config.yml /tmp/config.yml.backup

# 2. Зупинити та вимкнути службу
sudo systemctl stop pymon
sudo systemctl disable pymon

# 3. Видалити файли служби
sudo rm /etc/systemd/system/pymon.service
sudo systemctl daemon-reload

# 4. Видалити проект та дані
sudo rm -rf /opt/pymon
sudo rm -rf /etc/pymon
sudo rm -rf /var/lib/pymon

# 5. Видалити користувача
sudo userdel -r pymon 2>/dev/null || true

# 6. Перевірка
sudo systemctl status pymon 2>/dev/null && echo "⚠ Ще існує" || echo "✓ Видалено"
```

### Windows (повне видалення)
```powershell
# 1. Backup (якщо треба зберегти дані)
Copy-Item C:\pymon\pymon.db C:\pymon.db.backup -Force 2>$null
Copy-Item C:\pymon\config.yml C:\config.yml.backup -Force 2>$null

# 2. Зупинити задачу в планувальнику
Stop-ScheduledTask -TaskName "PyMonServer" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# 3. Вбити всі Python процеси що можуть блокувати файли
Get-Process python* | ForEach-Object { $_.Kill() } 2>$null
Get-Process python3* | ForEach-Object { $_.Kill() } 2>$null
Start-Sleep -Seconds 2

# 4. Видалити задачу з планувальника
Unregister-ScheduledTask -TaskName "PyMonServer" -Confirm:$false 2>$null

# 5. Видалити папку проекту
rm -r -Force C:\pymon

# 6. Перевірка
if (-not (Test-Path C:\pymon)) { Write-Host "✓ Видалено" -ForegroundColor Green }
```

---

## 📍 Шляхи до файлів

| Компонент | Linux | Windows |
|-----------|-------|---------|
| Конфігурація | `/etc/pymon/config.yml` або `config.yml` | `config.yml` в директорії |
| База даних | `/var/lib/pymon/pymon.db` | `pymon.db` в директорії |
| Логи | `journalctl -u pymon` | `logs/` в директорії |
| Служба | `/etc/systemd/system/pymon.service` | Task Scheduler |
| Скрипти | `/opt/pymon/scripts/` | `scripts/` |
