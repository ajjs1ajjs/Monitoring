# PyMon NOC (Go) - Windows installer
# Downloads the pre-built binary from GitHub Releases.
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
#     or: iwr https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install.ps1 -OutFile install.ps1; .\install.ps1

$ErrorActionPreference = "Stop"

$VERSION = if ($env:PYMON_VERSION) { $env:PYMON_VERSION } else { "latest" }
$REPO = "ajjs1ajjs/Monitoring"
$BINARY = "pymon-windows-amd64.exe"
$INSTALL_DIR = Join-Path $env:ProgramFiles "PyMon"
$DATA_DIR = Join-Path $env:USERPROFILE "UptimeMonitor\data"
$LOG_DIR = Join-Path $env:USERPROFILE "UptimeMonitor\logs"

Write-Host "PyMon NOC - Windows installer" -ForegroundColor Green
Write-Host "Version: $VERSION" -ForegroundColor Cyan

$url = if ($VERSION -eq "latest") {
    "https://github.com/$REPO/releases/latest/download/$BINARY"
} else {
    "https://github.com/$REPO/releases/download/$VERSION/$BINARY"
}

Write-Host "Downloading $url ..." -ForegroundColor Yellow
$tmp = Join-Path $env:TEMP $BINARY
try {
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
} catch {
    Write-Host "ERROR: download failed. Is release '$VERSION' published?" -ForegroundColor Red
    exit 1
}

# Verify it's a valid PE binary
$bytes = [System.IO.File]::ReadAllBytes($tmp)[0..1]
if (-not ($bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A)) {
    Write-Host "ERROR: downloaded file is not a valid PyMon binary" -ForegroundColor Red
    Remove-Item $tmp -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Installing to $INSTALL_DIR ..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
New-Item -ItemType Directory -Path $DATA_DIR -Force | Out-Null
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
Move-Item -LiteralPath $tmp -Destination (Join-Path $INSTALL_DIR "pymon.exe") -Force

if (-not (Test-Path (Join-Path $INSTALL_DIR "config.yml"))) {
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/$REPO/main/config.example.yml" `
            -OutFile (Join-Path $INSTALL_DIR "config.yml") -UseBasicParsing
    } catch {
        Write-Host "Note: config.example.yml download skipped." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "PyMon installed." -ForegroundColor Green
Write-Host "  Binary: $INSTALL_DIR\pymon.exe"
Write-Host "  Config: $INSTALL_DIR\config.yml"
Write-Host ""
Write-Host "Start it with:" -ForegroundColor Cyan
Write-Host "  & '$INSTALL_DIR\pymon.exe' server --config '$INSTALL_DIR\config.yml'" -ForegroundColor Yellow
Write-Host ""
Write-Host "First run creates the admin user and prints the generated password." -ForegroundColor Yellow
Write-Host "Dashboard: http://localhost:10000/"
