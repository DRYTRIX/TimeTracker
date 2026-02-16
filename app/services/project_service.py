"""
Service for project business logic.
"""

from typing import Optional, List, Dict, Any
from app import db
from app.repositories import ProjectRepository, ClientRepository
from app.models import Project, TimeEntry
from app.constants import ProjectStatus
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class ProjectService:
    """
    Service for project business logic operations.

    This service handles all project-related business logic including:
    - Creating and updating projects
    - Listing projects with filtering and pagination
    - Getting project details with related data
    - Archiving projects

    All methods use the repository pattern for data access and include
    eager loading to prevent N+1 query problems.

    Example:
        service = ProjectService()
        result = service.create_project(
            name="New Project",
            client_id=1,
            created_by=user_id
        )
        if result['success']:
            project = result['project']
    """

    def __init__(self):
        """
        Initialize ProjectService with required repositories.
        """
        self.project_repo = ProjectRepository()
        self.client_repo = ClientRepository()

    def get_by_id(self, project_id: int) -> Optional[Project]:
        """
        Get a project by its ID.

        Returns:
            Project instance or None if not found
        """
        return self.project_repo.get_by_id(project_id)

    def create_project(
        self,
        name: str,
        client_id: int,
        created_by: int,
        description: Optional[str] = None,
        billable: bool = True,
        hourly_rate: Optional[float] = None,
        code: Optional[str] = None,
        budget_amount: Optional[float] = None,
        budget_threshold_percent: Optional[int] = None,
        billing_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project.

        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        # Validate client
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return {"success": False, "message": "Invalid client", "error": "invalid_client"}

        # Check for duplicate name
        existing = self.project_repo.find_one_by(name=name, client_id=client_id)
        if existing:
            return {
                "success": False,
                "message": "A project with this name already exists for this client",
                "error": "duplicate_project",
            }

        # Validate code uniqueness if provided
        if code:
            normalized_code = code.upper().strip()
            existing_code = self.project_repo.find_one_by(code=normalized_code)
            if existing_code:
                return {
                    "success": False,
                    "message": "Project code already in use",
                    "error": "duplicate_code",
                }
        else:
            normalized_code = None

        # Create project using model directly (repository doesn't support all fields yet)
        from app.models import Project
        from decimal import Decimal

        project = Project(
            name=name,
            client_id=client_id,
            description=description,
            billable=billable,
            hourly_rate=hourly_rate,
            code=normalized_code,
            budget_amount=Decimal(str(budget_amount)) if budget_amount else None,
            budget_threshold_percent=budget_threshold_percent or 80,
            billing_ref=billing_ref,
            status=ProjectStatus.ACTIVE.value,
        )

        db.session.add(project)

        if not safe_commit("create_project", {"client_id": client_id, "name": name}):
            return {
                "success": False,
                "message": "Could not create project due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(WebhookEvent.PROJECT_CREATED.value, {"project_id": project.id, "client_id": client_id})

        return {"success": True, "message": "Project created successfully", "project": project}

    def update_project(self, project_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update a project.

        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        project = self.project_repo.get_by_id(project_id)

        if not project:
            return {"success": False, "message": "Project not found", "error": "not_found"}

        # Update fields
        self.project_repo.update(project, **kwargs)

        if not safe_commit("update_project", {"project_id": project_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not update project due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Project updated successfully", "project": project}

    def archive_project(self, project_id: int, user_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive a project.

        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        project = self.project_repo.archive(project_id, user_id, reason)

        if not project:
            return {"success": False, "message": "Project not found", "error": "not_found"}

        if not safe_commit("archive_project", {"project_id": project_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not archive project due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Project archived successfully", "project": project}

    def get_active_projects(self, user_id: Optional[int] = None, client_id: Optional[int] = None) -> List[Project]:
        """Get active projects with optional filters"""
        return self.project_repo.get_active_projects(user_id=user_id, client_id=client_id, include_relations=True)

    def get_project_with_details(
        self,
        project_id: int,
        include_time_entries: bool = True,
        include_tasks: bool = True,
        include_comments: bool = True,
        include_costs: bool = True,
    ) -> Optional[Project]:
        """
        Get project with all related data using eager loading to prevent N+1 queries.

        Args:
            project_id: The project ID
            include_time_entries: Whether to include time entries
            include_tasks: Whether to include tasks
            include_comments: Whether to include comments
            include_costs: Whether to include costs

        Returns:
            Project with eagerly loaded relations, or None if not found
        """
        from sqlalchemy.orm import joinedload
        from app.models import Task, Comment, ProjectCost

        query = self.project_repo.query().filter_by(id=project_id)

        # Eagerly load client (client_obj is not dynamic, so it can be eagerly loaded)
        query = query.options(joinedload(Project.client_obj))

        # Note: time_entries, tasks, costs, and comments are dynamic relationships
        # (lazy='dynamic'), so they cannot be eagerly loaded with joinedload().
        # They return query objects that can be filtered and accessed when needed.
        # We'll query them separately when needed instead.

        return query.first()

    def list_projects(
        self,
        status: Optional[str] = None,
        client_name: Optional[str] = None,
        client_id: Optional[int] = None,
        client_custom_field: Optional[Dict[str, str]] = None,  # {field_key: value}
        search: Optional[str] = None,
        favorites_only: bool = False,
        user_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        scope_client_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        List projects with filtering and pagination.
        Uses eager loading to prevent N+1 queries.

        Args:
            client_custom_field: Dict with field_key and value to filter by client custom fields
                Example: {"debtor_number": "12345"}

        Returns:
            dict with 'projects', 'pagination', and 'total' keys
        """
        from sqlalchemy.orm import joinedload
        from app.models import UserFavoriteProject, Client, CustomFieldDefinition

        query = self.project_repo.query()

        # Eagerly load client to prevent N+1
        query = query.options(joinedload(Project.client_obj))

        # Filter by favorites if requested
        if favorites_only and user_id:
            query = query.join(
                UserFavoriteProject,
                db.and_(UserFavoriteProject.project_id == Project.id, UserFavoriteProject.user_id == user_id),
            )

        # Filter by status (skip if "all" is selected)
        if status and status != "all":
            query = query.filter(Project.status == status)

        # Filter by client - join Client table if needed
        client_joined = False
        if client_name or client_id or client_custom_field:
            query = query.join(Client, Project.client_id == Client.id)
            client_joined = True

        # Filter by client name
        if client_name:
            query = query.filter(Client.name == client_name)

        # Filter by client ID
        if client_id:
            query = query.filter(Client.id == client_id)

        # Subcontractor scope: restrict to assigned clients
        if scope_client_ids is not None:
            if not scope_client_ids:
                query = query.filter(Project.id.in_([]))  # no access
            else:
                query = query.filter(Project.client_id.in_(scope_client_ids))

        # Filter by client custom fields
        if client_custom_field:
            # Ensure Client is joined
            if not client_joined:
                query = query.join(Client, Project.client_id == Client.id)
            
            # Determine database type for custom field filtering
            is_postgres = False
            try:
                from sqlalchemy import inspect
                engine = db.engine
                is_postgres = 'postgresql' in str(engine.url).lower()
            except Exception:
                pass

            # Build custom field filter conditions
            custom_field_conditions = []
            for field_key, field_value in client_custom_field.items():
                if not field_key or not field_value:
                    continue
                
                if is_postgres:
                    # PostgreSQL: Use JSONB operators
                    try:
                        from sqlalchemy import cast, String
                        # Match exact value in custom_fields JSONB
                        custom_field_conditions.append(
                            db.cast(Client.custom_fields[field_key].astext, String) == str(field_value)
                        )
                    except Exception:
                        # Fallback to Python filtering if JSONB fails
                        pass
                else:
                    # SQLite: Will filter in Python after query
                    pass
            
            if custom_field_conditions:
                query = query.filter(db.or_(*custom_field_conditions))

        # Search filter - must be applied after any joins
        if search:
            search = search.strip()
            if search:
                like = f"%{search}%"
                # Use ilike for case-insensitive search on name and description
                # Handle NULL descriptions properly
                search_filter = db.or_(
                    Project.name.ilike(like),
                    db.and_(Project.description.isnot(None), Project.description.ilike(like))
                )
                query = query.filter(search_filter)

        # Order and paginate
        query = query.order_by(Project.name)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        projects = pagination.items

        # For SQLite or if JSONB filtering didn't work, filter by custom fields in Python
        if client_custom_field and not is_postgres:
            try:
                filtered_projects = []
                for project in projects:
                    if not project.client_obj:
                        continue
                    
                    # Check if client matches all custom field filters
                    matches = True
                    for field_key, field_value in client_custom_field.items():
                        if not field_key or not field_value:
                            continue
                        
                        client_value = project.client_obj.custom_fields.get(field_key) if project.client_obj.custom_fields else None
                        if str(client_value) != str(field_value):
                            matches = False
                            break
                    
                    if matches:
                        filtered_projects.append(project)
                
                # Update pagination with filtered results
                # Note: This affects pagination accuracy, but is necessary for SQLite
                projects = filtered_projects
                # Recalculate pagination manually
                total = len(filtered_projects)
                start = (page - 1) * per_page
                end = start + per_page
                projects = filtered_projects[start:end]
                
                # Create a pagination-like object
                from flask_sqlalchemy import Pagination
                pagination = Pagination(
                    query=None,
                    page=page,
                    per_page=per_page,
                    total=total,
                    items=projects
                )
            except Exception:
                # If filtering fails, use original results
                pass

        return {"projects": projects, "pagination": pagination, "total": pagination.total}

    def get_project_view_data(
        self, project_id: int, time_entries_page: int = 1, time_entries_per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Get all data needed for project view page.
        Uses eager loading to prevent N+1 queries.

        Returns:
            dict with 'project', 'time_entries_pagination', 'tasks', 'comments',
            'recent_costs', 'total_costs_count', 'user_totals', 'kanban_columns'
        """
        from sqlalchemy.orm import joinedload
        from app.models import Task, Comment, ProjectCost, KanbanColumn
        from app.repositories import TimeEntryRepository

        # Get project with eager loading
        project = self.get_project_with_details(
            project_id=project_id,
            include_time_entries=True,
            include_tasks=True,
            include_comments=True,
            include_costs=True,
        )

        if not project:
            return {"success": False, "message": "Project not found", "error": "not_found"}

        # Get time entries with pagination and eager loading
        time_entry_repo = TimeEntryRepository()
        entries_query = (
            time_entry_repo.query()
            .filter(TimeEntry.project_id == project_id, TimeEntry.end_time.isnot(None))
            .options(joinedload(TimeEntry.user), joinedload(TimeEntry.task))
            .order_by(TimeEntry.start_time.desc())
        )

        entries_pagination = entries_query.paginate(
            page=time_entries_page, per_page=time_entries_per_page, error_out=False
        )

        # Get tasks with eager loading (already loaded but need to order)
        tasks = (
            Task.query.filter_by(project_id=project_id)
            .options(joinedload(Task.assigned_user))
            .order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc())
            .all()
        )

        # Get comments (already loaded via relationship)
        from app.models import Comment

        comments = Comment.get_project_comments(project_id, include_replies=True)

        # Get recent costs (already loaded but need to order)
        recent_costs = (
            ProjectCost.query.filter_by(project_id=project_id).order_by(ProjectCost.cost_date.desc()).limit(5).all()
        )

        # Get total cost count
        total_costs_count = ProjectCost.query.filter_by(project_id=project_id).count()

        # Get user totals
        user_totals = project.get_user_totals()

        # Get kanban columns
        kanban_columns = []
        if KanbanColumn:
            kanban_columns = KanbanColumn.get_active_columns(project_id=project_id)
            if not kanban_columns:
                kanban_columns = KanbanColumn.get_active_columns(project_id=None)
                if not kanban_columns:
                    KanbanColumn.initialize_default_columns(project_id=None)
                    kanban_columns = KanbanColumn.get_active_columns(project_id=None)

        return {
            "success": True,
            "project": project,
            "time_entries_pagination": entries_pagination,
            "tasks": tasks,
            "comments": comments,
            "recent_costs": recent_costs,
            "total_costs_count": total_costs_count,
            "user_totals": user_totals,
            "kanban_columns": kanban_columns,
        }
