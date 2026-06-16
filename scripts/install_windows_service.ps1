# PyMon - Windows Service Installer (via Task Scheduler)
# This script registers PyMon as a background task that starts automatically on boot.

$projectName = "PyMonServer"
$workDir = "D:\CODE\Monitoring"
$pythonExe = Join-Path $workDir ".venv\Scripts\python.exe"
$arguments = "-m pymon server"

# Check if .venv exists
if (-not (Test-Path $pythonExe)) {
    Write-Host "Error: Virtual environment not found at $pythonExe" -ForegroundColor Red
    Write-Host "Please run run.bat first to initialize the environment." -ForegroundColor Yellow
    exit 1
}

Write-Host "NOTE: install.ps1 now handles both install and update." -ForegroundColor Yellow
Write-Host "Run the following command again to update:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File install.ps1 -Service" -ForegroundColor White
Write-Host ""

Write-Host "Registering PyMon as a background service..." -ForegroundColor Cyan

# Create the action
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $arguments -WorkingDirectory $workDir

# Create the trigger (At system startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create the principal (Run as SYSTEM to stay in background)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the task
try {
    Unregister-ScheduledTask -TaskName $projectName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $projectName -Action $action -Trigger $trigger -Principal $principal -Settings $settings
    
    Write-Host "Success! PyMon is now registered as a background service." -ForegroundColor Green
    Write-Host "It will start automatically when Windows boots." -ForegroundColor White
    
    # Start it now
    Start-ScheduledTask -TaskName $projectName
    Write-Host "Service started successfully." -ForegroundColor Green
} catch {
    Write-Host "Error: Failed to register task. Please run PowerShell as Administrator." -ForegroundColor Red
    Write-Host $_
}
