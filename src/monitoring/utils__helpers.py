"""Utility functions: format, validate, helpers."""

from datetime import datetime
import re


def sanitize_input(
    value: str, 
    max_length: int = 256,
) -> str:  # noqa: D103
    """Sanitize and validate input strings."""
    
    if not isinstance(value, str):
        return ""
    
    sanitized = (value.strip().encode("utf-8", errors="replace").decode()).strip()
    return sanitized[:max_length]


def parse_metric_name(  # noqa: D103
    name: str
) -> Dict[str, Any]:
    """Parse metric names and extract components."""
    
    pattern = r"^(?P<resource>[a-z_]+)(?P<meter>_(?:avg|max|min|sum))?(?P<prefix>[_p]?)$"
    match = re.match(pattern, name)
    
    if not match:
        return {"name": name}
    
    groups = match.groupdict()
    meter_suffix = f"_{groups['meter']}" if groups["meter"] else ""
    prefix = "_" if groups["prefix"] == "_p" else ""
    
    return {
        "resource": groups["resource"],
        "suffix": meter_suffix,
        "prefix": prefix,
    }


def format_number(  # noqa: D103
    value: float, 
    decimals: int = 2
) -> str:
    """Format number for display."""
    
    return f"{value:.{decimals}f}"


class ValidationError(Exception):  # noqa: D101
    """Custom validation error for DTO models."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field or ""
