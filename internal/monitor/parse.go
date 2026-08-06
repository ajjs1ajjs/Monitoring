package monitor

import (
	"log"
	"strings"
)

// parseMetrics computes CPU/memory/disk/network + volume breakdown from an
// exporter text dump, mirroring the Python implementation.
func parseMetrics(text, name string) (*scrapeResult, error) {
	result := &scrapeResult{}
	samples, err := ParsePrometheusText(text)
	if err != nil {
		log.Printf("[ScrapeManager] metric parse error for %s: %v", name, err)
		return result, err
	}
	isLinux := false
	for k := range samples {
		if strings.Contains(k, "node_") {
			isLinux = true
			break
		}
	}
	if isLinux {
		parseLinux(samples, result)
	} else {
		parseWindows(samples, result)
	}
	return result, nil
}

func shouldIncludeVolume(vol string) bool {
	vl := strings.ToLower(vol)
	if strings.Contains(vl, "harddiskvolume") {
		return false
	}
	if strings.Contains(vl, "/snap/") {
		return false
	}
	if strings.Contains(vl, "docker") || strings.Contains(vl, "kubelet") ||
		strings.Contains(vl, "tmpfs") || strings.Contains(vl, "overlay") {
		return false
	}
	if vl == "shm" || strings.HasSuffix(vl, "/shm") || strings.Contains(vl, "/shm") {
		return false
	}
	if strings.Contains(vl, "/run/user/") {
		return false
	}
	return true
}

func parseLinux(m map[string][]Sample, r *scrapeResult) {
	var cpuTotal, cpuIdle float64
	for k, items := range m {
		if strings.Contains(k, "node_cpu_seconds_total") {
			for _, it := range items {
				if it.Labels["cpu"] == "cpu" {
					continue
				}
				cpuTotal += it.Value
				if it.Labels["mode"] == "idle" {
					cpuIdle += it.Value
				}
			}
		}
	}
	if cpuTotal > 0 {
		r.cpu = round1((1 - cpuIdle/cpuTotal) * 100)
	}

	var memTotal, memAvailable float64
	for k, items := range m {
		if strings.Contains(k, "node_memory_MemTotal_bytes") && len(items) > 0 {
			memTotal = items[0].Value
		} else if strings.Contains(k, "node_memory_MemAvailable_bytes") && len(items) > 0 {
			memAvailable = items[0].Value
		}
	}
	if memTotal > 0 {
		r.memory = round1(((memTotal - memAvailable) / memTotal) * 100)
	}

	skipFSType := map[string]bool{"tmpfs": true, "devtmpfs": true, "squashfs": true, "overlay": true, "nsfs": true}
	diskSize := map[string]float64{}
	diskFree := map[string]float64{}
	for k, items := range m {
		if strings.Contains(k, "node_filesystem_size_bytes") {
			for _, it := range items {
				if skipFSType[it.Labels["fstype"]] {
					continue
				}
				mp := it.Labels["mountpoint"]
				if mp == "" {
					mp = it.Labels["device"]
				}
				if mp == "" {
					continue
				}
				if cur, ok := diskSize[mp]; !ok || it.Value > cur {
					diskSize[mp] = it.Value
				}
			}
		} else if strings.Contains(k, "node_filesystem_avail_bytes") {
			for _, it := range items {
				if skipFSType[it.Labels["fstype"]] {
					continue
				}
				mp := it.Labels["mountpoint"]
				if mp == "" {
					mp = it.Labels["device"]
				}
				if mp == "" {
					continue
				}
				if cur, ok := diskFree[mp]; !ok || it.Value > cur {
					diskFree[mp] = it.Value
				}
			}
		}
	}
	var totalFree, totalSize float64
	for key, size := range diskSize {
		if !shouldIncludeVolume(key) {
			continue
		}
		freeVal, ok := diskFree[key]
		if !ok {
			freeVal = size
		}
		if size > 0 {
			usedPct := round1(((size - freeVal) / size) * 100)
			r.volumes = append(r.volumes, map[string]any{
				"volume": key, "size_bytes": size, "free_bytes": freeVal, "used_percent": usedPct,
			})
			totalFree += freeVal
			totalSize += size
		}
	}
	if totalSize > 0 {
		r.disk = round1(((totalSize - totalFree) / totalSize) * 100)
	}

	var netRx, netTx float64
	for k, items := range m {
		if strings.Contains(k, "node_network_receive_bytes_total") {
			for _, it := range items {
				if it.Labels["device"] == "lo" {
					continue
				}
				netRx += it.Value
			}
		} else if strings.Contains(k, "node_network_transmit_bytes_total") {
			for _, it := range items {
				if it.Labels["device"] == "lo" {
					continue
				}
				netTx += it.Value
			}
		}
	}
	if netRx > 0 || netTx > 0 {
		r.netRx = netRx
		r.netTx = netTx
	}
}

