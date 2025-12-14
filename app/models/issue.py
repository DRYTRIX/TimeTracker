from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


class Issue(db.Model):
    """Issue/Bug Report model for tracking client-reported issues"""

    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(20), default="open", nullable=False, index=True
    )  # 'open', 'in_progress', 'resolved', 'closed', 'cancelled'
    priority = db.Column(db.String(20), default="medium", nullable=False)  # 'low', 'medium', 'high', 'urgent'
    
    # Client submission info
    submitted_by_client = db.Column(db.Boolean, default=True, nullable=False)  # True if submitted via client portal
    client_submitter_name = db.Column(db.String(200), nullable=True)  # Name of person who submitted (if not a user)
    client_submitter_email = db.Column(db.String(200), nullable=True)  # Email of submitter
    
    # Internal assignment
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)  # Internal user who created/imported
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    client = db.relationship("Client", backref="issues", lazy="joined")
    project = db.relationship("Project", backref="issues", lazy="joined")
    task = db.relationship("Task", backref="issues", lazy="joined")
    assigned_user = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_issues", lazy="joined")
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_issues", lazy="joined")

    def __init__(
        self,
        client_id,
        title,
        description=None,
        project_id=None,
        task_id=None,
        priority="medium",
        status="open",
        submitted_by_client=True,
        client_submitter_name=None,
        client_submitter_email=None,
        assigned_to=None,
        created_by=None,
    ):
        self.client_id = client_id
        self.title = title.strip()
        self.description = description.strip() if description else None
        self.project_id = project_id
        self.task_id = task_id
        self.priority = priority
        self.status = status
        self.submitted_by_client = submitted_by_client
        self.client_submitter_name = client_submitter_name
        self.client_submitter_email = client_submitter_email
        self.assigned_to = assigned_to
        self.created_by = created_by

    def __repr__(self):
        return f"<Issue {self.title} ({self.status})>"

    @property
    def is_open(self):
        """Check if issue is open (not resolved or closed)"""
        return self.status in ["open", "in_progress"]

    @property
    def is_resolved(self):
        """Check if issue is resolved"""
        return self.status == "resolved"

    @property
    def is_closed(self):
        """Check if issue is closed"""
        return self.status == "closed"

    @property
    def status_display(self):
        """Get human-readable status"""
        status_map = {
            "open": "Open",
            "in_progress": "In Progress",
            "resolved": "Resolved",
            "closed": "Closed",
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

    def mark_in_progress(self):
        """Mark issue as in progress"""
        if self.status in ["closed", "cancelled"]:
            raise ValueError("Cannot mark a closed or cancelled issue as in progress")

        self.status = "in_progress"
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def mark_resolved(self):
        """Mark issue as resolved"""
        if self.status in ["closed", "cancelled"]:
            raise ValueError("Cannot resolve a closed or cancelled issue")

        self.status = "resolved"
        self.resolved_at = now_in_app_timezone()
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def mark_closed(self):
        """Mark issue as closed"""
        self.status = "closed"
        self.closed_at = now_in_app_timezone()
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def cancel(self):
        """Cancel the issue"""
        if self.status == "closed":
            raise ValueError("Cannot cancel a closed issue")

        self.status = "cancelled"
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def link_to_task(self, task_id):
        """Link this issue to a task"""
        from .task import Task
        task = Task.query.get(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Verify task belongs to same client (through project)
        if task.project.client_id != self.client_id:
            raise ValueError("Task must belong to a project from the same client")
        
        self.task_id = task_id
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def create_task_from_issue(self, project_id, assigned_to=None, created_by=None):
        """Create a new task from this issue"""
        from .task import Task
        
        # Verify project belongs to same client
        from .project import Project
        project = Project.query.get(project_id)
        if not project:
            raise ValueError("Project not found")
        if project.client_id != self.client_id:
            raise ValueError("Project must belong to the same client")
        
        # Create task
        task = Task(
            project_id=project_id,
            name=f"Issue: {self.title}",
            description=f"Created from issue #{self.id}\n\n{self.description or ''}",
            priority=self.priority,
            assigned_to=assigned_to,
            created_by=created_by or self.created_by,
            status="todo",
        )
        db.session.add(task)
        db.session.flush()  # Get task ID
        
        # Link issue to task
        self.task_id = task.id
        self.updated_at = now_in_app_timezone()
        db.session.commit()
        
        return task

    def reassign(self, user_id):
        """Reassign issue to different user"""
        self.assigned_to = user_id
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def update_priority(self, priority):
        """Update issue priority"""
        valid_priorities = ["low", "medium", "high", "urgent"]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

        self.priority = priority
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    def to_dict(self):
        """Convert issue to dictionary for API responses"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "task_id": self.task_id,
            "task_name": self.task.name if self.task else None,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "status_display": self.status_display,
            "priority": self.priority,
            "priority_display": self.priority_display,
            "priority_class": self.priority_class,
            "submitted_by_client": self.submitted_by_client,
            "client_submitter_name": self.client_submitter_name,
            "client_submitter_email": self.client_submitter_email,
            "assigned_to": self.assigned_to,
            "assigned_user": self.assigned_user.username if self.assigned_user else None,
            "created_by": self.created_by,
            "creator": self.creator.username if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "is_open": self.is_open,
            "is_resolved": self.is_resolved,
            "is_closed": self.is_closed,
        }

    @classmethod
    def get_issues_by_client(cls, client_id, status=None, priority=None):
        """Get issues for a specific client with optional filters"""
        query = cls.query.filter_by(client_id=client_id)

        if status:
            query = query.filter_by(status=status)

        if priority:
            query = query.filter_by(priority=priority)

        return query.order_by(cls.priority.desc(), cls.created_at.desc()).all()

    @classmethod
    def get_issues_by_project(cls, project_id, status=None):
        """Get issues for a specific project"""
        query = cls.query.filter_by(project_id=project_id)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(cls.priority.desc(), cls.created_at.desc()).all()

    @classmethod
    def get_issues_by_task(cls, task_id):
        """Get issues linked to a specific task"""
        return cls.query.filter_by(task_id=task_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_user_issues(cls, user_id, status=None):
        """Get issues assigned to a specific user"""
        query = cls.query.filter_by(assigned_to=user_id)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(cls.priority.desc(), cls.created_at.desc()).all()

    @classmethod
    def get_open_issues(cls):
        """Get all open issues"""
        return (
            cls.query.filter(cls.status.in_(["open", "in_progress"]))
            .order_by(cls.priority.desc(), cls.created_at.desc())
            .all()
        )
