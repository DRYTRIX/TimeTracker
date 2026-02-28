import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, Response, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
import app as app_module
from app import db
from app.models import Task, Project, User, TimeEntry, TaskActivity, KanbanColumn, Activity
from datetime import datetime, date
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.timezone import now_in_app_timezone, convert_app_datetime_to_user
from app.utils.pagination import get_pagination_params
import csv
import io

tasks_bp = Blueprint("tasks", __name__)

ALLOWED_NEXT_PREFIXES = ("/kanban", "/gantt", "/tasks", "/projects")


def _is_safe_next_url(next_url):
    """Validate next URL to avoid open redirects. Allow relative paths with allowed prefixes."""
    if not next_url or not isinstance(next_url, str):
        return False
    next_url = next_url.strip()
    if not next_url.startswith("/") or next_url.startswith("//"):
        return False
    return any(next_url == p or next_url.startswith(p + "?") or next_url.startswith(p + "#") for p in ALLOWED_NEXT_PREFIXES)


@tasks_bp.route("/tasks")
@login_required
def list_tasks():
    """List all tasks with filtering options - REFACTORED to use service layer with eager loading (supports multi-select)"""
    from app.services import TaskService

    # Get pagination parameters from request (respects per_page query param, defaults to DEFAULT_PAGE_SIZE)
    page, per_page = get_pagination_params()
    
    # Parse filter parameters - support both single ID (backward compatibility) and multi-select
    def parse_ids(param_name):
        """Parse comma-separated IDs or single ID into a list of integers"""
        # Try multi-select parameter first (e.g., project_ids)
        multi_param = request.args.get(param_name + 's', '').strip()
        if multi_param:
            try:
                return [int(x.strip()) for x in multi_param.split(',') if x.strip()]
            except (ValueError, AttributeError):
                return []
        # Fall back to single parameter for backward compatibility (e.g., project_id)
        single_param = request.args.get(param_name, type=int)
        if single_param:
            return [single_param]
        return []
    
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    project_ids = parse_ids('project_id')
    assigned_to_ids = parse_ids('assigned_to')
    search = request.args.get("search", "").strip()
    tags = request.args.get("tags", "").strip()
    overdue_param = request.args.get("overdue", "").strip().lower()
    overdue = overdue_param in ["1", "true", "on", "yes"]

    # Check if this is an AJAX request first (before loading filter data)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    # Use service layer to get tasks (prevents N+1 queries)
    task_service = TaskService()
    
    # Optimize permission check - check is_admin first (no DB query needed)
    has_view_all_tasks = current_user.is_admin
    if not has_view_all_tasks:
        # Only check permission if not admin (roles are already loaded via lazy="joined")
        has_view_all_tasks = current_user.has_permission("view_all_tasks")
    
    result = task_service.list_tasks(
        status=status if status else None,
        priority=priority if priority else None,
        project_ids=project_ids if project_ids else None,
        assigned_to_ids=assigned_to_ids if assigned_to_ids else None,
        search=search if search else None,
        tags=tags if tags else None,
        overdue=overdue,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        has_view_all_tasks=has_view_all_tasks,
        page=page,
        per_page=per_page,
    )

    # Check if this is an AJAX request
    if is_ajax:
        # Return only the tasks list HTML for AJAX requests
        response = make_response(render_template(
            "tasks/_tasks_list.html",
            tasks=result["tasks"],
            pagination=result["pagination"],
            status=status,
            priority=priority,
            project_ids=project_ids,
            assigned_to_ids=assigned_to_ids,
            # Keep old single params for backward compatibility
            project_id=project_ids[0] if len(project_ids) == 1 else None,
            assigned_to=assigned_to_ids[0] if len(assigned_to_ids) == 1 else None,
            search=search,
            tags=tags,
            overdue=overdue,
        ))
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    # Get filter options - only load for full page loads, not AJAX requests
    # These are used for filter dropdowns in the template
    # Use reasonable limits to avoid loading too many records
    projects = Project.query.filter_by(status="active").order_by(Project.name).limit(500).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).limit(200).all()
    
    # Kanban columns are already loaded in TaskService, but we need them for the template
    # This is a lightweight query, so it's acceptable
    kanban_columns = KanbanColumn.get_active_columns(project_id=None) if KanbanColumn else []

    # Pre-calculate task counts by status for summary cards (avoid template iteration)
    task_counts = {
        'todo': 0,
        'in_progress': 0,
        'review': 0,
        'done': 0
    }
    for task in result["tasks"]:
        if task.status in task_counts:
            task_counts[task.status] += 1

    # Prevent browser caching of kanban board
    response = render_template(
        "tasks/list.html",
        tasks=result["tasks"],
        pagination=result["pagination"],
        projects=projects,
        users=users,
        kanban_columns=kanban_columns,
        status=status,
        priority=priority,
        project_ids=project_ids,
        assigned_to_ids=assigned_to_ids,
        # Keep old single params for backward compatibility
        project_id=project_ids[0] if len(project_ids) == 1 else None,
        assigned_to=assigned_to_ids[0] if len(assigned_to_ids) == 1 else None,
        search=search,
        tags=tags,
        overdue=overdue,
        task_counts=task_counts,
    )
    resp = make_response(response)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@tasks_bp.route("/tasks/create", methods=["GET", "POST"])
