"""Time rounding utilities for per-user time entry rounding preferences"""

import math
from typing import Optional


def round_time_duration(duration_seconds: int, rounding_minutes: int = 1, rounding_method: str = "nearest") -> int:
    """
    Round a time duration in seconds based on the specified rounding settings.

    Args:
        duration_seconds: The raw duration in seconds
        rounding_minutes: The rounding interval in minutes (e.g., 1, 5, 10, 15, 30, 60)
        rounding_method: The rounding method ('nearest', 'up', or 'down')

    Returns:
        int: The rounded duration in seconds

    Examples:
        >>> round_time_duration(3720, 15, 'nearest')  # 62 minutes -> 60 minutes (1 hour)
        3600
        >>> round_time_duration(3720, 15, 'up')  # 62 minutes -> 75 minutes (1.25 hours)
        4500
        >>> round_time_duration(3720, 15, 'down')  # 62 minutes -> 60 minutes (1 hour)
        3600
    """
    # If rounding is disabled (rounding_minutes = 1), return raw duration
    if rounding_minutes <= 1:
        return duration_seconds

    # Validate rounding method
    if rounding_method not in ("nearest", "up", "down"):
        rounding_method = "nearest"

    # Convert to minutes for easier calculation
    duration_minutes = duration_seconds / 60.0

    # Apply rounding based on method
    if rounding_method == "up":
        rounded_minutes = math.ceil(duration_minutes / rounding_minutes) * rounding_minutes
    elif rounding_method == "down":
        rounded_minutes = math.floor(duration_minutes / rounding_minutes) * rounding_minutes
    else:  # 'nearest'
        rounded_minutes = round(duration_minutes / rounding_minutes) * rounding_minutes

    # Convert back to seconds
    return int(rounded_minutes * 60)


def get_user_rounding_settings(user) -> dict:
    """
    Get the time rounding settings for a user.

    Args:
        user: A User model instance

    Returns:
        dict: Dictionary with 'enabled', 'minutes', and 'method' keys
    """
    return {
        "enabled": getattr(user, "time_rounding_enabled", True),
        "minutes": getattr(user, "time_rounding_minutes", 1),
        "method": getattr(user, "time_rounding_method", "nearest"),
    }


def apply_user_rounding(duration_seconds: int, user) -> int:
    """
    Apply a user's rounding preferences to a duration.

    Args:
        duration_seconds: The raw duration in seconds
        user: A User model instance with rounding preferences

    Returns:
        int: The rounded duration in seconds
    """
    settings = get_user_rounding_settings(user)

    # If rounding is disabled for this user, return raw duration
    if not settings["enabled"]:
        return duration_seconds

    return round_time_duration(duration_seconds, settings["minutes"], settings["method"])


def format_rounding_interval(minutes: int) -> str:
    """
    Format a rounding interval in minutes as a human-readable string.

    Args:
        minutes: The rounding interval in minutes

    Returns:
        str: A human-readable description

    Examples:
        >>> format_rounding_interval(1)
        'No rounding (exact time)'
        >>> format_rounding_interval(15)
        '15 minutes'
        >>> format_rounding_interval(60)
        '1 hour'
    """
    if minutes <= 1:
        return "No rounding (exact time)"
    elif minutes == 60:
        return "1 hour"
    elif minutes >= 60:
        hours = minutes // 60
        return f'{hours} hour{"s" if hours > 1 else ""}'
    else:
        return f'{minutes} minute{"s" if minutes > 1 else ""}'


def get_available_rounding_intervals() -> list:
    """
    Get the list of available rounding intervals.

    Returns:
        list: List of tuples (minutes, label)
    """
    return [
        (1, "No rounding (exact time)"),
        (5, "5 minutes"),
        (10, "10 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
    ]


def get_available_rounding_methods() -> list:
    """
    Get the list of available rounding methods.

    Returns:
        list: List of tuples (method, label, description)
    """
    return [
        ("nearest", "Round to nearest", "Round to the nearest interval (standard rounding)"),
        ("up", "Always round up", "Always round up to the next interval (ceiling)"),
        ("down", "Always round down", "Always round down to the previous interval (floor)"),
    ]
