# Multi-stage build for production (Go)
FROM golang:1.25-ubuntu AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/pymon ./cmd/pymon

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r pymon && useradd -r -g pymon -d /var/lib/pymon -s /usr/sbin/nologin pymon \
    && mkdir -p /data /config /logs \
    && chown -R pymon:pymon /data /config /logs

COPY --from=builder /out/pymon /usr/local/bin/pymon
# Provide a default config so `docker run` starts out of the box; operators can
# mount their own over /config/config.yml.
COPY config.example.yml /config/config.yml
COPY docs/ /docs/
COPY README.md CHANGELOG.md LICENSE ./

ENV CONFIG_PATH=/config/config.yml \
    DATA_DIR=/data \
    LOG_DIR=/logs \
    DB_PATH=/data/pymon.db

USER pymon

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:10000/api/v1/health || exit 1

VOLUME ["/data", "/config", "/logs"]

LABEL maintainer="PyMon Team"
LABEL version="3.1.0"
LABEL description="Enterprise Server Monitoring NOC Dashboard (Go)"

CMD ["pymon", "server", "--config", "/config/config.yml"]