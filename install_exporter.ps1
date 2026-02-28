# Windows Exporter - Install with collectors for PyMon
# Run as Administrator in PowerShell

$ErrorActionPreference = "Stop"

# Download latest version
$url = "https://github.com/prometheus-community/windows_exporter/releases/download/v0.25.0/windows_exporter-0.25.0-amd64.msi"
$output = "$env:TEMP\windows_exporter.msi"

Write-Host "Downloading windows_exporter..."
Invoke-WebRequest -Uri $url -OutFile $output

# Install with essential collectors for PyMon
$collectors = "cpu,cs,memory,net,logical_disk,os,system,service"

Write-Host "Installing with collectors: $collectors"
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "$output", "ENABLED_COLLECTORS=$collectors", "/quiet", "/norestart" -Wait

Write-Host "Done! Service should be running on http://localhost:9182"

# Test
Start-Sleep -Seconds 3
try {
    $test = Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing
    if ($test.StatusCode -eq 200) {
        Write-Host "SUCCESS: http://localhost:9182/metrics is available"
        
        # Check for key metrics
        $content = $test.Content
        if ($content -match "windows_memory_physical") { Write-Host "[OK] Memory metrics" }
        if ($content -match "windows_cpu_time") { Write-Host "[OK] CPU metrics" }
        if ($content -match "windows_logical_disk") { Write-Host "[OK] Disk metrics" }
    }
} catch {
    Write-Host "WARNING: Could not verify metrics endpoint"
}

Remove-Item $output -Force
