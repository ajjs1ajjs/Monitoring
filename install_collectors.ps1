# Від імені Адміна!
# Скопіюй і встав в PowerShell

Write-Host "Downloading windows_exporter..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://github.com/prometheus-community/windows_exporter/releases/download/v0.25.0/windows_exporter-0.25.0-amd64.msi" -OutFile "$env:TEMP\we.msi"

Write-Host "Installing with collectors: cpu,memory,logical_disk,net,os,system" -ForegroundColor Cyan
Start-Process msiexec -ArgumentList "/i", "$env:TEMP\we.msi", "ENABLED_COLLECTORS=cpu,memory,logical_disk,net,os,system", "/quiet", "/norestart" -Wait

Write-Host "Starting service..." -ForegroundColor Cyan
Start-Service windows_exporter

Start-Sleep 3

Write-Host "`nChecking metrics..." -ForegroundColor Cyan
$metrics = Invoke-WebRequest "http://localhost:9182/metrics" -UseBasicParsing

if ($metrics.Content -match "windows_logical_disk") {
    Write-Host "SUCCESS! logical_disk collector enabled" -ForegroundColor Green
} else {
    Write-Host "ERROR: logical_disk not found" -ForegroundColor Red
}

if ($metrics.Content -match "windows_memory_physical") {
    Write-Host "SUCCESS! memory collector enabled" -ForegroundColor Green
} else {
    Write-Host "ERROR: memory not found" -ForegroundColor Red
}

Remove-Item "$env:TEMP\we.msi" -Force