func parseWindows(m map[string][]Sample, r *scrapeResult) {
	var cpuTotal, cpuIdle float64
	for k, items := range m {
		if strings.Contains(k, "windows_cpu_time_total") {
			for _, it := range items {
				cpuTotal += it.Value
				if it.Labels["mode"] == "idle" {
					cpuIdle += it.Value
				}
			}
		}
	}
	if cpuTotal > 0 {
		r.cpu = round1((1 - cpuIdle/cpuTotal) * 100)
	}
	if r.cpu == 0 {
		for k, items := range m {
			if strings.Contains(k, "windows_cpu_percent") || strings.Contains(k, "windows_cpu_processor_time_percent") {
				if len(items) > 0 {
					var sum float64
					for _, it := range items {
						sum += it.Value
					}
					avg := sum / float64(len(items))
					r.cpu = round1(min(max(avg, 0), 100))
					break
				}
			}
		}
	}

	var memTotal, memAvailable float64
	for k, items := range m {
		if strings.Contains(k, "windows_cs_physical_memory_bytes") && len(items) > 0 {
			memTotal = items[0].Value
		} else if strings.Contains(k, "windows_memory_available_bytes") && len(items) > 0 {
			memAvailable = items[0].Value
		}
	}
	if memTotal > 0 {
		r.memory = round1(((memTotal - memAvailable) / memTotal) * 100)
	}

	type diskData struct {
		free float64
		size float64
	}
	volData := map[string]*diskData{}
	for k, items := range m {
		if strings.Contains(k, "windows_logical_disk_free_bytes") {
			for _, it := range items {
				vol := it.Labels["volume"]
				if vol == "" {
					vol = "ALL"
				}
				d, ok := volData[vol]
				if !ok {
					d = &diskData{}
					volData[vol] = d
				}
				d.free = it.Value
			}
		} else if strings.Contains(k, "windows_logical_disk_size_bytes") {
			for _, it := range items {
				vol := it.Labels["volume"]
				if vol == "" {
					vol = "ALL"
				}
				d, ok := volData[vol]
				if !ok {
					d = &diskData{}
					volData[vol] = d
				}
				d.size = it.Value
			}
		}
	}
	var totalFree, totalSize float64
	for vol, d := range volData {
		if !shouldIncludeVolume(vol) {
			continue
		}
		if d.size > 0 {
			usedPct := round1(((d.size - d.free) / d.size) * 100)
			r.volumes = append(r.volumes, map[string]any{
				"volume": vol, "size_bytes": d.size, "free_bytes": d.free, "used_percent": usedPct,
			})
			totalFree += d.free
			totalSize += d.size
		}
	}
	if totalSize > 0 {
		r.disk = round1(((totalSize - totalFree) / totalSize) * 100)
	}

	var netRx, netTx float64
	for k, items := range m {
		if strings.Contains(k, "windows_net_bytes_received_total") {
			for _, it := range items {
				netRx += it.Value
			}
		} else if strings.Contains(k, "windows_net_bytes_sent_total") {
			for _, it := range items {
				netTx += it.Value
			}
		}
	}
	if netRx > 0 || netTx > 0 {
		r.netRx = netRx
		r.netTx = netTx
	}
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
