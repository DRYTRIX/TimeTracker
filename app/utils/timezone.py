import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones, ZoneInfoNotFoundError
from functools import lru_cache
from flask import current_app


# ---- Date/time format preference mappings ----

USER_DATE_FORMATS = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
}

USER_TIME_FORMATS = {
    "24h": "%H:%M",
    "12h": "%I:%M %p",
}

# Default fallbacks when no preference is set
_DEFAULT_DATE_FORMAT_KEY = "YYYY-MM-DD"
_DEFAULT_TIME_FORMAT_KEY = "24h"


def _get_system_date_format_key():
    """Return the system-wide date_format key from Settings, or the hardcoded default."""
    try:
        from flask import has_app_context
        if not has_app_context():
            return _DEFAULT_DATE_FORMAT_KEY
        from app.models import Settings
        from app import db
        try:
            if db.session.is_active and not getattr(db.session, "_flushing", False):
                settings = Settings.get_settings()
                if settings:
                    val = getattr(settings, "date_format", None)
                    if val and val in USER_DATE_FORMATS:
                        return val
        except Exception:
            pass
    except Exception:
        pass
    return _DEFAULT_DATE_FORMAT_KEY


def _get_system_time_format_key():
    """Return the system-wide time_format key from Settings, or the hardcoded default."""
    try:
        from flask import has_app_context
        if not has_app_context():
            return _DEFAULT_TIME_FORMAT_KEY
        from app.models import Settings
        from app import db
        try:
            if db.session.is_active and not getattr(db.session, "_flushing", False):
                settings = Settings.get_settings()
                if settings:
                    val = getattr(settings, "time_format", None)
                    if val and val in USER_TIME_FORMATS:
                        return val
        except Exception:
            pass
    except Exception:
        pass
    return _DEFAULT_TIME_FORMAT_KEY


def get_resolved_date_format_key(user=None):
    """Return the date format key (e.g. YYYY-MM-DD) for the user, falling back to system."""
    resolved_user = _get_authenticated_user(user)
    if resolved_user:
        pref = getattr(resolved_user, "date_format", None)
        if pref and pref in USER_DATE_FORMATS:
            return pref
    return _get_system_date_format_key()


def get_resolved_time_format_key(user=None):
    """Return the time format key (e.g. 24h) for the user, falling back to system."""
    resolved_user = _get_authenticated_user(user)
    if resolved_user:
        pref = getattr(resolved_user, "time_format", None)
        if pref and pref in USER_TIME_FORMATS:
            return pref
    return _get_system_time_format_key()


def get_resolved_week_start_day(user=None):
    """Return the week start day (0=Sunday, 1=Monday, ..., 6=Saturday) for the user, default 1."""
    resolved_user = _get_authenticated_user(user)
    if resolved_user:
        day = getattr(resolved_user, "week_start_day", None)
        if day is not None and 0 <= day <= 6:
            return day
    return 1


def get_user_date_format(user=None):
    """Return the strftime date format string for the user's preference.

    Fallback chain: user preference -> system setting -> hardcoded default.
    """
    resolved_user = _get_authenticated_user(user)
    if resolved_user:
        pref = getattr(resolved_user, "date_format", None)
        if pref and pref in USER_DATE_FORMATS:
            return USER_DATE_FORMATS[pref]
    # Fall back to system setting
    return USER_DATE_FORMATS[_get_system_date_format_key()]


def get_user_time_format(user=None):
    """Return the strftime time format string for the user's preference.

    Fallback chain: user preference -> system setting -> hardcoded default.
    """
    resolved_user = _get_authenticated_user(user)
    if resolved_user:
        pref = getattr(resolved_user, "time_format", None)
        if pref and pref in USER_TIME_FORMATS:
            return USER_TIME_FORMATS[pref]
    # Fall back to system setting
    return USER_TIME_FORMATS[_get_system_time_format_key()]


def get_user_datetime_format(user=None):
    """Return combined date+time strftime format string from user preferences."""
    return f"{get_user_date_format(user)} {get_user_time_format(user)}"


