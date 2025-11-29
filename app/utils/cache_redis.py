"""
Redis caching utilities for TimeTracker.
Provides caching layer for frequently accessed data.

Note: This is a foundation implementation. Redis integration requires:
1. Install redis: pip install redis
2. Set REDIS_URL environment variable
3. Start Redis server
"""

import os
import json
import logging
from typing import Optional, Any, Dict, Callable
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import redis, but don't fail if not available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Install with: pip install redis")


def get_redis_client():
    """
    Get Redis client instance.

    Returns:
        Redis client or None if Redis is not configured
    """
    if not REDIS_AVAILABLE:
        return None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        client = redis.from_url(redis_url, decode_responses=True)
        # Test connection
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Caching disabled.")
        return None


def cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    key_parts = [prefix]

    for arg in args:
        key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")

    return ":".join(key_parts)


def get_cache(key: str, default: Any = None) -> Optional[Any]:
    """
    Get value from cache.

    Args:
        key: Cache key
        default: Default value if key not found

    Returns:
        Cached value or default
    """
    client = get_redis_client()
    if not client:
        return default

    try:
        value = client.get(key)
        if value is None:
            return default

        # Try to deserialize JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return default


def set_cache(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    Set value in cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 1 hour)

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        # Serialize value if needed
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def delete_cache(key: str) -> bool:
    """
    Delete value from cache.

    Args:
        key: Cache key (supports wildcards with *)

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        if "*" in key:
            # Delete all keys matching pattern
            keys = client.keys(key)
            if keys:
                client.delete(*keys)
        else:
            client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


def cache_result(prefix: str, ttl: int = 3600, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from args/kwargs

    Usage:
        @cache_result('user_projects', ttl=300)
        def get_user_projects(user_id):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached = get_cache(cache_key_str)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            set_cache(cache_key_str, result, ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache keys matching a pattern.

    Args:
        pattern: Cache key pattern (supports *)

    Example:
        invalidate_cache_pattern('user_projects:*')  # Invalidate all user projects
    """
    return delete_cache(pattern)


# Cache key prefixes (for consistency)
class CacheKeys:
    """Standard cache key prefixes"""

    USER_PROJECTS = "user_projects"
    PROJECT_DETAILS = "project_details"
    TASK_LIST = "task_list"
    INVOICE_LIST = "invoice_list"
    SETTINGS = "settings"
    USER_PREFERENCES = "user_preferences"
    CLIENT_LIST = "client_list"
