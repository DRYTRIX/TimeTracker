"""Issue Management Routes

Provides routes for internal users to manage client-reported issues,
link them to tasks, and create tasks from issues.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Issue, Client, Project, Task, User
from app.utils.db import safe_commit
from app.utils.pagination import get_pagination_params
from sqlalchemy import or_

issues_bp = Blueprint("issues", __name__)


@issues_bp.route("/issues")
@login_required
def list_issues():
    """List all issues with filtering options"""
    page, per_page = get_pagination_params()
    
    # Get filter parameters
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    client_id = request.args.get("client_id", type=int)
    project_id = request.args.get("project_id", type=int)
    assigned_to = request.args.get("assigned_to", type=int)
    search = request.args.get("search", "").strip()
    
    # Build query
    query = Issue.query
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if project_id:
        query = query.filter_by(project_id=project_id)
    if assigned_to:
        query = query.filter_by(assigned_to=assigned_to)
    if search:
        query = query.filter(
            or_(
                Issue.title.ilike(f"%{search}%"),
                Issue.description.ilike(f"%{search}%"),
            )
        )
    
    # Check permissions - non-admin users can only see issues for their assigned clients/projects
    if not current_user.is_admin:
        # Get user's accessible client IDs (through projects they have access to)
        # For simplicity, we'll show all issues but filter in template if needed
        # In a real implementation, you'd want to filter by user permissions here
        pass
    
    # Order by priority and creation date
    query = query.order_by(
        Issue.priority.desc(),
        Issue.created_at.desc()
    )
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    issues = pagination.items
    
    # Get filter options
    clients = Client.query.filter_by(status="active").order_by(Client.name).limit(500).all()
    projects = Project.query.filter_by(status="active").order_by(Project.name).limit(500).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).limit(200).all()
    
    # Calculate statistics
    total_issues = Issue.query.count()
    open_issues = Issue.query.filter(Issue.status.in_(["open", "in_progress"])).count()
    resolved_issues = Issue.query.filter_by(status="resolved").count()
    closed_issues = Issue.query.filter_by(status="closed").count()
    
    return render_template(
        "issues/list.html",
        issues=issues,
        pagination=pagination,
        status=status,
        priority=priority,
        client_id=client_id,
        project_id=project_id,
        assigned_to=assigned_to,
        search=search,
        clients=clients,
        projects=projects,
        users=users,
        total_issues=total_issues,
        open_issues=open_issues,
        resolved_issues=resolved_issues,
        closed_issues=closed_issues,
    )


@issues_bp.route("/issues/<int:issue_id>")
@login_required
def view_issue(issue_id):
    """View a specific issue"""
    issue = Issue.query.get_or_404(issue_id)
    
    # Get related tasks if project is set
    related_tasks = []
    if issue.project_id:
        related_tasks = Task.query.filter_by(project_id=issue.project_id).order_by(Task.created_at.desc()).limit(20).all()
    
    # Get users for assignment dropdown
    users = User.query.filter_by(is_active=True).order_by(User.username).limit(200).all()
    
    # Get projects for create task form
    projects = []
    if issue.client_id:
        projects = Project.query.filter_by(client_id=issue.client_id, status="active").order_by(Project.name).limit(500).all()
    
    return render_template(
        "issues/view.html",
        issue=issue,
        related_tasks=related_tasks,
        users=users,
        projects=projects,
    )


@issues_bp.route("/issues/<int:issue_id>/edit", methods=["GET", "POST"])
@login_required
def edit_issue(issue_id):
    """Edit an issue"""
    issue = Issue.query.get_or_404(issue_id)
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "open")
        priority = request.form.get("priority", "medium")
        project_id = request.form.get("project_id", type=int)
        assigned_to = request.form.get("assigned_to", type=int) or None
        
        # Validate
        if not title:
            flash(_("Title is required."), "error")
            return redirect(url_for("issues.edit_issue", issue_id=issue_id))
        
        # Validate project belongs to same client if changed
        if project_id and project_id != issue.project_id:
            project = Project.query.get(project_id)
            if not project or project.client_id != issue.client_id:
                flash(_("Project must belong to the same client."), "error")
                return redirect(url_for("issues.edit_issue", issue_id=issue_id))
        
        # Update issue
        issue.title = title
        issue.description = description if description else None
        issue.status = status
        issue.priority = priority
        issue.project_id = project_id
        issue.assigned_to = assigned_to
        
        # Update status timestamps
        if status == "resolved" and not issue.resolved_at:
            from app.utils.timezone import now_in_app_timezone
            issue.resolved_at = now_in_app_timezone()
        elif status == "closed" and not issue.closed_at:
            from app.utils.timezone import now_in_app_timezone
            issue.closed_at = now_in_app_timezone()
        
        if not safe_commit("edit_issue", {"issue_id": issue.id, "user_id": current_user.id}):
            flash(_("Could not update issue due to a database error."), "error")
            return redirect(url_for("issues.edit_issue", issue_id=issue_id))
        
        flash(_("Issue updated successfully."), "success")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    # GET - show edit form
    clients = Client.query.filter_by(status="active").order_by(Client.name).limit(500).all()
    projects = Project.query.filter_by(client_id=issue.client_id, status="active").order_by(Project.name).limit(500).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).limit(200).all()
    
    return render_template(
        "issues/edit.html",
        issue=issue,
        clients=clients,
        projects=projects,
        users=users,
    )


@issues_bp.route("/issues/<int:issue_id>/link-task", methods=["POST"])
@login_required
def link_task(issue_id):
    """Link an issue to an existing task"""
    issue = Issue.query.get_or_404(issue_id)
    task_id = request.form.get("task_id", type=int)
    
    if not task_id:
        flash(_("Please select a task."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    try:
        issue.link_to_task(task_id)
        flash(_("Issue linked to task successfully."), "success")
    except ValueError as e:
        flash(_(str(e)), "error")
    
    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issues_bp.route("/issues/<int:issue_id>/create-task", methods=["POST"])
@login_required
def create_task_from_issue(issue_id):
    """Create a new task from an issue"""
    issue = Issue.query.get_or_404(issue_id)
    project_id = request.form.get("project_id", type=int)
    assigned_to = request.form.get("assigned_to", type=int) or None
    
    if not project_id:
        flash(_("Please select a project."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    try:
        task = issue.create_task_from_issue(
            project_id=project_id,
            assigned_to=assigned_to,
            created_by=current_user.id,
        )
        flash(_("Task created from issue successfully."), "success")
        return redirect(url_for("tasks.view_task", task_id=task.id))
    except ValueError as e:
        flash(_(str(e)), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issues_bp.route("/issues/<int:issue_id>/status", methods=["POST"])
@login_required
def update_status(issue_id):
    """Update issue status"""
    issue = Issue.query.get_or_404(issue_id)
    status = request.form.get("status", "")
    
    if not status:
        flash(_("Status is required."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    try:
        if status == "in_progress":
            issue.mark_in_progress()
        elif status == "resolved":
            issue.mark_resolved()
        elif status == "closed":
            issue.mark_closed()
        elif status == "cancelled":
            issue.cancel()
        else:
            issue.status = status
            from app.utils.timezone import now_in_app_timezone
            issue.updated_at = now_in_app_timezone()
            db.session.commit()
        
        flash(_("Issue status updated successfully."), "success")
    except ValueError as e:
        flash(_(str(e)), "error")
    
    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issues_bp.route("/issues/<int:issue_id>/assign", methods=["POST"])
@login_required
def assign_issue(issue_id):
    """Assign issue to a user"""
    issue = Issue.query.get_or_404(issue_id)
    user_id = request.form.get("user_id", type=int) or None
    
    try:
        issue.reassign(user_id)
        flash(_("Issue assigned successfully."), "success")
    except Exception as e:
        flash(_("Could not assign issue."), "error")
    
    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issues_bp.route("/issues/<int:issue_id>/priority", methods=["POST"])
@login_required
def update_priority(issue_id):
    """Update issue priority"""
    issue = Issue.query.get_or_404(issue_id)
    priority = request.form.get("priority", "")
    
    if not priority:
        flash(_("Priority is required."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    try:
        issue.update_priority(priority)
        flash(_("Issue priority updated successfully."), "success")
    except ValueError as e:
        flash(_(str(e)), "error")
    
    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issues_bp.route("/issues/<int:issue_id>/delete", methods=["POST"])
@login_required
def delete_issue(issue_id):
    """Delete an issue"""
    if not current_user.is_admin:
        flash(_("Only administrators can delete issues."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    issue = Issue.query.get_or_404(issue_id)
    
    db.session.delete(issue)
    
    if not safe_commit("delete_issue", {"issue_id": issue_id, "user_id": current_user.id}):
        flash(_("Could not delete issue due to a database error."), "error")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))
    
    flash(_("Issue deleted successfully."), "success")
    return redirect(url_for("issues.list_issues"))
