"""
Caching utilities for future Redis integration.
Currently provides a simple in-memory cache, can be replaced with Redis.
"""

from typing import Any, Optional, Callable, Dict
from functools import wraps
import time
import hashlib
import json


class Cache:
    """Simple in-memory cache (can be replaced with Redis)"""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._default_ttl = 3600  # 1 hour

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache"""
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete a value from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        if key not in self._cache:
            return False

        _, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return False

        return True


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance"""
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments"""
    key_data = {"args": args, "kwargs": sorted(kwargs.items())}
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str) -> None:
    """
    Invalidate cache entries matching a pattern.

    Note: This is a simple implementation. Redis would use pattern matching.
    """
    cache = get_cache()
    # Simple implementation - in production, use Redis pattern matching
    cache.clear()  # For now, just clear all (can be improved)


# Future Redis integration
def init_redis_cache(redis_url: Optional[str] = None) -> None:
    """
    Initialize Redis cache (for future use).

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
    """
    # This would be implemented when Redis is added
    # For now, keep using in-memory cache
    pass
