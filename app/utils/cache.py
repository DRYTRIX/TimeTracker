"""
Caching utilities with Redis support.
Falls back to in-memory cache if Redis is not available.
"""

from typing import Any, Optional, Callable, Dict
from functools import wraps
import time
import hashlib
import json
import pickle
from flask import current_app

# Try to import Redis
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class InMemoryCache:
    """Simple in-memory cache fallback"""

    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

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


class RedisCache:
    """Redis-backed cache implementation"""

    def __init__(self, redis_url: str, default_ttl: int = 3600):
        """Initialize Redis cache connection"""
        self._default_ttl = default_ttl
        try:
            # Parse Redis URL
            from urllib.parse import urlparse

            parsed = urlparse(redis_url)

            # Extract password from URL if present
            password = parsed.password or None

            self._client = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=password,
                db=int(parsed.path.lstrip("/")) if parsed.path else 0,
                decode_responses=False,  # We'll handle serialization ourselves
                socket_connect_timeout=1,  # Fast fail - don't block requests
                socket_timeout=1,  # Fast timeout for operations
                socket_keepalive=False,  # Disable keepalive to avoid delays
                retry_on_timeout=False,  # Don't retry on timeout
            )
            # Test connection with short timeout
            self._client.ping()
            self._connected = True
        except Exception as e:
            # Fallback to in-memory if Redis connection fails
            if current_app:
                current_app.logger.warning(f"Redis connection failed, using in-memory cache: {e}")
            self._connected = False
            self._fallback = InMemoryCache(default_ttl)

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self._connected:
            return self._fallback.get(key)

        try:
            data = self._client.get(key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache"""
        if not self._connected:
            self._fallback.set(key, value, ttl)
            return

        try:
            ttl = ttl or self._default_ttl
            data = pickle.dumps(value)
            self._client.setex(key, ttl, data)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        """Delete a value from cache"""
        if not self._connected:
            self._fallback.delete(key)
            return

        try:
            self._client.delete(key)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis delete error: {e}")

    def clear(self) -> None:
        """Clear all cache"""
        if not self._connected:
            self._fallback.clear()
            return

        try:
            self._client.flushdb()
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis clear error: {e}")

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        if not self._connected:
            return self._fallback.exists(key)

        try:
            return bool(self._client.exists(key))
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis exists error: {e}")
            return False


# Global cache instance (initialized on first use)
_cache: Optional[Any] = None


def get_cache():
    """Get the global cache instance (Redis if available, otherwise in-memory)"""
    global _cache

    if _cache is not None:
        return _cache

    # Try to initialize Redis if enabled
    try:
        if current_app and current_app.config.get("REDIS_ENABLED", True) and REDIS_AVAILABLE:
            redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
            default_ttl = current_app.config.get("REDIS_DEFAULT_TTL", 3600)
            _cache = RedisCache(redis_url, default_ttl)
            if _cache._connected:
                return _cache
    except RuntimeError:
        # Outside application context
        pass
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Failed to initialize Redis cache: {e}")

    # Fallback to in-memory cache
    default_ttl = 3600
    if current_app:
        default_ttl = current_app.config.get("REDIS_DEFAULT_TTL", 3600)
    _cache = InMemoryCache(default_ttl)
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


def invalidate_pattern(pattern: str) -> None:
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: Pattern to match (supports * wildcard)
    """
    cache = get_cache()
    if hasattr(cache, "_client") and cache._connected:
        # Redis pattern matching
        try:
            keys = cache._client.keys(pattern)
            if keys:
                cache._client.delete(*keys)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Redis pattern delete error: {e}")
    else:
        # For in-memory, use simple clear (can be improved)
        cache.clear()
