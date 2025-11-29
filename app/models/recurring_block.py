from datetime import datetime
from app import db


class RecurringBlock(db.Model):
    """Recurring time block template to generate time entries on a schedule.

    Supports weekly recurrences with selected weekdays, start/end times, and optional
    end date. Generation logic will live in a scheduler/route that expands these
    templates into concrete `TimeEntry` rows.
    """

    __tablename__ = "recurring_blocks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)

    name = db.Column(db.String(200), nullable=False)

    # Scheduling fields
    # 'weekly' for now; room to add 'daily', 'monthly' later
    recurrence = db.Column(db.String(20), nullable=False, default="weekly")
    # Weekdays CSV: e.g., "mon,tue,wed"; canonical lower 3-letter names
    weekdays = db.Column(db.String(50), nullable=True)
    # Time window in local time: "HH:MM" strings
    start_time_local = db.Column(db.String(5), nullable=False)  # 09:00
    end_time_local = db.Column(db.String(5), nullable=False)  # 11:00

    # Activation window
    starts_on = db.Column(db.Date, nullable=True)
    ends_on = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Entry details
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    billable = db.Column(db.Boolean, nullable=False, default=True)

    # Tracking last generation to avoid duplicates
    last_generated_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "name": self.name,
            "recurrence": self.recurrence,
            "weekdays": self.weekdays,
            "start_time_local": self.start_time_local,
            "end_time_local": self.end_time_local,
            "starts_on": self.starts_on.isoformat() if self.starts_on else None,
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
            "is_active": self.is_active,
            "notes": self.notes,
            "tags": self.tags,
            "billable": self.billable,
            "last_generated_at": self.last_generated_at.isoformat() if self.last_generated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
