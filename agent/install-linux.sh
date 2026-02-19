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
"""PyMon Agent - System metrics collector for Linux with RAID support"""

import os
import sys
import time
import json
import psutil
import socket
import requests
import subprocess
import re
from datetime import datetime

# Configuration
SERVER_URL = os.getenv("PYMON_SERVER", "http://localhost:8090")
API_KEY = os.getenv("PYMON_API_KEY", "")
HOSTNAME = socket.gethostname()
AGENT_PORT = int(os.getenv("PYMON_AGENT_PORT", "9100"))

def run_command(cmd, shell=False):
    """Run shell command and return output"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def get_raid_info():
    """Get RAID controller and disk information"""
    raid_info = {
        "controller": None,
        "arrays": [],
        "physical_disks": [],
        "has_raid": False
    }
    
    # Check for Software RAID (mdadm)
    try:
        mdstat = run_command("cat /proc/mdstat")
        if mdstat and "Personalities" in mdstat:
            raid_info["has_raid"] = True
            raid_info["type"] = "software"
            raid_info["controller"] = "Linux mdadm"
            
            # Parse mdstat
            for line in mdstat.split('\n'):
                if line.startswith('md'):
                    parts = line.split()
                    array_name = parts[0]
                    raid_level = ""
                    devices = []
                    status = "unknown"
                    
                    for part in parts:
                        if part.startswith('[') and part.endswith(']'):
                            raid_level = part.strip('[]')
                        if '[' in part and ']' in part and 'raid' not in part:
                            status = part.strip('[]')
                    
                    raid_info["arrays"].append({
                        "name": array_name,
                        "raid_level": raid_level,
                        "status": status,
                        "type": "mdadm"
                    })
            
            # Get detailed info with mdadm
            mdadm_detail = run_command("mdadm --detail --scan 2>/dev/null")
            raid_info["mdadm_scan"] = mdadm_detail
    except:
        pass
    
    # Check for MegaRAID/LSI (megacli or storcli)
    try:
        # Try storcli first (newer)
        storcli = run_command("which storcli")
        if storcli:
            raid_info["controller"] = "LSI MegaRAID (storcli)"
            raid_info["has_raid"] = True
            raid_info["type"] = "hardware"
            
            # Get virtual drives
            vds = run_command("storcli /c0/vall show 2>/dev/null | grep -E '^[0-9]'")
            for line in vds.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        raid_info["arrays"].append({
                            "name": f"VD{parts[0]}",
                            "raid_level": parts[1],
                            "status": parts[2],
                            "type": "megaraid"
                        })
            
            # Get physical disks
            pds = run_command("storcli /c0/eall/sall show 2>/dev/null | grep -E '^[0-9]:'")
            for line in pds.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        raid_info["physical_disks"].append({
                            "enclosure": parts[0].split(':')[0],
                            "slot": parts[0].split(':')[1],
                            "state": parts[2],
                            "size": parts[3],
                            "model": ' '.join(parts[4:]) if len(parts) > 4 else "Unknown"
                        })
        
        # Try megacli (older)
        megacli = run_command("which MegaCli")
        if megacli:
            raid_info["controller"] = "LSI MegaRAID (MegaCli)"
            raid_info["has_raid"] = True
            raid_info["type"] = "hardware"
            
            # Get virtual drives
            vds = run_command("MegaCli -LDInfo -Lall -aALL -NoLog 2>/dev/null | grep -E 'RAID Level|State'")
            vd_lines = vds.split('\n')
            for i in range(0, len(vd_lines)-1, 2):
                if 'Primary' in vd_lines[i] and i+1 < len(vd_lines):
                    raid_level = vd_lines[i].split(':')[1].strip().split(',')[0]
                    status = vd_lines[i+1].split(':')[1].strip()
                    raid_info["arrays"].append({
                        "name": f"VD{i//2}",
                        "raid_level": raid_level,
                        "status": status,
                        "type": "megaraid"
                    })
    except:
        pass
    
    # Check for HP Smart Array (ssacli)
    try:
        ssacli = run_command("which ssacli")
        if ssacli:
            raid_info["controller"] = "HP Smart Array"
            raid_info["has_raid"] = True
            raid_info["type"] = "hardware"
            
            # Get arrays
            arrays = run_command("ssacli ctrl all ld all show detail 2>/dev/null | grep -E 'logicaldrive|RAID|Status'")
            current_array = {}
            for line in arrays.split('\n'):
                if 'logicaldrive' in line:
                    if current_array:
                        raid_info["arrays"].append(current_array)
                    current_array = {"name": line.split()[0], "type": "smartarray"}
                elif 'RAID' in line:
                    current_array["raid_level"] = line.strip()
                elif 'Status' in line:
                    current_array["status"] = line.split(':')[1].strip()
            if current_array:
                raid_info["arrays"].append(current_array)
    except:
        pass
    
    # Check for Adaptec (arcconf)
    try:
        arcconf = run_command("which arcconf")
        if arcconf:
            raid_info["controller"] = "Adaptec"
            raid_info["has_raid"] = True
            raid_info["type"] = "hardware"
    except:
        pass
    
    # Get SMART status for all physical disks
    raid_info["smart_status"] = []
    try:
        # List all block devices
        devices = run_command("lsblk -ndo NAME,TYPE | grep disk | awk '{print $1}'")
        for device in devices.split('\n'):
            if device.strip():
                smart = run_command(f"smartctl -H /dev/{device.strip()} 2>/dev/null | grep -i 'test result'")
                status = "unknown"
                if "PASSED" in smart.upper():
                    status = "PASSED"
                elif "FAILED" in smart.upper():
                    status = "FAILED"
                
                raid_info["smart_status"].append({
                    "device": f"/dev/{device.strip()}",
                    "smart_status": status
                })
    except:
        pass
    
    return raid_info

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
        "boot_time": psutil.boot_time(),
        "raid": get_raid_info()
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

def format_prometheus_metrics(metrics):
    """Format metrics in Prometheus exposition format"""
    output = []
    
    # CPU metrics
    output.append("# HELP node_cpu_percent CPU usage percentage")
    output.append("# TYPE node_cpu_percent gauge")
    output.append(f"node_cpu_percent {metrics['cpu']['percent']}")
    output.append(f"node_cpu_count {metrics['cpu']['count']}")
    
    # Memory metrics
    output.append("# HELP node_memory_percent Memory usage percentage")
    output.append("# TYPE node_memory_percent gauge")
    output.append(f"node_memory_percent {metrics['memory']['percent']}")
    output.append(f"node_memory_total_bytes {metrics['memory']['total']}")
    output.append(f"node_memory_used_bytes {metrics['memory']['used']}")
    output.append(f"node_memory_available_bytes {metrics['memory']['available']}")
    
    # Disk metrics
    output.append("# HELP node_disk_percent Disk usage percentage")
    output.append("# TYPE node_disk_percent gauge")
    output.append(f"node_disk_percent {metrics['disk']['percent']}")
    
    for part in metrics.get('disks', []):
        device = part['device'].replace('/', '_').replace('-', '_')
        output.append(f'node_disk_usage_percent{{device="{device}",mountpoint="{part["mountpoint"]}"}} {part["percent"]}')
    
    # Network metrics
    output.append("# HELP node_network_receive_bytes Total bytes received")
    output.append("# TYPE node_network_receive_bytes counter")
    output.append(f"node_network_receive_bytes {metrics['network']['bytes_recv']}")
    output.append("# HELP node_network_transmit_bytes Total bytes transmitted")
    output.append("# TYPE node_network_transmit_bytes counter")
    output.append(f"node_network_transmit_bytes {metrics['network']['bytes_sent']}")
    
    # Load average
    output.append("# HELP node_load1 Load average 1 minute")
    output.append("# TYPE node_load1 gauge")
    output.append(f"node_load1 {metrics['load']['1min']}")
    output.append(f"node_load5 {metrics['load']['5min']}")
    output.append(f"node_load15 {metrics['load']['15min']}")
    
    # RAID metrics
    if metrics.get('raid', {}).get('has_raid'):
        output.append("# HELP node_raid_arrays_total Number of RAID arrays")
        output.append("# TYPE node_raid_arrays_total gauge")
        output.append(f"node_raid_arrays_total {len(metrics['raid']['arrays'])}")
        
        output.append("# HELP node_raid_physical_disks_total Number of physical RAID disks")
        output.append("# TYPE node_raid_physical_disks_total gauge")
        output.append(f"node_raid_physical_disks_total {len(metrics['raid']['physical_disks'])}")
        
        # Array status
        output.append("# HELP node_raid_array_status RAID array status (1=healthy, 0=degraded)")
        output.append("# TYPE node_raid_array_status gauge")
        for arr in metrics['raid']['arrays']:
            status = 1 if arr.get('status', '').upper() in ['CLEAN', 'ACTIVE', 'OPTIMAL', 'OK'] else 0
            output.append(f'node_raid_array_status{{array="{arr["name"]}",level="{arr.get("raid_level", "unknown")}"}} {status}')
    
    return "\n".join(output)

def run_http_server():
    """Run HTTP server for Prometheus-style metrics scraping"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                metrics = collect_metrics()
                output = format_prometheus_metrics(metrics)
                
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(output.encode())
            elif self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "healthy"}).encode())
            elif self.path == "/api/metrics":
                metrics = collect_metrics()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(metrics).encode())
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

