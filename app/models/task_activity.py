from app import db
from app.utils.timezone import now_in_app_timezone


class TaskActivity(db.Model):
    """Lightweight audit log for significant task events."""

    __tablename__ = "task_activities"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    event = db.Column(db.String(50), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False, index=True)

    task = db.relationship("Task", backref=db.backref("activities", lazy="dynamic", cascade="all, delete-orphan"))
    user = db.relationship("User")

    def __init__(self, task_id, event, user_id=None, details=None):
        self.task_id = task_id
        self.user_id = user_id
        self.event = event
        self.details = details

    def __repr__(self):
        return f"<TaskActivity task={self.task_id} event={self.event}>"
