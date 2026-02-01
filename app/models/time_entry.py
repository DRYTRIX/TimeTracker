from datetime import datetime, timedelta, timezone
from app import db
from app.config import Config
from app.utils.timezone import utc_to_local, local_to_utc


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    from app.utils.timezone import get_timezone_obj

    tz = get_timezone_obj()
    now = datetime.now(tz)
    return now.replace(tzinfo=None)


class TimeEntry(db.Model):
    """Time entry model for manual and automatic time tracking"""

    __tablename__ = "time_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=True, index=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    source = db.Column(db.String(20), default="manual", nullable=False)  # 'manual' or 'auto'
    billable = db.Column(db.Boolean, default=True, nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False, index=True)
    invoice_number = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    # Relationships
    # user and project relationships are defined via backref in their respective models
    # client relationship is defined via backref in Client model
    # task relationship is defined via backref in Task model

    def __init__(
        self,
        user_id=None,
        project_id=None,
        client_id=None,
        start_time=None,
        end_time=None,
        task_id=None,
        notes=None,
        tags=None,
        source="manual",
        billable=True,
        paid=False,
        invoice_number=None,
        duration_seconds=None,
        **kwargs,
    ):
        """Initialize a TimeEntry instance.

        Args:
            user_id: ID of the user who created this entry
            project_id: ID of the project this entry is associated with (optional if client_id is provided)
            client_id: ID of the client this entry is directly billed to (optional if project_id is provided)
            start_time: When the time entry started
            end_time: When the time entry ended (None for active timers)
            task_id: Optional task ID (only valid when project_id is provided)
            notes: Optional notes/description
            tags: Optional comma-separated tags
            source: Source of the entry ('manual' or 'auto')
            billable: Whether this entry is billable
            paid: Whether this entry has been paid
            invoice_number: Optional internal invoice number reference
            duration_seconds: Optional duration override (usually calculated automatically)
            **kwargs: Additional keyword arguments (for SQLAlchemy compatibility)
        """
        if user_id is not None:
            self.user_id = user_id
        if project_id is not None:
            self.project_id = project_id
        if client_id is not None:
            self.client_id = client_id
        if task_id is not None:
            self.task_id = task_id
        if start_time is not None:
            self.start_time = start_time
        if end_time is not None:
            self.end_time = end_time

        # Validate that either project_id or client_id is provided
        # Exception: auto-imported entries (source="auto") can be created without project or client
        if not self.project_id and not self.client_id and source != "auto":
            raise ValueError("Either project_id or client_id must be provided")

        # Validate that task_id is only provided when project_id is set
        if self.task_id and not self.project_id:
            raise ValueError("task_id can only be set when project_id is provided")

        self.notes = notes.strip() if notes else None
        self.tags = tags.strip() if tags else None
        self.source = source
        self.billable = billable
        self.paid = paid
        self.invoice_number = invoice_number.strip() if invoice_number else None

        # Allow manual duration override
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds
        # Otherwise, calculate duration if end time is provided
        elif self.end_time:
            self.calculate_duration()

    def __repr__(self):
        user_name = self.user.username if self.user else "deleted_user"
        if self.project:
            target = self.project.name
        elif self.client:
            target = self.client.name
        else:
            target = "unknown"
        return f"<TimeEntry {self.id}: {user_name} on {target}>"

    @property
    def is_active(self):
        """Check if this is an active timer (no end time)"""
        return self.end_time is None

    @property
    def duration_hours(self):
        """Get duration in hours"""
        if not self.duration_seconds:
            return 0
        return round(self.duration_seconds / 3600, 2)

    @property
    def duration_formatted(self):
        """Get duration formatted as HH:MM:SS"""
        # For active timers (end_time is None), use current_duration_seconds
        if not self.end_time:
            total_seconds = self.current_duration_seconds
        elif not self.duration_seconds:
            return "00:00:00"
        else:
            total_seconds = int(self.duration_seconds)

        # Convert to int to ensure integer values for formatting
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def tag_list(self):
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def current_duration_seconds(self):
        """Calculate current duration for active timers"""
        if self.end_time:
            return self.duration_seconds or 0

        # For active timers, calculate from start time to now
        # Since we store everything in local timezone, we can work with naive datetimes
        # as long as we treat them as local time

        # Get current time in local timezone (naive, matching database storage)
        now_local = local_now()

        # Calculate duration (both times are treated as local time)
        duration = now_local - self.start_time
        return int(duration.total_seconds())

    def _naive_dt(self, dt):
        """Return datetime as naive local for duration math (handles DB returning aware in some backends)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt
        from app.utils.timezone import get_timezone_obj
        tz = get_timezone_obj()
        return dt.astimezone(tz).replace(tzinfo=None)

    def calculate_duration(self):
        """Calculate and set duration in seconds with rounding"""
        if not self.end_time:
            return

        # Normalize to naive for subtraction (storage is local time; some DB drivers return aware)
        start = self._naive_dt(self.start_time)
        end = self._naive_dt(self.end_time)
        if start is None or end is None:
            return
        duration = end - start
        raw_seconds = int(duration.total_seconds())

        # Apply per-user rounding if user preferences are set
        if self.user and hasattr(self.user, "time_rounding_enabled"):
            from app.utils.time_rounding import apply_user_rounding

            self.duration_seconds = apply_user_rounding(raw_seconds, self.user)
        else:
            # Fallback to global rounding setting for backward compatibility
            rounding_minutes = Config.ROUNDING_MINUTES
            if rounding_minutes > 1:
                # Round to nearest interval
                minutes = raw_seconds / 60
                rounded_minutes = round(minutes / rounding_minutes) * rounding_minutes
                self.duration_seconds = int(rounded_minutes * 60)
            else:
                self.duration_seconds = raw_seconds

    def stop_timer(self, end_time=None):
        """Stop an active timer"""
        if self.end_time:
            raise ValueError("Timer is already stopped")

        # Use local timezone for consistency with database storage
        if end_time:
            self.end_time = end_time
        else:
            self.end_time = local_now()

        self.calculate_duration()
        self.updated_at = local_now()

        db.session.commit()

    def update_notes(self, notes):
        """Update notes for this entry"""
        self.notes = notes.strip() if notes else None
        self.updated_at = local_now()
        db.session.commit()

    def update_tags(self, tags):
        """Update tags for this entry"""
        self.tags = tags.strip() if tags else None
        self.updated_at = local_now()
        db.session.commit()

    def set_billable(self, billable):
        """Set billable status"""
        self.billable = billable
        self.updated_at = local_now()
        db.session.commit()

    def set_paid(self, paid, invoice_number=None):
        """Set paid status and optional invoice number"""
        self.paid = paid
        if invoice_number:
            self.invoice_number = invoice_number.strip() if invoice_number else None
        elif not paid:
            # Clear invoice number when marking as unpaid
            self.invoice_number = None
        self.updated_at = local_now()
        db.session.commit()

    def to_dict(self):
        """Convert time entry to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "duration_hours": self.duration_hours,
            "duration_formatted": self.duration_formatted,
            "notes": self.notes,
            "tags": self.tags,
            "tag_list": self.tag_list,
            "source": self.source,
            "billable": self.billable,
            "paid": self.paid,
            "invoice_number": self.invoice_number,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.username if self.user else None,
            "project": self.project.name if self.project else None,
            "client": self.client.name if self.client else None,
            "task": self.task.name if self.task else None,
        }

    @classmethod
    def get_active_timers(cls):
        """Get all active timers"""
        return cls.query.filter_by(end_time=None).all()

    @classmethod
    def get_user_active_timer(cls, user_id):
        """Get active timer for a specific user"""
        return cls.query.filter_by(user_id=user_id, end_time=None).first()

    @classmethod
    def get_entries_for_period(cls, start_date=None, end_date=None, user_id=None, project_id=None, client_id=None):
        """Get time entries for a specific period with optional filters"""
        query = cls.query.filter(cls.end_time.isnot(None))

        if start_date:
            query = query.filter(cls.start_time >= start_date)

        if end_date:
            query = query.filter(cls.start_time <= end_date)

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if project_id:
            query = query.filter(cls.project_id == project_id)

        if client_id:
            query = query.filter(cls.client_id == client_id)

        return query.order_by(cls.start_time.desc()).all()

    @classmethod
    def get_total_hours_for_period(
        cls, start_date=None, end_date=None, user_id=None, project_id=None, client_id=None, billable_only=False
    ):
        """Calculate total hours for a period with optional filters"""
        query = db.session.query(db.func.sum(cls.duration_seconds))

        if start_date:
            query = query.filter(cls.start_time >= start_date)

        if end_date:
            query = query.filter(cls.start_time <= end_date)

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if project_id:
            query = query.filter(cls.project_id == project_id)

        if client_id:
            query = query.filter(cls.client_id == client_id)

        if billable_only:
            query = query.filter(cls.billable == True)

        total_seconds = query.scalar() or 0
        return round(total_seconds / 3600, 2)
