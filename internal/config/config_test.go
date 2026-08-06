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