@login_required
def create_task():
    """Create a new task"""
    if request.method == "POST":
        project_id = request.form.get("project_id", type=int)
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        estimated_hours_str = request.form.get("estimated_hours", "").strip()
        due_date_str = request.form.get("due_date", "").strip()
        assigned_to = request.form.get("assigned_to", type=int)

        # Validate and sanitize input
        from app.utils.validation import validate_string, sanitize_input
        
        # Validate required fields
        if not project_id or not name:
            flash(_("Project and task name are required"), "error")
            projects = Project.query.filter_by(status="active").order_by(Project.name).all()
            users = User.query.order_by(User.username).all()
            return render_template("tasks/create.html", projects=projects, users=users)

        # Sanitize and validate name
        try:
            name = validate_string(sanitize_input(name), min_length=1, max_length=200)
        except Exception as e:
            flash(_("Invalid task name: %(error)s", error=str(e)), "error")
            projects = Project.query.filter_by(status="active").order_by(Project.name).all()
            users = User.query.order_by(User.username).all()
            return render_template("tasks/create.html", projects=projects, users=users)

        # Validate project exists
        project = Project.query.get(project_id)
        if not project:
            flash(_("Selected project does not exist"), "error")
            projects = Project.query.filter_by(status="active").order_by(Project.name).all()
            users = User.query.order_by(User.username).all()
            return render_template("tasks/create.html", projects=projects, users=users)

        # Validate priority
        if priority not in ["low", "medium", "high", "urgent"]:
            priority = "medium"

        # Validate initial status
        status = request.form.get("status", "todo").strip()
        if status not in ("todo", "in_progress", "review", "done", "cancelled"):
            status = "todo"

        # Parse estimated hours
        estimated_hours = None
        if estimated_hours_str:
            try:
                estimated_hours = float(estimated_hours_str)
                if estimated_hours < 0:
                    estimated_hours = None
            except (ValueError, TypeError):
                estimated_hours = None

        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash(_("Invalid due date format"), "error")
                projects = Project.query.filter_by(status="active").order_by(Project.name).all()
                users = User.query.order_by(User.username).all()
                return render_template("tasks/create.html", projects=projects, users=users)

        # Gantt color (hex e.g. #3b82f6)
        color_val = request.form.get("color", "").strip()
        if color_val and not re.match(r"^#[0-9A-Fa-f]{6}$", color_val):
            color_val = None
        if color_val == "":
            color_val = None

        # Tags (comma-separated, max 500 chars)
        tags_val = request.form.get("tags", "").strip()[:500] or None

        # Use service layer to create task
        from app.services import TaskService

        task_service = TaskService()

        result = task_service.create_task(
            name=name,
            project_id=project_id,
            description=description,
            assignee_id=assigned_to,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            created_by=current_user.id,
            color=color_val,
            status=status,
            tags=tags_val,
        )

        if not result["success"]:
            flash(_(result["message"]), "error")
            projects = Project.query.filter_by(status="active").order_by(Project.name).all()
            users = User.query.order_by(User.username).all()
            return render_template("tasks/create.html", projects=projects, users=users)

        task = result["task"]

        # Log task creation
        app_module.log_event(
            "task.created", user_id=current_user.id, task_id=task.id, project_id=project_id, priority=priority
        )
        app_module.track_event(
            current_user.id, "task.created", {"task_id": task.id, "project_id": project_id, "priority": priority}
        )

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="created",
            entity_type="task",
            entity_id=task.id,
            entity_name=task.name,
            description=f'Created task "{task.name}" in project "{project.name}"',
            extra_data={"project_id": project_id, "priority": priority},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        flash(f'Task "{name}" created successfully', "success")
        next_url = request.form.get("next") or request.args.get("next")
        if next_url and _is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Get available projects and users for form
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    users = User.query.order_by(User.username).all()

    return render_template("tasks/create.html", projects=projects, users=users)


