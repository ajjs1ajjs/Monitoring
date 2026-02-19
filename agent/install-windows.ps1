# PyMon Agent for Windows
# Like windows_exporter but for PyMon

param(
    [string]$ServerUrl = "http://localhost:8090",
    [string]$ApiKey = "",
    [int]$AgentPort = 9100
)

Write-Host "==========================================" -ForegroundColor Green
Write-Host "   PyMon Agent Installer for Windows" -ForegroundColor Green
Write-Host "   System Monitoring Agent" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Error: Please run as Administrator" -ForegroundColor Red
    exit 1
}

$InstallDir = "C:\Program Files\PyMonAgent"
$ServiceName = "PyMonAgent"

# Create directories
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null

# Create agent script
$AgentScript = @'
#!/usr/bin/env python3
"""PyMon Agent - System metrics collector for Windows"""

import os
import sys
import time
import json
import socket
import requests
from datetime import datetime

# Windows-specific imports
try:
    import psutil
    import wmi
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WINDOWS = True
except ImportError:
    WINDOWS = False
    print("Warning: Running in limited mode without Windows-specific modules")

# Configuration
SERVER_URL = os.getenv("PYMON_SERVER", "http://localhost:8090")
API_KEY = os.getenv("PYMON_API_KEY", "")
HOSTNAME = socket.gethostname()
AGENT_PORT = int(os.getenv("PYMON_AGENT_PORT", "9100"))

def collect_metrics():
    """Collect system metrics like windows_exporter"""
    metrics = {
        "hostname": HOSTNAME,
        "timestamp": datetime.utcnow().isoformat(),
        "os_type": "windows",
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
        },
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used
        },
        "disk": {
            "percent": psutil.disk_usage('C:\\').percent,
            "total": psutil.disk_usage('C:\\').total,
            "used": psutil.disk_usage('C:\\').used,
            "free": psutil.disk_usage('C:\\').free
        },
        "network": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
        }
    }
    
    # All disks
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
    
    # Windows-specific WMI data
    if WINDOWS and 'wmi' in sys.modules:
        try:
            c = wmi.WMI()
            # OS info
            os_info = c.Win32_OperatingSystem()[0]
            metrics["windows"] = {
                "os_name": os_info.Caption,
                "os_version": os_info.Version,
                "total_memory": int(os_info.TotalVisibleMemorySize),
                "free_memory": int(os_info.FreePhysicalMemory),
            }
            
            # Process count
            metrics["process_count"] = len(c.Win32_Process())
            
            # Services
            services = c.Win32_Service()
            metrics["services_running"] = len([s for s in services if s.State == "Running"])
            metrics["services_total"] = len(services)
        except Exception as e:
            print(f"WMI error: {e}", file=sys.stderr)
    
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
    """Run HTTP server for Prometheus-style metrics"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                metrics = collect_metrics()
                output = []
                output.append("# HELP windows_cpu_time_total Total CPU time")
                output.append("# TYPE windows_cpu_time_total counter")
                output.append(f"windows_cpu_percent {metrics['cpu']['percent']}")
                output.append(f"windows_memory_percent {metrics['memory']['percent']}")
                output.append(f"windows_disk_percent {metrics['disk']['percent']}")
                output.append(f"windows_net_bytes_received_total {metrics['network']['bytes_recv']}")
                output.append(f"windows_net_bytes_sent_total {metrics['network']['bytes_sent']}")
                
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
            pass
    
    server = HTTPServer(("0.0.0.0", AGENT_PORT), MetricsHandler)
    print(f"Agent HTTP server listening on port {AGENT_PORT}")
    server.serve_forever()

class PyMonAgentService(win32serviceutil.ServiceFramework):
    """Windows Service for PyMon Agent"""
    _svc_name_ = "PyMonAgent"
    _svc_display_name_ = "PyMon Agent"
    _svc_description_ = "System metrics collector for PyMon monitoring"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
    
    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.running = True
        self.main()
    
    def main(self):
        import threading
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        
        while self.running:
            try:
                metrics = collect_metrics()
                send_metrics(metrics)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
            
            time.sleep(15)

def run_console():
    """Run in console mode (for testing)"""
    print(f"PyMon Agent starting...")
    print(f"Server URL: {SERVER_URL}")
    print(f"Agent port: {AGENT_PORT}")
    
    import threading
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    while True:
        try:
            metrics = collect_metrics()
            if send_metrics(metrics):
                print(f"[{datetime.now()}] Metrics sent")
            else:
                print(f"[{datetime.now()}] Failed to send")
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}", file=sys.stderr)
        
        time.sleep(15)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_console()
    else:
        win32serviceutil.HandleCommandLine(PyMonAgentService)
'@

$AgentScript | Out-File -FilePath "$InstallDir\agent.py" -Encoding UTF8

# Create requirements file
@"
psutil
requests
pywin32
wmi
"@ | Out-File -FilePath "$InstallDir\requirements.txt" -Encoding UTF8

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Blue
pip install -r "$InstallDir\requirements.txt" -q

# Create configuration
$Config = @"
SERVER_URL=$ServerUrl
API_KEY=$ApiKey
AGENT_PORT=$AgentPort
"@

$Config | Out-File -FilePath "$InstallDir\config.env" -Encoding UTF8

# Create wrapper script
$Wrapper = @"
@echo off
setlocal
for /f "tokens=1,2 delims==" %%a in ('type "$InstallDir\config.env"') do set %%a=%%b
python "$InstallDir\agent.py" %*
"@

$Wrapper | Out-File -FilePath "$InstallDir\pymon-agent.bat" -Encoding ASCII

# Install as Windows Service
Write-Host "Installing Windows Service..." -ForegroundColor Blue
python "$InstallDir\agent.py" install

# Configure service
sc config $ServiceName start= auto
sc description $ServiceName "System metrics collector for PyMon monitoring server"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   PyMon Agent Installed Successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration file: $InstallDir\config.env" -ForegroundColor Yellow
Write-Host "Edit it to set your PyMon server URL and API key" -ForegroundColor Yellow
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Start Service:   Start-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Stop Service:    Stop-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Service Status:  Get-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Console Mode:    & '$InstallDir\pymon-agent.bat'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Metrics endpoint: http://localhost:$AgentPort/metrics" -ForegroundColor Cyan
Write-Host "Health check:     http://localhost:$AgentPort/health" -ForegroundColor Cyan
Write-Host ""
