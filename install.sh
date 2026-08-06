#!/bin/bash
# PyMon NOC (Go) - one-line installer (Linux/macOS)
# Downloads the pre-built binary from GitHub Releases.
# Usage: curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.sh | sudo bash

set -e

INSTALL_DIR="/opt/pymon"
CONFIG_DIR="/etc/pymon"
DATA_DIR="/var/lib/pymon"
LOG_DIR="/var/log/pymon"
SERVICE_NAME="pymon"
VERSION="${PYMON_VERSION:-latest}"
REPO="ajjs1ajjs/Monitoring"

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "=============================================="
echo "   PyMon NOC - Installation Script (Go)"
echo "=============================================="
echo ""

# --- Architecture detection ---------------------------------------------
case "$(uname -m)" in
    x86_64|amd64)  ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *)
        echo "ERROR: unsupported architecture: $(uname -m)"
        echo "Supported: x86_64/amd64, aarch64/arm64"
        exit 1
        ;;
esac
OS="linux"
if [ "$(uname -s)" = "Darwin" ]; then
    OS="darwin"
fi

BINARY_NAME="pymon-${OS}-${ARCH}"
if [ "$OS" = "linux" ] && [ "$ARCH" = "amd64" ]; then
    BINARY_NAME="pymon-linux-amd64"
elif [ "$OS" = "linux" ] && [ "$ARCH" = "arm64" ]; then
    BINARY_NAME="pymon-linux-arm64"
elif [ "$OS" = "darwin" ]; then
    BINARY_NAME="pymon-darwin-amd64"
fi

