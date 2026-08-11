package config

import "testing"

func TestParseDuration(t *testing.T) {
	cases := map[string]int{
		"15s": 15,
		"5m":  300,
		"1h":  3600,
		"30s": 30,
		"":    0,
	}
	for in, want := range cases {
		got := parseDurationSeconds(in)
		if got != want {
			t.Errorf("parseDurationSeconds(%q) = %d, want %d", in, got, want)
		}
	}
}

func TestDefaultScrapeInterval(t *testing.T) {
	c := Default()
	if got := c.ScrapeIntervalSeconds(); got != 15 {
		t.Errorf("default scrape interval = %d, want 15", got)
	}
	c.ScrapeConfigs = []ScrapeConfig{{ScrapeInterval: "30s"}}
	if got := c.ScrapeIntervalSeconds(); got != 30 {
		t.Errorf("configured scrape interval = %d, want 30", got)
	}
}

// TestParseDurationRejectsGarbage ensures malformed values like "5xyzs" are
// not silently accepted (the old Sscanf-based parser parsed "5" and ignored
// the trailing garbage).
func TestParseDurationRejectsGarbage(t *testing.T) {
	bad := []string{"5xyzs", "15seconds", "1d", "s", "-5s", "0s", "1.2.3s", "abc"}
	for _, in := range bad {
		if got := parseDurationSeconds(in); got != 0 {
			t.Errorf("parseDurationSeconds(%q) = %d, want 0 (malformed)", in, got)
		}
	}
	good := map[string]int{"15s": 15, "5m": 300, "1h": 3600, "1.5m": 90}
	for in, want := range good {
		if got := parseDurationSeconds(in); got != want {
			t.Errorf("parseDurationSeconds(%q) = %d, want %d", in, got, want)
		}
	}
}
