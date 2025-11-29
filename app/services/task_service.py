"""
Service for task business logic.
"""

from typing import Optional, Dict, Any, List
from app import db
from app.repositories import TaskRepository, ProjectRepository
from app.models import Task
from app.constants import TaskStatus
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class TaskService:
    """
    Service for task business logic operations.

    This service handles all task-related business logic including:
    - Creating and updating tasks
    - Listing tasks with filtering and pagination
    - Getting task details with related data
    - Task assignment and status management

    All methods use the repository pattern for data access and include
    eager loading to prevent N+1 query problems.

    Example:
        service = TaskService()
        result = service.create_task(
            name="New Task",
            project_id=1,
            created_by=user_id
        )
        if result['success']:
            task = result['task']
    """

    def __init__(self):
        """
        Initialize TaskService with required repositories.
        """
        self.task_repo = TaskRepository()
        self.project_repo = ProjectRepository()

    def create_task(
        self,
        name: str,
        project_id: int,
        created_by: int,
        description: Optional[str] = None,
        assignee_id: Optional[int] = None,
        priority: str = "medium",
        due_date: Optional[Any] = None,
        estimated_hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a new task.

        Args:
            name: Task name
            project_id: Project ID
            description: Task description
            assignee_id: User ID of assignee
            priority: Task priority (low, medium, high)
            due_date: Due date
            estimated_hours: Estimated hours
            created_by: User ID of creator

        Returns:
            dict with 'success', 'message', and 'task' keys
        """
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"success": False, "message": "Invalid project", "error": "invalid_project"}

        # Create task
        task = self.task_repo.create(
            name=name,
            project_id=project_id,
            description=description,
            assigned_to=assignee_id,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            status=TaskStatus.TODO.value,
            created_by=created_by,
        )

        if not safe_commit("create_task", {"project_id": project_id, "created_by": created_by}):
            return {
                "success": False,
                "message": "Could not create task due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(
            WebhookEvent.TASK_CREATED.value, {"task_id": task.id, "project_id": project_id, "created_by": created_by}
        )

        return {"success": True, "message": "Task created successfully", "task": task}

    def get_task_with_details(
        self,
        task_id: int,
        include_time_entries: bool = True,
        include_comments: bool = True,
        include_activities: bool = True,
    ) -> Optional[Task]:
        """
        Get task with all related data using eager loading to prevent N+1 queries.

        Args:
            task_id: The task ID
            include_time_entries: Whether to include time entries
            include_comments: Whether to include comments
            include_activities: Whether to include activities

        Returns:
            Task with eagerly loaded relations, or None if not found
        """
        from sqlalchemy.orm import joinedload
        from app.models import TimeEntry, Comment, TaskActivity

        query = self.task_repo.query().filter_by(id=task_id)

        # Eagerly load project and assignee
        query = query.options(joinedload(Task.project), joinedload(Task.assigned_user), joinedload(Task.creator))

        # Conditionally load relations
        # Note: time_entries is a dynamic relationship (lazy='dynamic') and cannot be eager loaded
        # Time entries must be queried separately using task.time_entries.order_by(...).all()

        if include_comments:
            query = query.options(joinedload(Task.comments).joinedload(Comment.author))

        # Note: activities is a dynamic relationship (lazy='dynamic') and cannot be eager loaded
        # Activities must be queried separately using task.activities.order_by(...).all()

        return query.first()

    def update_task(self, task_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update a task.

        Returns:
            dict with 'success', 'message', and 'task' keys
        """
        task = self.task_repo.get_by_id(task_id)

        if not task:
            return {"success": False, "message": "Task not found", "error": "not_found"}

        # Update fields
        self.task_repo.update(task, **kwargs)

        if not safe_commit("update_task", {"task_id": task_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not update task due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Task updated successfully", "task": task}

    def get_project_tasks(self, project_id: int, status: Optional[str] = None) -> List[Task]:
        """Get tasks for a project"""
        return self.task_repo.get_by_project(project_id=project_id, status=status, include_relations=True)

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        assigned_to: Optional[int] = None,
        search: Optional[str] = None,
        overdue: bool = False,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        List tasks with filtering and pagination.
        Uses eager loading to prevent N+1 queries.

        Returns:
            dict with 'tasks', 'pagination', and 'total' keys
        """
        from sqlalchemy.orm import joinedload
        from app.utils.timezone import now_in_app_timezone

        query = self.task_repo.query()

        # Eagerly load relations to prevent N+1
        query = query.options(joinedload(Task.project), joinedload(Task.assigned_user), joinedload(Task.creator))

        # Apply filters
        if status:
            query = query.filter(Task.status == status)

        if priority:
            query = query.filter(Task.priority == priority)

        if project_id:
            query = query.filter(Task.project_id == project_id)

        if assigned_to:
            query = query.filter(Task.assigned_to == assigned_to)

        if search:
            like = f"%{search}%"
            query = query.filter(db.or_(Task.name.ilike(like), Task.description.ilike(like)))

        # Overdue filter
        if overdue:
            today_local = now_in_app_timezone().date()
            query = query.filter(Task.due_date < today_local, Task.status.in_(["todo", "in_progress", "review"]))

        # Permission filter - non-admins only see their tasks
        if not is_admin and user_id:
            query = query.filter(db.or_(Task.assigned_to == user_id, Task.created_by == user_id))

        # Order by priority, due date, created date
        query = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc())

        # Determine pagination
        has_filters = bool(status or priority or project_id or assigned_to or search or overdue)
        if not has_filters:
            per_page = 10000  # Show all if no filters

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {"tasks": pagination.items, "pagination": pagination, "total": pagination.total}
