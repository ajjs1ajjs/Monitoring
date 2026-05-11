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

- **Професійний NOC Dashboard**: Сучасний інтерфейс у темній темі з потоковою передачею метрик, індикаторами здоров'я та зручним керуванням вузлами.
- **Моніторинг сервісів**: Зовнішні перевірки HTTP/TCP для моніторингу сайтів та баз даних без необхідності встановлення агентів.
- **Історія та Аналітика**: Зберігання історичних даних про затримки сервісів та продуктивність серверів.
- **Режим обслуговування (Maintenance)**: Відключення сповіщень для вузлів одним кліком під час планових робіт.
- **Детекція аномалій**: Інтелектуальний аналіз різких стрибків метрик (CPU/RAM) на основі історичних трендів.
- **PWA (Progressive Web App)**: Встановлюйте PyMon на мобільний телефон як окремий додаток із доступом з головного екрана.
- **Захист від "брязкання" (Flapping)**: Розумна логіка сповіщень, яка запобігає спаму повідомленнями при нестабільному з'єднанні.
- **Звіти про здоров'я**: Генерація професійних 24-годинних звітів із графіками трендів у форматі PDF.
- **Міграція з Prometheus**: Можливість імпорту існуючих конфігурацій `prometheus.yml` безпосередньо через інтерфейс.

## 🚀 Швидкий старт

### Встановлення сервера моніторингу

**Для Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash
```

**Для Windows Server (PowerShell від Адміністратора):**
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1')) -Service
```
*Використання прапорця `-Service` на Windows обов'язкове для роботи PyMon у фоновому режимі як системної служби.*

Після встановлення панель буде доступна за адресою: `http://<IP-адреса>:10000/dashboard/`  
**Логін за замовчуванням:** `admin` / `changeme` *(Обов'язково змініть пароль після першого входу!)*

### Розгортання агентів на цільових вузлах

PyMon використовує стандартні експортери Prometheus. Ви можете легко встановити їх:

**Linux Node (node_exporter):**
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash
```

**Windows Node (windows_exporter):**
```powershell
msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.6/windows_exporter-0.31.6-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system" /qn
```

## 🛠️ Ручне встановлення та розробка

```bash
# Клонування репозиторію
git clone https://github.com/ajjs1ajjs/Monitoring.git
cd Monitoring

# Створення та активація віртуального середовища
python -m venv .venv
# На Linux:
source .venv/bin/activate
# На Windows:
.venv\Scripts\activate

# Встановлення залежностей
pip install -e .

# Запуск сервера
pymon server
```

## ⚙️ Конфігурація

PyMon використовує файл `config.yml` у кореневій директорії. Ви можете налаштувати:
- **Server**: Порт, хост та домен.
- **Storage**: SQLite (за замовчуванням) або PostgreSQL для великих інсталяцій.
- **Auth**: Час дії JWT токенів та секрети.
- **Scraping**: Інтервали збору даних та таймаути.

## 📚 Документація

Детальну інформацію можна знайти в папці `docs/`:
- [API Reference](docs/API.md)
- [Огляд архітектури](docs/ARCHITECTURE.md)
- [Керівництво з міграції БД](docs/MIGRATION.md)

## 🛡️ Безпека

- Рекомендується використовувати PyMon за реверс-проксі (Nginx/Traefik) з підтримкою TLS.
- Обмежуйте доступ до портів агентів (9100/9182) за допомогою фаєрволу, дозволяючи трафік лише з IP вашого сервера PyMon.
- Регулярно змінюйте `JWT_SECRET` у налаштуваннях.

## 📄 Ліцензія

Цей проект розповсюджується під ліцензією MIT. Детальніше див. у файлі [LICENSE](LICENSE).
