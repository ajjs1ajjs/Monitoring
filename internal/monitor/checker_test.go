package monitor

import "testing"

// TestExtractHostPortStripsUserinfo guards against the SSRF-guard bypass where
// `http://user:pass@127.0.0.1/` compared the wrong host while the HTTP client
// still dialed the real (possibly localhost/metadata) address.
func TestExtractHostPortStripsUserinfo(t *testing.T) {
	cases := []struct{ in, wantHost string; wantPort int }{
		{"http://user:pass@127.0.0.1:8080/health", "127.0.0.1", 8080},
		{"http://alice@192.168.1.10/", "192.168.1.10", 443},
		{"https://example.com:8443/", "example.com", 8443},
		{"https://[::1]:9000/", "::1", 9000},
		{"example.com", "example.com", 443},
		{"10.0.0.5:9100", "10.0.0.5", 9100},
	}
	for _, c := range cases {
		host, port := extractHostPort(c.in, 443)
		if host != c.wantHost || port != c.wantPort {
			t.Errorf("extractHostPort(%q) = (%q, %d), want (%q, %d)", c.in, host, port, c.wantHost, c.wantPort)
		}
	}
}

// TestIsBlockedOutboundHostRejectsUserinfoMetadata ensures a userinfo-prefixed
// metadata/localhost target is still blocked after the host is extracted (the
// actual checkOne flow: extractHostPort -> IsBlockedOutboundHost).
func TestIsBlockedOutboundHostRejectsUserinfoMetadata(t *testing.T) {
	host, _ := extractHostPort("http://user:pass@169.254.169.254/", 443)
	if !IsBlockedOutboundHost(host) {
		t.Fatalf("metadata IP with userinfo must be blocked (host=%q)", host)
	}
	host, _ = extractHostPort("http://user:pass@127.0.0.1/", 443)
	if !IsBlockedOutboundHost(host) {
		t.Fatalf("loopback with userinfo must be blocked (host=%q)", host)
	}
}
