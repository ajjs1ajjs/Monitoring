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
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath $TempPath -Force

# 3. Move files
if (!(Test-Path $InstallPath)) { New-Item -ItemType Directory -Path $InstallPath | Out-Null }
Move-Item -Path "$TempPath\telegraf-$LatestVersion\*" -Destination $InstallPath -Force
Remove-Item $TempPath -Recurse -Force

# 4. Create config
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
    Counters = ["% Idle Time", "% Interrupt Time", "% Privileged Time", "% User Time", "% Processor Time", "% DPC Time", "Interrupts/sec", "DPCs Rate"]
    Measurement = "win_cpu"

  [[inputs.win_perf_counters.object]]
    ObjectName = "LogicalDisk"
    Instances = ["*"]
    Counters = ["% Idle Time", "% Disk Time","% Disk Read Time", "% Disk Write Time", "% Free Space", "Current Disk Queue Length", "Disk Reads/sec", "Disk Writes/sec", "Disk Transfers/sec", "Free Megabytes"]
    Measurement = "win_disk"

  [[inputs.win_perf_counters.object]]
    ObjectName = "PhysicalDisk"
    Instances = ["*"]
    Counters = ["Disk Read Bytes/sec", "Disk Write Bytes/sec", "Current Disk Queue Length", "% Disk Time"]
    Measurement = "win_physical_disk"

  [[inputs.win_perf_counters.object]]
    ObjectName = "Memory"
    Counters = ["Available Bytes", "Cache Bytes", "Committed Bytes", "Pages/sec", "Pages Input/sec", "Pages Output/sec", "Pool Nonpaged Bytes", "Pool Paged Bytes", "System Cache Resident Bytes"]
    Measurement = "win_mem"

  [[inputs.win_perf_counters.object]]
    ObjectName = "Network Interface"
    Instances = ["*"]
    Counters = ["Bytes Received/sec", "Bytes Sent/sec", "Packets Received/sec", "Packets Sent/sec", "Packets Outbound Errors", "Packets Received Errors"]
    Measurement = "win_net"

  [[inputs.win_perf_counters.object]]
    ObjectName = "System"
    Counters = ["Context Switches/sec", "System Calls/sec", "Processor Queue Length", "System Up Time", "Processes", "Threads"]
    Measurement = "win_system"

  [[inputs.win_perf_counters.object]]
    ObjectName = "Paging File"
    Instances = ["_Total"]
    Counters = ["% Usage", "% Usage Peak"]
    Measurement = "win_swap"

  [[inputs.win_perf_counters.object]]
    ObjectName = "TCPv4"
    Counters = ["Connections Established", "Connections Active", "Connections Passive", "Connection Failures"]
    Measurement = "win_tcp"

[[inputs.win_services]]
"@

$ConfigContent | Out-File -FilePath $ConfigPath -Encoding UTF8

# 5. Install Service
Set-Location -Path $InstallPath
.\telegraf.exe --service install --config "$ConfigPath"
Start-Service telegraf

Write-Host "Telegraf installed and started on port 9273" -ForegroundColor Green
