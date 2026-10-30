from datetime import datetime

from app import db
from app.utils.timezone import now_in_app_timezone


class TaskAssignee(db.Model):
    """Association table for task assignees (many-to-many)."""

    __tablename__ = "task_assignees"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)

    __table_args__ = (db.UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),)

    task = db.relationship("Task", back_populates="assignee_links")
    user = db.relationship(
        "User",
        backref=db.backref(
            "task_assignee_links",
            lazy="dynamic",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

    def __repr__(self):
        return f"<TaskAssignee task_id={self.task_id} user_id={self.user_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecurringTaskAssignee(db.Model):
    """Association table for recurring task template assignees."""

    __tablename__ = "recurring_task_assignees"

    id = db.Column(db.Integer, primary_key=True)
    recurring_task_id = db.Column(
        db.Integer, db.ForeignKey("recurring_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("recurring_task_id", "user_id", name="uq_recurring_task_assignee"),)

    recurring_task = db.relationship("RecurringTask", back_populates="assignee_links")
    user = db.relationship(
        "User",
        backref=db.backref(
            "recurring_task_assignee_links",
            lazy="dynamic",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

    def __repr__(self):
        return f"<RecurringTaskAssignee recurring_task_id={self.recurring_task_id} user_id={self.user_id}>"