@tasks_bp.route("/tasks/<int:task_id>")
@login_required
def view_task(task_id):
    """View task details - REFACTORED to use service layer with eager loading"""
    from app.services import TaskService
    from sqlalchemy.orm import joinedload
    from app.models import Comment

    task_service = TaskService()

    # Get task with all relations using eager loading (prevents N+1 queries)
    task = task_service.get_task_with_details(
        task_id=task_id, include_time_entries=False, include_comments=False, include_activities=False
    )

    if not task:
        flash(_("Task not found"), "error")
        return redirect(url_for("tasks.list_tasks"))

    # Check if user has access to this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        flash(_("You do not have access to this task"), "error")
        return redirect(url_for("tasks.list_tasks"))

    # Get time entries with pagination (limit to 100 most recent to avoid loading too many)
    # Eagerly load user relationship to prevent N+1 queries
    time_entries = (
        task.time_entries.options(joinedload(TimeEntry.user))
        .order_by(TimeEntry.start_time.desc(), TimeEntry.id.desc())
        .limit(100)
        .all()
    )

    # Recent activity entries (activities is a dynamic relationship, so query it)
    # Eagerly load user relationship to prevent N+1 queries
    activities = (
        task.activities.options(joinedload(TaskActivity.user))
        .order_by(TaskActivity.created_at.desc(), TaskActivity.id.desc())
        .limit(20)
        .all()
    )

    # Get comments for this task with eager loading of authors and replies to prevent N+1 queries
    # Load all comments (including replies) with their authors to avoid lazy loading issues
    # Use selectinload for replies to load them in a separate query, preventing circular loading
    from sqlalchemy.orm import selectinload
    
    # Load all comments for this task with eager loading
    all_comments = (
        Comment.query.filter_by(task_id=task_id)
        .options(
            joinedload(Comment.author),  # Eagerly load author for all comments
            # Load replies with their authors - selectinload loads all direct replies in one query
            # This prevents N+1 queries when accessing comment.replies in the template
            selectinload(Comment.replies).joinedload(Comment.author),
            # Note: Comment.attachments is a dynamic relationship (lazy="dynamic")
            # and cannot be eager loaded with selectinload/joinedload
        )
        .order_by(Comment.created_at.asc())
        .all()
    )
    
    # Filter to only top-level comments (no parent_id) for the template
    # The replies relationship is now eagerly loaded for direct replies
    # Nested replies beyond the first level will be loaded lazily, but the template depth limit prevents issues
    comments = [c for c in all_comments if c.parent_id is None]

    return render_template(
        "tasks/view.html", task=task, time_entries=time_entries, activities=activities, comments=comments
    )