if [ "$VERSION" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"
    VERSION_URL="latest/download/"
else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"
    VERSION_URL="download/${VERSION}/"
fi

# --- Download ------------------------------------------------------------
echo "[1/4] Downloading PyMon ${VERSION} (${BINARY_NAME})..."
TMP_BIN="$(mktemp)"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_URL" -o "$TMP_BIN" || { echo "ERROR: download failed. Is release ${VERSION} published?"; rm -f "$TMP_BIN"; exit 1; }
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$TMP_BIN" "$DOWNLOAD_URL" || { echo "ERROR: download failed. Is release ${VERSION} published?"; rm -f "$TMP_BIN"; exit 1; }
else
    echo "ERROR: neither curl nor wget is installed. Install one of them:"
    echo "  apt-get install -y curl   (Debian/Ubuntu)"
    echo "  yum install -y curl       (RHEL/CentOS)"
    rm -f "$TMP_BIN"
    exit 1
fi

# --- Verify SHA-256 checksum (from release checksums.txt) ------------------
echo "Verifying checksum..."
TMP_SUM="$(mktemp)"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "https://github.com/${REPO}/releases/${VERSION_URL}checksums.txt" -o "$TMP_SUM" 2>/dev/null || true
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$TMP_SUM" "https://github.com/${REPO}/releases/${VERSION_URL}checksums.txt" 2>/dev/null || true
fi
if [ -s "$TMP_SUM" ]; then
    EXPECTED="$(grep "${BINARY_NAME}$" "$TMP_SUM" | awk '{print $1}')"
    if [ -n "$EXPECTED" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            ACTUAL="$(sha256sum "$TMP_BIN" | awk '{print $1}')"
        elif command -v shasum >/dev/null 2>&1; then
            ACTUAL="$(shasum -a 256 "$TMP_BIN" | awk '{print $1}')"
        else
            echo "Warning: no sha256 utility found, skipping checksum verification."
            ACTUAL=""
        fi
        if [ -n "$ACTUAL" ] && [ "$EXPECTED" != "$ACTUAL" ]; then
            echo "ERROR: checksum mismatch for ${BINARY_NAME}."
            echo "  expected: ${EXPECTED}"
            echo "  actual:   ${ACTUAL}"
            rm -f "$TMP_BIN" "$TMP_SUM"
            exit 1
        fi
        echo "Checksum OK."
    else
        echo "Warning: no checksum entry for ${BINARY_NAME}, skipping verification."
    fi
else
    echo "Warning: could not download checksums.txt, skipping verification."
fi
rm -f "$TMP_SUM"

chmod +x "$TMP_BIN"
"$TMP_BIN" --version >/dev/null 2>&1 || { echo "ERROR: downloaded file is not a valid PyMon binary"; rm -f "$TMP_BIN"; exit 1; }

# --- Install files --------------------------------------------------------
echo "[2/4] Installing to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

# A broken previous install may have left /opt/pymon/pymon as a directory
# (mv would then tuck the binary inside it). Clean it up so the target is a file.
if [ -d "$INSTALL_DIR/pymon" ]; then
    echo "Removing stale directory at $INSTALL_DIR/pymon (leftover from a previous install)..."
    rm -rf "$INSTALL_DIR/pymon"
fi

install -m 0755 "$TMP_BIN" "$INSTALL_DIR/pymon"

# Sanity check: the installed binary must run.
if ! "$INSTALL_DIR/pymon" --version >/dev/null 2>&1; then
    echo "ERROR: installed binary at $INSTALL_DIR/pymon is not executable/runnable."
    echo "Check the file with: file $INSTALL_DIR/pymon"
    rm -f "$TMP_BIN"
    exit 1
fi

if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    # fetch example config from the release source (fallback to local copy)
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "https://raw.githubusercontent.com/${REPO}/main/config.example.yml" -o "$CONFIG_DIR/config.yml" \
            || cp "$(dirname "$0")/config.example.yml" "$CONFIG_DIR/config.yml" 2>/dev/null || true
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$CONFIG_DIR/config.yml" "https://raw.githubusercontent.com/${REPO}/main/config.example.yml" \
            || cp "$(dirname "$0")/config.example.yml" "$CONFIG_DIR/config.yml" 2>/dev/null || true
    fi
fi

# --- System user -----------------------------------------------------------
echo "[3/4] Creating system user and service..."
if ! id pymon >/dev/null 2>&1; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" pymon
fi
chown -R pymon:pymon "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

# Stop any previously running instance (e.g. the old Python service) so the
# newly installed Go binary actually takes over the port.
systemctl stop $SERVICE_NAME 2>/dev/null || true

cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=PyMon NOC Monitoring
After=network.target

[Service]
User=pymon
Group=pymon
ExecStart=$INSTALL_DIR/pymon server --config $CONFIG_DIR/config.yml
Restart=always
RestartSec=5
Environment=CONFIG_PATH=$CONFIG_DIR/config.yml
Environment=DATA_DIR=$DATA_DIR
Environment=LOG_DIR=$LOG_DIR
Environment=DB_PATH=$DATA_DIR/pymon.db

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME

# --- Admin password ---------------------------------------------------------
# On a FIRST install (no admin user yet) we generate a password, set it and
# print it right here. On a re-install we PRESERVE existing credentials
# (unless PYMON_ADMIN_PASSWORD is set, which forces a reset).
HAS_ADMIN="$(sudo -u pymon DB_PATH="$DATA_DIR/pymon.db" "$INSTALL_DIR/pymon" has-admin --config "$CONFIG_DIR/config.yml" 2>/dev/null || echo no)"

ADMIN_SET=0
if [ "$HAS_ADMIN" != "yes" ] || [ -n "$PYMON_ADMIN_PASSWORD" ]; then
    if [ -n "$PYMON_ADMIN_PASSWORD" ]; then
        ADMIN_PW="$PYMON_ADMIN_PASSWORD"
    else
        ADMIN_PW="$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 18)"
        if [ -z "$ADMIN_PW" ]; then ADMIN_PW="PyMon$(date +%s)"; fi
    fi
    sudo -u pymon PYMON_ADMIN_PASSWORD="$ADMIN_PW" DB_PATH="$DATA_DIR/pymon.db" \
        "$INSTALL_DIR/pymon" reset-admin --config "$CONFIG_DIR/config.yml"
    echo "$ADMIN_PW" > "$DATA_DIR/admin_password.txt"
    chown pymon:pymon "$DATA_DIR/admin_password.txt"
    chmod 600 "$DATA_DIR/admin_password.txt"
    ADMIN_SET=1
fi

# restart (not start) so an already-running old instance is replaced.
systemctl restart $SERVICE_NAME

# --- Health check -----------------------------------------------------------
echo -n "Waiting for the service to become healthy..."
for i in $(seq 1 15); do
    if curl -fsS "http://localhost:10000/api/v1/health" >/dev/null 2>&1; then
        echo " OK"
        break
    fi
    if [ "$i" = "15" ]; then
        echo " FAILED"
        echo "Check the service log: journalctl -u $SERVICE_NAME"
    else
        echo -n "."
        sleep 1
    fi
done

# --- Summary ---------------------------------------------------------------
echo "[4/4] Done."
echo ""
echo "PyMon NOC installed successfully:"
echo "  Binary:   $INSTALL_DIR/pymon"
echo "  Config:   $CONFIG_DIR/config.yml"
echo "  Database: $DATA_DIR/pymon.db"
echo "  Service:  systemctl status $SERVICE_NAME"
echo ""
echo "Dashboard: http://localhost:10000/"
echo ""
if [ "$ADMIN_SET" = "1" ]; then
    echo "===================================="
    echo "  Логін:    admin"
    echo "  Пароль:   $ADMIN_PW"
    echo "===================================="
    echo ""
    echo "При вході дашборд попросить змінити пароль."
    echo "Пароль також збережено: $DATA_DIR/admin_password.txt (видаліть після входу)"
    echo "  sudo rm $DATA_DIR/admin_password.txt"
else
    echo "Інсталяцію виявлено повторно — існуючі облікові дані збережено."
    echo "Якщо треба скинути пароль адміна:"
    echo "  sudo PYMON_ADMIN_PASSWORD='YourStrongPass123' $INSTALL_DIR/pymon reset-admin --config $CONFIG_DIR/config.yml"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "  Логін: admin / YourStrongPass123"
fi
echo ""
echo "Installed version: $("$INSTALL_DIR/pymon" --version)"
