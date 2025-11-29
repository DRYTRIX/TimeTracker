from datetime import datetime
from app import db


class FocusSession(db.Model):
    """Pomodoro-style focus session metadata linked to a time entry.

    Tracks configuration and outcomes for a single focus session so we can
    provide summaries independent of raw time entries.
    """

    __tablename__ = "focus_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id"), nullable=True, index=True)

    # Session timing
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    # Pomodoro configuration (minutes)
    pomodoro_length = db.Column(db.Integer, nullable=False, default=25)
    short_break_length = db.Column(db.Integer, nullable=False, default=5)
    long_break_length = db.Column(db.Integer, nullable=False, default=15)
    long_break_interval = db.Column(db.Integer, nullable=False, default=4)

    # Outcomes
    cycles_completed = db.Column(db.Integer, nullable=False, default=0)
    interruptions = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "time_entry_id": self.time_entry_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "pomodoro_length": self.pomodoro_length,
            "short_break_length": self.short_break_length,
            "long_break_length": self.long_break_length,
            "long_break_interval": self.long_break_interval,
            "cycles_completed": self.cycles_completed,
            "interruptions": self.interruptions,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
