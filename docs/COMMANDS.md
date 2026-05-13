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
# Через Task Scheduler: видалити задачу "PyMon"
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
export JWT_SECRET=ваш-секретний-ключ
export PYMON_ALLOWED_ORIGINS=http://localhost:10000
```

---

## 🔐 Authentication

```bash
# Змінити пароль адміна (через API)
curl -X POST http://localhost:10000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "chang3m3N0w!"}'

# Зміна пароля
curl -X PUT http://localhost:10000/api/v1/users/admin/password \
  -H "Content-Type: application/json" \
  -d '{"current_password": "oldpass", "new_password": "NewSecurePass789"}'
```

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

```bash
# Ручне копіювання БД
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
sudo systemctl stop pymon
sudo systemctl disable pymon
sudo rm /etc/systemd/system/pymon.service
sudo systemctl daemon-reload
sudo rm -rf /opt/pymon
sudo rm -rf /etc/pymon
sudo rm -rf /var/lib/pymon
```

### Windows
```powershell
$taskName = "PyMon"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
rm -r -Force C:\PyMon
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
