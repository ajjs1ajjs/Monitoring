#!/bin/bash
# PyMon NOC (Go) - one-line installer (Linux/macOS)
set -e

INSTALL_DIR="/opt/pymon"
CONFIG_DIR="/etc/pymon"
DATA_DIR="/var/lib/pymon"
LOG_DIR="/var/log/pymon"
SERVICE_NAME="pymon"
VERSION="3.0.0"
REPO="ajjs1ajjs/Monitoring"

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "PyMon NOC ${VERSION} (Go) installer"

if ! command -v go &> /dev/null && ! command -v docker &> /dev/null; then
    echo "ERROR: Go (for building) or Docker (for image) is required."
    exit 1
fi

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

if command -v docker &> /dev/null; then
    echo "Building binary via Docker image..."
    docker build -t "$REPO:$VERSION" "$(dirname "$0")"
    id=$(docker create "$REPO:$VERSION")
    docker cp "$id:/usr/local/bin/pymon" "$INSTALL_DIR/pymon"
    docker rm "$id"
else
    echo "Building binary..."
    ( cd "$(dirname "$0")" && go build -o "$INSTALL_DIR/pymon" ./cmd/pymon )
fi

if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    cp "$(dirname "$0")/config.example.yml" "$CONFIG_DIR/config.yml"
fi

useradd -r -s /bin/false pymon 2>/dev/null || true
chown -R pymon:pymon "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=PyMon NOC Monitoring
After=network.target

[Service]
User=pymon
ExecStart=$INSTALL_DIR/pymon server --config $CONFIG_DIR/config.yml
Restart=always
RestartSec=5
Environment=CONFIG_PATH=$CONFIG_DIR/config.yml
Environment=DATA_DIR=$DATA_DIR
Environment=LOG_DIR=$LOG_DIR
Environment=DB_PATH=$DATA_DIR/pymon.db

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

echo "PyMon installed. Dashboard: http://localhost:10000/"
echo "Check status: systemctl status $SERVICE_NAME"
echo "First-run admin password is printed to the service log."
