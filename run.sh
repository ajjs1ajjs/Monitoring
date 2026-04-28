#!/bin/bash
# PyMon Startup Script - SQLite Version
# Usage: ./run.sh

echo "========================================"
echo "PyMon Server - Quick Start (SQLite)"
echo "========================================"

# Check for Python
PYTHON=python3
if ! command -v $PYTHON &> /dev/null; then
    PYTHON=python
    if ! command -v $PYTHON &> /dev/null; then
        echo "ERROR: Python not found! Please install Python 3.10+"
        exit 1
    fi
fi

# Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    $PYTHON -m venv .venv
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
python -m pymon server
