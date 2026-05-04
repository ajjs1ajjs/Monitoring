#!/bin/bash

# Telegraf deployment for Linux
# Configured for Prometheus output on port 9273

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# 1. Install Telegraf
wget -qO- https://repos.influxdata.com/influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list
apt-get update
apt-get install telegraf -y

# 2. Configure Telegraf
cat <<EOF > /etc/telegraf/telegraf.conf
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

[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = true
  report_active = true

[[inputs.disk]]
  ignore_fs = ["tmpfs", "devtmpfs", "devfs", "iso9660", "overlay", "aufs", "squashfs"]

[[inputs.diskio]]
[[inputs.kernel]]
[[inputs.mem]]
[[inputs.processes]]
[[inputs.swap]]
[[inputs.system]]
[[inputs.net]]
[[inputs.netstat]]
[[inputs.interrupts]]
[[inputs.linux_sysctl_fs]]
[[inputs.entropy]]
EOF

# 3. Enable and Restart
systemctl enable --now telegraf
systemctl restart telegraf

echo "Telegraf installed and configured on port 9273"
