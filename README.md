<div align="center">

# PyMon NOC

**Enterprise Infrastructure Monitoring & NOC Dashboard**

Легка, швидка та сучасна платформа моніторингу інфраструктури для Linux і Windows — з панеллю керування у стилі Grafana, збором метрик у реальному часі та гнучкими сповіщеннями.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Version](https://img.shields.io/badge/Version-2.2.0-orange.svg)](CHANGELOG.md)
![Status](https://img.shields.io/badge/Status-Production_Ready-success)

</div>

---

## 📑 Зміст

- [Основні можливості](#-основні-можливості)
- [Швидкий старт](#-швидкий-старт)
- [Розгортання агентів](#-розгортання-агентів)
- [Команди](#-команди)
- [Конфігурація та змінні середовища](#️-конфігурація-та-змінні-середовища)
- [Безпека](#-безпека)
- [Документація](#-документація)
- [Технології](#-технології)

---

## ✨ Основні можливості

- **Професійний NOC Dashboard** — сучасний інтерфейс у темній темі з потоковою передачею метрик (WebSocket) та індикаторами здоров'я.
- **Моніторинг серверів** — CPU, RAM, диски та мережа через `node_exporter` (Linux) і `windows_exporter` (Windows).
- **Моніторинг сервісів** — зовнішні перевірки HTTP / TCP / Ping / SSL (Blackbox) для сайтів та API.
- **Сповіщення** — Telegram, Discord, MS Teams, Slack, Email (SMTP) та generic webhook.
- **Міграція з Prometheus** — імпорт наявних `prometheus.yml` (сервери та сервіси) прямо в інтерфейсі.
- **Режим обслуговування** — тимчасове відключення сповіщень для вузлів під час планових робіт.
- **Детекція аномалій** — аналіз різких стрибків CPU/RAM на основі історичних даних.
- **Звіти про здоров'я** — генерація 24-годинних звітів із графіками (PDF через друк).
- **PWA** — встановлення дашборду на мобільний як окремий застосунок.

---

## 🚀 Швидкий старт

### 1. Сервер моніторингу

**Windows Server** (PowerShell від імені Адміністратора):
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iwr -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1' -OutFile 'install.ps1'; .\install.ps1 -Service
```

**Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

> 💡 Та сама команда працює і для встановлення, і для оновлення — просто запустіть її знову.
> На Windows проект працює як фонова служба через Task Scheduler (задача `PyMonServer`).

Після встановлення:

- **Дашборд:** `http://<IP>:10000/dashboard/`
- **Логін:** `admin`
- **Пароль:** генерується випадково і **показується лише один раз** в логах інсталяції / службі. Якщо втрачено — див. [Безпека](#-безпека).

### 2. Перевірка

```bash
curl http://localhost:10000/api/v1/health   # {"status":"healthy"}
```

---

## 📡 Розгортання агентів

**Windows Node** (`windows_exporter`):
```powershell
msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.6/windows_exporter-0.31.6-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system" /qn
```

**Linux Node** (`node_exporter`):
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash
```

Далі додайте вузол у дашборді (**Servers → Add**) або імпортуйте `prometheus.yml`.

---

## 🔧 Команди

### Linux (systemd)
```bash
# Керування службою
sudo systemctl start|stop|restart|status pymon
sudo journalctl -u pymon -f

# Розгортання / видалення служби
sudo ./deploy.sh [--user pymon] [--port 10000]
sudo ./deploy.sh --remove

# Оновлення (те саме, що й встановлення)
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash

# Прямий запуск
python -m pymon.cli server --config config.yml
```

### Windows
```powershell
.\install.ps1            # встановлення
.\install.ps1 -Service   # встановлення як фонова служба
python -m pymon.cli server   # прямий запуск у консолі
python -m pytest tests/ -v   # тести
```

### Скидання пароля адміна
```bash
# Згенерувати новий випадковий пароль (показується ОДИН раз)
python -m pymon.cli reset-admin

# ...або задати конкретний пароль
PYMON_ADMIN_PASSWORD='YourStrongPass123' python -m pymon.cli reset-admin
```
> На проді з systemd вкажіть конфіг, щоб команда знайшла живу БД:
> ```bash
> sudo -u <user> CONFIG_PATH=/etc/pymon/config.yml /opt/pymon/venv/bin/pymon reset-admin
> ```

### Docker
```bash
docker compose up -d
curl http://localhost:10000/api/v1/health
```

📖 Повний довідник — [docs/COMMANDS.md](docs/COMMANDS.md).

---

## ⚙️ Конфігурація та змінні середовища

Конфігурація — у `config.yml` (за зразком [`config.example.yml`](config.example.yml)). Файл `config.yml` у `.gitignore` — **не комітьте секрети в git**.

| Змінна | Призначення | За замовчуванням |
|--------|-------------|------------------|
| `JWT_SECRET` | Ключ підпису JWT (мін. 32 символи). Задавайте на проді, щоб токени переживали рестарт. | авто → `.pymon_jwt_secret` |
| `PYMON_ADMIN_PASSWORD` | Початковий/скидальний пароль адміна. | випадковий (показ один раз) |
| `CONFIG_PATH` | Шлях до конфіга. | `config.yml` |
| `DB_PATH` | Шлях до бази (перекриває конфіг). | з `config.yml` |
| `STORAGE_BACKEND` | Бекенд сховища: `sqlite` / `memory`. | `sqlite` |
| `PYMON_ALLOWED_ORIGINS` | Дозволені CORS-origin (через кому). **Ніколи не ставте `*`** разом із cookie-авторизацією. | `localhost:10000` |
| `PYMON_ALLOW_METADATA` | Дозволити скрейп cloud-метаданих (`169.254.169.254`). | `false` |
| `TLS_CERT` / `TLS_KEY` | Сертифікат і ключ для HTTPS. | вимкнено (HTTP) |

Повний приклад — [`.env.example`](.env.example).

---

## 🔒 Безпека

- **Пароль адміна показується лише один раз** — при першому створенні або після `reset-admin`. Він **ніколи не зберігається у відкритому вигляді** (ні у файлі, ні в БД) — у базі лежить тільки bcrypt-хеш. Втратили — виконайте `python -m pymon.cli reset-admin`.
- **Дефолтного пароля в коді немає.** За порожнього/слабкого значення в `config.yml` на першому запуску генерується сильний випадковий пароль (можна задати через `PYMON_ADMIN_PASSWORD`).
- **Керування інфраструктурою — лише для адмінів.** Створення/зміна/видалення серверів, бекапи (`/backup/*`), очищення журналів і метрик доступні тільки адмінам.
- **API-ключі — лише для інжесту/читання.** Будь-які адмін-дії через `X-API-Key` повертають `403`.
- **Захист від XSS** — усі дані серверів/сервісів/користувачів/журналів екрануються перед виводом; хост валідовується суворим whitelist-ом символів.
- **Захист від SSRF** — скрейп відмовляє на адреси cloud-метаданих (вимикач `PYMON_ALLOW_METADATA=true`); приватні LAN-діапазони лишаються дозволеними.
- **Політика пароля** — мінімум 12 символів, верхній + нижній регістр + цифра.

---

## 📚 Документація

| Документ | Опис |
|----------|------|
| [docs/COMMANDS.md](docs/COMMANDS.md) | Повний довідник команд (Linux + Windows) |
| [docs/API.md](docs/API.md) | REST API довідка (укр) · [English](docs/API.en.md) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архітектура проекту |
| [docs/MIGRATION.md](docs/MIGRATION.md) | Міграція з інших систем |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Усунення несправностей |
| [CHANGELOG.md](CHANGELOG.md) | Журнал змін (укр) · [English](CHANGELOG.en.md) |

---

## 🧩 Технології

**Бекенд:** Python 3.10+ · FastAPI · Uvicorn · SQLite (WAL) · httpx · bcrypt · PyJWT
**Фронтенд:** Vanilla JS · Chart.js · WebSocket · PWA
**Агенти:** Prometheus `node_exporter` / `windows_exporter`

---

<div align="center">
<sub>PyMon NOC · MIT License</sub>
</div>
