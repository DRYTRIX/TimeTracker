from datetime import datetime, timedelta

from app import db
from app.models.time_entry import local_now


class WorkdaySession(db.Model):
    """Clock-in/clock-out workday session (separate from project time entries)."""

    __tablename__ = "workday_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=True, index=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    auto_closed = db.Column(db.Boolean, default=False, nullable=False)
    source = db.Column(db.String(20), default="manual", nullable=False)  # manual, kiosk, mobile
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    user = db.relationship("User", backref=db.backref("workday_sessions", lazy="dynamic"))

    def __init__(
        self,
        user_id=None,
        start_time=None,
        end_time=None,
        notes=None,
        source="manual",
        auto_closed=False,
        duration_seconds=None,
        **kwargs,
    ):
        if user_id is not None:
            self.user_id = user_id
        if start_time is not None:
            self.start_time = start_time
        if end_time is not None:
            self.end_time = end_time
        self.notes = notes.strip() if notes else None
        self.source = source or "manual"
        self.auto_closed = bool(auto_closed)
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds
        elif self.end_time and self.start_time:
            self.calculate_duration()

    @property
    def is_active(self):
        return self.end_time is None

    def calculate_duration(self):
        if not self.start_time:
            self.duration_seconds = None
            return
        end = self.end_time or local_now()
        self.duration_seconds = max(0, int((end - self.start_time).total_seconds()))

    @property
    def duration_formatted(self):
        if self.is_active:
            self.calculate_duration()
        seconds = self.duration_seconds or 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    @property
    def current_duration_seconds(self):
        if not self.is_active:
            return self.duration_seconds or 0
        return max(0, int((local_now() - self.start_time).total_seconds()))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "current_duration_seconds": self.current_duration_seconds,
            "notes": self.notes,
            "auto_closed": self.auto_closed,
            "source": self.source,
            "is_active": self.is_active,
        }

    @classmethod
    def get_active_for_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id, end_time=None).first()

    @classmethod
    def get_total_seconds_for_period(cls, user_id, start_date, end_date):
        """Sum completed session durations plus active session elapsed time in range."""
        from sqlalchemy import and_, or_

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        sessions = cls.query.filter(
            cls.user_id == user_id,
            cls.start_time <= end_dt,
            or_(cls.end_time.is_(None), cls.end_time >= start_dt),
        ).all()

        total = 0
        now = local_now()
        for session in sessions:
            if session.end_time:
                total += session.duration_seconds or 0
            else:
                effective_start = max(session.start_time, start_dt)
                effective_end = min(now, end_dt)
                if effective_end > effective_start:
                    total += int((effective_end - effective_start).total_seconds())
        return total

    @classmethod
    def get_total_hours_for_period(cls, user_id, start_date, end_date):
        return round(cls.get_total_seconds_for_period(user_id, start_date, end_date) / 3600, 2)
