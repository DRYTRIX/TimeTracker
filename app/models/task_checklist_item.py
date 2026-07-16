from app import db
from app.utils.timezone import now_in_app_timezone


class TaskChecklistItem(db.Model):
    """A single checklist/subtask entry on a task.

    Checklist items are lightweight to-dos that break a task into concrete
    steps. They carry no scheduling or time tracking of their own -- the
    parent task owns that -- so this stays a thin ordered list of
    text + done-state rows.
    """

    __tablename__ = "task_checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = db.Column(db.String(500), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=now_in_app_timezone,
        onupdate=now_in_app_timezone,
        nullable=False,
    )

    task = db.relationship(
        "Task",
        backref=db.backref(
            "checklist_items",
            order_by="TaskChecklistItem.position",
            cascade="all, delete-orphan",
        ),
    )

    def __init__(self, task_id, text, position=0, is_done=False):
        self.task_id = task_id
        self.text = text.strip()
        self.position = position
        self.is_done = is_done

    def __repr__(self):
        state = "x" if self.is_done else " "
        return f"<TaskChecklistItem [{state}] {self.text!r} task={self.task_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "text": self.text,
            "is_done": self.is_done,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
