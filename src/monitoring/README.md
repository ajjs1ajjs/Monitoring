# 📊 Monitoring Dashboard - Інтерактивний моніторинг метрик

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)  
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com/)  
[![Chart.js](https://img.shields.io/badge/chart.js-4.4+-blueviolet.svg)](https://www.chartjs.org/)  

## 🌟 Огляд проекту

**Monitoring Dashboard** - це сучасна платформа для візуалізації та моніторингу метрик системи в реальному часі. Проект реалізовано за допомогою **FastAPI**, **Chart.js** та сучасного веб-дизайну з підтримкою темної/світлої теми, адаптивним інтерфейсом та інтерактивними графіками.

### Ключові можливості

- 📈 **Інтерактивні графіки** - реалізовано лінійні, барові, doughnut та radar графіки
- 🎨 **Темна/світла тема** - автоматичне визначення теми з можливістю перемикача
- 📱 **Адаптивний дизайн** - мобільна версія, responsive layout (Grid/Flexbox)
- 🔌 **Real-time updates** - опціональна підтримка WebSocket для live даних
- ⚡ **High performance** - async operations, in-memory data caching

## 🎯 Цілі проекту

1. Надати зручний інтерфейс для перегляду метрик системи (CPU, Memory, Disk I/O, Network traffic)
2. Підтримувати реальні дані та симуляцію даних для демонстрації
3. Надати повну API документацію (Swagger/OpenAPI)
4. Реалізувати адаптивний інтерфейс з підтримкою тем

## 📦 Вимоги

- Python 3.8+
- FastAPI >= 0.104.0
- Jinja2
- Chart.js (встановлюється через CDN або локально)
- Git для клонування репозиторію

### Встановлення залежностей

```bash
# Створити віртуальне середовище
python -m venv .venv
.venv\Scripts\activate  # Windows
# або
source .venv/bin/activate  # Linux/Mac

# Встановити FastAPI та інші залежності
pip install fastapi[all] jinja2
```

## 🚀 Запуск проекту

### 1️⃣ Розробка (Development)

```bash
cd Monitoring
python -m uvicorn src.monitoring.app:app --reload --port 8000 --host 0.0.0.0
```

Доступ до інтерфейсу: `http://localhost:8000`  
API документація (Swagger UI): `http://localhost:8000/docs`

### 2️⃣ Продакшн (Production)

```bash
# Використовувати uvicorn з уривками або gunicorn/uvicorn worker'ами
uvicorn src.monitoring.app:app --workers 4 --host 0.0.0.0 --port 8000
```

### 3️⃣ Docker (опціонально)

Якщо є Docker, можна використати `Dockerfile` для контейнеризації.

## 📡 API Endpoints

| Endpoint | Метод | Опис |
|----------|-------|------|
| `/` | GET | Головна сторінка з графіками та метриками |
| `/api/metrics` | GET | Отримати поточні значення всіх метрик |
| `/api/metrics/history/{metric_name}` | GET | Історичні дані для конкретної метрики (1h-720h) |
| `/api/system` | GET | Інформація про систему, uptime, hardware specs |
| `/api/health` | GET | Health check endpoint для load balancer'ів |
| `/api/dashboard` | GET | Повний пакет даних для dashboard (charts + system info) |

### Приклад запиту API

```bash
# Отримати поточні метрики
curl http://localhost:8000/api/metrics

# Отримати історію CPU usage за останні 24 години
curl "http://localhost:8000/api/metrics/history/cpu_usage?hours=24"

# Перевірити health статус
curl http://localhost:8000/api/health
```

## 📖 Документація API

Повна документація доступна на `http://localhost:8000/docs` або завантажити JSON-файл:

```bash
# Отримати OpenAPI специфікацію
curl http://localhost:8000/openapi.json > openapi.json
```

## 🧪 Тестування

Запуск тестів через pytest:

```bash
pytest src/monitoring/tests/test_api.py -v
```

## 🎨 Дизайн та інтерфейс

### Графіки (Chart.js)

- **Lінійні графіки** - для CPU, Memory usage з плавними кривими
- **Bar charts** - для порівняння метрик за часом
- **Doughnut charts** - для розподілу трафіку мережі
- **Tooltip інтерактивність** - hover, zoom, export в PNG (опціонально)

### Адаптивність

| Роздільна здатність | Layout | Графіки |
|---------------------|--------|---------|
| Mobile (< 768px) | 1 колон