@lru_cache()
def get_available_timezones():
    """Return a cached, alphabetically sorted list of common timezones."""
    return tuple(sorted(available_timezones()))


def _get_authenticated_user(user=None):
    """Safely resolve an authenticated user either from argument or flask-login context."""
    if user is not None:
        return user

    try:
        from flask_login import current_user

        if current_user and getattr(current_user, "is_authenticated", False):
            return current_user
    except Exception:
        # Outside of request context or flask-login not set up yet
        pass

    return None


def get_app_timezone():
    """Get the application's configured timezone from database settings or environment."""
    try:
        # Check if we have an application context before accessing database
        from flask import has_app_context

        if not has_app_context():
            # No app context, skip database lookup
            return os.getenv("TZ", "Europe/Rome")

        # Try to get timezone from database settings first
        from app.models import Settings
        from app import db

        # Check if we have a database connection
        try:
            if db.session.is_active and not getattr(db.session, "_flushing", False):
                try:
                    settings = Settings.get_settings()
                    if settings and settings.timezone:
                        return settings.timezone
                except Exception as e:
                    # Log the error but continue with fallback
                    print(f"Warning: Could not get timezone from database: {e}")
        except RuntimeError as e:
            # RuntimeError typically means "Working outside of application context"
            # Fall back to environment variable
            pass
    except Exception as e:
        # If database is not available or settings don't exist, fall back to environment
        print(f"Warning: Database not available for timezone: {e}")

    # Fallback to environment variable
    return os.getenv("TZ", "Europe/Rome")


def get_timezone_obj():
    """Get timezone object for the configured application timezone."""
    tz_name = get_app_timezone()
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        # Fallback to UTC if timezone is invalid
        return ZoneInfo("UTC")


def get_user_timezone_name(user=None):
    """Return the timezone name for the given user, if defined and valid."""
    resolved_user = _get_authenticated_user(user)
    if not resolved_user:
        return None

    timezone_name = getattr(resolved_user, "timezone", None)
    if timezone_name:
        try:
            ZoneInfo(timezone_name)
            return timezone_name
        except (ZoneInfoNotFoundError, KeyError):
            try:
                current_app.logger.warning(
                    "User %s has invalid timezone '%s'. Falling back to app timezone.",
                    getattr(resolved_user, "id", None),
                    timezone_name,
                )
            except RuntimeError:
                # Current app not available, fallback to stdout
                print(f"Warning: Invalid timezone '{timezone_name}' for user {getattr(resolved_user, 'id', 'unknown')}")
    return None


def get_timezone_for_user(user=None):
    """Get timezone object respecting the user's preference when available."""
    timezone_name = get_user_timezone_name(user)
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, KeyError):
            pass
    return get_timezone_obj()


def now_in_app_timezone():
    """Get current time in the application's timezone."""
    tz = get_timezone_obj()
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(tz)


def now_in_user_timezone(user=None):
    """Get current time in the user's timezone (falls back to app timezone)."""
    tz = get_timezone_for_user(user)
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(tz)


def local_now():
    """Get current time in the application's timezone (alias for now_in_app_timezone)."""
    return now_in_app_timezone()


def _localize_with_timezone(dt, tz):
    """Localize a naive datetime with the given zoneinfo timezone, handling edge cases.

    For ambiguous times (e.g. fall-back), fold=0 selects the first (DST) occurrence
    and fold=1 selects the second (standard-time) occurrence.  We prefer standard time.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(tz)

    # Use fold=1 to prefer standard time for ambiguous datetimes
    return dt.replace(tzinfo=tz, fold=1)


def convert_app_datetime_to_user(dt, user=None):
    """Convert a datetime stored in application timezone to the user's timezone."""
    if dt is None:
        return None

    app_tz = get_timezone_obj()
    target_tz = get_timezone_for_user(user)

    localized = _localize_with_timezone(dt, app_tz)
    return localized.astimezone(target_tz)


