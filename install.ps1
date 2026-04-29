# PyMon - Windows Installation Script
# Run as Administrator

param(
    [string]$Port = "8090",
    [string]$InstallDir = "C:\pymon",
    [switch]$Service,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host @"
PyMon Installation Script

Usage: .\install.ps1 [OPTIONS]

Options:
  -Port PORT       Set port (default: 8090)
  -InstallDir DIR  Installation directory (default: C:\pymon)
  -Service        Register as Windows service
  -Help          Show this help

Examples:
  .\install.ps1                    # Default installation
  .\install.ps1 -Port 9000        # Custom port
  .\install.ps1 -Service        # Install as service

"@
    exit 0
}

$VERSION = "0.1.0"
$GREEN = ""
$RED = ""
$YELLOW = ""
$BLUE = ""

function Write-Success { param([string]$Msg) Write-Host "$GREEN[OK]$NC $Msg" -ForegroundColor Green }
function Write-Info { param([string]$Msg) Write-Host "$BLUE[*]$NC $Msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$Msg) Write-Host "$YELLOW[!]$NC $Msg" -ForegroundColor Yellow }
function Write-Error { param([string]$Msg) Write-Host "$RED[ERROR]$NC $Msg" -ForegroundColor Red }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   PyMon - Installation Script" -ForegroundColor Cyan
Write-Host "   Python Monitoring System v$VERSION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run as Administrator"
    exit 1
}

# Check Python
$pythonCmd = $null
foreach ($ver in @("python3.12", "python3.11", "python3.10", "python", "py")) {
    try {
        $verOut = & $ver --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $verOut -match "Python (\d+\.\d+)") {
            if ([float]$Matches[1] -ge 3.10) {
                $pythonCmd = $ver
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Error "Python 3.10+ not found. Download from https://python.org"
    exit 1
}

Write-Info "Using Python: $pythonCmd"
Write-Success "Python check passed"

# Check pip
& $pythonCmd -m pip --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Info "Installing pip..."
    & $pythonCmd -m ensurepip --upgrade 2>$null
}

# Create directories
Write-Info "Creating directories..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\backups" | Out-Null

# Download from GitHub
Write-Info "Downloading PyMon from GitHub..."
$zipUrl = "https://github.com/ajjs1ajjs/Monitoring/archive/refs/heads/main.zip"
$zipPath = "$env:TEMP\pymon.zip"

try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Error "Failed to download: $_"
    exit 1
}

Write-Success "Downloaded"

# Extract
Write-Info "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
Remove-Item $zipPath -Force

# Find extracted directory
$extractedDir = Get-ChildItem $InstallDir -Directory | Where-Object { $_.Name -match "^Monitoring" } | Select-Object -First 1
if (-not $extractedDir) {
    Write-Error "Failed to find extracted files"
    exit 1
}

# Move contents
Write-Info "Installing..."
Move-Item "$($extractedDir.FullName)\*" "$InstallDir\" -Force -ErrorAction SilentlyContinue
Remove-Item $extractedDir.FullName -Force

# Create virtual environment
Write-Info "Creating virtual environment..."
Set-Location $InstallDir
& $pythonCmd -m venv "$InstallDir\venv"

$venvPip = "$InstallDir\venv\Scripts\pip"
& $venvPip install --upgrade pip 2>&1 | Out-Null
& $venvPip install -r "$InstallDir\requirements.txt" 2>&1 | Out-Null

# Create config
Write-Info "Creating configuration..."
$serverIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" } | Select-Object -First 1).IPAddress
if (-not $serverIP) { $serverIP = "localhost" }

$configContent = @"
server:
  port: $Port
  host: 0.0.0.0
  domain: $serverIP

storage:
  backend: sqlite
  path: $InstallDir\pymon.db
  retention_hours: 168

auth:
  admin_username: admin
  admin_password: changeme
  jwt_expire_hours: 24

scrape_configs:
  - job_name: pymon_self
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs: []

backup:
  enabled: true
  max_backups: 10
  backup_dir: $InstallDir\backups
"@

$configPath = "$InstallDir\config.yml"
if (-not (Test-Path $configPath)) {
    Set-Content -Path $configPath -Value $configContent
}

Write-Success "Installed to: $InstallDir"

# Run as service if requested
if ($Service) {
    Write-Info "Installing as Windows service..."
    
    $serviceName = "PyMon"
    $exePath = "$InstallDir\venv\Scripts\pymon.exe"
    $pyScript = "$InstallDir\pymon\__main__.py"
    
    # Create service wrapper
    $wrapperPath = "$InstallDir\pymon-service.py"
    @"
import sys
sys.path.insert(0, r'$InstallDir')
from pymon.cli import main
if __name__ == '__main__':
    main()
"@ | Set-Content -Path $wrapperPath
    
    # Register with nssm if available, otherwise sc
    $scPath = "sc.exe"
    & $scPath create $serviceName binPath= "python `"$wrapperPath`" --config `"$configPath`"" start= auto
    & $scPath start $serviceName
}

# Final output
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Version:   $VERSION" -ForegroundColor White
Write-Host "  Port:     $Port" -ForegroundColor White
Write-Host "  URL:      http://$serverIP`:$Port/dashboard/" -ForegroundColor White
Write-Host ""
Write-Host "  Username: admin" -ForegroundColor Yellow
Write-Host "  Password: changeme" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To start:" -ForegroundColor Cyan
Write-Host "    Set-Location $InstallDir" -ForegroundColor White
Write-Host "    .\venv\Scripts\Activate" -ForegroundColor White  
Write-Host "    python -m pymon server" -ForegroundColor White
Write-Host ""

if ($Service) {
    Write-Host "  Service:   $serviceName (started)" -ForegroundColor Green
}
Write-Host ""