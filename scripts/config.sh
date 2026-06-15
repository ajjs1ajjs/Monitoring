#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONFIG_DIR="/etc/pymon"
CONFIG_FILE="$CONFIG_DIR/config.json"
SERVICE_NAME="pymon"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon - Configuration Manager"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --list                    Show all configuration"
    echo "  --get KEY                 Get configuration value (e.g., server.port)"
    echo "  --set KEY VALUE           Set configuration value"
    echo "  --port PORT               Change server port"
    echo "  --host HOST               Change server host"
    echo "  --storage TYPE            Change storage backend (memory/sqlite)"
    echo "  --retention HOURS         Change retention period"
    echo "  --admin-user USERNAME     Change admin username"
    echo "  --admin-pass PASSWORD     Change admin password"
    echo "  --backup                  Backup current configuration"
    echo "  --restore FILE            Restore configuration from backup"
    echo "  --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --get server.port"
    echo "  $0 --set server.port 9000"
    echo "  $0 --port 9000"
    echo "  $0 --backup"
}

get_value() {
    local key="$1"
    python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
keys = '$key'.split('.')
value = config
for k in keys:
    value = value.get(k, {})
if value == {}:
    print('Key not found')
else:
    if isinstance(value, dict):
        print(json.dumps(value, indent=2))
    else:
        print(value)
"
}

set_value() {
    local key="$1"
    local value="$2"
    python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
keys = '$key'.split('.')
obj = config
for k in keys[:-1]:
    obj = obj.setdefault(k, {})
try:
    obj[keys[-1]] = json.loads('''$value''')
except:
    obj[keys[-1]] = '''$value'''
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=4)
print('Updated $key = $value')
"
}

list_config() {
    echo -e "${BLUE}Current configuration:${NC}"
    cat "$CONFIG_FILE" | python3 -m json.tool
}

backup_config() {
    local backup_file="$CONFIG_DIR/config.backups/config_$(date +%Y%m%d_%H%M%S).json"
    mkdir -p "$CONFIG_DIR/config.backups"
    cp "$CONFIG_FILE" "$backup_file"
    echo -e "${GREEN}Configuration backed up to: $backup_file${NC}"
}

restore_config() {
    local backup_file="$1"
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Backup file not found: $backup_file${NC}"
        exit 1
    fi
    cp "$backup_file" "$CONFIG_FILE"
    echo -e "${GREEN}Configuration restored from: $backup_file${NC}"
    echo -e "${YELLOW}Restart service to apply changes: sudo systemctl restart $SERVICE_NAME${NC}"
}

restart_service() {
    echo -e "${YELLOW}Restarting service...${NC}"
    systemctl restart $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}Service restarted successfully${NC}"
    else
        echo -e "${RED}Service failed to restart. Check logs: sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    fi
}

if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --list)
            list_config
            exit 0
            ;;
        --get)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Key required${NC}"
                exit 1
            fi
            get_value "$2"
            exit 0
            ;;
        --set)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Key and value required${NC}"
                exit 1
            fi
            set_value "$2" "$3"
            restart_service
            exit 0
            ;;
        --port)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Port required${NC}"
                exit 1
            fi
            set_value "server.port" "$2"
            echo -e "${YELLOW}Don't forget to update firewall rules if needed${NC}"
            restart_service
            exit 0
            ;;
        --host)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Host required${NC}"
                exit 1
            fi
            set_value "server.host" "$2"
            restart_service
            exit 0
            ;;
        --storage)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Storage type required (memory/sqlite)${NC}"
                exit 1
            fi
            set_value "storage.backend" "$2"
            restart_service
            exit 0
            ;;
        --retention)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Hours required${NC}"
                exit 1
            fi
            set_value "retention_hours" "$2"
            restart_service
            exit 0
            ;;
        --admin-user)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Username required${NC}"
                exit 1
            fi
            set_value "auth.admin_username" "$2"
            restart_service
            exit 0
            ;;
        --admin-pass)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Password required${NC}"
                exit 1
            fi
            set_value "auth.admin_password" "$2"
            restart_service
            exit 0
            ;;
        --backup)
            backup_config
            exit 0
            ;;
        --restore)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Backup file required${NC}"
                echo "Available backups:"
                ls -lt "$CONFIG_DIR/config.backups/"*.json 2>/dev/null || echo "No backups found"
                exit 1
            fi
            restore_config "$2"
            restart_service
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done
