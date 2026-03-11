"""
Overtime Calculation Utilities

Provides functions to calculate overtime hours based on user's standard working hours
per day or per week (configurable via user.overtime_calculation_mode).
"""

from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple


def get_week_start_for_date(d: date, user: Any) -> date:
    """
    Return the week-start date for a given date using the user's week_start_day.

    User convention: 0=Sunday, 1=Monday, ..., 6=Saturday.
    Python weekday: 0=Monday, 6=Sunday.
    """
    week_start_day = getattr(user, "week_start_day", 1)
    python_week_start = (week_start_day - 1) % 7
    days_since = (d.weekday() - python_week_start) % 7
    return d - timedelta(days=days_since)


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

    Uses user.overtime_calculation_mode: 'daily' (cap per day) or 'weekly' (cap per week).
    user.standard_hours_per_day is used in daily mode; user.standard_hours_per_week in weekly mode.

    Args:
        user: User object with standard_hours_per_day, optional overtime_include_weekends,
            overtime_calculation_mode, standard_hours_per_week, week_start_day
        start_date: Start date of the period
        end_date: End date of the period
        include_weekends: If None, use user.overtime_include_weekends; if True, weekend hours
            count as regular/overtime like weekdays; if False, all weekend hours count as overtime.

    Returns:
        Dictionary with regular_hours, overtime_hours, undertime_hours, and total_hours
    """
    mode = getattr(user, "overtime_calculation_mode", "daily") or "daily"
    if mode == "weekly":
        return _calculate_period_overtime_weekly(user, start_date, end_date, include_weekends)

    if include_weekends is None:
        include_weekends = getattr(user, "overtime_include_weekends", True)
    from app.models import TimeEntry

    from datetime import datetime as dt

    start_datetime = dt.combine(start_date, dt.min.time())
    end_datetime = dt.combine(end_date, dt.max.time())

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user.id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_datetime,
        TimeEntry.start_time <= end_datetime,
    ).all()

    daily_hours = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        hours = entry.duration_hours
        if entry_date not in daily_hours:
            daily_hours[entry_date] = 0.0
        daily_hours[entry_date] += hours

    standard_hours = getattr(user, "standard_hours_per_day", 8.0) or 8.0
    total_regular = 0.0
    total_overtime = 0.0
    total_undertime = 0.0
    days_under = 0

    for day_date, hours in daily_hours.items():
        if not include_weekends and day_date.weekday() >= 5:
            total_overtime += hours
        else:
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


def _calculate_period_overtime_weekly(
    user, start_date: date, end_date: date, include_weekends: Optional[bool]
) -> Dict[str, float]:
    """Overtime for a period in weekly mode: group by week, cap at standard_hours_per_week."""
    if include_weekends is None:
        include_weekends = getattr(user, "overtime_include_weekends", True)
    from app.models import TimeEntry

    from datetime import datetime as dt

    standard_weekly = getattr(user, "standard_hours_per_week", None)
    if standard_weekly is None or standard_weekly <= 0:
        standard_weekly = (getattr(user, "standard_hours_per_day", 8.0) or 8.0) * 5

    start_datetime = dt.combine(start_date, dt.min.time())
    end_datetime = dt.combine(end_date, dt.max.time())

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user.id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_datetime,
        TimeEntry.start_time <= end_datetime,
    ).all()

    # Group by week (week-start date)
    weekly_hours: Dict[date, float] = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        if not include_weekends and entry_date.weekday() >= 5:
            # Weekend: count as overtime in weekly total (add to week bucket but we'll treat all as overtime for that week's excess)
            pass  # Still add to week total; overtime is (total - standard), so weekend hours push total up
        week_start = get_week_start_for_date(entry_date, user)
        if week_start not in weekly_hours:
            weekly_hours[week_start] = 0.0
        weekly_hours[week_start] += entry.duration_hours

    total_regular = 0.0
    total_overtime = 0.0
    total_undertime = 0.0
    weeks_under = 0
    weeks_with_overtime = 0

    for week_start, total_week_hours in weekly_hours.items():
        week_end = week_start + timedelta(days=6)
        # Only full weeks entirely inside [start_date, end_date] get regular/overtime split
        if week_start >= start_date and week_end <= end_date:
            regular_week = min(total_week_hours, standard_weekly)
            overtime_week = max(0.0, total_week_hours - standard_weekly)
            undertime_week = max(0.0, standard_weekly - total_week_hours)
            total_regular += regular_week
            total_overtime += overtime_week
            total_undertime += undertime_week
            if undertime_week > 0:
                weeks_under += 1
            if overtime_week > 0:
                weeks_with_overtime += 1
        else:
            # Partial week: count all as regular for simplicity (no overtime from partial weeks)
            total_regular += total_week_hours

    total_hours = total_regular + total_overtime
    return {
        "regular_hours": round(total_regular, 2),
        "overtime_hours": round(total_overtime, 2),
        "undertime_hours": round(total_undertime, 2),
        "days_under": weeks_under,  # reuse field for "weeks under" in weekly mode
        "total_hours": round(total_hours, 2),
        "days_with_overtime": weeks_with_overtime,  # reuse for "weeks with overtime"
    }


def get_daily_breakdown(
    user, start_date: date, end_date: date, include_weekends: Optional[bool] = None
) -> List[Dict]:
    """
    Get a daily breakdown of regular and overtime hours.

    In weekly mode (user.overtime_calculation_mode == 'weekly'), per-day regular/overtime
    are not defined; each row has total_hours and regular_hours=0, overtime_hours=0.
    Use calculate_period_overtime for period-level regular/overtime in that case.

    Args:
        user: User object with standard_hours_per_day and optional overtime_include_weekends
        start_date: Start date of the period
        end_date: End date of the period
        include_weekends: If None, use user.overtime_include_weekends (see calculate_period_overtime).

    Returns:
        List of dictionaries with daily breakdown
    """
    mode = getattr(user, "overtime_calculation_mode", "daily") or "daily"
    if include_weekends is None:
        include_weekends = getattr(user, "overtime_include_weekends", True)
    from app.models import TimeEntry

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

    daily_data = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        if entry_date not in daily_data:
            daily_data[entry_date] = {"date": entry_date, "total_hours": 0.0, "entries": []}
        daily_data[entry_date]["total_hours"] += entry.duration_hours
        daily_data[entry_date]["entries"].append(entry)

    if mode == "weekly":
        # In weekly mode no per-day split; just total_hours per day
        breakdown = []
        for day_date in sorted(daily_data.keys()):
            day_info = daily_data[day_date]
            total_hours = day_info["total_hours"]
            breakdown.append(
                {
                    "date": day_date,
                    "date_str": day_date.strftime("%Y-%m-%d"),
                    "weekday": day_date.strftime("%A"),
                    "total_hours": round(total_hours, 2),
                    "regular_hours": 0.0,
                    "overtime_hours": 0.0,
                    "undertime_hours": 0.0,
                    "is_overtime": False,
                    "is_undertime": False,
                    "entries_count": len(day_info["entries"]),
                }
            )
        return breakdown

    standard_hours = getattr(user, "standard_hours_per_day", 8.0) or 8.0
    breakdown = []
    for day_date in sorted(daily_data.keys()):
        day_info = daily_data[day_date]
        total_hours = day_info["total_hours"]
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

    Uses user's week_start_day for week boundaries. In weekly mode compares each
    week's total to standard_hours_per_week; in daily mode uses per-day cap then sums.
    """
    from app.models import TimeEntry

    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user.id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_datetime,
        TimeEntry.start_time <= end_datetime,
    ).all()

    # Group by week using user's week start
    weekly_data: Dict[date, Dict[date, float]] = {}
    for entry in entries:
        entry_date = entry.start_time.date()
        week_start = get_week_start_for_date(entry_date, user)
        if week_start not in weekly_data:
            weekly_data[week_start] = {}
        if entry_date not in weekly_data[week_start]:
            weekly_data[week_start][entry_date] = 0.0
        weekly_data[week_start][entry_date] += entry.duration_hours

    mode = getattr(user, "overtime_calculation_mode", "daily") or "daily"
    standard_daily = getattr(user, "standard_hours_per_day", 8.0) or 8.0
    standard_weekly = getattr(user, "standard_hours_per_week", None) or (standard_daily * 5)
    weekly_summary = []

    for week_start in sorted(weekly_data.keys()):
        daily_hours = weekly_data[week_start]
        week_total = sum(daily_hours.values())

        if mode == "weekly":
            week_regular = min(week_total, standard_weekly)
            week_overtime = max(0.0, week_total - standard_weekly)
        else:
            week_regular = 0.0
            week_overtime = 0.0
            for hours in daily_hours.values():
                if hours <= standard_daily:
                    week_regular += hours
                else:
                    week_regular += standard_daily
                    week_overtime += hours - standard_daily

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


def get_overtime_ytd(user) -> Dict[str, float]:
    """
    Return overtime for the current year to date (Jan 1 through today).
    Uses calculate_period_overtime; no stored balance.
    """
    today = datetime.now().date()
    start_ytd = date(today.year, 1, 1)
    return calculate_period_overtime(user, start_ytd, today)


def get_overtime_last_12_months(user) -> Dict[str, float]:
    """
    Return overtime for the last 12 months (rolling).
    """
    today = datetime.now().date()
    start = today - timedelta(days=365)
    return calculate_period_overtime(user, start, today)


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
