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
SERVICE_NAME="pymon"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon - Update Script"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

PYMON_VERSION="main"
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            PYMON_VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --version VERSION  Update to specific version (e.g., v0.2.0 or main)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: PyMon is not installed. Run install.sh first.${NC}"
    exit 1
fi

CURRENT_VERSION=$(cat "$INSTALL_DIR/.version" 2>/dev/null || echo "unknown")
echo -e "${YELLOW}Current version: $CURRENT_VERSION${NC}"
echo -e "${YELLOW}Updating to: $PYMON_VERSION${NC}"

if [[ "$PYMON_VERSION" == "main" ]]; then
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/archive/refs/heads/main.tar.gz"
elif [[ "$PYMON_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/archive/refs/tags/$PYMON_VERSION.tar.gz"
else
    echo -e "${RED}Error: Invalid version format${NC}"
    exit 1
fi

echo -e "${BLUE}Stopping service...${NC}"
systemctl stop $SERVICE_NAME || true

echo -e "${BLUE}Backing up current version...${NC}"
BACKUP_DIR="$CONFIG_DIR/backups/pre_update_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$INSTALL_DIR/pymon" "$BACKUP_DIR/" 2>/dev/null || true

echo -e "${BLUE}Downloading update...${NC}"
cd /tmp
curl -fsSL "$DOWNLOAD_URL" -o pymon-update.tar.gz
tar -xzf pymon-update.tar.gz

EXTRACT_DIR=$(find . -maxdepth 1 -type d \( -name "Monitoring*" -o -name "Project2*" -o -name "pymon*" \) | head -1)

if [ -z "$EXTRACT_DIR" ]; then
    echo -e "${RED}Error: Could not find extracted files${NC}"
    ls -la
    systemctl start $SERVICE_NAME || true
    exit 1
fi

echo -e "${BLUE}Found: $EXTRACT_DIR${NC}"

echo -e "${BLUE}Updating files...${NC}"
rm -rf "$INSTALL_DIR/pymon"
cp -r "$EXTRACT_DIR/pymon" "$INSTALL_DIR/"
cp "$EXTRACT_DIR/pyproject.toml" "$INSTALL_DIR/" 2>/dev/null || true

echo -e "${BLUE}Updating dependencies...${NC}"
cd "$INSTALL_DIR"
./venv/bin/pip install --upgrade pip > /dev/null
./venv/bin/pip install -e .

echo "$PYMON_VERSION" > "$INSTALL_DIR/.version"

echo -e "${BLUE}Starting service...${NC}"
systemctl start $SERVICE_NAME

sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "   Update Successful!"
    echo "==========================================${NC}"
    echo ""
    echo -e "  ${GREEN}Previous version:${NC} $CURRENT_VERSION"
    echo -e "  ${GREEN}New version:${NC}     $PYMON_VERSION"
    echo ""
    echo -e "  Backup saved to: $BACKUP_DIR"
    echo ""
else
    echo -e "${RED}=========================================="
    echo "   Update Failed - Rolling Back"
    echo "==========================================${NC}"
    
    rm -rf "$INSTALL_DIR/pymon"
    cp -r "$BACKUP_DIR/pymon" "$INSTALL_DIR/"
    systemctl start $SERVICE_NAME
    
    echo "Rolled back to previous version"
    echo "Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

rm -rf /tmp/pymon-update.tar.gz "$EXTRACT_DIR"

echo -e "${GREEN}Done!${NC}"
