# Multi-stage build for production
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    passwd \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --user --no-cache-dir pip --upgrade && \
    pip install --user --no-cache-dir fastapi uvicorn pydantic pydantic-settings \
    sqlalchemy aiosqlite httpx prometheus-client jinja2 python-multipart \
    websockets apscheduler bcrypt pyjwt python-dotenv pyyaml

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local

COPY pymon/ ./pymon/
COPY pyproject.toml .
COPY docs/ ./docs/
COPY examples/ ./examples/
COPY README.md CHANGELOG.md ./

RUN groupadd -r pymon && useradd -r -g pymon pymon \
    && mkdir -p /data /config /logs \
    && chown -R pymon:pymon /app /data /config /logs

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    CONFIG_PATH=/config/config.yml \
    DATA_DIR=/data \
    LOG_DIR=/logs \
    DB_PATH=/data/pymon.db

USER pymon

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/api/v1/health')" || exit 1

VOLUME ["/data", "/config", "/logs"]

LABEL maintainer="PyMon Team"
LABEL version="2.0.0"
LABEL description="Enterprise Server Monitoring with Grafana-style Dashboard"

CMD ["python", "-m", "pymon.cli", "server", "--config", "/config/config.yml"]
