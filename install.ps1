# PyMon NOC (Go) - Windows build/run helper
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$VERSION = "3.0.0"

Write-Host "PyMon NOC $VERSION (Go) build" -ForegroundColor Green

if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Go 1.25+ is required. Install from https://go.dev/dl/" -ForegroundColor Red
    exit 1
}

Write-Host "Building pymon.exe..."
go build -o pymon.exe ./cmd/pymon

Write-Host ""
Write-Host "Built. Start with:" -ForegroundColor Cyan
Write-Host "  .\run.bat --port 10000" -ForegroundColor Yellow
Write-Host ""
Write-Host "First run creates the admin user and prints the generated password." -ForegroundColor Yellow
