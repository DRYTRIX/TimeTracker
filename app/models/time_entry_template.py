from datetime import datetime
from app import db


class TimeEntryTemplate(db.Model):
    """Quick-start templates for common time entries

    Allows users to create reusable templates for frequently
    logged activities, saving time and ensuring consistency.
    """

    __tablename__ = "time_entry_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Default values for time entries
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    default_duration_minutes = db.Column(db.Integer, nullable=True)  # Optional default duration
    default_notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    billable = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    usage_count = db.Column(db.Integer, default=0, nullable=False)  # Track how often used
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref="time_entry_templates")
    project = db.relationship("Project", backref="time_entry_templates")
    task = db.relationship("Task", backref="time_entry_templates")

    def __repr__(self):
        return f"<TimeEntryTemplate {self.name}>"

    @property
    def default_duration(self):
        """Get duration in hours"""
        if self.default_duration_minutes is None:
            return None
        return self.default_duration_minutes / 60.0

    @default_duration.setter
    def default_duration(self, hours):
        """Set duration from hours"""
        if hours is None:
            self.default_duration_minutes = None
        else:
            self.default_duration_minutes = int(hours * 60)

    def record_usage(self):
        """Record that this template was used"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        # Safely access relationships to avoid DetachedInstanceError
        # Relationships should be eagerly loaded, but we handle the case where they're not
        project_name = None
        if self.project_id:
            try:
                project_name = self.project.name if self.project else None
            except Exception:
                # If accessing project fails (e.g., detached instance), just use None
                project_name = None
        
        task_name = None
        if self.task_id:
            try:
                task_name = self.task.name if self.task else None
            except Exception:
                # If accessing task fails (e.g., detached instance), just use None
                task_name = None
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "project_name": project_name,
            "task_id": self.task_id,
            "task_name": task_name,
            "default_duration": self.default_duration,  # In hours for API
            "default_duration_minutes": self.default_duration_minutes,  # Keep for compatibility
            "default_notes": self.default_notes,
            "tags": self.tags,
            "billable": self.billable,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
