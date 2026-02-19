#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GITHUB_REPO="ajjs1ajjs/Monitoring"
INSTALL_DIR="/opt/pymon"
CONFIG_DIR="/etc/pymon"
DATA_DIR="/var/lib/pymon"
LOG_DIR="/var/log/pymon"
SERVICE_NAME="pymon"
USER="pymon"
APP_VERSION="v0.1.0"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon - Installation Script"
echo "   Python Monitoring System"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

PORT=8090
VERSION="main"
STORAGE="sqlite"

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --storage)
            STORAGE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT       Set port (default: 8090)"
            echo "  --version VERSION Install specific version (e.g., v0.1.0 or main)"
            echo "  --storage TYPE    Storage backend: memory or sqlite (default: sqlite)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

if [[ "$VERSION" == "main" ]]; then
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/archive/refs/heads/main.tar.gz"
    APP_VERSION="latest (main branch)"
elif [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/archive/refs/tags/$VERSION.tar.gz"
    APP_VERSION="$VERSION"
else
    echo -e "${RED}Error: Invalid version format. Use 'main' or 'v0.1.0' format${NC}"
    exit 1
fi

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_VERSION=$VERSION_ID
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS_NAME $OS_VERSION${NC}"

PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}Error: Python 3.10+ is required${NC}"
    exit 1
fi

PYTHON_VER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Using Python: $PYTHON_VER${NC}"

echo -e "${BLUE}Installing system dependencies...${NC}"
case "$OS_NAME" in
    "Ubuntu"|"Debian GNU/Linux")
        apt-get update -qq
        apt-get install -y -qq python3-pip python3-venv python3-full sqlite3 curl > /dev/null
        ;;
    "CentOS Linux"|"Red Hat Enterprise Linux"|"Fedora")
        yum install -y -q python3-pip sqlite curl > /dev/null 2>&1 || \
        dnf install -y -q python3-pip sqlite curl > /dev/null 2>&1
        ;;
    *)
        echo -e "${RED}Unsupported OS: $OS_NAME${NC}"
        echo "Supported: Ubuntu, Debian, CentOS, RHEL, Fedora"
        exit 1
        ;;
esac

if ! id "$USER" &>/dev/null; then
    echo -e "${BLUE}Creating user: $USER${NC}"
    useradd -r -s /bin/false -d "$DATA_DIR" "$USER"
fi

echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

echo -e "${BLUE}Downloading version $VERSION from GitHub...${NC}"
cd /tmp

if ! curl -fsSL "$DOWNLOAD_URL" -o pymon.tar.gz 2>/dev/null; then
    echo -e "${RED}Error: Failed to download from GitHub${NC}"
    exit 1
fi

echo -e "${BLUE}Extracting...${NC}"
tar -xzf pymon.tar.gz

EXTRACT_DIR=$(find . -maxdepth 1 -type d -name "pymon*" | head -1)

if [ -z "$EXTRACT_DIR" ]; then
    echo -e "${RED}Error: Could not find extracted files${NC}"
    exit 1
fi

echo -e "${BLUE}Found: $EXTRACT_DIR${NC}"

echo -e "${BLUE}Installing application...${NC}"
cp -r "$EXTRACT_DIR/pymon" "$INSTALL_DIR/"
cp "$EXTRACT_DIR/pyproject.toml" "$INSTALL_DIR/" 2>/dev/null || true
cp "$EXTRACT_DIR/README.md" "$INSTALL_DIR/" 2>/dev/null || true

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "0.0.0.0")

echo -e "${BLUE}Creating configuration...${NC}"
if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    cat > "$CONFIG_DIR/config.yml" << EOF
# PyMon Configuration
server:
  port: $PORT
  host: 0.0.0.0
  domain: $SERVER_IP

storage:
  backend: $STORAGE
  path: $DATA_DIR/pymon.db
  retention_hours: 168

auth:
  admin_username: admin
  admin_password: admin
  jwt_expire_hours: 24

# Scrape configuration (Prometheus-style)
scrape_configs:
  - job_name: pymon_self
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets:
          - localhost:$PORT
        labels:
          env: production
          service: pymon

alerting:
  enabled: true
  evaluation_interval: 30s
  rules: []

backup:
  enabled: true
  max_backups: 10
  backup_dir: $CONFIG_DIR/backups
EOF
fi

mkdir -p "$CONFIG_DIR/backups"

echo -e "${BLUE}Creating virtual environment...${NC}"
cd "$INSTALL_DIR"
$PYTHON_CMD -m venv venv

echo -e "${BLUE}Installing Python packages...${NC}"
./venv/bin/pip install --upgrade pip > /dev/null
./venv/bin/pip install -e .

JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)

echo -e "${BLUE}Creating systemd service...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=PyMon Monitoring Service (Version $APP_VERSION)
Documentation=https://github.com/$GITHUB_REPO
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="CONFIG_PATH=$CONFIG_DIR/config.json"
Environment="JWT_SECRET=$JWT_SECRET"
Environment="APP_VERSION=$APP_VERSION"
ExecStart=$INSTALL_DIR/venv/bin/pymon server --config $CONFIG_DIR/config.yml
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/pymon.log
StandardError=append:$LOG_DIR/pymon.error.log

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${BLUE}Setting permissions...${NC}"
chown -R "$USER:$USER" "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
chmod 600 "$CONFIG_DIR/config.json"

echo -e "${BLUE}Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        ufw allow $PORT/tcp comment 'PyMon'
        echo -e "${GREEN}Added UFW rule for port $PORT${NC}"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if firewall-cmd --state 2>/dev/null; then
        firewall-cmd --permanent --add-port=$PORT/tcp
        firewall-cmd --reload
        echo -e "${GREEN}Added firewalld rule for port $PORT${NC}"
    fi
fi

echo -e "${BLUE}Starting service...${NC}"
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "   PyMon - Installation Successful!"
    echo "==========================================${NC}"
    echo ""
    echo -e "  ${GREEN}Version:${NC}     $APP_VERSION"
    echo -e "  ${GREEN}Port:${NC}        $PORT"
    echo -e "  ${GREEN}Storage:${NC}     $STORAGE"
    echo -e "  ${GREEN}URL:${NC}         http://$IP:$PORT"
    echo -e "  ${GREEN}API:${NC}         http://$IP:$PORT/api/v1/"
    echo -e "  ${GREEN}Dashboard:${NC}   http://$IP:$PORT/dashboard/"
    echo ""
    echo -e "  ${YELLOW}Default Credentials:${NC}"
    echo -e "    Username: ${BLUE}admin${NC}"
    echo -e "    Password: ${BLUE}admin${NC}"
    echo ""
    echo -e "  ${YELLOW}Please change the password after first login!${NC}"
    echo ""
    echo "Management Commands:"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "  sudo systemctl stop $SERVICE_NAME"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "Update Command:"
    echo "  curl -fsSL https://raw.githubusercontent.com/$GITHUB_REPO/main/update.sh | sudo bash"
    echo ""
    echo "Configuration:"
    echo "  Config: $CONFIG_DIR/config.json"
    echo "  Logs:   $LOG_DIR/"
    echo "  Data:   $DATA_DIR/"
    echo ""
else
    echo -e "${RED}=========================================="
    echo "   Installation Failed"
    echo "==========================================${NC}"
    echo ""
    echo "Service failed to start. Check logs:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 50"
    echo ""
    exit 1
fi

rm -rf /tmp/pymon.tar.gz "$EXTRACT_DIR"

echo -e "${GREEN}Done!${NC}"
