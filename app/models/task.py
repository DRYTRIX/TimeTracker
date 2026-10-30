from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm import Session

from app import db
from app.utils.timezone import now_in_app_timezone


class Task(db.Model):
    """Task model for breaking down projects into manageable components"""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(20), default="todo", nullable=False, index=True
    )  # 'todo', 'in_progress', 'review', 'done', 'cancelled'
    priority = db.Column(db.String(20), default="medium", nullable=False)  # 'low', 'medium', 'high', 'urgent'
    estimated_hours = db.Column(db.Float, nullable=True)
    due_date = db.Column(db.Date, nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    # Gantt chart bar color (hex e.g. #3b82f6). Overrides project color when set.
    color = db.Column(db.String(7), nullable=True)
    # Comma-separated tags for categorization
    tags = db.Column(db.String(500), nullable=True)
    # Integration metadata (e.g. GitHub issue id); see app.utils.integration_sync_context
    custom_fields = db.Column(db.JSON, nullable=True)
    # Canonical external reference for tasks created from third-party
    # integrations (e.g. "github_issue_42"). Indexed so connectors can
    # cheaply de-duplicate when syncing.
    external_ref = db.Column(db.String(200), nullable=True, index=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    # project relationship is defined via backref in Project model
    assignee_links = db.relationship(
        "TaskAssignee",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
    )
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_tasks")
    time_entries = db.relationship("TimeEntry", backref="task", lazy="dynamic")
    # comments relationship is defined via backref in Comment model

    def __init__(
        self,
        project_id,
        name,
        description=None,
        priority="medium",
        estimated_hours=None,
        due_date=None,
        assigned_to=None,
        assignee_ids=None,
        created_by=None,
        status="todo",
        tags=None,
    ):
        self.project_id = project_id
        self.name = name.strip()
        self.description = description.strip() if description else None
        self.priority = priority
        self.estimated_hours = estimated_hours
        self.due_date = due_date
        self.created_by = created_by
        self.status = status
        self.tags = (tags.strip() or None) if tags else None
        # Defer assignee links until after flush when possible; callers may also
        # call set_assignees after add. Support legacy assigned_to for create paths.
        ids = list(assignee_ids) if assignee_ids is not None else []
        if not ids and assigned_to is not None:
            ids = [assigned_to]
        self._pending_assignee_ids = ids

    def __repr__(self):
        return f"<Task {self.name} ({self.status})>"

    @property
    def assignee_ids(self):
        """List of assigned user IDs."""
        return [link.user_id for link in self.assignee_links]

    @property
    def assignees(self):
        """List of assigned User objects."""
        return [link.user for link in self.assignee_links if link.user is not None]

    @property
    def assigned_to(self):
        """Deprecated: first assignee id for API compatibility."""
        ids = self.assignee_ids
        return ids[0] if ids else None

    @property
    def assigned_user(self):
        """Deprecated: first assignee user for template/API compatibility."""
        users = self.assignees
        return users[0] if users else None

    def is_assigned_to(self, user_id):
        """Return True if user_id is among assignees."""
        if user_id is None:
            return False
        return any(link.user_id == user_id for link in self.assignee_links)

    def set_assignees(self, user_ids, *, commit=False):
        """Replace the assignee set. Deduplicates and ignores None/empty."""
        from app.models.task_assignee import TaskAssignee

        normalized = []
        seen = set()
        for uid in user_ids or []:
            if uid is None:
                continue
            uid = int(uid)
            if uid in seen:
                continue
            seen.add(uid)
            normalized.append(uid)

        # Diff the current collection so cascade delete-orphan stays consistent
        current = {link.user_id: link for link in list(self.assignee_links)}
        desired = set(normalized)

        for uid, link in list(current.items()):
            if uid not in desired:
                self.assignee_links.remove(link)
                db.session.delete(link)

        for uid in normalized:
            if uid not in current:
                self.assignee_links.append(
                    TaskAssignee(user_id=uid, task_id=self.id if self.id is not None else None)
                )

        self.updated_at = now_in_app_timezone()
        if commit:
            db.session.commit()

    def apply_pending_assignees(self):
        """Apply assignee IDs stored during __init__ (call after add/flush)."""
        pending = getattr(self, "_pending_assignee_ids", None)
        if pending is not None:
            self.set_assignees(pending)
            self._pending_assignee_ids = None

    @property
    def is_active(self):
        """Check if task is active (not done or cancelled)"""
        return self.status not in ["done", "cancelled"]

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.due_date:
            return False
        from datetime import date

        return date.today() > self.due_date and self.status not in ["done", "cancelled"]

    @property
    def checklist_total(self):
        """Number of checklist items on this task."""
        return len(self.checklist_items)

    @property
    def checklist_done(self):
        """Number of completed checklist items on this task."""
        return sum(1 for item in self.checklist_items if item.is_done)

    @property
    def checklist_progress(self):
        """Checklist completion as an integer percentage (0-100)."""
        total = self.checklist_total
        if not total:
            return 0
        return round(self.checklist_done * 100 / total)

    @property
    def total_hours(self):
        """Calculate total hours spent on this task"""
        # Use cached value if available (set by TaskService.list_tasks for performance)
        if hasattr(self, "_cached_total_hours"):
            return self._cached_total_hours

        try:
            from .time_entry import TimeEntry

            total_seconds = (
                db.session.query(db.func.sum(TimeEntry.duration_seconds))
                .filter(TimeEntry.task_id == self.id, TimeEntry.end_time.isnot(None))
                .scalar()
                or 0
            )

            return round(total_seconds / 3600, 2)
        except Exception:
            return 0.0

    @property
    def total_billable_hours(self):
        """Calculate total billable hours spent on this task"""
        try:
            from .time_entry import TimeEntry

            total_seconds = (
                db.session.query(db.func.sum(TimeEntry.duration_seconds))
                .filter(TimeEntry.task_id == self.id, TimeEntry.end_time.isnot(None), TimeEntry.billable == True)
                .scalar()
                or 0
            )
            return round(total_seconds / 3600, 2)
        except Exception:
            return 0.0

    @property
    def progress_percentage(self):
        """Calculate progress percentage based on estimated vs actual hours"""
        if not self.estimated_hours or self.estimated_hours == 0:
            return 0

        actual_hours = self.total_hours
        if actual_hours >= self.estimated_hours:
            return 100

        return round((actual_hours / self.estimated_hours) * 100, 1)

    @property
    def status_display(self):
        """Get human-readable status from kanban columns"""
        # Use cached value if available (set by TaskService.list_tasks for performance)
        if hasattr(self, "_cached_status_display"):
            return self._cached_status_display

        from .kanban_column import KanbanColumn

        column = KanbanColumn.get_column_by_key(self.status)
        if column:
            return column.label
        # Fallback to hardcoded map if column not found
        status_map = {
            "todo": "To Do",
            "in_progress": "In Progress",
            "review": "Review",
            "done": "Done",
            "cancelled": "Cancelled",
        }
        return status_map.get(self.status, self.status.replace("_", " ").title())

    @property
    def priority_display(self):
        """Get human-readable priority"""
        priority_map = {"low": "Low", "medium": "Medium", "high": "High", "urgent": "Urgent"}
        return priority_map.get(self.priority, self.priority)

    @property
    def priority_class(self):
        """Get CSS class for priority styling"""
        priority_classes = {
            "low": "priority-low",
            "medium": "priority-medium",
            "high": "priority-high",
            "urgent": "priority-urgent",
        }
        return priority_classes.get(self.priority, "priority-medium")

    @property
    def tag_list(self):
        """Get list of tags from comma-separated string"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def is_blocked(self):
        """True if any unfinished blocker task exists."""
        for link in self.blocking_links:
            blocker = link.depends_on
            if blocker and blocker.status not in ["done", "cancelled"]:
                return True
        return False

    @property
    def blocker_tasks(self):
        return [link.depends_on for link in self.blocking_links if link.depends_on]

    @property
    def dependent_tasks(self):
        return [link.task for link in self.dependent_links if link.task]

    def start_task(self):
        """Mark task as in progress"""
        if self.status == "done":
            raise ValueError("Cannot start a completed task")
        if self.is_blocked:
            names = ", ".join(t.name for t in self.blocker_tasks if t.status not in ["done", "cancelled"])
            raise ValueError(f"Cannot start a blocked task. Waiting on: {names}")

        self.status = "in_progress"
        self.started_at = now_in_app_timezone()
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def pause_task(self):
        """Pause task (mark as todo)"""
        if self.status != "in_progress":
            raise ValueError("Can only pause tasks that are in progress")

        self.status = "todo"
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def mark_for_review(self):
        """Mark task as ready for review"""
        if self.status not in ["in_progress", "todo"]:
            raise ValueError("Task must be in progress or todo to mark for review")

        self.status = "review"
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def complete_task(self):
        """Mark task as completed"""
        if self.status == "cancelled":
            raise ValueError("Cannot complete a cancelled task")

        self.status = "done"
        self.completed_at = now_in_app_timezone()
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def cancel_task(self):
        """Cancel the task"""
        if self.status == "done":
            raise ValueError("Cannot cancel a completed task")

        self.status = "cancelled"
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def reassign(self, user_id):
        """Reassign task to a single user (replaces the assignee set)."""
        self.set_assignees([user_id] if user_id is not None else [], commit=True)

    def update_priority(self, priority):
        """Update task priority"""
        valid_priorities = ["low", "medium", "high", "urgent"]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

        self.priority = priority
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def update_due_date(self, due_date):
        """Update task due date"""
        self.due_date = due_date
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def to_dict(self):
        """Convert task to dictionary for API responses"""
        assignee_list = [
            {"id": u.id, "username": u.username, "display_name": getattr(u, "display_name", u.username)}
            for u in self.assignees
        ]
        first = assignee_list[0] if assignee_list else None
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "status_display": self.status_display,
            "priority": self.priority,
            "priority_display": self.priority_display,
            "priority_class": self.priority_class,
            "estimated_hours": self.estimated_hours,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assignee_ids": self.assignee_ids,
            "assignees": assignee_list,
            # Deprecated single-assignee fields for API compatibility
            "assigned_to": first["id"] if first else None,
            "assigned_user": first["username"] if first else None,
            "created_by": self.created_by,
            "creator": self.creator.username if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_hours": self.total_hours,
            "total_billable_hours": self.total_billable_hours,
            "progress_percentage": self.progress_percentage,
            "is_active": self.is_active,
            "is_overdue": self.is_overdue,
            "tags": self.tags,
            "tag_list": self.tag_list,
            "milestone_id": self.milestone_id,
            "is_blocked": self.is_blocked,
            "blocker_ids": [link.depends_on_id for link in self.blocking_links],
            "dependent_ids": [link.task_id for link in self.dependent_links],
        }

    @classmethod
    def assigned_user_exists(cls, user_id):
        """SQLAlchemy exists() clause: task is assigned to user_id."""
        from app.models.task_assignee import TaskAssignee

        return db.exists().where(
            TaskAssignee.task_id == cls.id,
            TaskAssignee.user_id == user_id,
        )

    @classmethod
    def get_tasks_by_project(cls, project_id, status=None, priority=None):
        """Get tasks for a specific project with optional filters"""
        query = cls.query.filter_by(project_id=project_id)

        if status:
            query = query.filter_by(status=status)

        if priority:
            query = query.filter_by(priority=priority)

        return query.order_by(cls.priority.desc(), cls.due_date.asc(), cls.created_at.asc()).all()

    @classmethod
    def get_user_tasks(cls, user_id, status=None, include_assigned=True, include_created=True):
        """Get tasks for a specific user"""
        if not include_assigned and not include_created:
            return []

        from app.models.task_assignee import TaskAssignee

        query = cls.query

        if include_assigned and include_created:
            query = query.filter(
                db.or_(
                    cls.id.in_(db.session.query(TaskAssignee.task_id).filter(TaskAssignee.user_id == user_id)),
                    cls.created_by == user_id,
                )
            )
        elif include_assigned:
            query = query.filter(
                cls.id.in_(db.session.query(TaskAssignee.task_id).filter(TaskAssignee.user_id == user_id))
            )
        elif include_created:
            query = query.filter_by(created_by=user_id)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(cls.priority.desc(), cls.due_date.asc(), cls.created_at.asc()).all()

    @classmethod
    def get_overdue_tasks(cls):
        """Get all overdue tasks"""
        from datetime import date

        today = date.today()

        return (
            cls.query.filter(cls.due_date < today, cls.status.in_(["todo", "in_progress", "review"]))
            .order_by(cls.priority.desc(), cls.due_date.asc())
            .all()
        )


@event.listens_for(Session, "before_flush")
def _apply_pending_task_assignees(session, flush_context, instances):
    """Ensure Task/RecurringTask pending assignee IDs become association rows on flush."""
    for obj in list(session.new) + list(session.dirty):
        apply = getattr(obj, "apply_pending_assignees", None)
        if callable(apply) and getattr(obj, "_pending_assignee_ids", None) is not None:
            apply()
