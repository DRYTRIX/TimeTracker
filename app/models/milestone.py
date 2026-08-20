from datetime import date

from app import db
from app.utils.timezone import now_in_app_timezone

VALID_MILESTONE_STATUSES = ("upcoming", "in_progress", "completed", "missed")


class Milestone(db.Model):
    """Named project checkpoint with a due date and optional linked tasks."""

    __tablename__ = "milestones"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(20), default="upcoming", nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)

    project = db.relationship("Project", backref=db.backref("milestones", lazy="dynamic", cascade="all, delete-orphan"))
    creator = db.relationship("User", foreign_keys=[created_by])
    tasks = db.relationship("Task", backref="milestone", lazy="dynamic", foreign_keys="Task.milestone_id")

    def __init__(self, project_id, name, created_by=None, description=None, due_date=None, status="upcoming"):
        self.project_id = project_id
        self.name = name.strip()
        self.created_by = created_by
        self.description = description.strip() if description else None
        self.due_date = due_date
        self.status = status if status in VALID_MILESTONE_STATUSES else "upcoming"

    def __repr__(self):
        return f"<Milestone {self.name} ({self.status})>"

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter_by(status="done").count()

    @property
    def progress_percentage(self):
        total = self.task_count
        if not total:
            return 0
        return round(self.completed_task_count * 100 / total)

    @property
    def is_overdue(self):
        if not self.due_date or self.status == "completed":
            return False
        return date.today() > self.due_date

    def refresh_status(self):
        """Derive status from linked tasks and due date when not manually completed."""
        if self.status == "completed":
            return
        total = self.task_count
        done = self.completed_task_count
        if total and done == total:
            self.status = "completed"
            return
        if self.is_overdue:
            self.status = "missed"
            return
        if done > 0 or (total and done < total):
            self.status = "in_progress"
            return
        self.status = "upcoming"

    def mark_completed(self):
        self.status = "completed"
        self.updated_at = now_in_app_timezone()

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "task_count": self.task_count,
            "completed_task_count": self.completed_task_count,
            "progress_percentage": self.progress_percentage,
            "is_overdue": self.is_overdue,
        }
