# PyMon Agent for Windows
# Like windows_exporter but for PyMon with RAID support

param(
    [string]$ServerUrl = "http://localhost:8090",
    [string]$ApiKey = "",
    [int]$AgentPort = 9100
)

Write-Host "==========================================" -ForegroundColor Green
Write-Host "   PyMon Agent Installer for Windows" -ForegroundColor Green
Write-Host "   System Monitoring Agent with RAID" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Error: Please run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$InstallDir = "C:\Program Files\PyMonAgent"
$ServiceName = "PyMonAgent"

# Create directories
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null

# Create agent script with RAID support
$AgentScript = @'
#!/usr/bin/env python3
"""PyMon Agent - System metrics collector for Windows with RAID support"""

import os
import sys
import time
import json
import socket
import requests
from datetime import datetime

# Configuration
SERVER_URL = os.getenv("PYMON_SERVER", "http://localhost:8090")
API_KEY = os.getenv("PYMON_API_KEY", "")
HOSTNAME = socket.gethostname()
AGENT_PORT = int(os.getenv("PYMON_AGENT_PORT", "9100"))

# Windows-specific imports
try:
    import psutil
    import wmi
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import win32api
    import win32con
    WINDOWS = True
except ImportError as e:
    WINDOWS = False
    print(f"Warning: Running in limited mode without Windows-specific modules: {e}")

def get_raid_info():
    """Get RAID controller and disk information using WMI"""
    raid_info = {
        "controller": None,
        "arrays": [],
        "physical_disks": [],
        "has_raid": False,
        "storage_spaces": []
    }
    
    if not WINDOWS or 'wmi' not in sys.modules:
        return raid_info
    
    try:
        c = wmi.WMI()
        
        # Get physical disks with media type (SSD/HDD)
        for disk in c.Win32_DiskDrive():
            disk_info = {
                "device": disk.DeviceID,
                "model": disk.Model,
                "size": int(disk.Size) if disk.Size else 0,
                "status": disk.Status,
                "media_type": disk.MediaType if disk.MediaType else "Unknown",
                "interface": disk.InterfaceType if disk.InterfaceType else "Unknown",
                "partitions": disk.Partitions
            }
            raid_info["physical_disks"].append(disk_info)
        
        # Check for RAID configuration via DiskDrive
        raid_controllers = []
        for disk in c.Win32_DiskDrive():
            if "RAID" in disk.Model.upper() or "ARRAY" in disk.Model.upper():
                raid_controllers.append(disk.Model)
        
        if raid_controllers:
            raid_info["controller"] = ", ".join(set(raid_controllers))
            raid_info["has_raid"] = True
        
        # Check for Storage Spaces (Windows 8+ / Server 2012+)
        try:
            for pool in c.MSFT_StoragePool():
                raid_info["has_raid"] = True
                if not raid_info["controller"]:
                    raid_info["controller"] = "Windows Storage Spaces"
                
                space_info = {
                    "name": pool.FriendlyName,
                    "health": pool.HealthStatus,
                    "operational_status": pool.OperationalStatus,
                    "size": pool.Size,
                    "allocated": pool.AllocatedSize,
                    "free": pool.Size - pool.AllocatedSize if pool.Size and pool.AllocatedSize else 0
                }
                raid_info["storage_spaces"].append(space_info)
        except:
            pass  # Storage Spaces might not be available
        
        # Check for Intel RST RAID
        try:
            rst = c.query("SELECT * FROM Win32_PnPEntity WHERE Name LIKE '%Intel%RST%' OR Name LIKE '%Intel%Rapid%'")
            if rst:
                raid_info["has_raid"] = True
                raid_info["controller"] = "Intel Rapid Storage Technology"
        except:
            pass
        
        # Check for LSI/Avago RAID
        try:
            lsi = c.query("SELECT * FROM Win32_PnPEntity WHERE Name LIKE '%LSI%' OR Name LIKE '%MegaRAID%' OR Name LIKE '%Avago%'")
            if lsi:
                raid_info["has_raid"] = True
                controller_name = lsi[0].Name if lsi else "LSI RAID Controller"
                raid_info["controller"] = controller_name
        except:
            pass
        
        # Check for volumes on RAID
        for vol in c.Win32_Volume():
            if vol.DriveLetter:
                vol_info = {
                    "drive": vol.DriveLetter,
                    "label": vol.Label if vol.Label else "",
                    "filesystem": vol.FileSystem if vol.FileSystem else "Unknown",
                    "size": int(vol.Capacity) if vol.Capacity else 0,
                    "free": int(vol.FreeSpace) if vol.FreeSpace else 0,
                    "used_percent": round(((int(vol.Capacity) - int(vol.FreeSpace)) / int(vol.Capacity)) * 100, 1) if vol.Capacity and vol.FreeSpace else 0
                }
                raid_info["arrays"].append(vol_info)
        
        # Check disk SMART status through MSStorageDriver_FailurePredictStatus
        try:
            smart_status = []
            for disk in c.MSStorageDriver_FailurePredictStatus():
                smart_status.append({
                    "instance": disk.InstanceName,
                    "predict_failure": disk.PredictFailure,
                    "reason": disk.Reason if hasattr(disk, 'Reason') else ""
                })
            raid_info["smart_status"] = smart_status
        except:
            pass
        
        # Get logical disks with detailed info
        for ld in c.Win32_LogicalDisk():
            if ld.DriveType == 3:  # Fixed disk
                try:
                    usage = psutil.disk_usage(ld.DeviceID)
                    raid_info["arrays"].append({
                        "drive": ld.DeviceID,
                        "filesystem": ld.FileSystem if ld.FileSystem else "Unknown",
                        "size": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "used_percent": round(usage.percent, 1)
                    })
                except:
                    pass
        
    except Exception as e:
        raid_info["error"] = str(e)
    
    return raid_info

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
        },
        "raid": get_raid_info()
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
            
            # System uptime
            metrics["uptime_seconds"] = int(float(os_info.LocalDateTime[:14]) - float(os_info.LastBootUpTime[:14])) if len(os_info.LocalDateTime) >= 14 and len(os_info.LastBootUpTime) >= 14 else 0
            
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

