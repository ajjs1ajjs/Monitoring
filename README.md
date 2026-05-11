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

> **Важливо:** Після встановлення на Windows проект працюватиме як фонова служба (черер Task Scheduler), яка автоматично запускається при старті системи.

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

## 🛠️ Додаткова інформація

- **Доступ до панелі**: `http://<IP-адреса>:10000/dashboard/`
- **Логін за замовчуванням**: `admin` / `changeme`
- **Конфігурація**: Файл `config.yml` у директорії проекту.
- **База даних**: `pymon.db` (SQLite).

Детальна документація доступна в папці `docs/`.
