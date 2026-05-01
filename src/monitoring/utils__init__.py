"""Monitoring utility helpers."""

from .utils__helpers import (  # noqa: D103
    sanitize_input,
    parse_metric_name,
    format_number,
    ValidationError,
)


def get_sanitizer(max_length: int = 256) -> callable:  # noqa: D103
    """Get a sanitizer function with custom max_length."""
    
    def validate(value):
        return sanitize_input(value, max_length)
    
    return validate
