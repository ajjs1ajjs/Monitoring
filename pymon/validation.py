"""Input validation utilities"""

import os
import re
from typing import Any


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_server_host(host: str) -> bool:
    """Validate server hostname/IP"""
    if not host or len(host) < 3:
        raise ValidationError("Host must be at least 3 characters")

    if len(host) > 255:
        raise ValidationError("Host must be less than 255 characters")

    return True


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

    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
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


def validate_db_path(path: str) -> bool:
    """Validate database path"""
    if not path:
        raise ValidationError("Database path is required")

    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        raise ValidationError(f"Directory does not exist: {db_dir}")

    return True