def format_prometheus_metrics(metrics):
    """Format metrics in Prometheus exposition format"""
    output = []
    
    # CPU metrics
    output.append("# HELP windows_cpu_percent CPU usage percentage")
    output.append("# TYPE windows_cpu_percent gauge")
    output.append(f"windows_cpu_percent {metrics['cpu']['percent']}")
    output.append(f"windows_cpu_count {metrics['cpu']['count']}")
    
    # Memory metrics
    output.append("# HELP windows_memory_percent Memory usage percentage")
    output.append("# TYPE windows_memory_percent gauge")
    output.append(f"windows_memory_percent {metrics['memory']['percent']}")
    output.append(f"windows_memory_total_bytes {metrics['memory']['total']}")
    output.append(f"windows_memory_used_bytes {metrics['memory']['used']}")
    
    # Disk metrics
    output.append("# HELP windows_disk_percent Disk usage percentage")
    output.append("# TYPE windows_disk_percent gauge")
    output.append(f"windows_disk_percent {metrics['disk']['percent']}")
    
    for part in metrics.get('disks', []):
        drive = part['mountpoint'].replace(':', '').replace('\\', '')
        output.append(f'windows_disk_usage_percent{{drive="{drive}",device="{part["device"]}"}} {part["percent"]}')
    
    # Network metrics
    output.append("# HELP windows_net_bytes_received_total Total bytes received")
    output.append("# TYPE windows_net_bytes_received_total counter")
    output.append(f"windows_net_bytes_received_total {metrics['network']['bytes_recv']}")
    output.append("# HELP windows_net_bytes_sent_total Total bytes sent")
    output.append("# TYPE windows_net_bytes_sent_total counter")
    output.append(f"windows_net_bytes_sent_total {metrics['network']['bytes_sent']}")
    
    # Services
    output.append("# HELP windows_services_total Total number of services")
    output.append("# TYPE windows_services_total gauge")
    output.append(f"windows_services_total {metrics.get('services_total', 0)}")
    output.append("# HELP windows_services_running Number of running services")
    output.append("# TYPE windows_services_running gauge")
    output.append(f"windows_services_running {metrics.get('services_running', 0)}")
    
    # RAID metrics
    if metrics.get('raid', {}).get('has_raid'):
        output.append("# HELP windows_raid_arrays_total Number of RAID arrays/volumes")
        output.append("# TYPE windows_raid_arrays_total gauge")
        output.append(f"windows_raid_arrays_total {len(metrics['raid']['arrays'])}")
        
        output.append("# HELP windows_raid_physical_disks_total Number of physical RAID disks")
        output.append("# TYPE windows_raid_physical_disks_total gauge")
        output.append(f"windows_raid_physical_disks_total {len(metrics['raid']['physical_disks'])}")
        
        # Physical disk status
        output.append("# HELP windows_raid_disk_status Physical disk status (1=healthy, 0=failed)")
        output.append("# TYPE windows_raid_disk_status gauge")
        for disk in metrics['raid']['physical_disks']:
            status = 1 if disk.get('status', '').lower() in ['ok', 'healthy'] else 0
            model = disk.get('model', 'unknown').replace('"', '\\"')
            output.append(f'windows_raid_disk_status{{device="{disk["device"]}",model="{model}"}} {status}')
    
    return "\n".join(output)

