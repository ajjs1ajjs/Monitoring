package monitor

import (
	"testing"
)

const linuxMetrics = `# HELP node_cpu_seconds_total Seconds the cpus spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 1000
node_cpu_seconds_total{cpu="0",mode="user"} 500
node_cpu_seconds_total{cpu="0",mode="system"} 300
node_cpu_seconds_total{cpu="0",mode="iowait"} 100
# HELP node_memory_MemTotal_bytes Memory information field.
# TYPE node_memory_MemTotal_bytes gauge
node_memory_MemTotal_bytes 16000000000
node_memory_MemAvailable_bytes 8000000000
# HELP node_filesystem_size_bytes Filesystem size in bytes.
# TYPE node_filesystem_size_bytes gauge
node_filesystem_size_bytes{fstype="ext4",mountpoint="/"} 1000000000
node_filesystem_size_bytes{fstype="tmpfs",mountpoint="/run"} 1000000000
# HELP node_filesystem_avail_bytes Filesystem space available to non-root users.
# TYPE node_filesystem_avail_bytes gauge
node_filesystem_avail_bytes{fstype="ext4",mountpoint="/"} 500000000
node_filesystem_avail_bytes{fstype="tmpfs",mountpoint="/run"} 900000000
# HELP node_network_receive_bytes_total Network device statistic.
# TYPE node_network_receive_bytes_total counter
node_network_receive_bytes_total{device="eth0"} 1000
node_network_receive_bytes_total{device="lo"} 99999
node_network_transmit_bytes_total{device="eth0"} 2000
node_network_transmit_bytes_total{device="lo"} 99999
node_exporter_build_info{version="1.8.2"} 1
`

func TestParseLinuxMetrics(t *testing.T) {
	res, err := parseMetrics(linuxMetrics, "test")
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	// cpu = 1 - idle/total = 1 - 1000/1900 = 0.4737 -> 47.4
	if res.cpu < 47.0 || res.cpu > 48.0 {
		t.Errorf("cpu = %v, want ~47.4", res.cpu)
	}
	if res.memory < 49.0 || res.memory > 51.0 {
		t.Errorf("memory = %v, want ~50", res.memory)
	}
	if res.disk < 49.0 || res.disk > 51.0 {
		t.Errorf("disk = %v, want ~50 (tmpfs excluded)", res.disk)
	}
	// lo excluded from network
	if res.netRx != 1000 {
		t.Errorf("net_rx = %v, want 1000", res.netRx)
	}
	if res.netTx != 2000 {
		t.Errorf("net_tx = %v, want 2000", res.netTx)
	}
	if len(res.volumes) != 1 {
		t.Fatalf("volumes = %v, want only / (tmpfs excluded)", res.volumes)
	}
}

const windowsMetrics = `# TYPE windows_cpu_time_total counter
windows_cpu_time_total{mode="idle"} 800
windows_cpu_time_total{mode="user"} 200
windows_cpu_time_total{mode="privileged"} 100
# TYPE windows_cs_physical_memory_bytes gauge
windows_cs_physical_memory_bytes 1000000000
# TYPE windows_memory_available_bytes gauge
windows_memory_available_bytes 400000000
# TYPE windows_logical_disk_size_bytes gauge
windows_logical_disk_size_bytes{volume="C:"} 200000000
# TYPE windows_logical_disk_free_bytes gauge
windows_logical_disk_free_bytes{volume="C:"} 100000000
# TYPE windows_net_bytes_received_total counter
windows_net_bytes_received_total{nic="Ethernet"} 500
# TYPE windows_net_bytes_sent_total counter
windows_net_bytes_sent_total{nic="Ethernet"} 600
`

func TestParseWindowsMetrics(t *testing.T) {
	res, err := parseMetrics(windowsMetrics, "win")
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	// cpu = 1 - 800/1100 = 0.2727 -> 27.3
	if res.cpu < 27.0 || res.cpu > 28.0 {
		t.Errorf("cpu = %v, want ~27.3", res.cpu)
	}
	if res.memory < 59.0 || res.memory > 61.0 {
		t.Errorf("memory = %v, want ~60", res.memory)
	}
	if res.disk < 49.0 || res.disk > 51.0 {
		t.Errorf("disk = %v, want ~50", res.disk)
	}
	if res.netRx != 500 || res.netTx != 600 {
		t.Errorf("net rx/tx = %v/%v, want 500/600", res.netRx, res.netTx)
	}
}

func TestExtractHostPort(t *testing.T) {
	cases := []struct {
		in       string
		defPort  int
		wantHost string
		wantPort int
	}{
		{"https://example.com:8443/path", 443, "example.com", 8443},
		{"example.com:8080", 80, "example.com", 8080},
		{"192.168.1.1", 443, "192.168.1.1", 443},
	}
	for _, c := range cases {
		h, p := extractHostPort(c.in, c.defPort)
		if h != c.wantHost || p != c.wantPort {
			t.Errorf("extractHostPort(%q,%d) = %q,%d; want %q,%d", c.in, c.defPort, h, p, c.wantHost, c.wantPort)
		}
	}
}
