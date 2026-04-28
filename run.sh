#!/bin/bash
# PyMon Startup Script - Pure Linux Version
# Usage: ./run.sh

set -e # Exit on error

echo "========================================"
echo "PyMon Server - Linux Enterprise Edition"
echo "========================================"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found! Please install it: sudo apt install python3 python3-venv"
    exit 1
fi

# Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
echo "[2/3] Installing/Updating dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install -e . --no-deps -q

# Run
echo "[3/3] Starting server..."
echo "Dashboard: http://localhost:8090/dashboard/"
echo
python3 -m pymon server
