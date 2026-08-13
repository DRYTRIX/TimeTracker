"""Time rounding utilities for per-user time entry rounding preferences"""

import math
from datetime import datetime, timedelta
from typing import Optional, Tuple


def round_time_duration(duration_seconds: int, rounding_minutes: int = 1, rounding_method: str = "nearest") -> int:
    """
    Round a time duration in seconds based on the specified rounding settings.

    Args:
        duration_seconds: The raw duration in seconds
        rounding_minutes: The rounding interval in minutes (e.g., 1, 5, 10, 15, 30, 60)
        rounding_method: The rounding method ('nearest', 'up', 'down', or 'boundary')

    Returns:
        int: The rounded duration in seconds

    Notes:
        ``boundary`` mode does not change duration by itself — callers should use
        :func:`round_entry_boundaries` to adjust start/end timestamps and then
        recompute duration. For safety, ``boundary`` here behaves like ``nearest``.
    """
    # If rounding is disabled (rounding_minutes = 1), return raw duration
    if rounding_minutes <= 1:
        return duration_seconds

    # Validate rounding method
    if rounding_method not in ("nearest", "up", "down", "boundary"):
        rounding_method = "nearest"

    # Boundary is handled by round_entry_boundaries; fall through to nearest for duration-only
    if rounding_method == "boundary":
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


def round_entry_boundaries(
    start_time: datetime, end_time: datetime, rounding_minutes: int
) -> Tuple[datetime, datetime]:
    """
    Round start_time DOWN and end_time UP to the nearest interval boundary.

    Example (5-minute interval): 09:46–09:54 → 09:45–09:55.

    Seconds and microseconds are cleared on both timestamps.
    """
    if rounding_minutes <= 1 or start_time is None or end_time is None:
        return start_time, end_time

    def _floor_to_interval(dt: datetime) -> datetime:
        total_minutes = dt.hour * 60 + dt.minute
        floored = (total_minutes // rounding_minutes) * rounding_minutes
        return dt.replace(
            hour=floored // 60,
            minute=floored % 60,
            second=0,
            microsecond=0,
        )

    def _ceil_to_interval(dt: datetime) -> datetime:
        # If already exactly on a boundary (and no leftover seconds), keep it
        if dt.second == 0 and dt.microsecond == 0 and (dt.hour * 60 + dt.minute) % rounding_minutes == 0:
            return dt.replace(second=0, microsecond=0)
        total_minutes = dt.hour * 60 + dt.minute
        # Any leftover seconds push us into the next minute for ceiling purposes
        if dt.second > 0 or dt.microsecond > 0:
            total_minutes += 1
        ceiled = math.ceil(total_minutes / rounding_minutes) * rounding_minutes
        # Handle overflow past midnight by using timedelta from midnight of the day
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start + timedelta(minutes=ceiled)

    rounded_start = _floor_to_interval(start_time)
    rounded_end = _ceil_to_interval(end_time)

    # Guarantee end is strictly after start (at least one interval)
    if rounded_end <= rounded_start:
        rounded_end = rounded_start + timedelta(minutes=rounding_minutes)

    return rounded_start, rounded_end


def apply_minimum_duration(duration_seconds: int, minimum_minutes: int) -> int:
    """Raise duration to at least ``minimum_minutes`` (0 or less = no floor)."""
    if not minimum_minutes or minimum_minutes <= 0:
        return duration_seconds
    minimum_seconds = int(minimum_minutes) * 60
    return max(duration_seconds, minimum_seconds)


def get_user_rounding_settings(user) -> dict:
    """
    Get the time rounding settings for a user.

    When the user has the default "no rounding" interval (1 minute), fall back
    to the global Settings.rounding_minutes so the admin setting actually applies
    (Issue #725).
    """
    enabled = getattr(user, "time_rounding_enabled", True)
    minutes = getattr(user, "time_rounding_minutes", 1)
    method = getattr(user, "time_rounding_method", "nearest")
    minimum = getattr(user, "time_rounding_minimum_minutes", 0) or 0

    # Fall back to global admin setting when user has not customised the interval
    if enabled and minutes <= 1:
        try:
            from app.models.settings import Settings

            settings = Settings.get_settings()
            global_minutes = int(getattr(settings, "rounding_minutes", 1) or 1)
            if global_minutes > 1:
                minutes = global_minutes
                # Prefer user method if they set one other than nearest; else nearest
                if method not in ("nearest", "up", "down", "boundary"):
                    method = "nearest"
        except Exception:
            from app.config import Config

            global_minutes = int(getattr(Config, "ROUNDING_MINUTES", 1) or 1)
            if global_minutes > 1:
                minutes = global_minutes

    return {
        "enabled": enabled,
        "minutes": minutes,
        "method": method,
        "minimum_minutes": minimum,
    }


def apply_user_rounding(duration_seconds: int, user) -> int:
    """
    Apply a user's rounding preferences to a duration.

    For ``boundary`` method this only applies the minimum-duration floor —
    callers must adjust timestamps via :func:`round_entry_boundaries` first.
    """
    settings = get_user_rounding_settings(user)

    # If rounding is disabled for this user, still apply minimum duration
    if not settings["enabled"]:
        return apply_minimum_duration(duration_seconds, settings["minimum_minutes"])

    if settings["method"] == "boundary":
        # Duration already reflects boundary-adjusted timestamps
        rounded = duration_seconds
    else:
        rounded = round_time_duration(duration_seconds, settings["minutes"], settings["method"])

    return apply_minimum_duration(rounded, settings["minimum_minutes"])


def format_rounding_interval(minutes: int) -> str:
    """
    Format a rounding interval in minutes as a human-readable string.
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
    """Get the list of available rounding intervals."""
    return [
        (1, "No rounding / use system default"),
        (5, "5 minutes"),
        (10, "10 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
    ]


def get_available_rounding_methods() -> list:
    """Get the list of available rounding methods."""
    return [
        ("nearest", "Round to nearest", "Round the total duration to the nearest interval"),
        ("up", "Always round up", "Always round the total duration up to the next interval"),
        ("down", "Always round down", "Always round the total duration down to the previous interval"),
        (
            "boundary",
            "Round start/end to boundaries",
            "Round start time down and end time up to interval markers (e.g. 09:46–09:54 → 09:45–09:55)",
        ),
    ]


def get_available_minimum_durations() -> list:
    """Get the list of available minimum billable durations."""
    return [
        (0, "No minimum"),
        (5, "5 minutes"),
        (10, "10 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
    ]