def utc_to_local(utc_dt):
    """Convert UTC datetime to local application timezone."""
    if utc_dt is None:
        return None

    # If datetime is naive (no timezone), assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    tz = get_timezone_obj()
    return utc_dt.astimezone(tz)


def utc_to_user_local(utc_dt, user=None):
    """Convert UTC datetime to the user's local timezone."""
    if utc_dt is None:
        return None

    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    tz = get_timezone_for_user(user)
    return utc_dt.astimezone(tz)


def local_to_utc(local_dt):
    """Convert local datetime (in application timezone) to UTC."""
    if local_dt is None:
        return None

    tz = get_timezone_obj()
    localized = _localize_with_timezone(local_dt, tz)
    return localized.astimezone(timezone.utc)


def user_local_to_utc(local_dt, user=None):
    """Convert a user-local datetime to UTC (assumes datetime is in user's timezone)."""
    if local_dt is None:
        return None

    tz = get_timezone_for_user(user)
    localized = _localize_with_timezone(local_dt, tz)
    return localized.astimezone(timezone.utc)


def parse_local_datetime(date_str, time_str):
    """Parse date and time strings in local application timezone."""
    try:
        # Combine date and time
        datetime_str = f"{date_str} {time_str}"

        # Parse as naive datetime (assumed to be in local timezone)
        naive_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

        # Localize to application timezone using zoneinfo
        tz = get_timezone_obj()
        local_dt = _localize_with_timezone(naive_dt, tz)

        # Convert to UTC for storage
        return local_dt.astimezone(timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid date/time format: {e}")


def parse_user_local_datetime(date_str, time_str, user=None):
    """Parse date and time strings as user's local time; return naive datetime in app timezone for storage.

    Use this for manual time entry forms where the user enters a time in their local timezone.
    When user has no timezone set, falls back to app timezone (same as parse_local_datetime input semantics).
    """
    try:
        datetime_str = f"{date_str} {time_str}"
        naive_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

        # Treat input as user's timezone (or app timezone if no user / no user TZ)
        user_tz = get_timezone_for_user(user)
        app_tz = get_timezone_obj()
        localized_in_user_tz = _localize_with_timezone(naive_dt, user_tz)
        in_app_tz = localized_in_user_tz.astimezone(app_tz)
        return in_app_tz.replace(tzinfo=None)
    except ValueError as e:
        raise ValueError(f"Invalid date/time format: {e}")


def format_local_datetime(utc_dt, format_str="%Y-%m-%d %H:%M"):
    """Format UTC datetime in local application timezone."""
    if utc_dt is None:
        return ""

    local_dt = utc_to_local(utc_dt)
    return local_dt.strftime(format_str)


def format_user_datetime(dt, format_str=None, user=None, assume_app_timezone=True):
    """Format datetime using the user's timezone and format preferences.

    When *format_str* is ``None`` (the default), the format is resolved
    automatically from the user's ``date_format`` / ``time_format``
    preferences, falling back to the system-wide setting and ultimately
    to ``%Y-%m-%d %H:%M``.

    Callers that pass an explicit *format_str* get the exact same
    behaviour as before (the string is used as-is).
    """
    if dt is None:
        return ""

    resolved_user = _get_authenticated_user(user)

    if format_str is None:
        format_str = get_user_datetime_format(resolved_user)

    if assume_app_timezone:
        localized = convert_app_datetime_to_user(dt, user=resolved_user)
    else:
        localized = utc_to_user_local(dt, user=resolved_user)

    return localized.strftime(format_str) if localized else ""


def get_timezone_offset():
    """Get current timezone offset from UTC in hours for the application timezone."""
    tz = get_timezone_obj()
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(tz)
    offset = local_now.utcoffset()
    return offset.total_seconds() / 3600 if offset else 0


def get_timezone_offset_for_timezone(tz_name):
    """Get timezone offset for a specific timezone name."""
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(timezone.utc)
        local_now = now.astimezone(tz)
        offset = local_now.utcoffset()
        return offset.total_seconds() / 3600 if offset else 0
    except (ZoneInfoNotFoundError, KeyError):
        return 0
