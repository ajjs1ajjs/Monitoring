# PyMon - Windows Installation Script
# Run as Administrator

param(
    [string]$Port = "10000",
    [string]$InstallDir = "",
    [switch]$Service,
    [switch]$Help
)

# Auto-detect InstallDir if not provided
if ($InstallDir -eq "") {
    if (Test-Path ".\pymon\__init__.py") {
        $InstallDir = (Get-Item ".").FullName
    } else {
        $InstallDir = "C:\pymon"
    }
}

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host @"
PyMon Installation Script

Usage: .\install.ps1 [OPTIONS]

Options:
  -Port PORT       Set port (default: 10000)
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

$VERSION = "2.1.0"
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
& $pythonCmd -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Info "Installing pip..."
    & $pythonCmd -m ensurepip --upgrade | Out-Null
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

# Extract outside the install directory so updates do not merge with stale files
Write-Info "Extracting..."
$extractRoot = Join-Path $env:TEMP ("pymon_extract_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null
Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force
Remove-Item $zipPath -Force

# Find extracted directory
$extractedDir = Get-ChildItem $extractRoot -Directory | Where-Object { $_.Name -match "^Monitoring" } | Select-Object -First 1
if (-not $extractedDir) {
    Write-Error "Failed to find extracted files"
    exit 1
}

# Remove old code artifacts but preserve runtime data, config, logs, backups, and venv
Write-Info "Installing..."
$staleItems = @(
    "pymon", "docs", "examples", "agent", "scripts", ".github",
    "dashboard_unified.py", "PROJECT_REPORT.md", "config.json",
    "pyproject.toml", "requirements.txt", "README.md", "CHANGELOG.md",
    "Dockerfile", "docker-compose.yml", "run.bat", "run.sh", "install_exporter.ps1"
)
foreach ($item in $staleItems) {
    $target = Join-Path $InstallDir $item
    if (Test-Path $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
Copy-Item -Path (Join-Path $extractedDir.FullName "*") -Destination $InstallDir -Recurse -Force
Remove-Item -LiteralPath $extractRoot -Recurse -Force

# Create virtual environment
Write-Info "Creating virtual environment..."
Set-Location $InstallDir
& $pythonCmd -m venv "$InstallDir\venv"

# Install dependencies
Write-Info "Installing Python packages..."
$pipExe = "$InstallDir\venv\Scripts\pip.exe"
$venvPython = "$InstallDir\venv\Scripts\python.exe"

# Upgrade pip first
$pipUpgrade = Start-Process -FilePath $venvPython -ArgumentList "-m","pip","install","--upgrade","pip" -NoNewWindow -Wait -PassThru
if ($pipUpgrade.ExitCode -ne 0) {
    Write-Warn "pip upgrade had issues, continuing..."
}

# Install requirements
$pipInstall = Start-Process -FilePath $pipExe -ArgumentList "install","-r","requirements.txt" -NoNewWindow -Wait -PassThru
if ($pipInstall.ExitCode -ne 0) {
    Write-Error "Failed to install requirements"
    exit 1
}

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
  admin_password: chang3m3N0w!
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
    Write-Info "Registering PyMon as a background service via Task Scheduler..."
    
    $taskName = "PyMonServer"
    $venvPython = "$InstallDir\venv\Scripts\python.exe"
    $arguments = "-m pymon server --config `"$configPath`""
    
    $action = New-ScheduledTaskAction -Execute $venvPython -Argument $arguments -WorkingDirectory $InstallDir
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings
        Start-ScheduledTask -TaskName $taskName
        Write-Success "PyMon registered and started as background task '$taskName'"
    } catch {
        Write-Warn "Failed to register task. Ensure you are running as Administrator."
    }
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
Write-Host "  Password: chang3m3N0w!" -ForegroundColor Yellow
Write-Host "  IMPORTANT: Change this password immediately after login!" -ForegroundColor Red
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
