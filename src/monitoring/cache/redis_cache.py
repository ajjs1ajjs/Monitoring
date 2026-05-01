"""Redis/Memcached cache layer with TTL decorators."""

import functools
from typing import Any, Callable, Optional, Union

import redis.asyncio as redis  # type: ignore[import-untyped]
from .ttr_config import CACHE_KEY_PREFIX, CACHE_TTL_SECONDS


class RedisCacheClient:
    """Async Redis client with error handling and fallback."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._fallback_enabled = False

    async def _get_client(self) -> redis.Redis:
        host = "localhost"
        port = 6379
        db = 0
        
        # Read from environment or use defaults
        try:
            from dotenv import load_dotenv, find_dotenv
            
            env_file = find_dotenv()
            if env_file:
                load_dotenv(env_file)
                
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
        except Exception:
            pass
        
        try:
            return redis.Redis(host=host, port=port, db=db, decode_responses=True)
        except Exception:
            raise ConnectionError(
                f"Failed to connect to Redis at {host}:{port}. "
                "Check if the Redis server is running."
            )

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            client = await self._get_client()
            data = await client.get(f"{CACHE_KEY_PREFIX}{key}")
            if not data:
                return None
            # Check TTL and refresh if close to expiry
            ttl = await client.ttl(f"{CACHE_KEY_PREFIX}{key}")
            if ttl < 60:  # Less than 1 minute remaining
                await self.set(key, data)
            return data
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        try:
            client = await self._get_client()
            ttl_val = ttl or CACHE_TTL_SECONDS
            return await client.set(f"{CACHE_KEY_PREFIX}{key}", value, ex=ttl_val)
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        try:
            client = await self._get_client()
            return await client.delete(f"{CACHE_KEY_PREFIX}{key}")
        except Exception:
            return False


# Global cache instance
cache_client = RedisCacheClient()


def get_cached(key: str) -> Optional[Any]:  # noqa: ANN001, D103
    """Synchronous wrapper for async get."""
    import asyncio
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(cache_client.get(key))
    finally:
        if not loop.is_closed():
            loop.close()


def set_cached(  # noqa: ANN001, D103
    key: str, value: Any, ttl: Optional[int] = None
) -> bool:
    """Synchronous wrapper for async set."""
    import asyncio
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(cache_client.set(key, value, ttl))
    finally:
        if not loop.is_closed():
            loop.close()


def cache_with_ttl(  # noqa: ANN001, D103
    ttl: Optional[int] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to cache async function results with TTL."""
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN003, D102
            cache_key = f"{func.__name__}:{str(sorted(kwargs.items()))}"
            
            cached_value = await cache_client.get(cache_key)
            if cached_value is not None and isinstance(cached_value, dict):
                return cached_value
            
            # Call original function
            result = await func(*args, **kwargs)
            
            # Store with TTL
            try:
                await cache_client.set(cache_key, str(result), ttl or CACHE_TTL_SECONDS)
            except Exception:
                pass  # Don't fail the API if caching fails
            
            return result
        
        return wrapper
    
    return decorator
