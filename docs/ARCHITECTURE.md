# Огляд архітектури PyMon NOC

### Загальний огляд
- **Backend**: Побудований на **Go** (`net/http` + `http.ServeMux` з pattern routing), з високою конкурентністю для збору метрик. Експонує REST API для збору метрик, керування серверами/сервісами та сповіщеннями.
- **Storage**: **SQLite** (WAL, `modernc.org/sqlite`) для історії метрик та конфігурацій. Автоматична ротація даних (retention) та періодичний `VACUUM`.
- **Frontend**: Односторінковий додаток (SPA) на Vanilla JS + Chart.js, вбудований у бінарник через `go:embed` та віддається тим самим сервером.

### Основні компоненти
1. **API Layer** (`internal/api`):
   - REST-хендлери для агентів, фронтенду та адміністрування.
   - Автентифікація: JWT (HttpOnly cookie для SPA, Bearer для клієнтів) та API-ключі.
   - Експорт даних у CSV/JSON, генерація звітів.
2. **Monitor / Scrape Manager** (`internal/monitor`):
   - Фоновий цикл збору метрик (паралельно, семофор ×10).
   - Оцінка Alerting Rules з deduplication та suppression (flapping).
   - SSRF-захист для outbound scrape/check цілей (cloud metadata blocked, DNS-кеш).
3. **Storage Layer** (`internal/storage`):
   - SQLite-сховище метрик, серверів, сервісів, алертів, аудиту.
   - Шифрування чутливих значень (секрети нотифікацій) у стані спокою.
4. **Notifier** (`internal/notify`):
   - Email (SMTP), Telegram, Slack/Discord/Teams webhooks.

### Потік даних (Data Flow)
- **Збір**: Scrape Manager опитує агенти (`node_exporter`, `windows_exporter`) за розкладом.
- **Зберігання**: Дані записуються в `metrics_history` та `services_history`.
- **Аналіз**: Система перевіряє значення на відповідність Alerting Rules.
- **Візуалізація**: Користувач отримує дані через REST API та WebSocket (`/api/v1/ws/metrics`), що відображаються на графіках у реальному часі.

### Безпека та розгортання
- **Автентифікація**: JWT у **HttpOnly** cookie (`SameSite=Strict`) для браузера; Bearer-токени та API-ключі для програмних клієнтів.
- **CSP**: `Content-Security-Policy` з `script-src 'self'`; WebSocket-з'єднання проходять Origin-перевірку (CSWSH-захист).
- **Rate limiting**: login 10/хв/IP, auth-дії 30/хв/IP.
- **Service Mode**: Windows — Task Scheduler, Linux — `systemd`.
- **Docker**: Повна підтримка через Dockerfile та docker-compose.yml.

### Плани на майбутнє
- Інтеграція з **PostgreSQL** для надвеликих інфраструктур.
- Розширення детекції аномалій (ML).
- Підтримка мобільних пуш-повідомлень через PWA.
