#!/bin/bash
# PyMon Agent Installer for Linux
# Like node_exporter but for PyMon

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

AGENT_VERSION="0.1.0"
INSTALL_DIR="/opt/pymon-agent"
SERVICE_NAME="pymon-agent"
USER="pymon-agent"

echo -e "${GREEN}"
echo "=========================================="
echo "   PyMon Agent Installer for Linux"
echo "   System Monitoring Agent"
echo "=========================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS_NAME${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${BLUE}Installing Python...${NC}"
    if [[ "$OS_NAME" == *"Ubuntu"* ]] || [[ "$OS_NAME" == *"Debian"* ]]; then
        apt-get update -qq && apt-get install -y -qq python3 python3-pip
    elif [[ "$OS_NAME" == *"CentOS"* ]] || [[ "$OS_NAME" == *"Red Hat"* ]] || [[ "$OS_NAME" == *"Fedora"* ]]; then
        yum install -y python3 python3-pip || dnf install -y python3 python3-pip
    fi
fi

# Create user
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/false "$USER"
fi

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "/var/log/pymon-agent"

# Install agent script
cat > "$INSTALL_DIR/agent.py" << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""PyMon Agent - System metrics collector for Linux"""

import os
import sys
import time
import json
import psutil
import socket
import requests
from datetime import datetime

# Configuration
SERVER_URL = os.getenv("PYMON_SERVER", "http://localhost:8090")
API_KEY = os.getenv("PYMON_API_KEY", "")
HOSTNAME = socket.gethostname()
AGENT_PORT = int(os.getenv("PYMON_AGENT_PORT", "9100"))

def collect_metrics():
    """Collect system metrics like node_exporter"""
    metrics = {
        "hostname": HOSTNAME,
        "timestamp": datetime.utcnow().isoformat(),
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
        },
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free
        },
        "network": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
            "packets_sent": psutil.net_io_counters().packets_sent,
            "packets_recv": psutil.net_io_counters().packets_recv
        },
        "load": {
            "1min": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
            "5min": os.getloadavg()[1] if hasattr(os, 'getloadavg') else 0,
            "15min": os.getloadavg()[2] if hasattr(os, 'getloadavg') else 0
        },
        "boot_time": psutil.boot_time()
    }
    
    # Disk usage for all partitions
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "percent": usage.percent,
                "total": usage.total,
                "used": usage.used
            })
        except:
            pass
    metrics["disks"] = partitions
    
    # Network interfaces
    interfaces = {}
    for name, stats in psutil.net_io_counters(pernic=True).items():
        interfaces[name] = {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv
        }
    metrics["network_interfaces"] = interfaces
    
    return metrics

def send_metrics(metrics):
    """Send metrics to PyMon server"""
    try:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["X-API-Key"] = API_KEY
        
        response = requests.post(
            f"{SERVER_URL}/api/v1/agents/metrics",
            json=metrics,
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending metrics: {e}", file=sys.stderr)
        return False

def run_http_server():
    """Run HTTP server for Prometheus-style metrics scraping"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                metrics = collect_metrics()
                # Format as Prometheus exposition format
                output = []
                output.append(f"# HELP node_cpu_seconds_total Total CPU time")
                output.append(f"# TYPE node_cpu_seconds_total counter")
                output.append(f"node_cpu_percent {metrics['cpu']['percent']}")
                output.append(f"node_memory_percent {metrics['memory']['percent']}")
                output.append(f"node_disk_percent {metrics['disk']['percent']}")
                output.append(f"node_network_receive_bytes {metrics['network']['bytes_recv']}")
                output.append(f"node_network_transmit_bytes {metrics['network']['bytes_sent']}")
                
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write("\n".join(output).encode())
            elif self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "healthy"}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress logs
    
    server = HTTPServer(("0.0.0.0", AGENT_PORT), MetricsHandler)
    print(f"Agent HTTP server listening on port {AGENT_PORT}")
    server.serve_forever()

def main():
    print(f"PyMon Agent starting...")
    print(f"Server URL: {SERVER_URL}")
    print(f"Agent port: {AGENT_PORT}")
    
    # Start HTTP server in background thread
    import threading
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Main loop - send metrics to server
    while True:
        try:
            metrics = collect_metrics()
            if send_metrics(metrics):
                print(f"[{datetime.now()}] Metrics sent successfully")
            else:
                print(f"[{datetime.now()}] Failed to send metrics")
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}", file=sys.stderr)
        
        time.sleep(15)  # Send every 15 seconds

if __name__ == "__main__":
    main()
PYTHON_SCRIPT

chmod +x "$INSTALL_DIR/agent.py"

# Install psutil
pip3 install psutil requests -q

# Create systemd service
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=PyMon Agent - System Metrics Collector
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PYMON_SERVER=http://your-pymon-server:8090"
Environment="PYMON_API_KEY=your-api-key"
Environment="PYMON_AGENT_PORT=9100"
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/pymon-agent/agent.log
StandardError=append:/var/log/pymon-agent/agent.error.log

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chown -R "$USER:$USER" "$INSTALL_DIR"
chown -R "$USER:$USER" "/var/log/pymon-agent"
chmod 755 "$INSTALL_DIR"

# Enable service
systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo ""
echo -e "${GREEN}=========================================="
echo "   PyMon Agent Installed Successfully!"
echo "==========================================${NC}"
echo ""
echo "Configuration:"
echo "  Edit /etc/systemd/system/$SERVICE_NAME.service"
echo "  Set PYMON_SERVER to your PyMon server URL"
echo "  Set PYMON_API_KEY (generate in PyMon dashboard)"
echo ""
echo "Commands:"
echo "  sudo systemctl start $SERVICE_NAME"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo -e "${YELLOW}Don't forget to configure the server URL!${NC}"
