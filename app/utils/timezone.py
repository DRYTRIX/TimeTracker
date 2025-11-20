import os
import pytz
from datetime import datetime, timezone
from functools import lru_cache
from flask import current_app


@lru_cache()
def get_available_timezones():
    """Return a cached, alphabetically sorted list of common timezones."""
    return tuple(sorted(pytz.common_timezones))


def _get_authenticated_user(user=None):
    """Safely resolve an authenticated user either from argument or flask-login context."""
    if user is not None:
        return user
    
    try:
        from flask_login import current_user
        if current_user and getattr(current_user, 'is_authenticated', False):
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
            return os.getenv('TZ', 'Europe/Rome')
        
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
    return os.getenv('TZ', 'Europe/Rome')


def get_timezone_obj():
    """Get timezone object for the configured application timezone."""
    tz_name = get_app_timezone()
    try:
        return pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        # Fallback to UTC if timezone is invalid
        return pytz.UTC


def get_user_timezone_name(user=None):
    """Return the timezone name for the given user, if defined and valid."""
    resolved_user = _get_authenticated_user(user)
    if not resolved_user:
        return None
    
    timezone_name = getattr(resolved_user, 'timezone', None)
    if timezone_name:
        try:
            pytz.timezone(timezone_name)
            return timezone_name
        except pytz.exceptions.UnknownTimeZoneError:
            try:
                current_app.logger.warning(
                    "User %s has invalid timezone '%s'. Falling back to app timezone.",
                    getattr(resolved_user, 'id', None),
                    timezone_name
                )
            except RuntimeError:
                # Current app not available, fallback to stdout
                print(f"Warning: Invalid timezone '{timezone_name}' for user {getattr(resolved_user, 'id', 'unknown')}")
    return None


def get_timezone_for_user(user=None):
    """Get pytz timezone object respecting the user's preference when available."""
    timezone_name = get_user_timezone_name(user)
    if timezone_name:
        try:
            return pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
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


def _localize_with_timezone(dt, tz):
    """Localize a naive datetime with the given pytz timezone, handling edge cases."""
    if dt.tzinfo is not None:
        return dt.astimezone(tz)
    
    try:
        return tz.localize(dt)
    except pytz.AmbiguousTimeError:
        # Prefer standard time when ambiguous
        return tz.localize(dt, is_dst=False)
    except pytz.NonExistentTimeError:
        # Fallback to DST when the time does not exist (typically spring forward)
        return tz.localize(dt, is_dst=True)
    except Exception:
        # Fallback: attach tzinfo directly (may be inaccurate around DST boundaries)
        return dt.replace(tzinfo=tz)


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
        datetime_str = f'{date_str} {time_str}'
        
        # Parse as naive datetime (assumed to be in local timezone)
        naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        
        # Localize to application timezone
        tz = get_timezone_obj()
        local_dt = tz.localize(naive_dt)
        
        # Convert to UTC for storage
        return local_dt.astimezone(timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid date/time format: {e}")


def format_local_datetime(utc_dt, format_str='%Y-%m-%d %H:%M'):
    """Format UTC datetime in local application timezone."""
    if utc_dt is None:
        return ""
    
    local_dt = utc_to_local(utc_dt)
    return local_dt.strftime(format_str)


def format_user_datetime(dt, format_str='%Y-%m-%d %H:%M', user=None, assume_app_timezone=True):
    """Format datetime using the user's timezone preference."""
    if dt is None:
        return ""
    
    resolved_user = _get_authenticated_user(user)
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
        tz = pytz.timezone(tz_name)
        now = datetime.now(timezone.utc)
        local_now = now.astimezone(tz)
        offset = local_now.utcoffset()
        return offset.total_seconds() / 3600 if offset else 0
    except pytz.exceptions.UnknownTimeZoneError:
        return 0
