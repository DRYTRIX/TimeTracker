"""
Service for workday clock-in/clock-out sessions.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app import db
from app.models import WorkdaySession
from app.models.time_entry import local_now
from app.utils.db import safe_commit


class WorkdaySessionService:
    """Business logic for workday sessions."""

    def get_active_session(self, user_id: int) -> Optional[WorkdaySession]:
        return WorkdaySession.get_active_for_user(user_id)

    def can_start_workday(self, user_id: int) -> tuple[bool, Optional[str]]:
        if self.get_active_session(user_id):
            return False, "You already have an active workday session. End it before starting a new one."
        return True, None

    def start_workday(
        self,
        user_id: int,
        notes: Optional[str] = None,
        source: str = "manual",
    ) -> Dict[str, Any]:
        ok, msg = self.can_start_workday(user_id)
        if not ok:
            return {"success": False, "message": msg, "error": "workday_already_active"}

        session = WorkdaySession(
            user_id=user_id,
            start_time=local_now(),
            notes=notes,
            source=source,
        )
        db.session.add(session)

        if not safe_commit("start_workday", {"user_id": user_id}):
            return {
                "success": False,
                "message": "Could not start workday due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Workday started", "session": session}

    def end_workday(self, user_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        session = self.get_active_session(user_id)
        if not session:
            return {"success": False, "message": "No active workday session", "error": "no_active_workday"}

        session.end_time = local_now()
        if notes:
            session.notes = (session.notes or "") + ("\n" if session.notes else "") + notes.strip()
        session.calculate_duration()

        if not safe_commit("end_workday", {"user_id": user_id, "session_id": session.id}):
            return {
                "success": False,
                "message": "Could not end workday due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Workday ended", "session": session}

    def get_session_for_day(self, user_id: int, day) -> list:
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        return (
            WorkdaySession.query.filter(
                WorkdaySession.user_id == user_id,
                WorkdaySession.start_time >= start_dt,
                WorkdaySession.start_time <= end_dt,
            )
            .order_by(WorkdaySession.start_time.desc())
            .all()
        )

    def get_total_hours(
        self,
        user_id: int,
        start_date,
        end_date,
    ) -> float:
        return WorkdaySession.get_total_hours_for_period(user_id, start_date, end_date)

    def auto_close_stale_sessions(self, max_hours: int = 18) -> int:
        """Auto-close open sessions older than max_hours. Returns count closed."""
        cutoff = local_now() - timedelta(hours=max_hours)
        stale = WorkdaySession.query.filter(
            WorkdaySession.end_time.is_(None),
            WorkdaySession.start_time < cutoff,
        ).all()
        count = 0
        for session in stale:
            session.end_time = session.start_time + timedelta(hours=max_hours)
            session.auto_closed = True
            session.calculate_duration()
            count += 1
        if count:
            safe_commit("auto_close_stale_workday_sessions", {"count": count})
        return count
