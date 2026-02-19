#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONFIG_DIR="/etc/pymon"
DATA_DIR="/var/lib/pymon"
SERVICE_NAME="pymon"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon - Restore Script"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root${NC}"
    exit 1
fi

BACKUP_FILE=""
AUTO=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backup)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --auto)
            AUTO=true
            shift
            ;;
        --list)
            echo "Available backups:"
            ls -lht "$CONFIG_DIR/backups"/pymon_backup_*.tar.gz 2>/dev/null || echo "No backups found"
            exit 0
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backup FILE   Restore from specific backup file"
            echo "  --auto          Restore from latest backup"
            echo "  --list          List available backups"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

if [ -z "$BACKUP_FILE" ]; then
    if [ "$AUTO" = true ]; then
        BACKUP_FILE=$(ls -t "$CONFIG_DIR/backups"/pymon_backup_*.tar.gz 2>/dev/null | head -1)
        if [ -z "$BACKUP_FILE" ]; then
            echo -e "${RED}No backups found${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Auto-selected: $BACKUP_FILE${NC}"
    else
        echo -e "${RED}Error: No backup file specified. Use --backup FILE or --auto${NC}"
        exit 1
    fi
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Warning: This will replace current configuration and data!${NC}"
read -p "Continue? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 0
fi

echo -e "${BLUE}Stopping service...${NC}"
systemctl stop $SERVICE_NAME || true

echo -e "${BLUE}Restoring from backup...${NC}"

TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

echo "  - Restoring configuration..."
cp -r "$TEMP_DIR/pymon_backup/"* "$CONFIG_DIR/" 2>/dev/null || true

echo "  - Restoring data..."
cp -r "$TEMP_DIR/pymon_backup/"* "$DATA_DIR/" 2>/dev/null || true

if [ -f "$TEMP_DIR/pymon_backup/pymon_backup.db" ]; then
    echo "  - Restoring database..."
    cp "$TEMP_DIR/pymon_backup/pymon_backup.db" "$DATA_DIR/pymon.db"
fi

rm -rf "$TEMP_DIR"

echo -e "${BLUE}Starting service...${NC}"
systemctl start $SERVICE_NAME

sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "   Restore Successful!"
    echo "==========================================${NC}"
    echo ""
    echo "Restored from: $BACKUP_FILE"
else
    echo -e "${RED}Service failed to start. Check logs:${NC}"
    echo "  sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
