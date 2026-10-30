"""
Recurring Task model for automated task creation
Similar to recurring invoices but for tasks
"""

from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from app import db


class RecurringTask(db.Model):
    """Recurring task template for automated task creation"""

    __tablename__ = "recurring_tasks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Template name/description
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)

    # Recurrence settings
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    interval = db.Column(db.Integer, nullable=False, default=1)  # Every N periods
    next_run_date = db.Column(db.Date, nullable=False)  # Next date to create task
    end_date = db.Column(db.Date, nullable=True)  # Optional end date

    # Task template settings (copied to generated tasks)
    task_name_template = db.Column(db.String(500), nullable=False)  # Can include {{date}} etc.
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default="medium", nullable=False)  # 'low', 'medium', 'high'
    estimated_hours = db.Column(db.Numeric(10, 2), nullable=True)

    # Auto-creation settings
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    auto_assign = db.Column(db.Boolean, nullable=False, default=False)  # Auto-assign to template creator

    # Tracking
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_created_at = db.Column(db.DateTime, nullable=True)  # Last time a task was created from this template
    tasks_created_count = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    project = db.relationship("Project", backref=db.backref("recurring_tasks", lazy="dynamic"))
    creator = db.relationship(
        "User", foreign_keys=[created_by], backref=db.backref("created_recurring_tasks", lazy="dynamic")
    )
    assignee_links = db.relationship(
        "RecurringTaskAssignee",
        back_populates="recurring_task",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
    )

    def __init__(self, name, project_id, frequency, next_run_date, created_by, **kwargs):
        self.name = name
        self.project_id = project_id
        self.frequency = frequency
        self.next_run_date = next_run_date
        self.created_by = created_by

        # Set optional fields
        self.interval = kwargs.get("interval", 1)
        self.end_date = kwargs.get("end_date")
        self.task_name_template = kwargs.get("task_name_template", name)
        self.description = kwargs.get("description")
        self.priority = kwargs.get("priority", "medium")
        self.estimated_hours = kwargs.get("estimated_hours")
        self.is_active = kwargs.get("is_active", True)
        self.auto_assign = kwargs.get("auto_assign", False)

        ids = list(kwargs.get("assignee_ids") or [])
        if not ids and kwargs.get("assigned_to") is not None:
            ids = [kwargs.get("assigned_to")]
        self._pending_assignee_ids = ids

    def __repr__(self):
        return f"<RecurringTask {self.name} ({self.frequency})>"

    @property
    def assignee_ids(self):
        return [link.user_id for link in self.assignee_links]

    @property
    def assignees(self):
        return [link.user for link in self.assignee_links if link.user is not None]

    @property
    def assigned_to(self):
        """Deprecated: first assignee id for compatibility."""
        ids = self.assignee_ids
        return ids[0] if ids else None

    @property
    def assignee(self):
        """Deprecated: first assignee user for template compatibility."""
        users = self.assignees
        return users[0] if users else None

    def set_assignees(self, user_ids, *, commit=False):
        from app.models.task_assignee import RecurringTaskAssignee

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

        current = {link.user_id: link for link in list(self.assignee_links)}
        desired = set(normalized)

        for uid, link in list(current.items()):
            if uid not in desired:
                self.assignee_links.remove(link)
                db.session.delete(link)

        for uid in normalized:
            if uid not in current:
                self.assignee_links.append(
                    RecurringTaskAssignee(
                        user_id=uid,
                        recurring_task_id=self.id if self.id is not None else None,
                    )
                )

        self.updated_at = datetime.utcnow()
        if commit:
            db.session.commit()

    def apply_pending_assignees(self):
        pending = getattr(self, "_pending_assignee_ids", None)
        if pending is not None:
            self.set_assignees(pending)
            self._pending_assignee_ids = None

    def calculate_next_run_date(self, from_date=None):
        """Calculate the next run date based on frequency and interval"""
        if from_date is None:
            from_date = datetime.utcnow().date()

        if self.frequency == "daily":
            return from_date + timedelta(days=self.interval)
        elif self.frequency == "weekly":
            return from_date + timedelta(weeks=self.interval)
        elif self.frequency == "monthly":
            return from_date + relativedelta(months=self.interval)
        elif self.frequency == "yearly":
            return from_date + relativedelta(years=self.interval)
        else:
            raise ValueError(f"Invalid frequency: {self.frequency}")

    def create_task(self):
        """Create a task from this template"""
        from app.models import Task

        # Resolve task name template variables
        task_name = self.task_name_template
        task_name = task_name.replace("{{date}}", self.next_run_date.strftime("%Y-%m-%d"))
        task_name = task_name.replace("{{week}}", f"Week {self.next_run_date.isocalendar()[1]}")
        task_name = task_name.replace("{{month}}", self.next_run_date.strftime("%B"))

        if self.auto_assign:
            assignee_ids = [self.created_by]
        else:
            assignee_ids = list(self.assignee_ids)

        task = Task(
            project_id=self.project_id,
            name=task_name,
            description=self.description,
            priority=self.priority,
            estimated_hours=float(self.estimated_hours) if self.estimated_hours else None,
            assignee_ids=assignee_ids,
            created_by=self.created_by,
            status="todo",
        )
        db.session.add(task)
        db.session.flush()
        task.apply_pending_assignees()

        # Update template
        self.last_created_at = datetime.utcnow()
        self.tasks_created_count += 1
        self.next_run_date = self.calculate_next_run_date(self.next_run_date)

        # Check if we've reached the end date
        if self.end_date and self.next_run_date > self.end_date:
            self.is_active = False

        db.session.commit()

        return task

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "frequency": self.frequency,
            "interval": self.interval,
            "next_run_date": self.next_run_date.isoformat() if self.next_run_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "task_name_template": self.task_name_template,
            "description": self.description,
            "priority": self.priority,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None,
            "assignee_ids": self.assignee_ids,
            "assigned_to": self.assigned_to,
            "is_active": self.is_active,
            "auto_assign": self.auto_assign,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_created_at": self.last_created_at.isoformat() if self.last_created_at else None,
            "tasks_created_count": self.tasks_created_count,
        }