def run_http_server():
    """Run HTTP server for Prometheus-style metrics"""
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
                self.wfile.write(json.dumps(metrics, indent=2).encode())
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
    _svc_description_ = "System metrics collector for PyMon monitoring with RAID support"
    
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
    print(f"RAID Support: Enabled")
    
    import threading
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    while True:
        try:
            metrics = collect_metrics()
            if send_metrics(metrics):
                print(f"[{datetime.now()}] Metrics sent - RAID: {metrics['raid']['has_raid']}")
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
$pipResult = pip install -r "$InstallDir\requirements.txt" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Some packages may not have installed correctly" -ForegroundColor Yellow
    Write-Host $pipResult -ForegroundColor Gray
}

# Test Python imports
Write-Host "Testing agent..." -ForegroundColor Blue
python -c "import psutil; import wmi; import win32service; print('All imports successful')" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Some Python packages missing. Service may not work correctly." -ForegroundColor Yellow
}

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
setlocal enabledelayedexpansion
set "CONFIG_FILE=$InstallDir\config.env"
if exist "%CONFIG_FILE%" (
    for /f "tokens=1,2 delims==" %%a in (%CONFIG_FILE%) do (
        set "%%a=%%b"
    )
)
python "$InstallDir\agent.py" %*
"@

$Wrapper | Out-File -FilePath "$InstallDir\pymon-agent.bat" -Encoding ASCII

# Stop and remove existing service if exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc delete $ServiceName | Out-Null
    Start-Sleep -Seconds 2
}

# Install as Windows Service
Write-Host "Installing Windows Service..." -ForegroundColor Blue

# Install the service using Python
$installResult = python "$InstallDir\agent.py" install 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Service installation output: $installResult" -ForegroundColor Gray
}

# Configure service startup and description
$scResult = sc config $ServiceName start= auto 2>&1
sc description $ServiceName "System metrics collector for PyMon monitoring server with RAID support" 2>&1 | Out-Null
sc failure $ServiceName reset= 86400 actions= restart/60000/restart/60000/restart/60000 2>&1 | Out-Null

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   PyMon Agent Installed Successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration file: $InstallDir\config.env" -ForegroundColor Yellow
Write-Host "Edit it to set your PyMon server URL and API key" -ForegroundColor Yellow
Write-Host ""
Write-Host "Service Commands:" -ForegroundColor Cyan
Write-Host "  Start Service:   Start-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Stop Service:    Stop-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Restart Service: Restart-Service $ServiceName" -ForegroundColor Cyan
Write-Host "  Service Status:  Get-Service $ServiceName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Console Mode (for testing):" -ForegroundColor Cyan
Write-Host "  & '$InstallDir\pymon-agent.bat'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Metrics endpoints:" -ForegroundColor Cyan
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1).IPAddress
if (-not $ip) { $ip = "localhost" }
Write-Host "  http://${ip}:$AgentPort/metrics     - Prometheus format" -ForegroundColor Cyan
Write-Host "  http://${ip}:$AgentPort/api/metrics - JSON format with RAID info" -ForegroundColor Cyan
Write-Host "  http://${ip}:$AgentPort/health      - Health check" -ForegroundColor Cyan
Write-Host ""

# Check if service was created successfully
$newService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($newService) {
    Write-Host "Service status: $($newService.Status)" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the service, run:" -ForegroundColor Yellow
    Write-Host "  Start-Service $ServiceName" -ForegroundColor Yellow
} else {
    Write-Host "WARNING: Service may not have been created successfully" -ForegroundColor Red
    Write-Host "You can run the agent in console mode instead:" -ForegroundColor Yellow
    Write-Host "  & '$InstallDir\pymon-agent.bat'" -ForegroundColor Yellow
}
Write-Host ""
