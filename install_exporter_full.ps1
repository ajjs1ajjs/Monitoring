# Windows Exporter - Full Install with all collectors
# Run as Administrator

$ErrorActionPreference = "Stop"

# Stop existing service if running
$svc = Get-Service -Name windows_exporter -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "Stopping existing service..."
    Stop-Service -Name windows_exporter -Force
    Start-Sleep -Seconds 2
    
    # Get MSI GUID and uninstall
    $product = Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*windows_exporter*"}
    if ($product) {
        Write-Host "Uninstalling old version..."
        $product.Uninstall()
    }
}

Write-Host "Downloading windows_exporter..."
$url = "https://github.com/prometheus-community/windows_exporter/releases/download/v0.25.0/windows_exporter-0.25.0-amd64.msi"
$output = "$env:TEMP\windows_exporter.msi"
Invoke-WebRequest -Uri $url -OutFile $output

Write-Host "Installing with all collectors..."
# Install with ALL collectors for full metrics
$collectors = @(
    "cpu", "cs", "memory", "net", "logical_disk", 
    "os", "system", "process", "service", "tcp",
    "udp", "scheduled_task", "hyperv", "mssql", "iis"
) -join ","

$args = @("/i", $output, "ENABLED_COLLECTORS=$collectors", "/quiet", "/norestart")
Start-Process -FilePath "msiexec.exe" -ArgumentList $args -Wait

Write-Host "Starting service..."
Start-Service -WindowsExporter -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Verify
$test = Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing -ErrorAction SilentlyContinue
if ($test) {
    Write-Host "SUCCESS! Windows Exporter running at http://localhost:9182/metrics"
    
    # Check for memory metrics
    if ($test.Content -match "windows_cs_physical_memory_bytes") {
        Write-Host "Memory metrics: OK"
    } else {
        Write-Host "WARNING: Memory metrics not found. Check collectors."
    }
} else {
    Write-Host "ERROR: Failed to start service"
}

Remove-Item $output -Force -ErrorAction SilentlyContinue
