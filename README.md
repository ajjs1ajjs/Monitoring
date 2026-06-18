<div align="center">
  <h1>PyMon NOC</h1>
  <p><b>Enterprise Infrastructure Monitoring & NOC Dashboard</b></p>
  
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

  <img src="https://img.shields.io/badge/Статус-Production_Ready-success" alt="Production Ready">
</div>

---

**PyMon NOC** — це легка, швидка та сучасна платформа для моніторингу інфраструктури, розроблена для роботи в середовищах Linux та Windows. Система включає професійну панель керування (NOC Dashboard) у стилі Grafana, збір метрик у реальному часі та гнучку систему сповіщень.

## ✨ Основні можливості

- **Професійний NOC Dashboard**: Сучасний інтерфейс у темній темі з потоковою передачею метрик та індикаторами здоров'я.
- **Моніторинг сервісів**: Зовнішні перевірки HTTP/TCP (Blackbox) для моніторингу сайтів та API.
- **Міграція з Prometheus**: Імпорт існуючих конфігурацій `prometheus.yml` (сервери та сервіси) прямо в інтерфейсі.
- **Режим обслуговування (Maintenance)**: Відключення сповіщень для вузлів під час планових робіт.
- **Детекція аномалій**: Аналіз різких стрибків метрик (CPU/RAM) на основі історичних даних.
- **PWA (Progressive Web App)**: Встановлення на мобільний телефон як окремий додаток.
- **Звіти про здоров'я**: Генерація 24-годинних звітів із графіками у форматі PDF.

## 🚀 Швидке встановлення (Full Commands)

### 1. Встановлення сервера моніторингу

**Для Windows Server (PowerShell від Адміністратора):**
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iwr -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1' -OutFile 'install.ps1'; .\install.ps1 -Service
```

**Для Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

> **Security (v2.1.0+):** Пароль треба змінити після першого входу. Мінімум 12 символів з upper+lower+digit. `config.yml` тепер в `.gitignore` — не комітьте секрети в git!

> **Важливо:** На Windows проект працює як фонова служба (через Task Scheduler).

### 2. Розгортання агентів на серверах

**Windows Node (windows_exporter):**
```powershell
msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.6/windows_exporter-0.31.6-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system" /qn
```

**Linux Node (node_exporter):**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash
```

---

## 📚 Документація

| Документ | Опис |
|----------|------|
| **[docs/COMMANDS.md](docs/COMMANDS.md)** | Повний довідник команд (Linux + Windows) |
| **[docs/API.md](docs/API.md)** | REST API довідка (укр) / [English](docs/API.en.md) |
| **[docs/CHANGELOG.md](CHANGELOG.md)** | Журнал змін (укр) / [English](CHANGELOG.en.md) |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Усунення несправностей |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Архітектура проекту |
| **[docs/MIGRATION.md](docs/MIGRATION.md)** | Міграція з інших систем |

## 🔧 Basic Commands

### Linux
```bash
# Service
sudo systemctl start|stop|restart|status pymon
sudo journalctl -u pymon -f

# Deploy
sudo ./deploy.sh
sudo ./deploy.sh --remove

# Update (one-command, same as install)
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash

# Direct
python -m pymon.cli server --config config.yml

# Reset the admin password (prints a new random password ONCE)
python -m pymon.cli reset-admin
# ...or choose the password explicitly:
PYMON_ADMIN_PASSWORD='YourStrongPass123' python -m pymon.cli reset-admin
```

### Windows
```powershell
# Install
.\install.ps1
.\install.ps1 -Service

# Direct
python -m pymon.cli server

# Test
python -m pytest tests/ -v
```

### Docker
```bash
docker compose up -d
curl http://localhost:10000/api/v1/health
```

---

## 🛠️ Додаткова інформація

- **Доступ до панелі**: `http://<IP-адреса>:10000/dashboard/`
- **Логін за замовчуванням**: `admin` / `auto-generated` (ЗМІНИТИ ПІСЛЯ ВХОДУ!)
- **Конфігурація**: `config.yml` (в `.gitignore` — не комітити!)
- **База даних**: `pymon.db` (SQLite)
- **Пароль**: мін. 12 символів, upper+lower+digit

---

## 🔒 Безпека

- **Пароль адміна показується лише один раз** — при першому створенні або після `reset-admin`. Він **ніколи не зберігається у відкритому вигляді** (ні у файлі, ні в БД) — у базі лежить тільки bcrypt-хеш. Якщо пароль втрачено, виконайте `python -m pymon.cli reset-admin`.
- **Дефолтного пароля в коді немає.** Якщо `auth.admin_password` у `config.yml` порожній або слабкий, на першому запуску генерується сильний випадковий пароль (його можна задати через змінну `PYMON_ADMIN_PASSWORD`).
- **Керування інфраструктурою — лише для адмінів.** Створення/зміна/видалення серверів, бекапи (`/backup/*`), очищення журналів і метрик вимагають адмін-прав.
- **JWT-секрет** береться зі змінної `JWT_SECRET`; інакше зберігається у `.pymon_jwt_secret` (в `.gitignore`). Для продакшну задавайте `JWT_SECRET` явно, щоб токени переживали рестарт.
- **CORS** обмежується змінною `PYMON_ALLOWED_ORIGINS` (через кому). За замовчуванням — лише `localhost`.
- **Хост сервера** валідовується суворим whitelist-ом символів — жодних HTML/скрипт-навантажень; усі дані серверів/сервісів/журналів екрануються перед виводом у дашборді (захист від збереженого XSS).
