# Install windows_exporter with all collectors
# Run in CMD as Administrator

@echo off
echo Downloading windows_exporter...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/prometheus-community/windows_exporter/releases/download/v0.25.0/windows_exporter-0.25.0-amd64.msi' -OutFile '%TEMP%\we.msi'"

echo Installing...
msiexec /i "%TEMP%\we.msi" ENABLED_COLLECTORS="cpu,cs,memory,net,logical_disk,os,system,service" /quiet

echo Done!
del "%TEMP%\we.msi"

echo.
echo Starting service...
sc start windows_exporter

timeout /t 5

echo Testing metrics...
curl -s http://localhost:9182/metrics | findstr windows_logical_disk