@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    """Edit task details"""
    task = Task.query.get_or_404(task_id)

    # Check if user can edit this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash(_("You can only edit tasks you created"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    if request.method == "POST":
        # Preload context for potential validation errors
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        users = User.query.order_by(User.username).all()
        project_id = request.form.get("project_id", type=int)
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        estimated_hours_str = request.form.get("estimated_hours", "").strip()
        due_date_str = request.form.get("due_date", "").strip()
        assigned_to = request.form.get("assigned_to", type=int)

        # Validate and sanitize input
        from app.utils.validation import validate_string, sanitize_input

        # Validate required fields
        if not name:
            flash(_("Task name is required"), "error")
            return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Sanitize and validate name
        try:
            name = validate_string(sanitize_input(name), min_length=1, max_length=200)
        except Exception as e:
            flash(_("Invalid task name: %(error)s", error=str(e)), "error")
            return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Sanitize description
        if description:
            try:
                description = sanitize_input(description, max_length=5000)
            except Exception:
                description = sanitize_input(description[:5000] if len(description) > 5000 else description)

        # Validate project selection
        if not project_id:
            flash(_("Project is required"), "error")
            return render_template("tasks/edit.html", task=task, projects=projects, users=users)
        new_project = Project.query.filter_by(id=project_id, status="active").first()
        if not new_project:
            flash(_("Selected project does not exist or is inactive"), "error")
            return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Validate priority
        if priority not in ["low", "medium", "high", "urgent"]:
            priority = task.priority or "medium"

        # Parse estimated hours
        estimated_hours = None
        if estimated_hours_str:
            try:
                estimated_hours = float(estimated_hours_str)
                if estimated_hours < 0:
                    estimated_hours = None
            except (ValueError, TypeError):
                estimated_hours = None

        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash(_("Invalid due date format"), "error")
                return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Update task
        # Handle project change first so any early returns (status flows) still persist it
        if project_id != task.project_id:
            old_project_id = task.project_id
            task.project_id = project_id
            # Keep related time entries consistent with the task's project
            try:
                TimeEntry.query.filter_by(task_id=task.id).update(
                    {"project_id": project_id}, synchronize_session="fetch"
                )
                db.session.add(
                    TaskActivity(
                        task_id=task.id,
                        user_id=current_user.id,
                        event="project_change",
                        details=f"Project changed from {old_project_id} to {project_id}",
                    )
                )
            except Exception as e:
                # If anything goes wrong here, fall back to just changing the task
                current_app.logger.warning(f"Failed to log task project change activity: {e}")

        task.name = name
        task.description = description
        task.priority = priority
        task.estimated_hours = estimated_hours
        task.due_date = due_date
        task.assigned_to = assigned_to
        # Tags (comma-separated, max 500 chars)
        tags_val = request.form.get("tags", "").strip()[:500]
        task.tags = tags_val or None
        # Gantt color (hex e.g. #3b82f6)
        color_val = request.form.get("color", "").strip()
        if color_val and re.match(r"^#[0-9A-Fa-f]{6}$", color_val):
            task.color = color_val
        elif color_val == "":
            task.color = None
        # Handle status update (including reopening from done)
        selected_status = request.form.get("status", "").strip()
        valid_statuses = KanbanColumn.get_valid_status_keys(project_id=task.project_id)
        if selected_status and selected_status in valid_statuses and selected_status != task.status:
            try:
                previous_status = task.status
                if selected_status == "in_progress":
                    # If reopening from done, preserve started_at
                    if task.status == "done":
                        task.completed_at = None
                        task.status = "in_progress"
                        if not task.started_at:
                            task.started_at = now_in_app_timezone()
                        task.updated_at = now_in_app_timezone()
                        db.session.add(
                            TaskActivity(
                                task_id=task.id,
                                user_id=current_user.id,
                                event="reopen",
                                details="Task reopened to In Progress",
                            )
                        )
                        if not safe_commit("edit_task_reopen_in_progress", {"task_id": task.id}):
                            flash(
                                _("Could not update status due to a database error. Please check server logs."), "error"
                            )
                        return render_template("tasks/edit.html", task=task, projects=projects, users=users)
                    else:
                        task.start_task()
                        db.session.add(
                            TaskActivity(
                                task_id=task.id,
                                user_id=current_user.id,
                                event="start",
                                details=f"Task moved from {previous_status} to In Progress",
                            )
                        )
                        safe_commit("log_task_start_from_edit", {"task_id": task.id})
                elif selected_status == "done":
                    task.complete_task()
                    db.session.add(
                        TaskActivity(
                            task_id=task.id, user_id=current_user.id, event="complete", details="Task completed"
                        )
                    )
                    safe_commit("log_task_complete_from_edit", {"task_id": task.id})
                elif selected_status == "cancelled":
                    task.cancel_task()
                    db.session.add(
                        TaskActivity(task_id=task.id, user_id=current_user.id, event="cancel", details="Task cancelled")
                    )
                    safe_commit("log_task_cancel_from_edit", {"task_id": task.id})
                else:
                    # Reopen or move to non-special states
                    # Clear completed_at if reopening from done
                    if task.status == "done" and selected_status in ["todo", "review"]:
                        task.completed_at = None
                    task.status = selected_status
                    task.updated_at = now_in_app_timezone()
                    event_name = (
                        "reopen"
                        if previous_status == "done" and selected_status in ["todo", "review"]
                        else (
                            "pause"
                            if selected_status == "todo"
                            else ("review" if selected_status == "review" else "status_change")
                        )
                    )
                    db.session.add(
                        TaskActivity(
                            task_id=task.id,
                            user_id=current_user.id,
                            event=event_name,
                            details=f"Task moved from {previous_status} to {selected_status}",
                        )
                    )
                    if not safe_commit("edit_task_status_change", {"task_id": task.id, "status": selected_status}):
                        flash("Could not update status due to a database error. Please check server logs.", "error")
                        return render_template("tasks/edit.html", task=task, projects=projects, users=users)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Always update the updated_at timestamp to local time after edits
        task.updated_at = now_in_app_timezone()

        if not safe_commit("edit_task", {"task_id": task.id}):
            flash(_("Could not update task due to a database error. Please check server logs."), "error")
            return render_template("tasks/edit.html", task=task, projects=projects, users=users)

        # Log task update
        app_module.log_event("task.updated", user_id=current_user.id, task_id=task.id, project_id=task.project_id)
        app_module.track_event(current_user.id, "task.updated", {"task_id": task.id, "project_id": task.project_id})

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="updated",
            entity_type="task",
            entity_id=task.id,
            entity_name=task.name,
            description=f'Updated task "{task.name}"',
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        flash(f'Task "{name}" updated successfully', "success")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Get available projects and users for form
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    users = User.query.order_by(User.username).all()

    return render_template("tasks/edit.html", task=task, projects=projects, users=users)


