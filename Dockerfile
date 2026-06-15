# Multi-stage build for production
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

COPY pymon/ ./pymon/
COPY pyproject.toml .
COPY docs/ ./docs/
COPY README.md CHANGELOG.md ./

RUN addgroup --system pymon && adduser --system --ingroup pymon pymon \
    && mkdir -p /data /config /logs \
    && chown -R pymon:pymon /app /data /config /logs

ENV PATH=/usr/local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    CONFIG_PATH=/config/config.yml \
    DATA_DIR=/data \
    LOG_DIR=/logs \
    DB_PATH=/data/pymon.db

USER pymon

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:10000/api/v1/health || exit 1

VOLUME ["/data", "/config", "/logs"]

LABEL maintainer="PyMon Team"
LABEL version="2.1.0"
LABEL description="PyMon - Python Monitoring System (Prometheus + Grafana alternative)"

CMD ["python", "-m", "pymon", "server", "--config", "/config/config.yml"]
