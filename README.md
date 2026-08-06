<div align="center">

# PyMon NOC

**Enterprise Infrastructure Monitoring & NOC Dashboard**

Легка, швидка та сучасна платформа моніторингу інфраструктури для Linux і Windows — з панеллю керування у стилі Grafana, збором метрик у реальному часі та гнучкими сповіщеннями.

[![Go 1.25](https://img.shields.io/badge/Go-1.25-blue.svg)](https://go.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Version](https://img.shields.io/badge/Version-3.0.0-orange.svg)](CHANGELOG.md)
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
- **Сповіщення** — Telegram, Discord, MS Teams, Slack, Email (SMTP).
- **Міграція з Prometheus** — імпорт наявних `prometheus.yml` (сервери та сервіси) прямо в інтерфейсі.
- **Режим обслуговування** — тимчасове відключення сповіщень для вузлів під час планових робіт.
- **Alerting rules** — гнучкі правила на CPU/RAM/диск з дебаунсингом за тривалістю.
- **Звіти про здоров'я** — генерація 24-годинних звітів із графіками (PDF через друк).
- **Бекапи** — автоматичні за розкладом (cron) та ручні, з відновленням.
- **PWA** — встановлення дашборду на мобільний як окремий застосунок.

---

## 🚀 Швидкий старт

### 1. Сервер моніторингу

**Windows** (PowerShell):
```powershell
iwr https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1 -OutFile install.ps1; .\install.ps1
```
Або збірка з сирців:
```powershell
.\install.ps1          # тепер качає готовий бінарник з GitHub Releases
.\run.bat --port 10000 # або для запуску з сирців
```

**Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

Після встановлення:

- **Дашборд:** `http://<IP>:10000/dashboard/`
- **Логін:** `admin`

### 🗝️ Перший вхід (пароль адміна)

При встановленні скрипт **завжди** задає відомий пароль адміна і друкує його прямо у висновку:

```
ADMIN LOGIN:
  Username: admin
  Password: <згенерований>
```

Пароль також зберігається одноразово у `$DATA_DIR/admin_password.txt` (права 0600):
```bash
sudo cat /var/lib/pymon/admin_password.txt
sudo rm /var/lib/pymon/admin_password.txt    # видаліть після входу
```

**Втратили пароль або хочете свій** — скиньте:
```bash
sudo PYMON_ADMIN_PASSWORD='YourStrongPass123' /opt/pymon/pymon reset-admin --config /etc/pymon/config.yml
sudo systemctl restart pymon
# Логін: admin / YourStrongPass123
```

> 💡 При першому вході дашборд попросить **змінити пароль** перед використанням (це стандартний flow `must_change_password`). Після зміни — інтерфейс повністю активний.

### 2. Перевірка

```bash
curl http://localhost:10000/api/v1/health   # {"status":"ok"}
```

---

## 📡 Розгортання агентів

**Windows Node** (`windows_exporter`):
```powershell
msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.6/windows_exporter-0.31.6-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system" /qn
```

**Linux Node** (`node_exporter`):
```bash
curl -sSL https://github.com/prometheus/node_exporter/releases/latest/download/node_exporter-*.linux-amd64.tar.gz -o ne.tar.gz
tar xzf ne.tar.gz && ./node_exporter/node_exporter &
```

Далі додайте вузол у дашборді (**Servers → Add**) або імпортуйте `prometheus.yml`.

---

## 🔧 Команди

### Linux (systemd)
```bash
sudo systemctl start|stop|restart|status pymon
sudo journalctl -u pymon -f

# Прямий запуск з сирців
./run.sh --port 10000
```

### Windows
```powershell
.\install.ps1     # завантаження готового бінарника (не потребує Go)
.\run.bat         # запуск з сирців (для розробки)
```

### Скидання пароля адміна
```bash
# Згенерувати новий випадковий пароль (показується ОДИН раз)
pymon reset-admin

# ...або задати конкретний пароль
PYMON_ADMIN_PASSWORD='YourStrongPass123' pymon reset-admin
```

### Docker
```bash
docker compose up -d
curl http://localhost:10000/api/v1/health
```

---

## ⚙️ Конфігурація та змінні середовища

Конфігурація — у `config.yml` (за зразком [`config.example.yml`](config.example.yml)). Файл `config.yml` у `.gitignore` — **не комітьте секрети в git**.

| Змінна | Призначення | За замовчуванням |
|--------|-------------|------------------|
| `JWT_SECRET` | Ключ підпису JWT (мін. 32 символи). Задавайте на проді, щоб токени переживали рестарт. | авто → `.pymon_jwt_secret` |
| `PYMON_ADMIN_PASSWORD` | Початковий/скидальний пароль адміна. | випадковий (показ один раз) |
| `CONFIG_PATH` | Шлях до конфіга. | `config.yml` |
| `DB_PATH` | Шлях до бази (перекриває конфіг). | з `config.yml` |
| `DATA_DIR` / `LOG_DIR` | Директорії даних і логів. | `.` |
| `PYMON_ALLOW_METADATA` | Дозволити скрейп cloud-метаданих (`169.254.169.254`). | `false` |

Повний приклад — [`.env.example`](.env.example).

---

## 🔒 Безпека

- **Пароль адміна показується лише один раз** — при першому створенні або після `reset-admin`. Він **ніколи не зберігається у відкритому вигляді** — у базі лежить тільки bcrypt-хеш. Втратили — виконайте `pymon reset-admin`.
- **Дефолтного пароля в коді немає.** За порожнього/слабкого значення в `config.yml` на першому запуску генерується сильний випадковий пароль (можна задати через `PYMON_ADMIN_PASSWORD`).
- **Керування інфраструктурою — лише для адмінів.** Створення/зміна/видалення серверів, бекапи (`/backup/*`), очищення журналів і метрик доступні тільки адмінам.
- **API-ключі — лише для інжесту/читання.** Будь-які адмін-дії через `X-API-Key` повертають `403`.
- **Захист від XSS** — усі дані екрануються; хост валідовується суворим whitelist-ом символів.
- **Захист від SSRF** — скрейп відмовляє на адреси cloud-метаданих (вимикач `PYMON_ALLOW_METADATA=true`); приватні LAN-діапазони лишаються дозволеними.
- **Політика пароля** — мінімум 12 символів, верхній + нижній регістр + цифра.

---

## 📚 Документація

| Документ | Опис |
|----------|------|
| [docs/API.md](docs/API.md) | REST API довідка |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архітектура проекту |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Усунення несправностей |
| [CHANGELOG.md](CHANGELOG.md) | Журнал змін |
| [MIGRATION_PLAN.md](MIGRATION_PLAN.md) | План міграції Python → Go |

---

## 🧩 Технології

**Бекенд:** Go 1.25 · net/http · SQLite (WAL, modernc.org/sqlite) · gorilla/websocket · golang-jwt · prometheus/common
**Фронтенд:** Vanilla JS · Chart.js · WebSocket · PWA (embedded через `go:embed`)
**Агенти:** Prometheus `node_exporter` / `windows_exporter`

---

<div align="center">
<sub>PyMon NOC · MIT License</sub>
</div>
