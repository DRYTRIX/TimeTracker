"""Validation helpers for RateOverride create/update."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union

from app.models.rate_override import RateOverride

DateLike = Union[date, datetime, str, None]


def parse_optional_date(value: DateLike, field_name: str) -> Tuple[Optional[date], Optional[str]]:
    """Parse an optional YYYY-MM-DD date. Returns (date_or_none, error_or_none)."""
    if value is None or value == "":
        return None, None
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date(), None
        except ValueError:
            return None, f"{field_name} must be a valid date (YYYY-MM-DD)"
    return None, f"{field_name} must be a valid date (YYYY-MM-DD)"


def parse_hourly_rate(value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse and validate hourly_rate. Returns (rate_or_none, error_or_none)."""
    if value is None or value == "":
        return None, "hourly_rate is required"
    try:
        rate = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None, "hourly_rate must be a number"
    if rate < 0:
        return None, "hourly_rate must not be negative"
    return rate, None


def validate_date_window(effective_from: Optional[date], effective_to: Optional[date]) -> Optional[str]:
    """Return an error message if effective_to is before effective_from."""
    if effective_from is not None and effective_to is not None and effective_to < effective_from:
        return "effective_to must not be before effective_from"
    return None


def validate_rate_override_fields(
    *,
    hourly_rate: Any,
    effective_from: DateLike = None,
    effective_to: DateLike = None,
    project_id: int,
    user_id: Optional[int] = None,
    exclude_id: Optional[int] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, List[str]]]:
    """Validate rate override fields and check for overlapping windows.

    Returns ``(parsed_values, errors)``. ``parsed_values`` is None when there
    are errors. On success, parsed_values contains hourly_rate, effective_from,
    effective_to (and echoes project_id / user_id).
    """
    errors: Dict[str, List[str]] = {}

    rate, rate_err = parse_hourly_rate(hourly_rate)
    if rate_err:
        errors["hourly_rate"] = [rate_err]

    from_date, from_err = parse_optional_date(effective_from, "effective_from")
    if from_err:
        errors["effective_from"] = [from_err]

    to_date, to_err = parse_optional_date(effective_to, "effective_to")
    if to_err:
        errors["effective_to"] = [to_err]

    if not errors:
        window_err = validate_date_window(from_date, to_date)
        if window_err:
            errors["effective_to"] = [window_err]

    if not errors and RateOverride.has_overlapping_window(
        project_id=project_id,
        user_id=user_id,
        effective_from=from_date,
        effective_to=to_date,
        exclude_id=exclude_id,
    ):
        errors["effective_from"] = ["An override for this project and person already overlaps this date range"]

    if errors:
        return None, errors

    return {
        "hourly_rate": rate,
        "effective_from": from_date,
        "effective_to": to_date,
        "project_id": project_id,
        "user_id": user_id,
    }, {}
