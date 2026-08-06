package monitor

import (
	"net"
	"os"
	"strings"
)

// blocked outbound hosts — cloud metadata SSRF guard (mirrors Python).
var blockedOutboundHosts = map[string]bool{
	"metadata.google.internal": true,
}

var blockedMetadataIPs = map[string]bool{
	"169.254.169.254": true, // AWS/GCP/Azure/DO/OpenStack IMDS
	"fd00:ec2::254":   true, // AWS IMDS over IPv6
	"100.100.100.200": true, // Alibaba Cloud metadata
}

func metadataOptOut() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv("PYMON_ALLOW_METADATA")))
	return v == "1" || v == "true" || v == "yes" || v == "on"
}

// IsBlockedOutboundHost returns true if a scrape/check target must be refused.
// Private LAN ranges are intentionally allowed.
func IsBlockedOutboundHost(host string) bool {
	if metadataOptOut() {
		return false
	}
	h := strings.TrimSpace(host)
	h = strings.Trim(h, "[]")
	lower := strings.ToLower(h)
	if blockedOutboundHosts[lower] {
		return true
	}
	for _, ip := range candidateIPs(h) {
		if ipBlocked(ip) {
			return true
		}
	}
	return false
}

func candidateIPs(host string) []net.IP {
	var ips []net.IP
	if ip := net.ParseIP(host); ip != nil {
		ips = append(ips, ip)
	}
	// integer IPv4 encodings
	if n, err := parseIntIP(host); err == nil {
		ips = append(ips, ipv4FromInt(n))
	}
	// DNS resolution
	addrs, err := net.LookupHost(host)
	if err == nil {
		for _, a := range addrs {
			if ip := net.ParseIP(a); ip != nil {
				ips = append(ips, ip)
			}
		}
	}
	return ips
}

func parseIntIP(h string) (uint32, error) {
	low := strings.ToLower(h)
	var n uint64
	if strings.HasPrefix(low, "0x") {
		for _, c := range strings.TrimPrefix(low, "0x") {
			n = n * 16
			switch {
			case c >= '0' && c <= '9':
				n += uint64(c - '0')
			case c >= 'a' && c <= 'f':
				n += uint64(c-'a') + 10
			default:
				return 0, errBadIP
			}
		}
	} else if strings.HasPrefix(low, "0o") {
		for _, c := range strings.TrimPrefix(low, "0o") {
			if c < '0' || c > '7' {
				return 0, errBadIP
			}
			n = n*8 + uint64(c-'0')
		}
	} else {
		for _, c := range h {
			if c < '0' || c > '9' {
				return 0, errBadIP
			}
			n = n*10 + uint64(c-'0')
		}
	}
	if n > 0xFFFFFFFF {
		return 0, errBadIP
	}
	return uint32(n), nil
}

var errBadIP = &badIPError{}

type badIPError struct{}

func (e *badIPError) Error() string { return "invalid integer IP" }

func ipv4FromInt(n uint32) net.IP {
	return net.IPv4(byte(n>>24), byte(n>>16), byte(n>>8), byte(n))
}

func ipBlocked(ip net.IP) bool {
	if blockedMetadataIPs[ip.String()] {
		return true
	}
	return ip.IsLoopback() || ip.IsLinkLocalMulticast() || ip.IsLinkLocalUnicast() ||
		ip.IsMulticast() || ip.IsUnspecified()
}
