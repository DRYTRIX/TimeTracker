"""Holidays and time-off items for calendar views."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from app.models.time_off import CompanyHoliday, TimeOffRequest, TimeOffRequestStatus

HOLIDAY_COLOR = "#9333ea"
TIME_OFF_COLOR = "#ec4899"
TIME_OFF_PENDING_COLOR = "#f472b6"


def _date_range_items(
    item_id: int,
    name: str,
    start: date,
    end: date,
    *,
    item_type: str,
    color: str,
    extra: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Expand a date range into per-day all-day calendar items."""
    items: List[Dict[str, Any]] = []
    day = start
    while day <= end:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        payload = {
            "id": f"{item_type}_{item_id}_{day.isoformat()}",
            "title": name,
            "start": day_start.isoformat(),
            "end": day_end.isoformat(),
            "allDay": True,
            "color": color,
            "type": item_type,
            "item_type": item_type,
        }
        if extra:
            payload.update(extra)
        items.append(payload)
        day += timedelta(days=1)
    return items


def get_holidays_for_calendar(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    holidays = CompanyHoliday.query.filter(
        CompanyHoliday.enabled.is_(True),
        CompanyHoliday.end_date >= start_date,
        CompanyHoliday.start_date <= end_date,
    ).all()
    items: List[Dict[str, Any]] = []
    for holiday in holidays:
        span_start = max(holiday.start_date, start_date)
        span_end = min(holiday.end_date, end_date)
        items.extend(
            _date_range_items(
                holiday.id,
                holiday.name,
                span_start,
                span_end,
                item_type="holiday",
                color=HOLIDAY_COLOR,
                extra={"holiday_id": holiday.id, "region": holiday.region},
            )
        )
    return items


def get_time_off_for_calendar(user_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    requests = TimeOffRequest.query.filter(
        TimeOffRequest.user_id == user_id,
        TimeOffRequest.end_date >= start_date,
        TimeOffRequest.start_date <= end_date,
        TimeOffRequest.status.in_(
            [
                TimeOffRequestStatus.APPROVED,
                TimeOffRequestStatus.SUBMITTED,
                TimeOffRequestStatus.DRAFT,
            ]
        ),
    ).all()
    items: List[Dict[str, Any]] = []
    for req in requests:
        status = req.status.value if isinstance(req.status, TimeOffRequestStatus) else str(req.status)
        leave_name = req.leave_type.name if req.leave_type else "Time off"
        title = f"{leave_name} ({status})" if status != TimeOffRequestStatus.APPROVED.value else leave_name
        color = TIME_OFF_COLOR if status == TimeOffRequestStatus.APPROVED.value else TIME_OFF_PENDING_COLOR
        span_start = max(req.start_date, start_date)
        span_end = min(req.end_date, end_date)
        items.extend(
            _date_range_items(
                req.id,
                title,
                span_start,
                span_end,
                item_type="time_off",
                color=color,
                extra={
                    "request_id": req.id,
                    "status": status,
                    "leave_type": leave_name,
                },
            )
        )
    return items
