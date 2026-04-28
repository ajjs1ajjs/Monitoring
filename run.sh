#!/bin/bash
# PyMon Startup Script - Single command to install and run
# Usage: ./run.sh           - Install deps + run with SQLite (default)
#        ./run.sh postgres - Install deps + run with PostgreSQL
#        ./run.sh tls       - Install deps + run with TLS
#        ./run.sh full     - Install deps + run with PostgreSQL + TLS

MODE=${1:-sqlite}

echo "========================================"
echo "PyMon Server - Installing & Running"
echo "========================================"
echo

# Check Python
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Python not found!"
    echo "Please install Python 3.10+ from https://python.org"
    exit 1
fi

PYTHON=python
$PYTHON --version >/dev/null 2>&1 || PYTHON=python3

# Install dependencies
echo "[1/3] Installing dependencies..."
pip install -r requirements.txt -q
pip install -e . --no-deps -q 2>/dev/null

# Set defaults
STORAGE="sqlite"
PG_DSN=""
TLS_ENABLED="false"

# Parse mode
case "$MODE" in
    postgres)
        echo "[2/3] PostgreSQL mode selected"
        STORAGE="postgres"
        PG_DSN="postgresql://user:password@localhost/pymon"
        echo "       Set PG_DSN env var for your PostgreSQL"
        ;;
    tls)
        echo "[2/3] TLS mode selected"
        TLS_ENABLED="true"
        echo "       Place cert.pem and key.pem in this folder"
        ;;
    full)
        echo "[2/3] Full mode: PostgreSQL + TLS"
        STORAGE="postgres"
        PG_DSN="postgresql://user:password@localhost/pymon"
        TLS_ENABLED="true"
        echo "       Set PG_DSN and place certs"
        ;;
    *)
        echo "[2/3] SQLite mode (default)"
        ;;
esac

echo "[3/3] Starting server..."
echo

# Export env vars
export STORAGE_BACKEND="$STORAGE"
export TLS_ENABLED

if [ -n "$PG_DSN" ]; then
    export PG_DSN
fi

# Run with selected backend
if [ "$STORAGE" = "postgres" ]; then
    $PYTHON -m pymon.cli server --storage postgres --pg-dsn "$PG_DSN"
else
    $PYTHON -m pymon.cli server
fi