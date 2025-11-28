"""
Enhanced date and time utilities.
"""

from typing import Optional, Tuple
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from app.utils.timezone import now_in_app_timezone, to_app_timezone, from_app_timezone


def parse_date(date_str: str, format: Optional[str] = None) -> Optional[date]:
    """
    Parse a date string to a date object.

    Args:
        date_str: Date string
        format: Optional format string (defaults to ISO format)

    Returns:
        date object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        if format:
            return datetime.strptime(date_str, format).date()
        else:
            # Try ISO format first
            try:
                return datetime.fromisoformat(date_str).date()
            except ValueError:
                # Try common formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                return None
    except Exception:
        return None


def parse_datetime(datetime_str: str, format: Optional[str] = None) -> Optional[datetime]:
    """
    Parse a datetime string to a datetime object.

    Args:
        datetime_str: Datetime string
        format: Optional format string (defaults to ISO format)

    Returns:
        datetime object or None if parsing fails
    """
    if not datetime_str:
        return None

    try:
        if format:
            return datetime.strptime(datetime_str, format)
        else:
            # Try ISO format first
            try:
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except ValueError:
                # Try common formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
                    try:
                        return datetime.strptime(datetime_str, fmt)
                    except ValueError:
                        continue
                return None
    except Exception:
        return None


def format_date(d: date, format: str = "%Y-%m-%d") -> str:
    """
    Format a date object to a string.

    Args:
        d: date object
        format: Format string

    Returns:
        Formatted date string
    """
    if not d:
        return ""
    return d.strftime(format)


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object to a string.

    Args:
        dt: datetime object
        format: Format string

    Returns:
        Formatted datetime string
    """
    if not dt:
        return ""
    return dt.strftime(format)


def get_date_range(
    period: str = "month", start_date: Optional[date] = None, end_date: Optional[date] = None
) -> Tuple[date, date]:
    """
    Get a date range for common periods.

    Args:
        period: Period type ('today', 'week', 'month', 'quarter', 'year', 'custom')
        start_date: Custom start date (for 'custom' period)
        end_date: Custom end date (for 'custom' period)

    Returns:
        tuple of (start_date, end_date)
    """
    today = date.today()

    if period == "today":
        return today, today

    elif period == "week":
        # Start of week (Monday)
        start = today - timedelta(days=today.weekday())
        return start, today

    elif period == "month":
        start = today.replace(day=1)
        return start, today

    elif period == "quarter":
        quarter = (today.month - 1) // 3
        start = date(today.year, quarter * 3 + 1, 1)
        return start, today

    elif period == "year":
        start = date(today.year, 1, 1)
        return start, today

    elif period == "custom":
        if start_date and end_date:
            return start_date, end_date
        return today, today

    else:
        return today, today


def get_previous_period(period: str = "month", reference_date: Optional[date] = None) -> Tuple[date, date]:
    """
    Get the previous period date range.

    Args:
        period: Period type ('week', 'month', 'quarter', 'year')
        reference_date: Reference date (defaults to today)

    Returns:
        tuple of (start_date, end_date)
    """
    ref = reference_date or date.today()

    if period == "week":
        start = ref - timedelta(days=ref.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end

    elif period == "month":
        first_day = ref.replace(day=1)
        start = first_day - relativedelta(months=1)
        end = first_day - timedelta(days=1)
        return start, end

    elif period == "quarter":
        quarter = (ref.month - 1) // 3
        start = date(ref.year, quarter * 3 + 1, 1)
        if quarter == 0:
            start = date(ref.year - 1, 10, 1)
            end = date(ref.year - 1, 12, 31)
        else:
            end = date(ref.year, quarter * 3, 1) - timedelta(days=1)
        return start, end

    elif period == "year":
        start = date(ref.year - 1, 1, 1)
        end = date(ref.year - 1, 12, 31)
        return start, end

    else:
        return ref, ref


def calculate_duration(start: datetime, end: datetime) -> timedelta:
    """
    Calculate duration between two datetimes.

    Args:
        start: Start datetime
        end: End datetime

    Returns:
        timedelta object
    """
    if not start or not end:
        return timedelta(0)

    return end - start


def format_duration(seconds: float, format: str = "hours") -> str:
    """
    Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds
        format: Format type ('hours', 'detailed', 'short')

    Returns:
        Formatted duration string
    """
    if format == "hours":
        hours = seconds / 3600
        return f"{hours:.2f}h"

    elif format == "detailed":
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    elif format == "short":
        hours = seconds / 3600
        if hours < 1:
            minutes = seconds / 60
            return f"{int(minutes)}m"
        return f"{hours:.1f}h"

    else:
        return f"{seconds}s"


def is_business_day(d: date) -> bool:
    """
    Check if a date is a business day (Monday-Friday).

    Args:
        d: date object

    Returns:
        True if business day, False otherwise
    """
    return d.weekday() < 5  # Monday = 0, Friday = 4


def add_business_days(start_date: date, days: int) -> date:
    """
    Add business days to a date.

    Args:
        start_date: Start date
        days: Number of business days to add

    Returns:
        Result date
    """
    current = start_date
    added = 0

    while added < days:
        current += timedelta(days=1)
        if is_business_day(current):
            added += 1

    return current


def get_week_start_end(d: date) -> Tuple[date, date]:
    """
    Get the start (Monday) and end (Sunday) of the week for a date.

    Args:
        d: date object

    Returns:
        tuple of (week_start, week_end)
    """
    week_start = d - timedelta(days=d.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_month_start_end(d: date) -> Tuple[date, date]:
    """
    Get the start and end of the month for a date.

    Args:
        d: date object

    Returns:
        tuple of (month_start, month_end)
    """
    month_start = d.replace(day=1)
    if d.month == 12:
        month_end = date(d.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(d.year, d.month + 1, 1) - timedelta(days=1)
    return month_start, month_end
