"""
Overtime Calculation Utilities

Provides functions to calculate overtime hours based on user's standard working hours per day.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func


def calculate_daily_overtime(total_hours: float, standard_hours: float) -> float:
    """
    Calculate overtime hours for a single day.

    Args:
        total_hours: Total hours worked in a day
        standard_hours: Standard working hours per day

    Returns:
        Overtime hours (0 if no overtime)
    """
    if total_hours <= standard_hours:
        return 0.0
    return round(total_hours - standard_hours, 2)


def calculate_period_overtime(
    user, start_date: date, end_date: date, include_weekends: Optional[bool] = None
) -> Dict[str, float]:
    """
    Calculate overtime for a specific period.

    Args:
        user: User object with standard_hours_per_day and optional overtime_include_weekends
        start_date: Start date of the period
        end_date: End date of the period
        include_weekends: If None, use user.overtime_include_weekends; if True, weekend hours
            count as regular/overtime like weekdays; if False, all weekend hours count as overtime.

    Returns:
        Dictionary with regular_hours, overtime_hours, undertime_hours, and total_hours
    """
    if include_weekends is None:
        include_weekends = getattr(user, "overtime_include_weekends", True)
    from app.models import TimeEntry
    from app import db

    # Get all time entries for the period
    # Convert dates to datetime ranges to include full day
    from datetime import datetime as dt

    start_datetime = dt.combine(start_date, dt.min.time())
    end_datetime = dt.combine(end_date, dt.max.time())

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user.id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_datetime,
        TimeEntry.start_time <= end_datetime,
    ).all()

    # Group entries by date
    daily_hours = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        hours = entry.duration_hours

        if entry_date not in daily_hours:
            daily_hours[entry_date] = 0.0
        daily_hours[entry_date] += hours

    # Calculate overtime and undertime per day
    standard_hours = getattr(user, "standard_hours_per_day", 8.0) or 8.0
    total_regular = 0.0
    total_overtime = 0.0
    total_undertime = 0.0
    days_under = 0

    for day_date, hours in daily_hours.items():
        # Check if weekend
        if not include_weekends and day_date.weekday() >= 5:  # Saturday=5, Sunday=6
            # All weekend hours are overtime
            total_overtime += hours
        else:
            # Calculate regular vs overtime vs undertime
            if hours <= standard_hours:
                total_regular += hours
                undertime = max(0.0, standard_hours - hours)
                if undertime > 0:
                    total_undertime += undertime
                    days_under += 1
            else:
                total_regular += standard_hours
                total_overtime += hours - standard_hours

    return {
        "regular_hours": round(total_regular, 2),
        "overtime_hours": round(total_overtime, 2),
        "undertime_hours": round(total_undertime, 2),
        "days_under": days_under,
        "total_hours": round(total_regular + total_overtime, 2),
        "days_with_overtime": sum(1 for h in daily_hours.values() if h > standard_hours),
    }


def get_daily_breakdown(
    user, start_date: date, end_date: date, include_weekends: Optional[bool] = None
) -> List[Dict]:
    """
    Get a daily breakdown of regular and overtime hours.

    Args:
        user: User object with standard_hours_per_day and optional overtime_include_weekends
        start_date: Start date of the period
        end_date: End date of the period
        include_weekends: If None, use user.overtime_include_weekends (see calculate_period_overtime).

    Returns:
        List of dictionaries with daily breakdown
    """
    if include_weekends is None:
        include_weekends = getattr(user, "overtime_include_weekends", True)
    from app.models import TimeEntry
    from app import db

    # Get all time entries for the period
    # Convert dates to datetime ranges to include full day
    from datetime import datetime as dt

    start_datetime = dt.combine(start_date, dt.min.time())
    end_datetime = dt.combine(end_date, dt.max.time())

    entries = (
        TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_datetime,
            TimeEntry.start_time <= end_datetime,
        )
        .order_by(TimeEntry.start_time)
        .all()
    )

    # Group entries by date
    daily_data = {}
    for entry in entries:
        entry_date = entry.start_time.date()

        if entry_date not in daily_data:
            daily_data[entry_date] = {"date": entry_date, "total_hours": 0.0, "entries": []}

        daily_data[entry_date]["total_hours"] += entry.duration_hours
        daily_data[entry_date]["entries"].append(entry)

    # Calculate overtime and undertime for each day
    standard_hours = getattr(user, "standard_hours_per_day", 8.0) or 8.0
    breakdown = []

    for day_date in sorted(daily_data.keys()):
        day_info = daily_data[day_date]
        total_hours = day_info["total_hours"]

        # When include_weekends is False, weekend days count all hours as overtime
        if not include_weekends and day_date.weekday() >= 5:
            regular_hours = 0.0
            overtime_hours = total_hours
            undertime_hours = 0.0
        else:
            regular_hours = min(total_hours, standard_hours)
            overtime_hours = max(0, total_hours - standard_hours)
            undertime_hours = max(0, standard_hours - total_hours) if total_hours < standard_hours else 0.0
        is_undertime = undertime_hours > 0

        breakdown.append(
            {
                "date": day_date,
                "date_str": day_date.strftime("%Y-%m-%d"),
                "weekday": day_date.strftime("%A"),
                "total_hours": round(total_hours, 2),
                "regular_hours": round(regular_hours, 2),
                "overtime_hours": round(overtime_hours, 2),
                "undertime_hours": round(undertime_hours, 2),
                "is_overtime": overtime_hours > 0,
                "is_undertime": is_undertime,
                "entries_count": len(day_info["entries"]),
            }
        )

    return breakdown


def get_weekly_overtime_summary(user, weeks: int = 4) -> List[Dict]:
    """
    Get a weekly summary of overtime for the last N weeks.

    Args:
        user: User object with standard_hours_per_day setting
        weeks: Number of weeks to look back

    Returns:
        List of weekly summaries
    """
    from app.models import TimeEntry
    from app import db

    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)

    # Convert dates to datetime ranges to include full day
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get all time entries
    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user.id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_datetime,
        TimeEntry.start_time <= end_datetime,
    ).all()

    # Group by week
    weekly_data = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        # Get Monday of that week
        week_start = entry_date - timedelta(days=entry_date.weekday())

        if week_start not in weekly_data:
            weekly_data[week_start] = {}

        if entry_date not in weekly_data[week_start]:
            weekly_data[week_start][entry_date] = 0.0

        weekly_data[week_start][entry_date] += entry.duration_hours

    # Calculate overtime per week
    standard_hours = user.standard_hours_per_day
    weekly_summary = []

    for week_start in sorted(weekly_data.keys()):
        daily_hours = weekly_data[week_start]

        week_regular = 0.0
        week_overtime = 0.0

        for day_date, hours in daily_hours.items():
            if hours <= standard_hours:
                week_regular += hours
            else:
                week_regular += standard_hours
                week_overtime += hours - standard_hours

        week_end = week_start + timedelta(days=6)

        weekly_summary.append(
            {
                "week_start": week_start,
                "week_end": week_end,
                "week_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                "regular_hours": round(week_regular, 2),
                "overtime_hours": round(week_overtime, 2),
                "total_hours": round(week_regular + week_overtime, 2),
                "days_worked": len(daily_hours),
            }
        )

    return weekly_summary


def get_overtime_statistics(user, start_date: date, end_date: date) -> Dict:
    """
    Get comprehensive overtime statistics for a period.

    Args:
        user: User object
        start_date: Start date
        end_date: End date

    Returns:
        Dictionary with various overtime statistics
    """
    period_data = calculate_period_overtime(user, start_date, end_date)
    daily_breakdown = get_daily_breakdown(user, start_date, end_date)

    # Calculate additional statistics
    days_worked = len(daily_breakdown)
    days_with_overtime = sum(1 for day in daily_breakdown if day["is_overtime"])

    # Average hours per day
    avg_hours_per_day = period_data["total_hours"] / days_worked if days_worked > 0 else 0

    # Max overtime in a single day
    max_overtime_day = max(
        (day for day in daily_breakdown if day["is_overtime"]), key=lambda x: x["overtime_hours"], default=None
    )

    return {
        "period": {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "days_in_period": (end_date - start_date).days + 1,
        },
        "hours": period_data,
        "days_statistics": {
            "days_worked": days_worked,
            "days_with_overtime": days_with_overtime,
            "percentage_overtime_days": (round(days_with_overtime / days_worked * 100, 1) if days_worked > 0 else 0),
        },
        "averages": {
            "avg_hours_per_day": round(avg_hours_per_day, 2),
            "avg_overtime_per_overtime_day": (
                round(period_data["overtime_hours"] / days_with_overtime, 2) if days_with_overtime > 0 else 0
            ),
        },
        "max_overtime": {
            "date": max_overtime_day["date_str"] if max_overtime_day else None,
            "hours": max_overtime_day["overtime_hours"] if max_overtime_day else 0,
        },
    }
