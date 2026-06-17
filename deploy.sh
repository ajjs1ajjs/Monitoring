#!/bin/bash
# =============================================================================
# PyMon NOC - Linux Systemd Deployment Script
# =============================================================================
# Usage:
#   sudo ./deploy.sh                    # Deploy with defaults
#   sudo ./deploy.sh --user pymon       # Custom user
#   sudo ./deploy.sh --port 10000       # Custom port
#   sudo ./deploy.sh --remove           # Remove service
# =============================================================================

set -euo pipefail

APP_DIR="/opt/pymon"
APP_USER="pymon"
PORT=10000
CONFIG_PATH="/etc/pymon/config.yml"
DATA_DIR="/var/lib/pymon"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user) APP_USER="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --dir) APP_DIR="$2"; shift 2 ;;
        --remove) REMOVE=1; shift ;;
        --help) echo "Usage: $0 [--user pymon] [--port 10000] [--remove]"; exit 0 ;;
        *) error "Unknown option: $1"; exit 1 ;;
    esac
done

if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo)"
    exit 1
fi

if [ "${REMOVE:-0}" = "1" ]; then
    info "Removing PyMon service..."
    systemctl stop pymon 2>/dev/null || true
    systemctl disable pymon 2>/dev/null || true
    rm -f /etc/systemd/system/pymon.service
    systemctl daemon-reload
    info "Service removed."
    exit 0
fi

info "Creating user '$APP_USER'..."
id -u "$APP_USER" &>/dev/null || useradd -r -s /bin/false "$APP_USER"

info "Creating directories..."
mkdir -p "$APP_DIR" "$DATA_DIR" "$(dirname "$CONFIG_PATH")"

info "Copying project files..."
cp -r . "$APP_DIR/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$DATA_DIR"

info "Creating Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt --quiet

info "Generating persistent JWT secret..."
if [ ! -f "$APP_DIR/.env" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    cat > "$APP_DIR/.env" <<EOF
JWT_SECRET=$JWT_SECRET
EOF
    chmod 600 "$APP_DIR/.env"
fi

info "Creating systemd service..."
cat > /etc/systemd/system/pymon.service <<EOF
[Unit]
Description=PyMon NOC Monitoring Service
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/pymon server --config $CONFIG_PATH
Restart=always
RestartSec=10
EnvironmentFile=$APP_DIR/.env
Environment=PYMON_ALLOWED_ORIGINS=http://localhost:$PORT

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pymon
systemctl start pymon

info "Waiting for service to start..."
sleep 3

if systemctl is-active --quiet pymon; then
    info "PyMon service started successfully!"
    echo ""
    echo "  Access: http://$(hostname -I | awk '{print $1}'):$PORT"
    echo "  Logs:   sudo journalctl -u pymon -f"
    echo "  Status: sudo systemctl status pymon"
    echo ""
    warn "IMPORTANT: Change default password after first login!"
else
    error "Service failed to start. Check logs: sudo journalctl -u pymon -n 50"
    exit 1
fi
