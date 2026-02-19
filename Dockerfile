# Multi-stage build for production
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --user --no-cache-dir pip --upgrade && \
    pip install --user --no-cache-dir fastapi uvicorn pydantic pydantic-settings \
    sqlalchemy aiosqlite httpx prometheus-client jinja2 python-multipart \
    websockets apscheduler bcrypt pyjwt python-dotenv

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local

COPY pymon/ ./pymon/
COPY pyproject.toml .

RUN groupadd -r pymon && useradd -r -g pymon pymon \
    && mkdir -p /data /config /logs \
    && chown -R pymon:pymon /app /data /config /logs

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    CONFIG_PATH=/config/config.json \
    DATA_DIR=/data \
    LOG_DIR=/logs

USER pymon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "pymon.cli", "server", "--host", "0.0.0.0", "--port", "8000"]
