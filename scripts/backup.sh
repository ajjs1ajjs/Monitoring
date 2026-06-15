#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/pymon"
CONFIG_DIR="/etc/pymon"
DATA_DIR="/var/lib/pymon"
BACKUP_DIR="$CONFIG_DIR/backups"
LOG_DIR="/var/log/pymon"
SERVICE_NAME="pymon"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon - Backup Script"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root${NC}"
    exit 1
fi

DEST=""
MAX_BACKUPS=10

while [[ $# -gt 0 ]]; do
    case $1 in
        --dest)
            DEST="$2"
            shift 2
            ;;
        --max)
            MAX_BACKUPS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dest DIR    Destination directory (default: $BACKUP_DIR)"
            echo "  --max N       Maximum backups to keep (default: 10)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

DEST="${DEST:-$BACKUP_DIR}"
mkdir -p "$DEST"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$DEST/pymon_backup_$TIMESTAMP.tar.gz"

echo -e "${BLUE}Creating backup...${NC}"

TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/pymon_backup"

echo "  - Copying configuration..."
cp -r "$CONFIG_DIR"/* "$TEMP_DIR/pymon_backup/" 2>/dev/null || true

echo "  - Copying data..."
cp -r "$DATA_DIR"/* "$TEMP_DIR/pymon_backup/" 2>/dev/null || true

echo "  - Exporting database..."
if [ -f "$DATA_DIR/pymon.db" ]; then
    sqlite3 "$DATA_DIR/pymon.db" ".backup '$TEMP_DIR/pymon_backup/pymon_backup.db'" 2>/dev/null || \
    cp "$DATA_DIR/pymon.db" "$TEMP_DIR/pymon_backup/pymon_backup.db"
fi

echo "  - Saving version info..."
cat > "$TEMP_DIR/pymon_backup/backup_info.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "version": "$(cat $INSTALL_DIR/.version 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "pymon_version": "$(pymon --version 2>/dev/null || echo 'unknown')"
}
EOF

tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" pymon_backup
rm -rf "$TEMP_DIR"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo -e "${GREEN}Backup created: $BACKUP_FILE ($SIZE)${NC}"

echo -e "${BLUE}Cleaning old backups...${NC}"
cd "$DEST"
ls -t pymon_backup_*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true

BACKUP_COUNT=$(ls -1 pymon_backup_*.tar.gz 2>/dev/null | wc -l)
echo -e "${GREEN}Total backups: $BACKUP_COUNT${NC}"

echo ""
echo -e "${GREEN}Backup completed successfully!${NC}"
