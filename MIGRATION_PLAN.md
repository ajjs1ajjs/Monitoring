# PyMon NOC — План міграції Python → Go

## Мета

Переписати бекенд з Python (FastAPI + aiosqlite) на **Go** для real-time моніторингу з нижчим споживанням ресурсів та вищою продуктивністю.

| Аспект | Було (Python) | Стало (Go) |
|--------|---------------|------------|
| Мова | Python 3.12 | **Go 1.25** |
| Веб-фреймворк | FastAPI + Uvicorn | **net/http** (Go 1.22+ роутинг) |
| WebSocket | fastapi websockets | **gorilla/websocket** |
| БД | sqlite3 (sync) + aiosqlite (async) | **modernc.org/sqlite** (pure-Go, WAL) |
| Парсинг Prometheus | prometheus_client.parser | **github.com/prometheus/common/expfmt** |
| JWT | PyJWT | **golang-jwt/jwt/v5** |
| bcrypt | passlib/bcrypt | **golang.org/x/crypto/bcrypt** |
| YAML | PyYAML + Pydantic | **gopkg.in/yaml.v3** |
| Один бінар | python-залежності | **статичний бінар** (go:embed фронтенд) |

## Стратегія

- **Той самий REST API + WebSocket контракт** → фронтенд (dashboard.html/js, login) перевикористовується як embedded assets через `go:embed`.
- **Схема БД ідентична** → міграція даних не потрібна (можна вказати на існуючий `pymon.db`).
- **Моніторинг**: ScrapeManager (node_exporter/windows_exporter) + ServiceChecker (http/ping/ssl) як горутини.
- **Ті ж сповіщення**: Telegram, Discord, MS Teams, Email.
- **Виправлення відомих багів**: додати реальний Slack-вебхук, видалення API-ключа.

## Етапи

1. Скелет проєкту: `go.mod`, `cmd/pymon/main.go`, конфіг.
2. Storage: схема, WAL, запити (servers/services/history/alerts/audit/users/api_keys/notifications).
3. Auth: JWT, bcrypt, API-ключі, must_change_password, audit trail.
4. REST API: всі роутери (auth, servers, metrics, alerts, settings, logs, services, reports, backup) + health + prometheus-export.
5. WebSocket `/api/v1/ws/metrics`.
6. Моніторинг: Prometheus-парсер, ScrapeManager, ServiceChecker, retention, backup cron, alerting rules.
7. Сповіщення: Telegram/Discord/Slack/Teams/Email + тестовий ендпоінт.
8. Frontend: `go:embed` шаблонів та статики (CSP без unsafe-inline).
9. Docker: Dockerfile multi-stage (scratch/alpine), docker-compose.
10. Тести Go (config, parser, storage, auth, API smoke), lint.
11. CI/CD: GitHub Actions build + test + release.
12. README, CHANGELOG, версія 3.0.0, реліз.

## Ключові рішення

- SQLite **тільки через `modernc.org/sqlite`** (немає CGO, кросплатформенний бінар).
- Двнсемплінг історії — window-функції SQLite (ROW_NUMBER OVER PARTITION).
- SSRF-захист збережено (блок cloud-metadata, loopback, link-local).
- Rate limit на `/auth/login` 10/хв на IP.
