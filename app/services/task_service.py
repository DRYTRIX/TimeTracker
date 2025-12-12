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
        has_view_all_tasks: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        List tasks with filtering and pagination.
        Uses eager loading to prevent N+1 queries.

        Returns:
            dict with 'tasks', 'pagination', and 'total' keys
        """
        import time
        import logging
        from sqlalchemy.orm import joinedload
        from app.utils.timezone import now_in_app_timezone

        logger = logging.getLogger(__name__)
        start_time = time.time()
        step_start = time.time()

        query = self.task_repo.query()
        logger.debug(f"[TaskService.list_tasks] Step 1: Initial query creation took {(time.time() - step_start) * 1000:.2f}ms")

        step_start = time.time()
        # Eagerly load relations to prevent N+1
        query = query.options(joinedload(Task.project), joinedload(Task.assigned_user), joinedload(Task.creator))
        logger.debug(f"[TaskService.list_tasks] Step 2: Eager loading setup took {(time.time() - step_start) * 1000:.2f}ms")

        step_start = time.time()
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

        # Permission filter - users without view_all_tasks permission only see their tasks
        if not has_view_all_tasks and user_id:
            query = query.filter(db.or_(Task.assigned_to == user_id, Task.created_by == user_id))
        logger.debug(f"[TaskService.list_tasks] Step 3: Applying filters took {(time.time() - step_start) * 1000:.2f}ms")

        step_start = time.time()
        # Order by priority, due date, created date
        query = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc())
        logger.debug(f"[TaskService.list_tasks] Step 4: Ordering query took {(time.time() - step_start) * 1000:.2f}ms")

        step_start = time.time()
        # Paginate (always use pagination for performance)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        logger.debug(f"[TaskService.list_tasks] Step 5: Pagination query execution took {(time.time() - step_start) * 1000:.2f}ms (total: {pagination.total} tasks, page: {page}, per_page: {per_page})")

        step_start = time.time()
        # Pre-calculate total_hours for all tasks in a single query to avoid N+1
        # This prevents the template from triggering individual queries for each task
        tasks = pagination.items
        logger.debug(f"[TaskService.list_tasks] Step 6: Getting pagination items took {(time.time() - step_start) * 1000:.2f}ms ({len(tasks)} tasks)")
        
        if tasks:
            from app.models import TimeEntry, KanbanColumn
            step_start = time.time()
            task_ids = [task.id for task in tasks]
            logger.debug(f"[TaskService.list_tasks] Step 7: Extracting task IDs took {(time.time() - step_start) * 1000:.2f}ms")
            
            step_start = time.time()
            # Calculate total hours for all tasks in one query
            results = (
                db.session.query(
                    TimeEntry.task_id,
                    db.func.sum(TimeEntry.duration_seconds).label('total_seconds')
                )
                .filter(
                    TimeEntry.task_id.in_(task_ids),
                    TimeEntry.end_time.isnot(None)
                )
                .group_by(TimeEntry.task_id)
                .all()
            )
            total_hours_map = {task_id: total_seconds for task_id, total_seconds in results}
            logger.debug(f"[TaskService.list_tasks] Step 8: Calculating total hours query took {(time.time() - step_start) * 1000:.2f}ms ({len(results)} results)")
            
            step_start = time.time()
            # Pre-load kanban columns to avoid N+1 queries in status_display property
            # Load global columns (project_id is None) since tasks don't have project-specific columns
            kanban_columns = KanbanColumn.get_active_columns(project_id=None)
            status_display_map = {}
            for col in kanban_columns:
                status_display_map[col.key] = col.label
            logger.debug(f"[TaskService.list_tasks] Step 9: Loading kanban columns took {(time.time() - step_start) * 1000:.2f}ms ({len(kanban_columns)} columns)")
            
            # Fallback status map if no columns found
            fallback_status_map = {
                "todo": "To Do",
                "in_progress": "In Progress",
                "review": "Review",
                "done": "Done",
                "cancelled": "Cancelled",
            }
            
            step_start = time.time()
            # Cache the calculated values on task objects to avoid property queries
            for task in tasks:
                total_seconds = total_hours_map.get(task.id, 0) or 0
                task._cached_total_hours = round(total_seconds / 3600, 2) if total_seconds else 0.0
                
                # Cache status_display to avoid N+1 queries
                task._cached_status_display = status_display_map.get(
                    task.status,
                    fallback_status_map.get(task.status, task.status.replace("_", " ").title())
                )
            logger.debug(f"[TaskService.list_tasks] Step 10: Caching task properties took {(time.time() - step_start) * 1000:.2f}ms")
        
        total_time = (time.time() - start_time) * 1000
        logger.info(f"[TaskService.list_tasks] Total time: {total_time:.2f}ms (tasks: {len(tasks) if tasks else 0}, page: {page}, per_page: {per_page})")

        return {"tasks": tasks, "pagination": pagination, "total": pagination.total}
