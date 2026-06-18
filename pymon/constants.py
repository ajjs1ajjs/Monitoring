"""Shared constants used across routers and background workers."""

# Maps a UI range token to the SQLite `datetime('now', ?)` modifier. Single source
# of truth so endpoints can't drift apart (previously duplicated in every router).
TIME_RANGES: dict[str, str] = {
    "5m": "-5 minutes",
    "15m": "-15 minutes",
    "30m": "-30 minutes",
    "1h": "-1 hour",
    "6h": "-6 hours",
    "12h": "-12 hours",
    "24h": "-24 hours",
    "3d": "-3 days",
    "7d": "-7 days",
    "15d": "-15 days",
    "30d": "-30 days",
}


def time_filter(range_token: str, default: str = "-1 hour") -> str:
    """Resolve a range token (e.g. ``"24h"``) to a SQLite datetime modifier."""
    return TIME_RANGES.get(range_token, default)
