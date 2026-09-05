package api

import (
	"fmt"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

// prometheusLabelNameRe matches the Prometheus label name grammar
// ([a-zA-Z_][a-zA-Z0-9_]*).
var prometheusLabelNameRe = regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*$`)

type registryEntry struct {
	Name   string
	Type   string
	Help   string
	Value  float64
	Labels map[string]string
}

// maxRegistryEntries bounds the in-memory registry so an authenticated client
// pushing many unique label combinations cannot exhaust memory (the push API
// is available to every authenticated user, and /metrics is public).
const maxRegistryEntries = 5000

// MetricRegistry is an in-memory store for push metrics (POST /api/v1/metrics).
type MetricRegistry struct {
	mu    sync.Mutex
	items []registryEntry
}

func (r *MetricRegistry) Add(e registryEntry) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for i, it := range r.items {
		if it.Name == e.Name && labelEqual(it.Labels, e.Labels) {
			r.items[i] = e
			return
		}
	}
	if len(r.items) >= maxRegistryEntries {
		return
	}
	r.items = append(r.items, e)
}

func (r *MetricRegistry) Snapshot() []registryEntry {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]registryEntry, len(r.items))
	copy(out, r.items)
	return out
}

func labelEqual(a, b map[string]string) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if b[k] != v {
			return false
		}
	}
	return true
}

func (a *App) handlePrometheusExport(w http.ResponseWriter, r *http.Request) {
	var sb strings.Builder
	sb.WriteString("# HELP pymon_uptime_seconds Seconds the server has been up\n")
	sb.WriteString("# TYPE pymon_uptime_seconds gauge\n")
	fmt.Fprintf(&sb, "pymon_uptime_seconds %.0f\n", time.Since(a.StartTime).Seconds())

	if servers, err := a.Store.ListServers(); err == nil {
		online := 0
		for _, s := range servers {
			if s.LastStatus == "up" {
				online++
			}
		}
		sb.WriteString("# HELP pymon_servers_total Total servers\n# TYPE pymon_servers_total gauge\n")
		fmt.Fprintf(&sb, "pymon_servers_total %d\n", len(servers))
		sb.WriteString("# HELP pymon_servers_online Online servers\n# TYPE pymon_servers_online gauge\n")
		fmt.Fprintf(&sb, "pymon_servers_online %d\n", online)
	}

	var entries []registryEntry
	if a.Metrics != nil {
		entries = a.Metrics.Snapshot()
	}
	for _, e := range entries {
		// Defense in depth: even if a bad name slips past the push validator,
		// never emit control characters into the public exposition.
		name := sanitizeMetricName(e.Name)
		help := sanitizeHelpText(e.Help)
		if name == "" {
			continue
		}
		if help != "" {
			fmt.Fprintf(&sb, "# HELP %s %s\n", name, help)
		}
		if e.Type != "" {
			fmt.Fprintf(&sb, "# TYPE %s %s\n", name, e.Type)
		}
		sb.WriteString(name)
		if len(e.Labels) > 0 {
			keys := make([]string, 0, len(e.Labels))
			for k := range e.Labels {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			var labels []string
			for _, k := range keys {
				labels = append(labels, fmt.Sprintf("%s=%q", k, e.Labels[k]))
			}
			sb.WriteString("{" + strings.Join(labels, ",") + "}")
		}
		fmt.Fprintf(&sb, " %g\n", e.Value)
	}

	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
	_, _ = w.Write([]byte(sb.String()))
}

// sanitizeMetricName strips control characters (most importantly newlines) so
// a crafted metric name cannot inject extra lines into the exposition text.
func sanitizeMetricName(name string) string {
	out := make([]rune, 0, len(name))
	for _, c := range name {
		if c < 0x20 || c == 0x7f {
			continue
		}
		out = append(out, c)
	}
	return strings.TrimSpace(string(out))
}

func sanitizeHelpText(help string) string {
	out := make([]rune, 0, len(help))
	for _, c := range help {
		if c == '\n' || c == '\r' || c < 0x20 || c == 0x7f {
			continue
		}
		out = append(out, c)
	}
	return strings.TrimSpace(string(out))
}
