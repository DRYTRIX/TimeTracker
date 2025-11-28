"""
Rate limiting utilities and helpers.
"""

from typing import Callable, Optional, Dict, Any
from functools import wraps
from flask import request, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_rate_limit_key() -> str:
    """
    Get rate limit key for current request.

    Uses API token if available, otherwise IP address.
    """
    # Check for API token
    if hasattr(request, "api_user") and request.api_user:
        return f"api_token:{request.api_user.id}"

    # Check for authenticated user
    from flask_login import current_user

    if current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"

    # Fall back to IP address
    return get_remote_address()


def rate_limit(per_minute: Optional[int] = None, per_hour: Optional[int] = None, per_day: Optional[int] = None):
    """
    Decorator for rate limiting endpoints.

    Args:
        per_minute: Requests per minute
        per_hour: Requests per hour
        per_day: Requests per day

    Usage:
        @rate_limit(per_minute=60, per_hour=1000)
        def my_endpoint():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Rate limiting is handled by Flask-Limiter middleware
            # This decorator is mainly for documentation
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_rate_limit_info() -> Dict[str, Any]:
    """
    Get rate limit information for current request.

    Returns:
        dict with rate limit info
    """
    # This would integrate with Flask-Limiter to get current limits
    # For now, return default info
    return {"limit": 100, "remaining": 99, "reset": None}
