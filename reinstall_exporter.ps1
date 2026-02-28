# Reinstall windows_exporter with logical_disk collector
# Run as Administrator

$svc = Get-Service -Name windows_exporter -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "Stopping service..."
    Stop-Service -Name windows_exporter -Force
    Start-Sleep -Seconds 2
}

# Download
$url = "https://github.com/prometheus-community/windows_exporter/releases/download/v0.25.0/windows_exporter-0.25.0-amd64.msi"
$output = "$env:TEMP\we.msi"
Write-Host "Downloading..."
Invoke-WebRequest -Uri $url -OutFile $output

# Install with logical_disk
Write-Host "Installing with logical_disk collector..."
Start-Process msiexec -ArgumentList "/i $output ENABLED_COLLECTORS=cpu,cs,memory,net,logical_disk,os,system /quiet" -Wait

Write-Host "Starting service..."
Start-Service windows_exporter
Start-Sleep -Seconds 3

# Verify
$r = Invoke-WebRequest "http://localhost:9182/metrics" -UseBasicParsing
if ($r.Content -match "windows_logical_disk") {
    Write-Host "SUCCESS - logical_disk collector enabled!"
} else {
    Write-Host "WARNING - logical_disk not found"
}

Remove-Item $output -Force