@tasks_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id):
    """Update task status"""
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get("status", "").strip()

    # Check if user can update this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        flash(_("You do not have permission to update this task"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Validate status against configured kanban columns for this task's project
    valid_statuses = KanbanColumn.get_valid_status_keys(project_id=task.project_id)
    if new_status not in valid_statuses:
        flash(_("Invalid status"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Update status
    try:
        if new_status == "in_progress":
            # If reopening from done, bypass start_task restriction
            if task.status == "done":
                task.completed_at = None
                task.status = "in_progress"
                # Preserve existing started_at if present, otherwise set now
                if not task.started_at:
                    task.started_at = now_in_app_timezone()
                task.updated_at = now_in_app_timezone()
                db.session.add(
                    TaskActivity(
                        task_id=task.id, user_id=current_user.id, event="reopen", details="Task reopened to In Progress"
                    )
                )
                if not safe_commit("update_task_status_reopen_in_progress", {"task_id": task.id, "status": new_status}):
                    flash("Could not update status due to a database error. Please check server logs.", "error")
                    return redirect(url_for("tasks.view_task", task_id=task.id))
            else:
                previous_status = task.status
                task.start_task()
                db.session.add(
                    TaskActivity(
                        task_id=task.id,
                        user_id=current_user.id,
                        event="start",
                        details=f"Task moved from {previous_status} to In Progress",
                    )
                )
                safe_commit("log_task_start", {"task_id": task.id})
        elif new_status == "done":
            task.complete_task()
            db.session.add(
                TaskActivity(task_id=task.id, user_id=current_user.id, event="complete", details="Task completed")
            )
            safe_commit("log_task_complete", {"task_id": task.id})
        elif new_status == "cancelled":
            task.cancel_task()
            db.session.add(
                TaskActivity(task_id=task.id, user_id=current_user.id, event="cancel", details="Task cancelled")
            )
            safe_commit("log_task_cancel", {"task_id": task.id})
        else:
            # For other transitions, handle reopening from done and local timestamps
            if task.status == "done" and new_status in ["todo", "review"]:
                task.completed_at = None
            previous_status = task.status
            task.status = new_status
            task.updated_at = now_in_app_timezone()
            # Log pause or review or generic change
            if previous_status == "done" and new_status in ["todo", "review"]:
                event_name = "reopen"
            else:
                event_map = {
                    "todo": "pause",
                    "review": "review",
                }
                event_name = event_map.get(new_status, "status_change")
            db.session.add(
                TaskActivity(
                    task_id=task.id,
                    user_id=current_user.id,
                    event=event_name,
                    details=f"Task moved from {previous_status} to {new_status}",
                )
            )
            if not safe_commit("update_task_status", {"task_id": task.id, "status": new_status}):
                flash("Could not update status due to a database error. Please check server logs.", "error")
                return redirect(url_for("tasks.view_task", task_id=task.id))

            # Log task status change
            app_module.log_event(
                "task.status_changed",
                user_id=current_user.id,
                task_id=task.id,
                old_status=previous_status,
                new_status=new_status,
            )
            app_module.track_event(
                current_user.id,
                "task.status_changed",
                {"task_id": task.id, "old_status": previous_status, "new_status": new_status},
            )

        flash(f"Task status updated to {task.status_display}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("tasks.view_task", task_id=task.id))


@tasks_bp.route("/tasks/<int:task_id>/priority", methods=["POST"])
@login_required
def update_task_priority(task_id):
    """Update task priority"""
    task = Task.query.get_or_404(task_id)
    new_priority = request.form.get("priority", "").strip()

    # Check if user can update this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash(_("You can only update tasks you created"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    try:
        task.update_priority(new_priority)
        flash(f"Task priority updated to {task.priority_display}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("tasks.view_task", task_id=task.id))


@tasks_bp.route("/tasks/<int:task_id>/assign", methods=["POST"])
@login_required
def assign_task(task_id):
    """Assign task to a user"""
    task = Task.query.get_or_404(task_id)
    user_id = request.form.get("user_id", type=int)

    # Check if user can assign this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash(_("You can only assign tasks you created"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    if user_id:
        user = User.query.get(user_id)
        if not user:
            flash(_("Selected user does not exist"), "error")
            return redirect(url_for("tasks.view_task", task_id=task.id))

    task.reassign(user_id)
    if user_id:
        flash(f"Task assigned to {user.username}", "success")
    else:
        flash(_("Task unassigned"), "success")

    return redirect(url_for("tasks.view_task", task_id=task.id))


@tasks_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)

    # Check if user can delete this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash(_("You can only delete tasks you created"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Check if task has time entries
    if task.time_entries.count() > 0:
        flash(_("Cannot delete task with existing time entries"), "error")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    task_name = task.name
    task_id_for_log = task.id
    project_id_for_log = task.project_id

    # Log activity before deletion
    Activity.log(
        user_id=current_user.id,
        action="deleted",
        entity_type="task",
        entity_id=task_id_for_log,
        entity_name=task_name,
        description=f'Deleted task "{task_name}"',
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    db.session.delete(task)
    if not safe_commit("delete_task", {"task_id": task_id_for_log}):
        flash(_("Could not delete task due to a database error. Please check server logs."), "error")
        return redirect(url_for("tasks.view_task", task_id=task_id_for_log))

    # Log task deletion
    app_module.log_event(
        "task.deleted", user_id=current_user.id, task_id=task_id_for_log, project_id=project_id_for_log
    )
    app_module.track_event(
        current_user.id, "task.deleted", {"task_id": task_id_for_log, "project_id": project_id_for_log}
    )

    flash(f'Task "{task_name}" deleted successfully', "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_tasks():
    """Delete multiple tasks at once"""
    task_ids = request.form.getlist("task_ids[]")

    if not task_ids:
        flash(_("No tasks selected for deletion"), "warning")
        return redirect(url_for("tasks.list_tasks"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    # Use eager loading to prevent N+1 queries when checking time entries
    from sqlalchemy.orm import joinedload
    
    for task_id_str in task_ids:
        try:
            task_id = int(task_id_str)
            # Use get_or_404 for better error handling, but catch 404 for bulk operations
            try:
                task = Task.query.options(joinedload(Task.project)).get(task_id)
            except Exception:
                task = None

            if not task:
                continue

            # Check permissions
            if not current_user.is_admin and task.created_by != current_user.id:
                skipped_count += 1
                errors.append(f"'{task.name}': No permission")
                continue

            # Check for time entries - use exists() for better performance
            from app.models import TimeEntry
            from sqlalchemy import exists
            has_time_entries = db.session.query(
                exists().where(TimeEntry.task_id == task_id)
            ).scalar()
            if has_time_entries:
                skipped_count += 1
                errors.append(f"'{task.name}': Has time entries")
                continue

            # Delete the task
            task_id_for_log = task.id
            project_id_for_log = task.project_id
            task_name = task.name

            db.session.delete(task)
            deleted_count += 1

            # Log the deletion
            app_module.log_event(
                "task.deleted", user_id=current_user.id, task_id=task_id_for_log, project_id=project_id_for_log
            )
            app_module.track_event(
                current_user.id, "task.deleted", {"task_id": task_id_for_log, "project_id": project_id_for_log}
            )

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {task_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit("bulk_delete_tasks", {"count": deleted_count}):
            flash(_("Could not delete tasks due to a database error. Please check server logs."), "error")
            return redirect(url_for("tasks.list_tasks"))

    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} task{"s" if deleted_count != 1 else ""}', "success")

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} task{"s" if skipped_count != 1 else ""}: {"; ".join(errors[:3])}', "warning")

    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/bulk-status", methods=["POST"])
@login_required
def bulk_update_status():
    """Update status for multiple tasks at once"""
    task_ids = request.form.getlist("task_ids[]")
    new_status = request.form.get("status", "").strip()

    if not task_ids:
        flash(_("No tasks selected"), "warning")
        return redirect(url_for("tasks.list_tasks"))

    if not new_status:
        flash(_("Invalid status value"), "error")
        return redirect(url_for("tasks.list_tasks"))

    updated_count = 0
    skipped_count = 0

    for task_id_str in task_ids:
        try:
            task_id = int(task_id_str)
            task = Task.query.get(task_id)

            if not task:
                continue

            # Validate status against configured kanban columns for this task's project
            valid_statuses = set(
                KanbanColumn.get_valid_status_keys(project_id=task.project_id)
                if KanbanColumn
                else ["todo", "in_progress", "review", "done", "cancelled"]
            )
            if new_status not in valid_statuses:
                skipped_count += 1
                continue

            if not task:
                continue

            # Check permissions
            if not current_user.is_admin and task.created_by != current_user.id:
                skipped_count += 1
                continue

            # Handle reopening from done if needed
            if task.status == "done" and new_status in ["todo", "review", "in_progress"]:
                task.completed_at = None
            task.status = new_status
            task.updated_at = now_in_app_timezone()
            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_update_task_status", {"count": updated_count, "status": new_status}):
            flash(_("Could not update tasks due to a database error"), "error")
            return redirect(url_for("tasks.list_tasks"))

        flash(
            f'Successfully updated {updated_count} task{"s" if updated_count != 1 else ""} to {new_status}', "success"
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} task{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/bulk-priority", methods=["POST"])
@login_required
def bulk_update_priority():
    """Update priority for multiple tasks at once"""
    task_ids = request.form.getlist("task_ids[]")
    new_priority = request.form.get("priority", "").strip()

    if not task_ids:
        flash(_("No tasks selected"), "warning")
        return redirect(url_for("tasks.list_tasks"))

    if not new_priority or new_priority not in ["low", "medium", "high", "urgent"]:
        flash(_("Invalid priority value"), "error")
        return redirect(url_for("tasks.list_tasks"))

    updated_count = 0
    skipped_count = 0

    for task_id_str in task_ids:
        try:
            task_id = int(task_id_str)
            task = Task.query.get(task_id)

            if not task:
                continue

            # Check permissions
            if not current_user.is_admin and task.created_by != current_user.id:
                skipped_count += 1
                continue

            task.priority = new_priority
            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_update_task_priority", {"count": updated_count, "priority": new_priority}):
            flash(_("Could not update tasks due to a database error"), "error")
            return redirect(url_for("tasks.list_tasks"))

        flash(
            f'Successfully updated {updated_count} task{"s" if updated_count != 1 else ""} to {new_priority} priority',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} task{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/bulk-assign", methods=["POST"])
@login_required
def bulk_assign_tasks():
    """Assign multiple tasks to a user"""
    task_ids = request.form.getlist("task_ids[]")
    assigned_to = request.form.get("assigned_to", type=int)

    if not task_ids:
        flash(_("No tasks selected"), "warning")
        return redirect(url_for("tasks.list_tasks"))

    if not assigned_to:
        flash(_("No user selected for assignment"), "error")
        return redirect(url_for("tasks.list_tasks"))

    # Verify user exists
    user = User.query.get(assigned_to)
    if not user:
        flash(_("Invalid user selected"), "error")
        return redirect(url_for("tasks.list_tasks"))

    updated_count = 0
    skipped_count = 0

    for task_id_str in task_ids:
        try:
            task_id = int(task_id_str)
            task = Task.query.get(task_id)

            if not task:
                continue

            # Check permissions
            if not current_user.is_admin and task.created_by != current_user.id:
                skipped_count += 1
                continue

            task.assigned_to = assigned_to
            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_assign_tasks", {"count": updated_count, "assigned_to": assigned_to}):
            flash(_("Could not assign tasks due to a database error"), "error")
            return redirect(url_for("tasks.list_tasks"))

        flash(
            f'Successfully assigned {updated_count} task{"s" if updated_count != 1 else ""} to {user.display_name}',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} task{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/bulk-move-project", methods=["POST"])
@login_required
def bulk_move_project():
    """Move multiple tasks to a different project"""
    task_ids = request.form.getlist("task_ids[]")
    new_project_id = request.form.get("project_id", type=int)

    if not task_ids:
        flash(_("No tasks selected"), "warning")
        return redirect(url_for("tasks.list_tasks"))

    if not new_project_id:
        flash(_("No project selected"), "error")
        return redirect(url_for("tasks.list_tasks"))

    # Verify project exists and is active
    new_project = Project.query.filter_by(id=new_project_id, status="active").first()
    if not new_project:
        flash(_("Invalid project selected"), "error")
        return redirect(url_for("tasks.list_tasks"))

    updated_count = 0
    skipped_count = 0

    for task_id_str in task_ids:
        try:
            task_id = int(task_id_str)
            task = Task.query.get(task_id)

            if not task:
                continue

            # Check permissions
            if not current_user.is_admin and task.created_by != current_user.id:
                skipped_count += 1
                continue

            # Update task project
            old_project_id = task.project_id
            task.project_id = new_project_id

            # Batch-update related time entries to match the new project
            TimeEntry.query.filter_by(task_id=task.id).update(
                {"project_id": new_project_id}, synchronize_session="fetch"
            )

            # Log activity
            db.session.add(
                TaskActivity(
                    task_id=task.id,
                    user_id=current_user.id,
                    event="project_change",
                    details=f"Project changed from {old_project_id} to {new_project_id}",
                )
            )

            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_move_project", {"count": updated_count, "project_id": new_project_id}):
            flash(_("Could not move tasks due to a database error"), "error")
            return redirect(url_for("tasks.list_tasks"))

        flash(
            f'Successfully moved {updated_count} task{"s" if updated_count != 1 else ""} to {new_project.name}',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} task{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/tasks/export")
@login_required
def export_tasks():
    """Export tasks to CSV (supports same filters as list view, including multi-select)"""
    # Parse filter parameters - same logic as list_tasks (multi-select + backward compat)
    def parse_ids(param_name):
        multi_param = request.args.get(param_name + "s", "").strip()
        if multi_param:
            try:
                return [int(x.strip()) for x in multi_param.split(",") if x.strip()]
            except (ValueError, AttributeError):
                return []
        single_param = request.args.get(param_name, type=int)
        if single_param:
            return [single_param]
        return []

    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    project_ids = parse_ids("project_id")
    assigned_to_ids = parse_ids("assigned_to")
    search = request.args.get("search", "").strip()
    tags = request.args.get("tags", "").strip()
    overdue_param = request.args.get("overdue", "").strip().lower()
    overdue = overdue_param in ["1", "true", "on", "yes"]

    query = Task.query

    # Apply filters (same as list_tasks)
    if status:
        query = query.filter_by(status=status)

    if priority:
        query = query.filter_by(priority=priority)

    if project_ids:
        query = query.filter(Task.project_id.in_(project_ids))

    if assigned_to_ids:
        query = query.filter(Task.assigned_to.in_(assigned_to_ids))

    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Task.name.ilike(like), Task.description.ilike(like)))

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            tag_conditions = [Task.tags.ilike(f"%{tag}%") for tag in tag_list]
            query = query.filter(db.or_(*tag_conditions))

    # Overdue filter
    if overdue:
        today_local = now_in_app_timezone().date()
        query = query.filter(Task.due_date < today_local, Task.status.in_(["todo", "in_progress", "review"]))

    # Permission filter - users without view_all_tasks permission only see their tasks
    has_view_all_tasks = current_user.is_admin or current_user.has_permission("view_all_tasks")
    if not has_view_all_tasks:
        query = query.filter(db.or_(Task.assigned_to == current_user.id, Task.created_by == current_user.id))

    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "ID",
            "Name",
            "Description",
            "Project",
            "Status",
            "Priority",
            "Tags",
            "Assigned To",
            "Created By",
            "Due Date",
            "Estimated Hours",
            "Created At",
            "Updated At",
        ]
    )

    # Write task data
    for task in tasks:
        writer.writerow(
            [
                task.id,
                task.name,
                task.description or "",
                task.project.name if task.project else "",
                task.status,
                task.priority,
                task.tags or "",
                task.assigned_user.display_name if task.assigned_user else "",
                task.creator.display_name if task.creator else "",
                task.due_date.strftime("%Y-%m-%d") if task.due_date else "",
                task.estimated_hours or "",
                (
                    convert_app_datetime_to_user(task.created_at, user=current_user).strftime("%Y-%m-%d %H:%M:%S")
                    if task.created_at
                    else ""
                ),
                (
                    convert_app_datetime_to_user(task.updated_at, user=current_user).strftime("%Y-%m-%d %H:%M:%S")
                    if task.updated_at
                    else ""
                ),
            ]
        )

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        },
    )


@tasks_bp.route("/tasks/my-tasks")
@login_required
def my_tasks():
    """Show current user's tasks with filters and pagination"""
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    project_id = request.args.get("project_id", type=int)
    search = request.args.get("search", "").strip()
    tags = request.args.get("tags", "").strip()
    task_type = request.args.get("task_type", "")  # '', 'assigned', 'created'
    overdue_param = request.args.get("overdue", "").strip().lower()
    overdue = overdue_param in ["1", "true", "on", "yes"]

    query = Task.query

    # Restrict to current user's tasks depending on task_type filter
    if task_type == "assigned":
        query = query.filter(Task.assigned_to == current_user.id)
    elif task_type == "created":
        query = query.filter(Task.created_by == current_user.id)
    else:
        query = query.filter(db.or_(Task.assigned_to == current_user.id, Task.created_by == current_user.id))

    # Apply filters
    if status:
        query = query.filter_by(status=status)

    if priority:
        query = query.filter_by(priority=priority)

    if project_id:
        query = query.filter_by(project_id=project_id)

    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Task.name.ilike(like), Task.description.ilike(like)))

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            tag_conditions = [Task.tags.ilike(f"%{tag}%") for tag in tag_list]
            query = query.filter(db.or_(*tag_conditions))

    # Overdue filter (uses application's local date)
    if overdue:
        today_local = now_in_app_timezone().date()
        query = query.filter(Task.due_date < today_local, Task.status.in_(["todo", "in_progress", "review"]))

    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Provide projects for filter dropdown
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    # Force fresh kanban columns from database (no cache)
    db.session.expire_all()
    kanban_columns = KanbanColumn.get_active_columns() if KanbanColumn else []

    # Prevent browser caching of kanban board
    response = render_template(
        "tasks/my_tasks.html",
        tasks=tasks.items,
        pagination=tasks,
        projects=projects,
        kanban_columns=kanban_columns,
        status=status,
        priority=priority,
        project_id=project_id,
        search=search,
        tags=tags,
        task_type=task_type,
        overdue=overdue,
    )
    resp = make_response(response)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@tasks_bp.route("/tasks/overdue")
@login_required
def overdue_tasks():
    """Show all overdue tasks"""
    if not current_user.is_admin:
        flash(_("Only administrators can view all overdue tasks"), "error")
        return redirect(url_for("tasks.list_tasks"))

    tasks = Task.get_overdue_tasks()
    kanban_columns = KanbanColumn.get_active_columns() if KanbanColumn else []

    return render_template("tasks/overdue.html", tasks=tasks, kanban_columns=kanban_columns)


@tasks_bp.route("/api/tasks/<int:task_id>")
@login_required
def api_task(task_id):
    """API endpoint to get task details"""
    task = Task.query.get_or_404(task_id)

    # Check if user has access to this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(task.to_dict())


@tasks_bp.route("/api/tasks/<int:task_id>/status", methods=["PUT"])
@login_required
def api_update_status(task_id):
    """API endpoint to update task status"""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    new_status = data.get("status", "").strip()

    # Check if user can update this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    # Validate status against configured kanban columns for this task's project
    valid_statuses = KanbanColumn.get_valid_status_keys(project_id=task.project_id)
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400

    # Update status
    try:
        if new_status == "in_progress":
            if task.status == "done":
                task.completed_at = None
                task.status = "in_progress"
                if not task.started_at:
                    task.started_at = now_in_app_timezone()
                task.updated_at = now_in_app_timezone()
                if not safe_commit(
                    "api_update_task_status_reopen_in_progress", {"task_id": task.id, "status": new_status}
                ):
                    return jsonify({"error": "Database error while updating status"}), 500
            else:
                task.start_task()
        elif new_status == "done":
            task.complete_task()
        elif new_status == "cancelled":
            task.cancel_task()
        else:
            if task.status == "done" and new_status in ["todo", "review"]:
                task.completed_at = None
            task.status = new_status
            task.updated_at = now_in_app_timezone()
            if not safe_commit("api_update_task_status", {"task_id": task.id, "status": new_status}):
                return jsonify({"error": "Database error while updating status"}), 500

        return jsonify({"success": True, "task": task.to_dict()})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
