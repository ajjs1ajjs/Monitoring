#!/bin/bash
# PyMon NOC (Go) — run from source
# Usage: ./run.sh [--port PORT]
set -e

if ! command -v go &> /dev/null; then
    echo "ERROR: Go 1.25+ not found. Install it from https://go.dev/dl/"
    exit 1
fi

echo "Building PyMon..."
go build -o pymon ./cmd/pymon

echo "Starting PyMon..."
exec ./pymon server "$@"
