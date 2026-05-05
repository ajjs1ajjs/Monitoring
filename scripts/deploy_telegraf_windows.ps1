# Telegraf deployment for Windows
# Run this script as Administrator

$InstallPath = "C:\Program Files\Telegraf"
$ConfigPath = Join-Path $InstallPath "telegraf.conf"

# 1. Get latest version
$Release = Invoke-RestMethod -Uri "https://api.github.com/repos/influxdata/telegraf/releases/latest"
$LatestVersion = $Release.tag_name.TrimStart('v')
$DownloadUrl = "https://dl.influxdata.com/telegraf/releases/telegraf-$LatestVersion`_windows_amd64.zip"

# 2. Download and Extract
$TempPath = Join-Path $env:TEMP "telegraf_install"
if (Test-Path $TempPath) { Remove-Item $TempPath -Recurse -Force }
New-Item -ItemType Directory -Force -Path $TempPath | Out-Null

$ZipPath = Join-Path $TempPath "telegraf.zip"
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing
Expand-Archive -Path $ZipPath -DestinationPath $TempPath -Force

# 3. Move files
if (!(Test-Path $InstallPath)) { New-Item -ItemType Directory -Path $InstallPath | Out-Null }
Move-Item -Path "$TempPath\telegraf-$LatestVersion\*" -Destination $InstallPath -Force
Remove-Item $TempPath -Recurse -Force

# 4. Create Pymon-compatible config
$ConfigContent = @"
[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  hostname = ""
  omit_hostname = false

[[outputs.prometheus_client]]
  listen = ":9273"

[[inputs.win_perf_counters]]
  UseWildcardsExpansion = true
  [[inputs.win_perf_counters.object]]
    ObjectName = "Processor"
    Instances = ["*"]
    Counters = ["% Idle Time", "% Processor Time"]
    Measurement = "win_cpu"
  [[inputs.win_perf_counters.object]]
    ObjectName = "LogicalDisk"
    Instances = ["*"]
    Counters = ["% Free Space", "Free Megabytes"]
    Measurement = "win_disk"
  [[inputs.win_perf_counters.object]]
    ObjectName = "Memory"
    Counters = ["Available Bytes"]
    Measurement = "win_mem"

[[processors.rename]]
  [[processors.rename.replace]]
    measurement = "win_cpu"
    field = "Percent_Idle_Time"
    rename = "windows_cpu_time_total_idle"
  [[processors.rename.replace]]
    measurement = "win_cpu"
    field = "Percent_Processor_Time"
    rename = "windows_cpu_time_total_all"
  [[processors.rename.replace]]
    measurement = "win_disk"
    field = "Free_Megabytes"
    rename = "windows_logical_disk_free_bytes"
"@

$ConfigContent | Out-File -FilePath $ConfigPath -Encoding UTF8

# 5. Install Service
Set-Location -Path $InstallPath
.\telegraf.exe --service install --config "$ConfigPath"
Start-Service telegraf

Write-Host "Telegraf installed and started on port 9273" -ForegroundColor Green
