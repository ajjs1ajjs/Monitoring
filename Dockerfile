# Multi-stage build for production (Go)
FROM golang:1.27 AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/pymon ./cmd/pymon

FROM alpine:3.22

# busybox provides ping + wget (used by ICMP checks and HEALTHCHECK);
# setcap lets the non-root pymon user send ICMP echo requests.
RUN apk add --no-cache ca-certificates tzdata iputils libcap \
    && setcap cap_net_raw=ep /bin/ping \
    && addgroup -S pymon \
    && adduser -S -G pymon -h /var/lib/pymon -s /sbin/nologin pymon \
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
LABEL version="3.0.6"
LABEL description="Enterprise Server Monitoring NOC Dashboard (Go)"

CMD ["pymon", "server", "--config", "/config/config.yml"]