# Install psutil and smartmontools
if [[ "$OS_NAME" == *"Ubuntu"* ]] || [[ "$OS_NAME" == *"Debian"* ]]; then
    apt-get update -qq
    apt-get install -y -qq python3-psutil python3-requests smartmontools 2>/dev/null || true
    
    # Install RAID management tools if available
    apt-get install -y -qq mdadm 2>/dev/null || true
fi

# Fallback: install Python packages via pip if not available via apt
if ! python3 -c "import psutil" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python packages via pip...${NC}"
    pip3 install psutil requests --break-system-packages -q 2>/dev/null || \
    pip3 install psutil requests --user -q
fi

# Create systemd service
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=PyMon Agent - System Metrics Collector with RAID Support
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PYMON_SERVER=http://your-pymon-server:8090"
Environment="PYMON_API_KEY=your-api-key"
Environment="PYMON_AGENT_PORT=9100"
Environment="PYTHONUNBUFFERED=1"
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

# Enable and reload systemd
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
echo "  sudo systemctl start $SERVICE_NAME     - Start the agent"
echo "  sudo systemctl stop $SERVICE_NAME      - Stop the agent"
echo "  sudo systemctl restart $SERVICE_NAME   - Restart the agent"
echo "  sudo systemctl status $SERVICE_NAME    - Check status"
echo "  sudo journalctl -u $SERVICE_NAME -f    - View logs"
echo ""
echo "Metrics endpoints:"
echo "  http://$(hostname -I | awk '{print $1}'):9100/metrics     - Prometheus format"
echo "  http://$(hostname -I | awk '{print $1}'):9100/api/metrics - JSON format"
echo "  http://$(hostname -I | awk '{print $1}'):9100/health      - Health check"
echo ""
echo -e "${YELLOW}Don't forget to configure the server URL!${NC}"
