from datetime import datetime, timedelta
from app import db
from sqlalchemy import func


def local_now():
    """Get current time in local timezone"""
    import os
    import pytz

    # Get timezone from environment variable, default to Europe/Rome
    timezone_name = os.getenv("TZ", "Europe/Rome")
    tz = pytz.timezone(timezone_name)
    now = datetime.now(tz)
    return now.replace(tzinfo=None)


class WeeklyTimeGoal(db.Model):
    """Weekly time goal model for tracking user's weekly hour targets"""

    __tablename__ = "weekly_time_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_hours = db.Column(db.Float, nullable=False)  # Target hours for the week
    week_start_date = db.Column(db.Date, nullable=False, index=True)  # Monday of the week
    week_end_date = db.Column(db.Date, nullable=False)  # Sunday of the week (or Friday if exclude_weekends is True)
    exclude_weekends = db.Column(db.Boolean, default=False, nullable=False)  # If True, only count weekdays (5-day work week)
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active', 'completed', 'failed', 'cancelled'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("weekly_goals", lazy="dynamic", cascade="all, delete-orphan"))

    def __init__(self, user_id, target_hours, week_start_date=None, notes=None, exclude_weekends=False, **kwargs):
        """Initialize a WeeklyTimeGoal instance.

        Args:
            user_id: ID of the user who created this goal
            target_hours: Target hours for the week
            week_start_date: Start date of the week (Monday). If None, uses current week.
            notes: Optional notes about the goal
            exclude_weekends: If True, only count weekdays (5-day work week). Default False.
            **kwargs: Additional keyword arguments (for SQLAlchemy compatibility)
        """
        self.user_id = user_id
        self.target_hours = target_hours
        self.exclude_weekends = exclude_weekends

        # If no week_start_date provided, calculate the current week's Monday
        if week_start_date is None:
            from app.models.user import User

            user = User.query.get(user_id)
            week_start_day = (
                user.week_start_day if user else 1
            )  # Default to Monday (user convention: 0=Sunday, 1=Monday)
            today = local_now().date()
            # Convert user convention (0=Sunday, 1=Monday) to Python weekday (0=Monday, 6=Sunday)
            python_week_start_day = (week_start_day - 1) % 7
            days_since_week_start = (today.weekday() - python_week_start_day) % 7
            week_start_date = today - timedelta(days=days_since_week_start)

        self.week_start_date = week_start_date
        # If exclude_weekends is True, week ends on Friday (4 days after Monday), otherwise Sunday (6 days after Monday)
        if exclude_weekends:
            self.week_end_date = week_start_date + timedelta(days=4)  # Monday to Friday
        else:
            self.week_end_date = week_start_date + timedelta(days=6)  # Monday to Sunday
        self.notes = notes

        # Allow status override from kwargs
        if "status" in kwargs:
            self.status = kwargs["status"]

    def __repr__(self):
        return f"<WeeklyTimeGoal user_id={self.user_id} week={self.week_start_date} target={self.target_hours}h>"

    @property
    def actual_hours(self):
        """Calculate actual hours worked during this week"""
        from app.models.time_entry import TimeEntry

        # Query time entries for this user within the week range
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == self.user_id,
            TimeEntry.end_time.isnot(None),
            func.date(TimeEntry.start_time) >= self.week_start_date,
            func.date(TimeEntry.start_time) <= self.week_end_date,
        ).all()
        
        # If exclude_weekends is True, filter out Saturday (5) and Sunday (6)
        # Python weekday: Monday=0, Tuesday=1, ..., Sunday=6
        if self.exclude_weekends:
            entries = [e for e in entries if e.start_time.date().weekday() < 5]
        
        total_seconds = sum(entry.duration_seconds for entry in entries)
        return round(total_seconds / 3600, 2)

    @property
    def progress_percentage(self):
        """Calculate progress as a percentage"""
        if self.target_hours <= 0:
            return 0
        percentage = (self.actual_hours / self.target_hours) * 100
        return min(round(percentage, 1), 100)  # Cap at 100%

    @property
    def remaining_hours(self):
        """Calculate remaining hours to reach the goal"""
        remaining = self.target_hours - self.actual_hours
        return max(round(remaining, 2), 0)

    @property
    def is_completed(self):
        """Check if the goal has been met"""
        return self.actual_hours >= self.target_hours

    @property
    def is_overdue(self):
        """Check if the week has passed and goal is not completed"""
        today = local_now().date()
        return today > self.week_end_date and not self.is_completed

    @property
    def days_remaining(self):
        """Calculate days remaining in the week"""
        today = local_now().date()
        if today > self.week_end_date:
            return 0
        return (self.week_end_date - today).days + 1

    @property
    def average_hours_per_day(self):
        """Calculate average hours needed per day to reach goal"""
        if self.days_remaining <= 0:
            return 0
        return round(self.remaining_hours / self.days_remaining, 2)

    @property
    def week_label(self):
        """Get a human-readable label for the week"""
        if self.exclude_weekends:
            return f"{self.week_start_date.strftime('%b %d')} - {self.week_end_date.strftime('%b %d, %Y')} (Weekdays only)"
        return f"{self.week_start_date.strftime('%b %d')} - {self.week_end_date.strftime('%b %d, %Y')}"

    def update_status(self):
        """Update the goal status based on current date and progress"""
        today = local_now().date()

        if self.status == "cancelled":
            return  # Don't auto-update cancelled goals

        if today > self.week_end_date:
            # Week has ended
            if self.is_completed:
                self.status = "completed"
            else:
                self.status = "failed"
        elif self.is_completed and self.status == "active":
            self.status = "completed"

        db.session.commit()

    def to_dict(self):
        """Convert goal to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_hours": self.target_hours,
            "actual_hours": self.actual_hours,
            "week_start_date": self.week_start_date.isoformat(),
            "week_end_date": self.week_end_date.isoformat(),
            "exclude_weekends": self.exclude_weekends,
            "week_label": self.week_label,
            "status": self.status,
            "notes": self.notes,
            "progress_percentage": self.progress_percentage,
            "remaining_hours": self.remaining_hours,
            "is_completed": self.is_completed,
            "is_overdue": self.is_overdue,
            "days_remaining": self.days_remaining,
            "average_hours_per_day": self.average_hours_per_day,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_current_week_goal(user_id):
        """Get the goal for the current week for a specific user"""
        from app.models.user import User

        user = User.query.get(user_id)
        week_start_day = user.week_start_day if user else 1  # User convention: 0=Sunday, 1=Monday

        today = local_now().date()
        # Convert user convention (0=Sunday, 1=Monday) to Python weekday (0=Monday, 6=Sunday)
        python_week_start_day = (week_start_day - 1) % 7
        days_since_week_start = (today.weekday() - python_week_start_day) % 7
        week_start = today - timedelta(days=days_since_week_start)
        week_end = week_start + timedelta(days=6)

        return WeeklyTimeGoal.query.filter(
            WeeklyTimeGoal.user_id == user_id,
            WeeklyTimeGoal.week_start_date == week_start,
            WeeklyTimeGoal.status != "cancelled",
        ).first()

    @staticmethod
    def get_or_create_current_week(user_id, default_target_hours=40):
        """Get or create a goal for the current week"""
        goal = WeeklyTimeGoal.get_current_week_goal(user_id)

        if not goal:
            goal = WeeklyTimeGoal(user_id=user_id, target_hours=default_target_hours)
            db.session.add(goal)
            db.session.commit()

        return goal
