# Deploy Windows Exporter
$ExporterVersion = "0.30.0"
$DownloadUrl = "https://github.com/prometheus-community/windows_exporter/releases/download/v$ExporterVersion/windows_exporter-$ExporterVersion-amd64.msi"

Invoke-WebRequest -Uri $DownloadUrl -OutFile "$env:TEMP\windows_exporter.msi" -UseBasicParsing
Start-Process msiexec.exe -Wait -ArgumentList "/i $env:TEMP\windows_exporter.msi /quiet ENABLED_COLLECTORS=cpu,cs,memory,net,logical_disk,os,service"
Write-Host "Windows Exporter installed."
