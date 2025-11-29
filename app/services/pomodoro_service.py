"""
Enhanced Pomodoro Timer Service
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app import db
from app.models.focus_session import FocusSession
from app.models import TimeEntry, Project, Task
from app.services.time_approval_service import TimeApprovalService
import logging

logger = logging.getLogger(__name__)


class PomodoroService:
    """Enhanced service for Pomodoro timer functionality"""

    def start_session(
        self,
        user_id: int,
        project_id: int = None,
        task_id: int = None,
        pomodoro_length: int = 25,
        short_break_length: int = 5,
        long_break_length: int = 15,
        long_break_interval: int = 4,
    ) -> Dict[str, Any]:
        """Start a new Pomodoro focus session"""

        # Check for active session
        active = FocusSession.query.filter_by(user_id=user_id, ended_at=None).first()

        if active:
            return {"success": False, "message": "Active session already exists", "session": active.to_dict()}

        # Create new session
        session = FocusSession(
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            pomodoro_length=pomodoro_length,
            short_break_length=short_break_length,
            long_break_length=long_break_length,
            long_break_interval=long_break_interval,
        )

        db.session.add(session)
        db.session.commit()

        # Optionally start a time entry
        time_entry = None
        if project_id:
            time_entry = TimeEntry(
                user_id=user_id,
                project_id=project_id,
                task_id=task_id,
                start_time=datetime.utcnow(),
                source="pomodoro",
                billable=True,
            )
            db.session.add(time_entry)
            db.session.flush()

            session.time_entry_id = time_entry.id
            db.session.commit()

        return {
            "success": True,
            "session": session.to_dict(),
            "time_entry": time_entry.to_dict() if time_entry else None,
        }

    def complete_cycle(self, session_id: int) -> Dict[str, Any]:
        """Complete a Pomodoro cycle"""
        session = FocusSession.query.get_or_404(session_id)

        session.cycles_completed += 1
        session.updated_at = datetime.utcnow()

        # Check if long break is due
        needs_long_break = session.cycles_completed % session.long_break_interval == 0

        db.session.commit()

        return {
            "success": True,
            "session": session.to_dict(),
            "needs_long_break": needs_long_break,
            "next_break_length": session.long_break_length if needs_long_break else session.short_break_length,
        }

    def end_session(self, session_id: int, notes: str = None) -> Dict[str, Any]:
        """End a Pomodoro focus session"""
        session = FocusSession.query.get_or_404(session_id)

        session.ended_at = datetime.utcnow()
        session.notes = notes

        # Update linked time entry if exists
        if session.time_entry_id:
            time_entry = TimeEntry.query.get(session.time_entry_id)
            if time_entry and not time_entry.end_time:
                time_entry.end_time = datetime.utcnow()
                time_entry.duration_seconds = int((time_entry.end_time - time_entry.start_time).total_seconds())

                # Add note about Pomodoro session
                if notes:
                    existing_notes = time_entry.notes or ""
                    time_entry.notes = f"{existing_notes}\n[Pomodoro: {session.cycles_completed} cycles]".strip()

        db.session.commit()

        return {
            "success": True,
            "session": session.to_dict(),
            "summary": {
                "duration_minutes": int((session.ended_at - session.started_at).total_seconds() / 60),
                "cycles_completed": session.cycles_completed,
                "interruptions": session.interruptions,
            },
        }

    def log_interruption(self, session_id: int, reason: str = None) -> Dict[str, Any]:
        """Log an interruption during a Pomodoro session"""
        session = FocusSession.query.get_or_404(session_id)

        session.interruptions += 1

        # Add to notes
        if reason:
            existing_notes = session.notes or ""
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            session.notes = f"{existing_notes}\n[Interruption {session.interruptions} at {timestamp}: {reason}]".strip()

        db.session.commit()

        return {"success": True, "session": session.to_dict()}

    def get_session_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get Pomodoro session statistics for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        sessions = FocusSession.query.filter(
            FocusSession.user_id == user_id, FocusSession.ended_at.isnot(None), FocusSession.ended_at >= cutoff_date
        ).all()

        total_sessions = len(sessions)
        total_cycles = sum(s.cycles_completed for s in sessions)
        total_interruptions = sum(s.interruptions for s in sessions)
        total_minutes = sum(int((s.ended_at - s.started_at).total_seconds() / 60) for s in sessions if s.ended_at)

        return {
            "total_sessions": total_sessions,
            "total_cycles": total_cycles,
            "total_interruptions": total_interruptions,
            "total_minutes": total_minutes,
            "average_cycles_per_session": round(total_cycles / total_sessions, 2) if total_sessions > 0 else 0,
            "average_minutes_per_session": round(total_minutes / total_sessions, 2) if total_sessions > 0 else 0,
        }

    def get_active_session(self, user_id: int) -> Optional[FocusSession]:
        """Get active Pomodoro session for a user"""
        return FocusSession.query.filter_by(user_id=user_id, ended_at=None).first()
