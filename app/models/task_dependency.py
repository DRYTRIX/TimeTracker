from sqlalchemy import UniqueConstraint

from app import db
from app.utils.timezone import now_in_app_timezone

VALID_DEPENDENCY_TYPES = ("finish_to_start", "blocks")


class TaskDependency(db.Model):
    """Directed dependency between two tasks in the same project.

    ``task_id`` depends on ``depends_on_id`` (finish-to-start by default):
    the dependent task is blocked until the blocker is done or cancelled.
    """

    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependencies_pair"),)

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type = db.Column(db.String(20), default="finish_to_start", nullable=False)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)

    task = db.relationship(
        "Task",
        foreign_keys=[task_id],
        backref=db.backref("blocking_links", cascade="all, delete-orphan", lazy="select"),
    )
    depends_on = db.relationship(
        "Task",
        foreign_keys=[depends_on_id],
        backref=db.backref("dependent_links", cascade="all, delete-orphan", lazy="select"),
    )

    def __init__(self, task_id, depends_on_id, dependency_type="finish_to_start"):
        self.task_id = task_id
        self.depends_on_id = depends_on_id
        self.dependency_type = dependency_type if dependency_type in VALID_DEPENDENCY_TYPES else "finish_to_start"

    def __repr__(self):
        return f"<TaskDependency task={self.task_id} depends_on={self.depends_on_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "depends_on_id": self.depends_on_id,
            "dependency_type": self.dependency_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "depends_on_name": self.depends_on.name if self.depends_on else None,
            "task_name": self.task.name if self.task else None,
        }

    @classmethod
    def would_create_cycle(cls, task_id, depends_on_id):
        """Return True if adding task_id -> depends_on_id would create a cycle."""
        if task_id == depends_on_id:
            return True
        visited = set()
        stack = [depends_on_id]
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            blockers = cls.query.filter_by(task_id=current).all()
            stack.extend(d.depends_on_id for d in blockers)
        return False
