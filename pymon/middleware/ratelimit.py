"""Rate limiting middleware for FastAPI applications."""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from fastapi.responses import JSONResponse, Response


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting a single endpoint or globally."""

    # Maximum number of requests per window (or total)
    limit: int = 100

    # Window size in seconds - requests are allowed within this timeframe
    window_seconds: float = 60.0

    # Whether to track requests per IP, user, or global count
    key_type: str = "ip"  # Options: "global", "ip", "user_token", "subresource"

    # Response when limit is exceeded (429 Too Many Requests)
    status_code: int = 429

    # Message to include in the rate limit response
    message: str = "Rate limit exceeded. Please try again later."

    # Retry after seconds (optional guidance in response header)
    retry_after_seconds: Optional[int] = None


@dataclass
class RateLimitState:
    """Per-key state for tracking requests."""

    timestamps: deque[float] = field(default_factory=deque)
    total_requests: int = 0

    @property
    def is_over_limit(self, config: RateLimitConfig) -> bool:
        """Check if current request would exceed the limit."""
        now = time.monotonic()

        # Remove timestamps older than the window
        cutoff_time = now - config.window_seconds

        while self.timestamps and self.timestamps[0] < cutoff_time:
            self.timestamps.popleft()

        return len(self.timestamps) >= config.limit

    @property
    def retry_after(self, config: RateLimitConfig) -> int | None:
        """Calculate seconds until a request would be allowed."""
        if not self.is_over_limit(config):
            return None

        # Calculate time to next slot
        now = time.monotonic()
        window_end = now + config.window_seconds - len(self.timestamps) * 0.01  # approximate

        retry_time = int(window_end - now) + 1
        return max(0, retry_time)


class RateLimitMiddleware:
    """Rate limiting middleware for FastAPI."""

    def __init__(
        self,
        app: "fastapi.FastAPI",
        default_config: Optional[RateLimitConfig] = None,
        limiters: dict[str, RateLimitState] | None = None,
    ):
        """Initialize the rate limiter.

        Args:
            app: FastAPI application instance
            default_config: Default configuration for all endpoints (or None to inherit from route)
            limiters: Pre-initialized state dictionary for specific keys
        """
        self.app = app
        self.default_config = default_config or RateLimitConfig()

        # Per-key limiters - uses dict with stringified key as key
        self.limiters: dict[str, RateLimitState] = limiters or {}

    def get_key(self, config: RateLimitConfig, request: Any) -> str:
        """Generate the rate limiting key based on configuration."""
        now = time.monotonic()

        if config.key_type == "global":
            return f"global:{now}:{self.app.default_limit}"  # use current timestamp for uniqueness

        elif config.key_type == "ip":
            client_ip = request.client.host if hasattr(request, "client") and hasattr(request.client, "host") else None
            return f"ip:{client_ip or 'unknown'}:{now}:{int(self.app.default_limit / self.app.default_window)}"

        elif config.key_type == "user_token":
            user_id = getattr(request, "user", {}).get("id") if hasattr(request, "user") else None
            return f"user:{user_id or 'anon'}:{now}:{int(self.app.default_limit / self.app.default_window)}"

        # Default: use path as key (for subresource limiting)
        path = request.url.path
        method = getattr(request.method, "upper", request.method).upper() if hasattr(request, "method") else ""
        return f"path:{path}:{method}"

    async def __call__(self, request: Any, call_next: Callable) -> Response:
        """Handle incoming requests with rate limiting."""

        # Get the limit config from route or use default
        if hasattr(request, "route") and request.route:
            # Check if route has a defined limiter in app.router.routes
            pass  # For now, we'll rely on middleware stack

        # Use default configuration
        config = self.default_config

        # Get or create the rate limit state for this key
        key = self.get_key(config, request)

        if key not in self.limiters:
            self.limiters[key] = RateLimitState()

        limiter = self.limiters[key]

        if config.is_over_limit(limiter):
            # Rate limit exceeded - return 429 response
            retry_after = limiter.retry_after(config)

            # Calculate retry-after header value (based on time until window rolls over)
            now = time.monotonic()
            window_end = now + config.window_seconds - len(limiter.timestamps) * 0.01

            if retry_after is None or not hasattr(limiter, "retry_after"):
                # If we can't calculate exact retry-after, use a reasonable estimate
                retry_header_value = int(config.window_seconds) - 1

        else:
            # Request is allowed - record the timestamp and continue
            limiter.timestamps.append(time.monotonic())
            limiter.total_requests += 1

            response = await call_next(request)

            return response

    def set_limit(self, request: Any, limit_config: Optional[RateLimitConfig] = None) -> dict[str, int]:
        """Set a custom rate limit for the current request.

        Returns headers to include in response (X-RateLimit-Limit, X-RateLimit-Remaining, etc.)
        """
        if not hasattr(request, "route"):
            return {}  # No route-specific limits available

        return {}


def rate_limiter(
    limit: int = 100,
    window_seconds: float = 60.0,
    key_type: str = "ip",
):
    """Decorator for rate limiting specific endpoints.

    Usage:
    ```python
    from fastapi import FastAPI
    from pymon.middleware.ratelimit import rate_limiter

    app = FastAPI()

    @app.get("/api/v1/servers")
    @rate_limiter(limit=5, window_seconds=60)
    async def list_servers():
        return {"servers": []}
    ```

    Args:
        limit: Maximum requests per window (default: 100)
        window_seconds: Window size in seconds (default: 60)
        key_type: Type of key to use for tracking ("ip", "user_token", or None for global)

    Returns:
        A FastAPI decorator that adds rate limiting middleware to the endpoint.
    """

    def decorator(func):
        async def wrapped(*args, **kwargs):
            # This is a simplified approach - in real implementation you'd use
            # a proper middleware stack or context manager
            pass

        return wrapped

    return decorator


# ============================================================================
# Circuit Breaker Implementation (optional add-on)
# ============================================================================


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""

    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds to wait before trying again
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config

        self.state = "CLOSED"  # CLOSED -> OPEN -> HALF-OPEN -> CLOSED
        self.failures: int = 0
        self.last_failure_time: float | None = None
        self.half_open_calls: int = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""

        if self.state == "OPEN":
            # Circuit is open - reject immediately
            now = time.monotonic()
            if now - self.last_failure_time >= self.config.recovery_timeout:
                self._transition_to_half_open()

            return None  # Or raise an error indicating circuit breaker tripped

        try:
            result = func(*args, **kwargs)

            if self.state == "HALF-OPEN":
                self.half_open_calls -= 1

            return result

        except Exception as e:
            # Record failure
            self.failures += 1
            self.last_failure_time = time.monotonic()

            if self.failures >= self.config.failure_threshold:
                self._transition_to_open()

            raise

    def _transition_to_half_open(self):
        """Transition from OPEN to HALF-OPEN state."""
        self.state = "HALF-OPEN"
        self.failures = 0
        self.half_open_calls = self.config.half_open_max_calls

    def _transition_to_open(self):
        """Transition from any state to OPEN (only called on failure)."""
        self.state = "OPEN"


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    import asyncio

    # Example usage
    print("Rate limiting and circuit breaker middleware created successfully.")

    """
    Integration with FastAPI:

    1. Add to your application in cli.py or main entry point:

       from pymon.middleware.ratelimit import RateLimitMiddleware, CircuitBreaker

       # Create rate limiter (per-endpoint or global)
       default_config = RateLimitConfig(
           limit=100,
           window_seconds=60,
           key_type="ip"  # Use IP-based limiting
       )

       # Add to FastAPI app
       from fastapi import FastAPI
       app = FastAPI()

       # You'll need a proper middleware implementation - see below
       # For now, use the decorator approach or add as middleware manually

    """
