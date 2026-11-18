"""Create in-app calendar events from CRM lead/deal activities with due dates."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from app import db
from app.models import CalendarEvent

logger = logging.getLogger(__name__)


def sync_activity_to_calendar(
    *,
    user_id: int,
    title: str,
    due_date,
    description: Optional[str] = None,
    client_id: Optional[int] = None,
    duration_minutes: int = 30,
) -> Optional[CalendarEvent]:
    """Create a calendar reminder/meeting for a CRM activity due date.

    Returns the created CalendarEvent, or None if due_date is missing / creation fails.
    """
    if not due_date:
        return None
    try:
        end_time = due_date + timedelta(minutes=duration_minutes)
        event = CalendarEvent(
            user_id=user_id,
            title=title[:200],
            start_time=due_date,
            end_time=end_time,
            description=description,
            event_type="reminder",
            client_id=client_id,
            color="#2563EB",
        )
        db.session.add(event)
        return event
    except Exception:
        logger.exception("Failed to sync CRM activity to calendar")
        return None
