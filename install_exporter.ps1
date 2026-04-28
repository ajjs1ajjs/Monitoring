# PyMon - Windows Exporter Installer
$version = "0.24.0"
$url = "https://github.com/prometheus-community/windows_exporter/releases/download/v$version/windows_exporter-$version-amd64.msi"
$output = "$env:TEMP\windows_exporter.msi"

echo "Downloading windows_exporter v$version..."
Invoke-WebRequest -Uri $url -OutFile $output

echo "Installing windows_exporter..."
Start-Process msiexec.exe -ArgumentList "/i $output /quiet /qn /norestart ENABLED_COLLECTORS=`"cpu,memory,net,logical_disk,os,system,service`"" -Wait

echo "Cleaning up..."
Remove-Item $output

echo "------------------------------------------------"
echo "SUCCESS: windows_exporter installed and running on port 9182"
echo "------------------------------------------------"
