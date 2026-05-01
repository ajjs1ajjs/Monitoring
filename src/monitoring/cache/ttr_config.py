"""Cache configuration: TTL defaults, key prefixes."""

import os

# Default TTL in seconds (5-10 min range)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 600))

# Key prefix for cache entries to avoid collisions
CACHE_KEY_PREFIX = "monitoring_cache_"
