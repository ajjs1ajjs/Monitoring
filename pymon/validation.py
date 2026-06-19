"""Input validation utilities"""

import ipaddress
import os
import re
import socket


class ValidationError(Exception):
    """Custom validation error"""
    pass


# Hostnames, IPv4, and bracketed IPv6 (with optional :port). Deliberately a strict
# whitelist so a host value can never carry HTML/script payloads into the dashboard.
_HOST_RE = re.compile(r"^[A-Za-z0-9._\-:\[\]]+$")


def validate_server_host(host: str) -> str:
    """Validate and sanitize server hostname/IP. Strips protocol prefixes and URL paths."""
    host = host.strip()
    for prefix in ('http://', 'https://'):
        if host.startswith(prefix):
            host = host[len(prefix):]
    host = host.split('/')[0].split('?')[0]
    if not host or len(host) < 3:
        raise ValidationError("Host must be at least 3 characters")
    if len(host) > 255:
        raise ValidationError("Host must be less than 255 characters")
    if not _HOST_RE.match(host):
        raise ValidationError("Host may only contain letters, digits, dots, hyphens, colons and brackets")
    return host


def validate_port(port: int) -> bool:
    """Validate port number"""
    if not isinstance(port, int):
        try:
            port = int(port)
        except (ValueError, TypeError):
            raise ValidationError("Port must be a number")

    if port < 1 or port > 65535:
        raise ValidationError("Port must be between 1 and 65535")

    return True


def validate_server_name(name: str) -> bool:
    """Validate server name"""
    if not name or len(name) < 1:
        raise ValidationError("Name is required")

    if len(name) > 100:
        raise ValidationError("Name must be less than 100 characters")

    if not re.match(r"^[a-zA-Z0-9_\-\ \.а-яА-ЯіїєґІЇЄҐ]+$", name):
        raise ValidationError("Name can only contain letters, numbers, hyphens, underscores, and dots")

    return True


def validate_os_type(os_type: str) -> bool:
    """Validate OS type"""
    valid_types = ["linux", "windows", "darwin", "freebsd", "netbsd"]
    if os_type.lower() not in valid_types:
        raise ValidationError(f"OS must be one of: {', '.join(valid_types)}")

    return True


def validate_time_range(range_str: str) -> bool:
    """Validate time range string"""
    valid_ranges = ["5m", "15m", "1h", "6h", "24h", "7d"]
    if range_str not in valid_ranges:
        raise ValidationError(f"Range must be one of: {', '.join(valid_ranges)}")

    return True


def validate_metric_name(name: str) -> bool:
    """Validate metric name"""
    if not name:
        raise ValidationError("Metric name is required")

    if not re.match(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$", name):
        raise ValidationError("Invalid metric name format")

    return True


def sanitize_input(value: str, max_length: int = 255) -> str:
    """Sanitize string input"""
    if not value:
        return ""

    value = value.strip()[:max_length]
    value = re.sub(r"[<>\"'&]", "", value)

    return value


# Cloud instance-metadata endpoints are the classic SSRF target. We block them for
# outbound scrape/service checks by default. Private LAN ranges are intentionally
# NOT blocked — monitoring internal hosts is the whole point of this app.
_BLOCKED_OUTBOUND_HOSTS = {
    "metadata.google.internal",   # GCP
}
# Explicit cloud-metadata IPs (in addition to the link-local/loopback ranges below).
_BLOCKED_METADATA_IPS = {
    "169.254.169.254",   # AWS/GCP/Azure/DO/OpenStack IMDS
    "fd00:ec2::254",     # AWS IMDS over IPv6
    "100.100.100.200",   # Alibaba Cloud metadata
}


def _candidate_ips(host: str) -> list:
    """Best-effort enumeration of every IP a host string could connect to.

    Covers literal IPs, integer/hex/octal IPv4 encodings (e.g. 2852039166,
    0xa9fea9fe) and DNS resolution — so an alternate encoding or a name that
    resolves to a metadata/link-local address can't slip past the check.
    """
    ips: list = []
    h = (host or "").strip().strip("[]")
    if not h:
        return ips
    # Literal IP (also accepts compressed IPv6).
    try:
        ips.append(ipaddress.ip_address(h))
    except ValueError:
        pass
    # Single-integer IPv4 encodings: decimal / 0x-hex / 0o-octal.
    try:
        val = int(h, 0) if h.lower().startswith(("0x", "0o")) else int(h)
        if 0 <= val <= 0xFFFFFFFF:
            ips.append(ipaddress.IPv4Address(val))
    except (ValueError, ipaddress.AddressValueError):
        pass
    # DNS / OS resolution (also normalises dotted-hex/octal forms the resolver accepts).
    try:
        for *_, sockaddr in socket.getaddrinfo(h, None):
            try:
                ips.append(ipaddress.ip_address(sockaddr[0]))
            except ValueError:
                pass
    except (OSError, UnicodeError):
        pass
    return ips


def _ip_is_blocked(ip) -> bool:
    # Block metadata + loopback + link-local + multicast + unspecified, but NOT
    # general private ranges (monitoring internal LAN hosts is intended).
    return (
        str(ip) in _BLOCKED_METADATA_IPS
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_blocked_outbound_host(host: str) -> bool:
    """True if a scrape/check target must be refused (cloud-metadata SSRF guard).

    Resolves the host (and normalises alternate IP encodings) and refuses it if
    ANY resulting address is a cloud-metadata IP, loopback, link-local
    (incl. 169.254.0.0/16 / fe80::/10), multicast or unspecified address.
    Private LAN ranges remain allowed by design.

    Set PYMON_ALLOW_METADATA=true to opt out (e.g. if you really do monitor IMDS).
    """
    if os.getenv("PYMON_ALLOW_METADATA", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    h = (host or "").strip().strip("[]").lower()
    if h in _BLOCKED_OUTBOUND_HOSTS:
        return True
    return any(_ip_is_blocked(ip) for ip in _candidate_ips(host))


def validate_db_path(path: str) -> bool:
    """Validate database path"""
    if not path:
        raise ValidationError("Database path is required")

    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        raise ValidationError(f"Directory does not exist: {db_dir}")

    return True
