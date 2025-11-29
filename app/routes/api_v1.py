"""REST API v1 - Comprehensive API endpoints with token authentication"""

from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models import (
    User,
    Project,
    TimeEntry,
    Task,
    Client,
    Invoice,
    Expense,
    SavedFilter,
    FocusSession,
    RecurringBlock,
    Comment,
    Payment,
    Mileage,
    PerDiem,
    PerDiemRate,
    BudgetAlert,
    CalendarEvent,
    KanbanColumn,
    TimeEntryTemplate,
    CreditNote,
    RecurringInvoice,
    ClientNote,
    ProjectCost,
    TaxRule,
    Currency,
    ExchangeRate,
    UserFavoriteProject,
    Activity,
    AuditLog,
    InvoicePDFTemplate,
    InvoiceTemplate,
    Webhook,
    WebhookDelivery,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
    StockReservation,
    Supplier,
    PurchaseOrder,
)
from app.utils.api_auth import require_api_token
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from app.utils.timezone import parse_local_datetime, utc_to_local
from app.models.time_entry import local_now

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# ==================== Helper Functions ====================


def paginate_query(query, page=None, per_page=None):
    """Paginate a SQLAlchemy query"""
    page = page or int(request.args.get("page", 1))
    per_page = per_page or int(request.args.get("per_page", 50))
    per_page = min(per_page, 100)  # Max 100 items per page

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": paginated.items,
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
            "next_page": paginated.page + 1 if paginated.has_next else None,
            "prev_page": paginated.page - 1 if paginated.has_prev else None,
        },
    }


def parse_datetime(dt_str):
    """Parse datetime string from API request"""
    if not dt_str:
        return None
    try:
        # Handle ISO format with timezone
        ts = dt_str.strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        # Convert to local naive for storage
        if dt.tzinfo is not None:
            dt = utc_to_local(dt).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _parse_date(dstr):
    """Parse a YYYY-MM-DD string to date."""
    if not dstr:
        return None
    try:
        from datetime import date as _date

        return _date.fromisoformat(str(dstr))
    except Exception:
        return None


# ==================== API Info & Health ====================


@api_v1_bp.route("/info", methods=["GET"])
def api_info():
    """Get API information and version
    ---
    tags:
      - System
    responses:
      200:
        description: API information
        schema:
          type: object
          properties:
            api_version:
              type: string
            app_version:
              type: string
            endpoints:
              type: array
            documentation_url:
              type: string
    """
    return jsonify(
        {
            "api_version": "v1",
            "app_version": current_app.config.get("APP_VERSION", "1.0.0"),
            "documentation_url": "/api/docs",
            "authentication": "API Token (Bearer or X-API-Key header)",
            "endpoints": {
                "projects": "/api/v1/projects",
                "time_entries": "/api/v1/time-entries",
                "tasks": "/api/v1/tasks",
                "clients": "/api/v1/clients",
                "invoices": "/api/v1/invoices",
                "expenses": "/api/v1/expenses",
                "payments": "/api/v1/payments",
                "mileage": "/api/v1/mileage",
                "per_diems": "/api/v1/per-diems",
                "per_diem_rates": "/api/v1/per-diem-rates",
                "budget_alerts": "/api/v1/budget-alerts",
                "calendar_events": "/api/v1/calendar/events",
                "kanban_columns": "/api/v1/kanban/columns",
                "saved_filters": "/api/v1/saved-filters",
                "time_entry_templates": "/api/v1/time-entry-templates",
                "comments": "/api/v1/comments",
                "recurring_invoices": "/api/v1/recurring-invoices",
                "credit_notes": "/api/v1/credit-notes",
                "client_notes": "/api/v1/clients/<client_id>/notes",
                "project_costs": "/api/v1/projects/<project_id>/costs",
                "tax_rules": "/api/v1/tax-rules",
                "currencies": "/api/v1/currencies",
                "exchange_rates": "/api/v1/exchange-rates",
                "favorites": "/api/v1/users/me/favorites/projects",
                "activities": "/api/v1/activities",
                "audit_logs": "/api/v1/audit-logs",
                "invoice_pdf_templates": "/api/v1/invoice-pdf-templates",
                "invoice_templates": "/api/v1/invoice-templates",
                "webhooks": "/api/v1/webhooks",
                "users": "/api/v1/users",
                "reports": "/api/v1/reports",
            },
        }
    )


@api_v1_bp.route("/health", methods=["GET"])
def health_check():
    """API health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: API is healthy
    """
    return jsonify({"status": "healthy", "timestamp": local_now().isoformat()})


# ==================== Projects ====================


@api_v1_bp.route("/projects", methods=["GET"])
@require_api_token("read:projects")
def list_projects():
    """List all projects
    ---
    tags:
      - Projects
    parameters:
      - name: status
        in: query
        type: string
        enum: [active, archived, on_hold]
      - name: client_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of projects
    """
    from app.services import ProjectService
    
    # Filter by status
    status = request.args.get("status", "active")
    client_id = request.args.get("client_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    project_service = ProjectService()
    result = project_service.list_projects(
        status=status,
        client_id=client_id,
        page=page,
        per_page=per_page,
    )

    return jsonify({"projects": [p.to_dict() for p in result["projects"]], "pagination": result["pagination"]})


@api_v1_bp.route("/projects/<int:project_id>", methods=["GET"])
@require_api_token("read:projects")
def get_project(project_id):
    """Get a specific project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Project details
      404:
        description: Project not found
    """
    from app.services import ProjectService
    
    project_service = ProjectService()
    result = project_service.get_project_with_details(project_id=project_id, include_time_entries=False)
    
    if not result:
        return jsonify({"error": "Project not found"}), 404
    
    return jsonify({"project": result.to_dict()})


@api_v1_bp.route("/projects", methods=["POST"])
@require_api_token("write:projects")
def create_project():
    """Create a new project
    ---
    tags:
      - Projects
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            description:
              type: string
            client_id:
              type: integer
            hourly_rate:
              type: number
            estimated_hours:
              type: number
            status:
              type: string
              enum: [active, archived, on_hold]
    security:
      - Bearer: []
    responses:
      201:
        description: Project created
      400:
        description: Invalid input
    """
    from app.services import ProjectService
    
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "Project name is required"}), 400

    # Use service layer to create project
    project_service = ProjectService()
    result = project_service.create_project(
        name=data["name"],
        client_id=data.get("client_id"),
        created_by=g.api_user.id,
        description=data.get("description"),
        billable=data.get("billable", True),
        hourly_rate=data.get("hourly_rate"),
        code=data.get("code"),
        budget_amount=data.get("budget_amount"),
        budget_threshold_percent=data.get("budget_threshold_percent"),
        billing_ref=data.get("billing_ref"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create project")}), 400

    return jsonify({"message": "Project created successfully", "project": result["project"].to_dict()}), 201


@api_v1_bp.route("/projects/<int:project_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_project(project_id):
    """Update a project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Project updated
      404:
        description: Project not found
    """
    from app.services import ProjectService
    
    data = request.get_json() or {}

    # Use service layer to update project
    project_service = ProjectService()
    
    # Prepare update kwargs
    update_kwargs = {}
    if "name" in data:
        update_kwargs["name"] = data["name"]
    if "description" in data:
        update_kwargs["description"] = data["description"]
    if "client_id" in data:
        update_kwargs["client_id"] = data["client_id"]
    if "hourly_rate" in data:
        update_kwargs["hourly_rate"] = data["hourly_rate"]
    if "estimated_hours" in data:
        update_kwargs["estimated_hours"] = data["estimated_hours"]
    if "status" in data:
        update_kwargs["status"] = data["status"]
    if "code" in data:
        update_kwargs["code"] = data["code"]
    if "budget_amount" in data:
        update_kwargs["budget_amount"] = data["budget_amount"]
    if "billing_ref" in data:
        update_kwargs["billing_ref"] = data["billing_ref"]

    result = project_service.update_project(
        project_id=project_id,
        user_id=g.api_user.id,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update project")}), 400

    return jsonify({"message": "Project updated successfully", "project": result["project"].to_dict()})


@api_v1_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_project(project_id):
    """Delete/archive a project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Project archived
      404:
        description: Project not found
    """
    from app.services import ProjectService
    
    project_service = ProjectService()
    result = project_service.archive_project(
        project_id=project_id,
        user_id=g.api_user.id,
        reason="Archived via API"
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not archive project")}), 404

    return jsonify({"message": "Project archived successfully"})


# ==================== Time Entries ====================


@api_v1_bp.route("/time-entries", methods=["GET"])
@require_api_token("read:time_entries")
def list_time_entries():
    """List time entries
    ---
    tags:
      - Time Entries
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: user_id
        in: query
        type: integer
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: billable
        in: query
        type: boolean
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of time entries
    """
    from app.services import TimeTrackingService
    from sqlalchemy.orm import joinedload
    
    # Filter by project
    project_id = request.args.get("project_id", type=int)
    
    # Filter by user (non-admin can only see their own)
    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return jsonify({"error": "Access denied"}), 403
    else:
        # Default to current user's entries if not admin
        if not g.api_user.is_admin:
            user_id = g.api_user.id

    # Filter by date range
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    start_dt = parse_datetime(start_date) if start_date else None
    end_dt = parse_datetime(end_date) if end_date else None

    # Filter by billable
    billable = request.args.get("billable")
    billable_filter = None
    if billable is not None:
        billable_filter = billable.lower() == "true"

    # Only completed entries by default
    include_active = request.args.get("include_active") == "true"
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use repository with eager loading to avoid N+1 queries
    from app.repositories import TimeEntryRepository
    time_entry_repo = TimeEntryRepository()
    
    # Build query with eager loading (use model.query for base query)
    from app.models import TimeEntry
    query = TimeEntry.query.options(
        joinedload(TimeEntry.project),
        joinedload(TimeEntry.user),
        joinedload(TimeEntry.task)
    )
    
    # Apply filters
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    if start_dt:
        query = query.filter(TimeEntry.start_time >= start_dt)
    if end_dt:
        query = query.filter(TimeEntry.start_time <= end_dt)
    if billable_filter is not None:
        query = query.filter(TimeEntry.billable == billable_filter)
    if not include_active:
        query = query.filter(TimeEntry.end_time.isnot(None))
    
    # Order and paginate
    query = query.order_by(TimeEntry.start_time.desc())
    result = paginate_query(query, page, per_page)

    return jsonify({"time_entries": [e.to_dict() for e in result["items"]], "pagination": result["pagination"]})


@api_v1_bp.route("/time-entries/<int:entry_id>", methods=["GET"])
@require_api_token("read:time_entries")
def get_time_entry(entry_id):
    """Get a specific time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry details
      404:
        description: Time entry not found
    """
    from sqlalchemy.orm import joinedload
    from app.models import TimeEntry
    
    entry = TimeEntry.query.options(
        joinedload(TimeEntry.project),
        joinedload(TimeEntry.user),
        joinedload(TimeEntry.task)
    ).filter_by(id=entry_id).first_or_404()

    # Check permissions
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"time_entry": entry.to_dict()})


@api_v1_bp.route("/time-entries", methods=["POST"])
@require_api_token("write:time_entries")
def create_time_entry():
    """Create a new time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
            - start_time
          properties:
            project_id:
              type: integer
            task_id:
              type: integer
            start_time:
              type: string
              format: date-time
            end_time:
              type: string
              format: date-time
            notes:
              type: string
            tags:
              type: string
            billable:
              type: boolean
    security:
      - Bearer: []
    responses:
      201:
        description: Time entry created
      400:
        description: Invalid input
    """
    from app.services import TimeTrackingService
    
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("project_id") and not data.get("client_id"):
        return jsonify({"error": "Either project_id or client_id is required"}), 400
    if not data.get("start_time"):
        return jsonify({"error": "start_time is required"}), 400

    # Parse times
    start_time = parse_datetime(data["start_time"])
    if not start_time:
        return jsonify({"error": "Invalid start_time format"}), 400

    end_time = None
    if data.get("end_time"):
        end_time = parse_datetime(data["end_time"])
        if end_time and end_time <= start_time:
            return jsonify({"error": "end_time must be after start_time"}), 400

    # Use service layer to create time entry
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.create_manual_entry(
        user_id=g.api_user.id,
        project_id=data.get("project_id"),
        client_id=data.get("client_id"),
        start_time=start_time,
        end_time=end_time or start_time,  # Service requires end_time
        task_id=data.get("task_id"),
        notes=data.get("notes"),
        tags=data.get("tags"),
        billable=data.get("billable", True),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create time entry")}), 400

    return jsonify({"message": "Time entry created successfully", "time_entry": result["entry"].to_dict()}), 201


@api_v1_bp.route("/time-entries/<int:entry_id>", methods=["PUT", "PATCH"])
@require_api_token("write:time_entries")
def update_time_entry(entry_id):
    """Update a time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry updated
      404:
        description: Time entry not found
    """
    from app.services import TimeTrackingService
    
    data = request.get_json() or {}

    # Parse times
    start_time = None
    if "start_time" in data:
        start_time = parse_datetime(data["start_time"])
    
    end_time = None
    if "end_time" in data:
        if data["end_time"] is None:
            end_time = None
        else:
            end_time = parse_datetime(data["end_time"])

    # Use service layer to update time entry
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.update_entry(
        entry_id=entry_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        project_id=data.get("project_id"),
        task_id=data.get("task_id"),
        start_time=start_time,
        end_time=end_time,
        notes=data.get("notes"),
        tags=data.get("tags"),
        billable=data.get("billable"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update time entry")}), 400

    return jsonify({"message": "Time entry updated successfully", "time_entry": result["entry"].to_dict()})


@api_v1_bp.route("/time-entries/<int:entry_id>", methods=["DELETE"])
@require_api_token("write:time_entries")
def delete_time_entry(entry_id):
    """Delete a time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry deleted
      404:
        description: Time entry not found
    """
    from app.services import TimeTrackingService
    
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.delete_entry(
        entry_id=entry_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete time entry")}), 400

    return jsonify({"message": "Time entry deleted successfully"})


# ==================== Timer Control ====================


@api_v1_bp.route("/timer/status", methods=["GET"])
@require_api_token("read:time_entries")
def timer_status():
    """Get current timer status for authenticated user
    ---
    tags:
      - Timer
    security:
      - Bearer: []
    responses:
      200:
        description: Timer status
    """
    active_timer = g.api_user.active_timer

    if not active_timer:
        return jsonify({"active": False, "timer": None})

    return jsonify({"active": True, "timer": active_timer.to_dict()})


@api_v1_bp.route("/timer/start", methods=["POST"])
@require_api_token("write:time_entries")
def start_timer():
    """Start a new timer
    ---
    tags:
      - Timer
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
          properties:
            project_id:
              type: integer
            task_id:
              type: integer
    security:
      - Bearer: []
    responses:
      201:
        description: Timer started
      400:
        description: Invalid input or timer already running
    """
    from app.services import TimeTrackingService
    
    data = request.get_json() or {}

    # Validate project_id
    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    # Use service layer to start timer
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.start_timer(
        user_id=g.api_user.id,
        project_id=project_id,
        task_id=data.get("task_id"),
        notes=data.get("notes"),
        template_id=data.get("template_id"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not start timer")}), 400

    return jsonify({"message": "Timer started successfully", "timer": result["timer"].to_dict()}), 201


@api_v1_bp.route("/timer/stop", methods=["POST"])
@require_api_token("write:time_entries")
def stop_timer():
    """Stop the active timer
    ---
    tags:
      - Timer
    security:
      - Bearer: []
    responses:
      200:
        description: Timer stopped
      400:
        description: No active timer
    """
    from app.services import TimeTrackingService
    
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.stop_timer(user_id=g.api_user.id)

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not stop timer")}), 400

    return jsonify({"message": "Timer stopped successfully", "time_entry": result["entry"].to_dict()})


# ==================== Tasks ====================


@api_v1_bp.route("/tasks", methods=["GET"])
@require_api_token("read:tasks")
def list_tasks():
    """List tasks
    ---
    tags:
      - Tasks
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: status
        in: query
        type: string
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of tasks
    """
    from app.services import TaskService
    
    # Filter by project
    project_id = request.args.get("project_id", type=int)
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use service layer with eager loading to avoid N+1 queries
    task_service = TaskService()
    result = task_service.list_tasks(
        project_id=project_id,
        status=status,
        page=page,
        per_page=per_page,
    )

    # Convert pagination object to dict
    pagination = result["pagination"]
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"tasks": [t.to_dict() for t in result["tasks"]], "pagination": pagination_dict})


@api_v1_bp.route("/tasks/<int:task_id>", methods=["GET"])
@require_api_token("read:tasks")
def get_task(task_id):
    """Get a specific task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Task details
      404:
        description: Task not found
    """
    from sqlalchemy.orm import joinedload
    from app.models import Task
    
    task = Task.query.options(
        joinedload(Task.project),
        joinedload(Task.assignee),
        joinedload(Task.created_by_user)
    ).filter_by(id=task_id).first_or_404()
    
    return jsonify({"task": task.to_dict()})


@api_v1_bp.route("/tasks", methods=["POST"])
@require_api_token("write:tasks")
def create_task():
    """Create a new task
    ---
    tags:
      - Tasks
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - project_id
          properties:
            name:
              type: string
            description:
              type: string
            project_id:
              type: integer
            status:
              type: string
            priority:
              type: integer
    security:
      - Bearer: []
    responses:
      201:
        description: Task created
      400:
        description: Invalid input
    """
    from app.services import TaskService
    
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "Task name is required"}), 400
    if not data.get("project_id"):
        return jsonify({"error": "project_id is required"}), 400

    # Use service layer to create task
    task_service = TaskService()
    result = task_service.create_task(
        name=data["name"],
        project_id=data["project_id"],
        created_by=g.api_user.id,
        description=data.get("description"),
        assignee_id=data.get("assignee_id"),
        priority=data.get("priority", "medium"),
        due_date=data.get("due_date"),
        estimated_hours=data.get("estimated_hours"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create task")}), 400

    return jsonify({"message": "Task created successfully", "task": result["task"].to_dict()}), 201


@api_v1_bp.route("/tasks/<int:task_id>", methods=["PUT", "PATCH"])
@require_api_token("write:tasks")
def update_task(task_id):
    """Update a task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Task updated
      404:
        description: Task not found
    """
    from app.services import TaskService
    
    data = request.get_json() or {}

    # Use service layer to update task
    task_service = TaskService()
    
    # Prepare update kwargs
    update_kwargs = {}
    if "name" in data:
        update_kwargs["name"] = data["name"]
    if "description" in data:
        update_kwargs["description"] = data["description"]
    if "status" in data:
        update_kwargs["status"] = data["status"]
    if "priority" in data:
        update_kwargs["priority"] = data["priority"]
    if "assignee_id" in data:
        update_kwargs["assignee_id"] = data["assignee_id"]
    if "due_date" in data:
        update_kwargs["due_date"] = data["due_date"]
    if "estimated_hours" in data:
        update_kwargs["estimated_hours"] = data["estimated_hours"]

    result = task_service.update_task(
        task_id=task_id,
        user_id=g.api_user.id,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update task")}), 400

    return jsonify({"message": "Task updated successfully", "task": result["task"].to_dict()})


@api_v1_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@require_api_token("write:tasks")
def delete_task(task_id):
    """Delete a task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Task deleted
      404:
        description: Task not found
    """
    from app.services import TaskService
    
    task_service = TaskService()
    # For now, use repository directly (can add delete_task method to service later)
    from app.repositories import TaskRepository
    task_repo = TaskRepository()
    task = task_repo.get_by_id(task_id)
    
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message": "Task deleted successfully"})


# ==================== Clients ====================


@api_v1_bp.route("/clients", methods=["GET"])
@require_api_token("read:clients")
def list_clients():
    """List all clients
    ---
    tags:
      - Clients
    parameters:
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of clients
    """
    from app.services import ClientService
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use repository with eager loading (clients don't have many relations, but good practice)
    from app.repositories import ClientRepository
    client_repo = ClientRepository()
    query = client_repo.query().order_by(Client.name)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }

    return jsonify({"clients": [c.to_dict() for c in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/clients/<int:client_id>", methods=["GET"])
@require_api_token("read:clients")
def get_client(client_id):
    """Get a specific client
    ---
    tags:
      - Clients
    parameters:
      - name: client_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Client details
      404:
        description: Client not found
    """
    from sqlalchemy.orm import joinedload
    
    client = Client.query.options(
        joinedload(Client.projects)
    ).filter_by(id=client_id).first_or_404()
    
    return jsonify({"client": client.to_dict()})


@api_v1_bp.route("/clients", methods=["POST"])
@require_api_token("write:clients")
def create_client():
    """Create a new client
    ---
    tags:
      - Clients
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            email:
              type: string
            company:
              type: string
            phone:
              type: string
    security:
      - Bearer: []
    responses:
      201:
        description: Client created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "Client name is required"}), 400

    from app.services import ClientService
    from decimal import Decimal

    # Use service layer to create client
    client_service = ClientService()
    result = client_service.create_client(
        name=data["name"],
        created_by=g.api_user.id,
        email=data.get("email"),
        company=data.get("company"),
        phone=data.get("phone"),
        address=data.get("address"),
        default_hourly_rate=Decimal(str(data["default_hourly_rate"])) if data.get("default_hourly_rate") else None,
        custom_fields=data.get("custom_fields"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create client")}), 400

    return jsonify({"message": "Client created successfully", "client": result["client"].to_dict()}), 201


# ==================== Invoices ====================


@api_v1_bp.route("/invoices", methods=["GET"])
@require_api_token("read:invoices")
def list_invoices():
    """List invoices
    ---
    tags:
      - Invoices
    parameters:
      - name: status
        in: query
        type: string
      - name: client_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of invoices
    """
    from app.services import InvoiceService
    
    status = request.args.get("status")
    client_id = request.args.get("client_id", type=int)
    project_id = request.args.get("project_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use service layer with eager loading to avoid N+1 queries
    invoice_service = InvoiceService()
    result = invoice_service.list_invoices(
        status=status,
        user_id=g.api_user.id if not g.api_user.is_admin else None,
        is_admin=g.api_user.is_admin,
        page=page,
        per_page=per_page,
    )

    # Convert pagination object to dict
    pagination = result["pagination"]
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"invoices": [inv.to_dict() for inv in result["invoices"]], "pagination": pagination_dict})


@api_v1_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@require_api_token("read:invoices")
def get_invoice(invoice_id):
    """Get invoice by id
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice
      404:
        description: Not found
    """
    from sqlalchemy.orm import joinedload
    from app.models import Invoice
    
    invoice = Invoice.query.options(
        joinedload(Invoice.project),
        joinedload(Invoice.client)
    ).filter_by(id=invoice_id).first_or_404()
    
    return jsonify({"invoice": invoice.to_dict()})


@api_v1_bp.route("/invoices", methods=["POST"])
@require_api_token("write:invoices")
def create_invoice():
    """Create a new invoice
    ---
    tags:
      - Invoices
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
            - client_id
            - client_name
            - due_date
          properties:
            invoice_number: { type: string }
            project_id: { type: integer }
            client_id: { type: integer }
            client_name: { type: string }
            client_email: { type: string }
            client_address: { type: string }
            due_date: { type: string, format: date }
            tax_rate: { type: number }
            currency_code: { type: string }
            notes: { type: string }
            terms: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Invoice created
      400:
        description: Invalid input
    """
    from app.services import InvoiceService
    from datetime import date
    
    data = request.get_json() or {}
    
    # Validate required fields
    required = ["project_id", "client_id", "client_name", "due_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    # Parse due date
    due_dt = _parse_date(data.get("due_date"))
    if not due_dt:
        return jsonify({"error": "Invalid due_date format, expected YYYY-MM-DD"}), 400
    
    # Parse issue date if provided
    issue_dt = None
    if data.get("issue_date"):
        issue_dt = _parse_date(data.get("issue_date"))
        if not issue_dt:
            return jsonify({"error": "Invalid issue_date format, expected YYYY-MM-DD"}), 400
    
    # Use service layer to create invoice
    invoice_service = InvoiceService()
    result = invoice_service.create_invoice(
        project_id=data["project_id"],
        client_id=data["client_id"],
        client_name=data["client_name"],
        due_date=due_dt,
        created_by=g.api_user.id,
        invoice_number=data.get("invoice_number"),
        client_email=data.get("client_email"),
        client_address=data.get("client_address"),
        notes=data.get("notes"),
        terms=data.get("terms"),
        tax_rate=data.get("tax_rate"),
        currency_code=data.get("currency_code"),
        issue_date=issue_dt,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create invoice")}), 400

    return jsonify({"message": "Invoice created successfully", "invoice": result["invoice"].to_dict()}), 201


@api_v1_bp.route("/invoices/<int:invoice_id>", methods=["PUT", "PATCH"])
@require_api_token("write:invoices")
def update_invoice(invoice_id):
    """Update an invoice
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice updated
      404:
        description: Not found
    """
    from app.services import InvoiceService
    
    data = request.get_json() or {}
    
    # Prepare update kwargs
    update_kwargs = {}
    for field in ("client_name", "client_email", "client_address", "notes", "terms", "status", "currency_code"):
        if field in data:
            update_kwargs[field] = data[field]
    if "due_date" in data:
        parsed = _parse_date(data["due_date"])
        if parsed:
            update_kwargs["due_date"] = parsed
    if "tax_rate" in data:
        try:
            update_kwargs["tax_rate"] = float(data["tax_rate"])
        except Exception:
            pass
    if "amount_paid" in data:
        try:
            from decimal import Decimal
            update_kwargs["amount_paid"] = Decimal(str(data["amount_paid"]))
        except Exception:
            pass

    # Use service layer to update invoice
    invoice_service = InvoiceService()
    result = invoice_service.update_invoice(
        invoice_id=invoice_id,
        user_id=g.api_user.id,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update invoice")}), 400

    # Handle amount_paid update separately (updates payment status)
    if "amount_paid" in data:
        invoice = result["invoice"]
        invoice.update_payment_status()
        db.session.commit()

    return jsonify({"message": "Invoice updated successfully", "invoice": result["invoice"].to_dict()})


@api_v1_bp.route("/invoices/<int:invoice_id>", methods=["DELETE"])
@require_api_token("write:invoices")
def delete_invoice(invoice_id):
    """Cancel an invoice (soft-delete)
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice cancelled
      404:
        description: Not found
    """
    from app.services import InvoiceService
    
    invoice_service = InvoiceService()
    result = invoice_service.update_invoice(
        invoice_id=invoice_id,
        user_id=g.api_user.id,
        status="cancelled"
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not cancel invoice")}), 400

    return jsonify({"message": "Invoice cancelled successfully"})


# ==================== Expenses ====================


@api_v1_bp.route("/expenses", methods=["GET"])
@require_api_token("read:expenses")
def list_expenses():
    """List expenses
    ---
    tags:
      - Expenses
    parameters:
      - name: user_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: client_id
        in: query
        type: integer
      - name: status
        in: query
        type: string
      - name: category
        in: query
        type: string
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of expenses
    """
    from app.services import ExpenseService
    from datetime import date
    
    # Restrict by user if not admin
    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if not g.api_user.is_admin:
            user_id = g.api_user.id
    
    # Other filters
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    status = request.args.get("status")
    category = request.args.get("category")
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use service layer with eager loading to avoid N+1 queries
    expense_service = ExpenseService()
    result = expense_service.list_expenses(
        user_id=user_id,
        project_id=project_id,
        client_id=client_id,
        status=status,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_admin=g.api_user.is_admin,
        page=page,
        per_page=per_page,
    )

    # Convert pagination object to dict
    pagination = result["pagination"]
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"expenses": [e.to_dict() for e in result["expenses"]], "pagination": pagination_dict})


@api_v1_bp.route("/expenses/<int:expense_id>", methods=["GET"])
@require_api_token("read:expenses")
def get_expense(expense_id):
    """Get an expense
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense
      404:
        description: Not found
    """
    from sqlalchemy.orm import joinedload
    from app.models import Expense
    
    expense = Expense.query.options(
        joinedload(Expense.project),
        joinedload(Expense.user),
        joinedload(Expense.category)
    ).filter_by(id=expense_id).first_or_404()
    
    if not g.api_user.is_admin and expense.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"expense": expense.to_dict()})


@api_v1_bp.route("/expenses", methods=["POST"])
@require_api_token("write:expenses")
def create_expense():
    """Create a new expense
    ---
    tags:
      - Expenses
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - title
            - category
            - amount
            - expense_date
          properties:
            title: { type: string }
            description: { type: string }
            category: { type: string }
            amount: { type: number }
            currency_code: { type: string }
            expense_date: { type: string, format: date }
            project_id: { type: integer }
            client_id: { type: integer }
            billable: { type: boolean }
            reimbursable: { type: boolean }
            payment_method: { type: string }
            payment_date: { type: string, format: date }
            tags: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Expense created
      400:
        description: Invalid input
    """
    from app.services import ExpenseService
    from decimal import Decimal
    
    data = request.get_json() or {}
    required = ["title", "category", "amount", "expense_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    exp_date = _parse_date(data.get("expense_date"))
    if not exp_date:
        return jsonify({"error": "Invalid expense_date format, expected YYYY-MM-DD"}), 400
    
    pay_date = _parse_date(data.get("payment_date")) if data.get("payment_date") else None

    try:
        amount = Decimal(str(data["amount"]))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400

    # Use service layer to create expense
    expense_service = ExpenseService()
    result = expense_service.create_expense(
        amount=amount,
        expense_date=exp_date,
        created_by=g.api_user.id,
        title=data["title"],
        description=data.get("description"),
        project_id=data.get("project_id"),
        client_id=data.get("client_id"),
        category=data["category"],
        billable=data.get("billable", False),
        reimbursable=data.get("reimbursable", True),
        currency_code=data.get("currency_code", "EUR"),
        tax_amount=Decimal(str(data.get("tax_amount", 0))) if data.get("tax_amount") else None,
        tax_rate=Decimal(str(data.get("tax_rate", 0))) if data.get("tax_rate") else None,
        payment_method=data.get("payment_method"),
        payment_date=pay_date,
        tags=data.get("tags"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create expense")}), 400

    return jsonify({"message": "Expense created successfully", "expense": result["expense"].to_dict()}), 201


@api_v1_bp.route("/expenses/<int:expense_id>", methods=["PUT", "PATCH"])
@require_api_token("write:expenses")
def update_expense(expense_id):
    """Update an expense
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense updated
      404:
        description: Not found
    """
    from app.services import ExpenseService
    from decimal import Decimal
    
    data = request.get_json() or {}
    
    # Prepare update kwargs
    update_kwargs = {}
    for field in ("title", "description", "category", "currency_code", "payment_method", "status", "tags"):
        if field in data:
            update_kwargs[field] = data[field]
    if "amount" in data:
        try:
            update_kwargs["amount"] = Decimal(str(data["amount"]))
        except Exception:
            pass
    if "expense_date" in data:
        parsed = _parse_date(data["expense_date"])
        if parsed:
            update_kwargs["expense_date"] = parsed
    if "payment_date" in data:
        parsed = _parse_date(data["payment_date"])
        update_kwargs["payment_date"] = parsed
    for bfield in ("billable", "reimbursable", "reimbursed", "invoiced"):
        if bfield in data:
            update_kwargs[bfield] = bool(data[bfield])

    # Use service layer to update expense
    expense_service = ExpenseService()
    result = expense_service.update_expense(
        expense_id=expense_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update expense")}), 400

    return jsonify({"message": "Expense updated successfully", "expense": result["expense"].to_dict()})


@api_v1_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@require_api_token("write:expenses")
def delete_expense(expense_id):
    """Reject an expense (soft-delete)
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense rejected
      404:
        description: Not found
    """
    from app.services import ExpenseService
    
    expense_service = ExpenseService()
    result = expense_service.delete_expense(
        expense_id=expense_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not reject expense")}), 400

    return jsonify({"message": "Expense rejected successfully"})


# ==================== Payments ====================


@api_v1_bp.route("/payments", methods=["GET"])
@require_api_token("read:payments")
def list_payments():
    """List payments
    ---
    tags:
      - Payments
    parameters:
      - name: invoice_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of payments
    """
    from app.services import PaymentService
    from sqlalchemy.orm import joinedload
    from app.models import Payment
    
    invoice_id = request.args.get("invoice_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use repository with eager loading to avoid N+1 queries
    query = Payment.query.options(
        joinedload(Payment.invoice)
    )
    
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    
    query = query.order_by(Payment.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"payments": [p.to_dict() for p in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/payments/<int:payment_id>", methods=["GET"])
@require_api_token("read:payments")
def get_payment(payment_id):
    """Get a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment
    """
    from sqlalchemy.orm import joinedload
    from app.models import Payment
    
    payment = Payment.query.options(
        joinedload(Payment.invoice)
    ).filter_by(id=payment_id).first_or_404()
    
    return jsonify({"payment": payment.to_dict()})


@api_v1_bp.route("/payments", methods=["POST"])
@require_api_token("write:payments")
def create_payment():
    """Create a payment
    ---
    tags:
      - Payments
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [invoice_id, amount]
          properties:
            invoice_id: { type: integer }
            amount: { type: number }
            currency: { type: string }
            payment_date: { type: string, format: date }
            method: { type: string }
            reference: { type: string }
            notes: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Payment created
    """
    from app.services import PaymentService
    from decimal import Decimal
    
    data = request.get_json() or {}
    required = ["invoice_id", "amount"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        amount = Decimal(str(data["amount"]))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    
    pay_date = _parse_date(data.get("payment_date")) if data.get("payment_date") else None
    if not pay_date:
        from datetime import date
        pay_date = date.today()

    # Use service layer to create payment
    payment_service = PaymentService()
    result = payment_service.create_payment(
        invoice_id=data["invoice_id"],
        amount=amount,
        payment_date=pay_date,
        received_by=g.api_user.id,
        currency=data.get("currency"),
        method=data.get("method"),
        reference=data.get("reference"),
        notes=data.get("notes"),
        status=data.get("status", "completed"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create payment")}), 400

    return jsonify({"message": "Payment created successfully", "payment": result["payment"].to_dict()}), 201


@api_v1_bp.route("/payments/<int:payment_id>", methods=["PUT", "PATCH"])
@require_api_token("write:payments")
def update_payment(payment_id):
    """Update a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment updated
    """
    from app.services import PaymentService
    from decimal import Decimal
    
    data = request.get_json() or {}
    
    # Prepare update kwargs
    update_kwargs = {}
    for field in ("currency", "method", "reference", "notes", "status"):
        if field in data:
            update_kwargs[field] = data[field]
    if "amount" in data:
        try:
            update_kwargs["amount"] = Decimal(str(data["amount"]))
        except Exception:
            pass
    if "payment_date" in data:
        parsed = _parse_date(data["payment_date"])
        if parsed:
            update_kwargs["payment_date"] = parsed

    # Use service layer to update payment
    payment_service = PaymentService()
    result = payment_service.update_payment(
        payment_id=payment_id,
        user_id=g.api_user.id,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update payment")}), 400

    return jsonify({"message": "Payment updated successfully", "payment": result["payment"].to_dict()})


@api_v1_bp.route("/payments/<int:payment_id>", methods=["DELETE"])
@require_api_token("write:payments")
def delete_payment(payment_id):
    """Delete a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment deleted
    """
    from app.services import PaymentService
    
    payment_service = PaymentService()
    result = payment_service.delete_payment(
        payment_id=payment_id,
        user_id=g.api_user.id
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete payment")}), 400

    return jsonify({"message": "Payment deleted successfully"})


# ==================== Mileage ====================


@api_v1_bp.route("/mileage", methods=["GET"])
@require_api_token("read:mileage")
def list_mileage():
    """List mileage entries (non-admin see own only)
    ---
    tags:
      - Mileage
    parameters:
      - name: user_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of mileage entries
    """
    from sqlalchemy.orm import joinedload
    
    # Restrict by user if not admin
    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if not g.api_user.is_admin:
            user_id = g.api_user.id
    
    project_id = request.args.get("project_id", type=int)
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use eager loading to avoid N+1 queries
    query = Mileage.query.options(
        joinedload(Mileage.user),
        joinedload(Mileage.project),
        joinedload(Mileage.client)
    )
    
    # Apply filters
    if user_id:
        query = query.filter(Mileage.user_id == user_id)
    if project_id:
        query = query.filter(Mileage.project_id == project_id)
    if start_date:
        query = query.filter(Mileage.trip_date >= start_date)
    if end_date:
        query = query.filter(Mileage.trip_date <= end_date)
    
    query = query.order_by(Mileage.trip_date.desc(), Mileage.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"mileage": [m.to_dict() for m in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/mileage/<int:entry_id>", methods=["GET"])
@require_api_token("read:mileage")
def get_mileage(entry_id):
    """Get a mileage entry
    ---
    tags:
      - Mileage
    security:
      - Bearer: []
    """
    from sqlalchemy.orm import joinedload
    
    entry = Mileage.query.options(
        joinedload(Mileage.user),
        joinedload(Mileage.project),
        joinedload(Mileage.client)
    ).filter_by(id=entry_id).first_or_404()
    
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"mileage": entry.to_dict()})


@api_v1_bp.route("/mileage", methods=["POST"])
@require_api_token("write:mileage")
def create_mileage():
    """Create a mileage entry
    ---
    tags:
      - Mileage
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [trip_date, purpose, start_location, end_location, distance_km, rate_per_km]
          properties:
            trip_date: { type: string, format: date }
            purpose: { type: string }
            start_location: { type: string }
            end_location: { type: string }
            distance_km: { type: number }
            rate_per_km: { type: number }
            project_id: { type: integer }
            client_id: { type: integer }
            is_round_trip: { type: boolean }
    """
    data = request.get_json() or {}
    required = ["trip_date", "purpose", "start_location", "end_location", "distance_km", "rate_per_km"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    trip_date = _parse_date(data.get("trip_date"))
    if not trip_date:
        return jsonify({"error": "Invalid trip_date format, expected YYYY-MM-DD"}), 400
    from decimal import Decimal

    try:
        distance_km = Decimal(str(data["distance_km"]))
        rate_per_km = Decimal(str(data["rate_per_km"]))
    except Exception:
        return jsonify({"error": "Invalid distance_km or rate_per_km"}), 400
    entry = Mileage(
        user_id=g.api_user.id,
        trip_date=trip_date,
        purpose=data["purpose"],
        start_location=data["start_location"],
        end_location=data["end_location"],
        distance_km=distance_km,
        rate_per_km=rate_per_km,
        project_id=data.get("project_id"),
        client_id=data.get("client_id"),
        is_round_trip=bool(data.get("is_round_trip", False)),
        description=data.get("description"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "Mileage entry created successfully", "mileage": entry.to_dict()}), 201


@api_v1_bp.route("/mileage/<int:entry_id>", methods=["PUT", "PATCH"])
@require_api_token("write:mileage")
def update_mileage(entry_id):
    """Update a mileage entry
    ---
    tags:
      - Mileage
    """
    from sqlalchemy.orm import joinedload
    from decimal import Decimal
    
    entry = Mileage.query.options(
        joinedload(Mileage.user),
        joinedload(Mileage.project),
        joinedload(Mileage.client)
    ).filter_by(id=entry_id).first_or_404()
    
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    
    # Update fields
    for field in (
        "purpose",
        "start_location",
        "end_location",
        "description",
        "vehicle_type",
        "vehicle_description",
        "license_plate",
        "currency_code",
        "status",
        "notes",
    ):
        if field in data:
            setattr(entry, field, data[field])
    if "trip_date" in data:
        parsed = _parse_date(data["trip_date"])
        if parsed:
            entry.trip_date = parsed
    for numfield in ("distance_km", "rate_per_km", "start_odometer", "end_odometer"):
        if numfield in data:
            try:
                setattr(entry, numfield, Decimal(str(data[numfield])))
            except Exception:
                pass
    if "is_round_trip" in data:
        entry.is_round_trip = bool(data["is_round_trip"])
    
    # Recalculate amount if distance or rate changed
    if "distance_km" in data or "rate_per_km" in data:
        entry.calculated_amount = entry.distance_km * entry.rate_per_km
        if entry.is_round_trip:
            entry.calculated_amount *= Decimal("2")
    
    db.session.commit()
    return jsonify({"message": "Mileage entry updated successfully", "mileage": entry.to_dict()})


@api_v1_bp.route("/mileage/<int:entry_id>", methods=["DELETE"])
@require_api_token("write:mileage")
def delete_mileage(entry_id):
    """Reject a mileage entry
    ---
    tags:
      - Mileage
    """
    from sqlalchemy.orm import joinedload
    
    entry = Mileage.query.options(
        joinedload(Mileage.user),
        joinedload(Mileage.project),
        joinedload(Mileage.client)
    ).filter_by(id=entry_id).first_or_404()
    
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    entry.status = "rejected"
    db.session.commit()
    return jsonify({"message": "Mileage entry rejected successfully"})


# ==================== Per Diem ====================


@api_v1_bp.route("/per-diems", methods=["GET"])
@require_api_token("read:per_diem")
def list_per_diems():
    """List per diem claims (non-admin see own only)
    ---
    tags:
      - PerDiem
    """
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use eager loading to avoid N+1 queries
    query = PerDiem.query.options(joinedload(PerDiem.user))
    
    if not g.api_user.is_admin:
        query = query.filter(PerDiem.user_id == g.api_user.id)
    
    query = query.order_by(PerDiem.start_date.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"per_diems": [p.to_dict() for p in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/per-diems/<int:pd_id>", methods=["GET"])
@require_api_token("read:per_diem")
def get_per_diem(pd_id):
    """Get a per diem claim
    ---
    tags:
      - PerDiem
    """
    from sqlalchemy.orm import joinedload
    
    pd = PerDiem.query.options(joinedload(PerDiem.user)).filter_by(id=pd_id).first_or_404()
    
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"per_diem": pd.to_dict()})


@api_v1_bp.route("/per-diems", methods=["POST"])
@require_api_token("write:per_diem")
def create_per_diem():
    """Create a per diem claim
    ---
    tags:
      - PerDiem
    """
    data = request.get_json() or {}
    required = ["trip_purpose", "start_date", "end_date", "country", "full_day_rate", "half_day_rate"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    sdate = _parse_date(data.get("start_date"))
    edate = _parse_date(data.get("end_date"))
    if not sdate or not edate or edate < sdate:
        return jsonify({"error": "Invalid date range"}), 400
    from decimal import Decimal

    try:
        fdr = Decimal(str(data["full_day_rate"]))
        hdr = Decimal(str(data["half_day_rate"]))
    except Exception:
        return jsonify({"error": "Invalid rates"}), 400
    pd = PerDiem(
        user_id=g.api_user.id,
        trip_purpose=data["trip_purpose"],
        start_date=sdate,
        end_date=edate,
        country=data["country"],
        full_day_rate=fdr,
        half_day_rate=hdr,
        city=data.get("city"),
        description=data.get("description"),
        currency_code=data.get("currency_code", "EUR"),
        full_days=data.get("full_days", 0),
        half_days=data.get("half_days", 0),
        breakfast_provided=data.get("breakfast_provided", 0),
        lunch_provided=data.get("lunch_provided", 0),
        dinner_provided=data.get("dinner_provided", 0),
    )
    pd.recalculate_amount()
    db.session.add(pd)
    db.session.commit()
    return jsonify({"message": "Per diem created successfully", "per_diem": pd.to_dict()}), 201


@api_v1_bp.route("/per-diems/<int:pd_id>", methods=["PUT", "PATCH"])
@require_api_token("write:per_diem")
def update_per_diem(pd_id):
    """Update a per diem claim
    ---
    tags:
      - PerDiem
    """
    from sqlalchemy.orm import joinedload
    
    pd = PerDiem.query.options(joinedload(PerDiem.user)).filter_by(id=pd_id).first_or_404()
    
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    for field in ("trip_purpose", "description", "country", "city", "currency_code", "status", "notes"):
        if field in data:
            setattr(pd, field, data[field])
    for numfield in ("full_days", "half_days", "breakfast_provided", "lunch_provided", "dinner_provided"):
        if numfield in data:
            try:
                setattr(pd, numfield, int(data[numfield]))
            except Exception:
                pass
    for ratefield in ("full_day_rate", "half_day_rate", "breakfast_deduction", "lunch_deduction", "dinner_deduction"):
        if ratefield in data:
            try:
                from decimal import Decimal

                setattr(pd, ratefield, Decimal(str(data[ratefield])))
            except Exception:
                pass
    if "start_date" in data:
        parsed = _parse_date(data["start_date"])
        if parsed:
            pd.start_date = parsed
    if "end_date" in data:
        parsed = _parse_date(data["end_date"])
        if parsed:
            pd.end_date = parsed
    pd.recalculate_amount()
    db.session.commit()
    return jsonify({"message": "Per diem updated successfully", "per_diem": pd.to_dict()})


@api_v1_bp.route("/per-diems/<int:pd_id>", methods=["DELETE"])
@require_api_token("write:per_diem")
def delete_per_diem(pd_id):
    """Reject a per diem claim
    ---
    tags:
      - PerDiem
    """
    from sqlalchemy.orm import joinedload
    
    pd = PerDiem.query.options(joinedload(PerDiem.user)).filter_by(id=pd_id).first_or_404()
    
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    pd.status = "rejected"
    db.session.commit()
    return jsonify({"message": "Per diem rejected successfully"})


@api_v1_bp.route("/per-diem-rates", methods=["GET"])
@require_api_token("read:per_diem")
def list_per_diem_rates():
    """List per diem rates
    ---
    tags:
      - PerDiemRates
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = PerDiemRate.query.filter(PerDiemRate.is_active == True)
    query = query.order_by(PerDiemRate.country.asc(), PerDiemRate.city.asc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"rates": [r.to_dict() for r in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/per-diem-rates", methods=["POST"])
@require_api_token("admin:all")
def create_per_diem_rate():
    """Create a per diem rate (admin)
    ---
    tags:
      - PerDiemRates
    """
    data = request.get_json() or {}
    required = ["country", "full_day_rate", "half_day_rate", "effective_from"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    eff_from = _parse_date(data.get("effective_from"))
    eff_to = _parse_date(data.get("effective_to"))
    from decimal import Decimal

    try:
        fdr = Decimal(str(data["full_day_rate"]))
        hdr = Decimal(str(data["half_day_rate"]))
    except Exception:
        return jsonify({"error": "Invalid rates"}), 400
    rate = PerDiemRate(
        country=data["country"],
        full_day_rate=fdr,
        half_day_rate=hdr,
        effective_from=eff_from,
        effective_to=eff_to,
        city=data.get("city"),
        currency_code=data.get("currency_code", "EUR"),
        breakfast_rate=data.get("breakfast_rate"),
        lunch_rate=data.get("lunch_rate"),
        dinner_rate=data.get("dinner_rate"),
        incidental_rate=data.get("incidental_rate"),
        is_active=bool(data.get("is_active", True)),
        notes=data.get("notes"),
    )
    db.session.add(rate)
    db.session.commit()
    return jsonify({"message": "Per diem rate created successfully", "rate": rate.to_dict()}), 201


# ==================== Budget Alerts ====================


@api_v1_bp.route("/budget-alerts", methods=["GET"])
@require_api_token("read:budget_alerts")
def list_budget_alerts():
    """List budget alerts
    ---
    tags:
      - BudgetAlerts
    """
    from sqlalchemy.orm import joinedload
    
    project_id = request.args.get("project_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use eager loading to avoid N+1 queries
    query = BudgetAlert.query.options(
        joinedload(BudgetAlert.project)
    )
    
    if project_id:
        query = query.filter(BudgetAlert.project_id == project_id)
    
    query = query.order_by(BudgetAlert.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"alerts": [a.to_dict() for a in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/budget-alerts", methods=["POST"])
@require_api_token("admin:all")
def create_budget_alert():
    """Create a budget alert (admin)
    ---
    tags:
      - BudgetAlerts
    """
    data = request.get_json() or {}
    required = ["project_id", "alert_type", "budget_consumed_percent", "budget_amount", "consumed_amount", "message"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    alert = BudgetAlert(
        project_id=data["project_id"],
        alert_type=data["alert_type"],
        alert_level=data.get("alert_level", "info"),
        budget_consumed_percent=data["budget_consumed_percent"],
        budget_amount=data["budget_amount"],
        consumed_amount=data["consumed_amount"],
        message=data["message"],
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify({"message": "Budget alert created successfully", "alert": alert.to_dict()}), 201


@api_v1_bp.route("/budget-alerts/<int:alert_id>/ack", methods=["POST"])
@require_api_token("write:budget_alerts")
def acknowledge_budget_alert(alert_id):
    """Acknowledge a budget alert
    ---
    tags:
      - BudgetAlerts
    """
    from sqlalchemy.orm import joinedload
    
    alert = BudgetAlert.query.options(joinedload(BudgetAlert.project)).filter_by(id=alert_id).first_or_404()
    
    alert.acknowledge(g.api_user.id)
    return jsonify({"message": "Alert acknowledged"})


# ==================== Calendar Events ====================


@api_v1_bp.route("/calendar/events", methods=["GET"])
@require_api_token("read:calendar")
def list_calendar_events():
    """List calendar events for current user
    ---
    tags:
      - Calendar
    parameters:
      - name: start
        in: query
        type: string
      - name: end
        in: query
        type: string
    """
    start = request.args.get("start")
    end = request.args.get("end")
    start_dt = parse_datetime(start) if start else None
    end_dt = parse_datetime(end) if end else None
    from sqlalchemy.orm import joinedload
    
    query = CalendarEvent.query.options(joinedload(CalendarEvent.user))
    query = query.filter(CalendarEvent.user_id == g.api_user.id)
    
    if start_dt:
        query = query.filter(CalendarEvent.start_time >= start_dt)
    if end_dt:
        query = query.filter(CalendarEvent.start_time <= end_dt)
    
    events = query.order_by(CalendarEvent.start_time.asc()).all()
    return jsonify({"events": [e.to_dict() for e in events]})


@api_v1_bp.route("/calendar/events/<int:event_id>", methods=["GET"])
@require_api_token("read:calendar")
def get_calendar_event(event_id):
    """Get calendar event
    ---
    tags:
      - Calendar
    """
    from sqlalchemy.orm import joinedload
    
    ev = CalendarEvent.query.options(joinedload(CalendarEvent.user)).filter_by(id=event_id).first_or_404()
    
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"event": ev.to_dict()})


@api_v1_bp.route("/calendar/events", methods=["POST"])
@require_api_token("write:calendar")
def create_calendar_event():
    """Create calendar event
    ---
    tags:
      - Calendar
    """
    data = request.get_json() or {}
    required = ["title", "start_time", "end_time"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    start_dt = parse_datetime(data["start_time"])
    end_dt = parse_datetime(data["end_time"])
    if not start_dt or not end_dt or end_dt <= start_dt:
        return jsonify({"error": "Invalid start/end time"}), 400
    ev = CalendarEvent(
        user_id=g.api_user.id,
        title=data["title"],
        start_time=start_dt,
        end_time=end_dt,
        description=data.get("description"),
        all_day=bool(data.get("all_day", False)),
        location=data.get("location"),
        project_id=data.get("project_id"),
        task_id=data.get("task_id"),
        client_id=data.get("client_id"),
        event_type=data.get("event_type", "event"),
        reminder_minutes=data.get("reminder_minutes"),
        color=data.get("color"),
        is_private=bool(data.get("is_private", False)),
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify({"message": "Event created successfully", "event": ev.to_dict()}), 201


@api_v1_bp.route("/calendar/events/<int:event_id>", methods=["PUT", "PATCH"])
@require_api_token("write:calendar")
def update_calendar_event(event_id):
    """Update calendar event
    ---
    tags:
      - Calendar
    """
    from sqlalchemy.orm import joinedload
    
    ev = CalendarEvent.query.options(joinedload(CalendarEvent.user)).filter_by(id=event_id).first_or_404()
    
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    for field in ("title", "description", "location", "event_type", "color", "is_private", "reminder_minutes"):
        if field in data:
            setattr(ev, field, data[field])
    if "start_time" in data:
        parsed = parse_datetime(data["start_time"])
        if parsed:
            ev.start_time = parsed
    if "end_time" in data:
        parsed = parse_datetime(data["end_time"])
        if parsed:
            ev.end_time = parsed
    db.session.commit()
    return jsonify({"message": "Event updated successfully", "event": ev.to_dict()})


@api_v1_bp.route("/calendar/events/<int:event_id>", methods=["DELETE"])
@require_api_token("write:calendar")
def delete_calendar_event(event_id):
    """Delete calendar event
    ---
    tags:
      - Calendar
    """
    from sqlalchemy.orm import joinedload
    
    ev = CalendarEvent.query.options(joinedload(CalendarEvent.user)).filter_by(id=event_id).first_or_404()
    
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"message": "Event deleted successfully"})


# ==================== Kanban Columns ====================


@api_v1_bp.route("/kanban/columns", methods=["GET"])
@require_api_token("read:tasks")
def list_kanban_columns():
    """List kanban columns
    ---
    tags:
      - Kanban
    parameters:
      - name: project_id
        in: query
        type: integer
    """
    project_id = request.args.get("project_id", type=int)
    cols = KanbanColumn.get_all_columns(project_id=project_id)
    return jsonify({"columns": [c.to_dict() for c in cols]})


@api_v1_bp.route("/kanban/columns", methods=["POST"])
@require_api_token("write:tasks")
def create_kanban_column():
    """Create kanban column
    ---
    tags:
      - Kanban
    """
    data = request.get_json() or {}
    required = ["key", "label"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    col = KanbanColumn(
        key=data["key"],
        label=data["label"],
        icon=data.get("icon", "fas fa-circle"),
        color=data.get("color", "secondary"),
        position=data.get("position", 0),
        is_active=bool(data.get("is_active", True)),
        is_system=bool(data.get("is_system", False)),
        is_complete_state=bool(data.get("is_complete_state", False)),
        project_id=data.get("project_id"),
    )
    db.session.add(col)
    db.session.commit()
    return jsonify({"message": "Column created successfully", "column": col.to_dict()}), 201


@api_v1_bp.route("/kanban/columns/<int:col_id>", methods=["PUT", "PATCH"])
@require_api_token("write:tasks")
def update_kanban_column(col_id):
    """Update kanban column
    ---
    tags:
      - Kanban
    """
    from sqlalchemy.orm import joinedload
    
    col = KanbanColumn.query.options(joinedload(KanbanColumn.project)).filter_by(id=col_id).first_or_404()
    
    data = request.get_json() or {}
    for field in ("key", "label", "icon", "color", "position", "is_active", "is_complete_state"):
        if field in data:
            setattr(col, field, data[field])
    db.session.commit()
    return jsonify({"message": "Column updated successfully", "column": col.to_dict()})


@api_v1_bp.route("/kanban/columns/<int:col_id>", methods=["DELETE"])
@require_api_token("write:tasks")
def delete_kanban_column(col_id):
    """Delete kanban column
    ---
    tags:
      - Kanban
    """
    from sqlalchemy.orm import joinedload
    
    col = KanbanColumn.query.options(joinedload(KanbanColumn.project)).filter_by(id=col_id).first_or_404()
    
    if col.is_system:
        return jsonify({"error": "Cannot delete system column"}), 400
    
    db.session.delete(col)
    db.session.commit()
    return jsonify({"message": "Column deleted successfully"})


@api_v1_bp.route("/kanban/columns/reorder", methods=["POST"])
@require_api_token("write:tasks")
def reorder_kanban_columns():
    """Reorder kanban columns
    ---
    tags:
      - Kanban
    """
    data = request.get_json() or {}
    ids = data.get("column_ids") or []
    project_id = data.get("project_id")
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "column_ids must be a non-empty list"}), 400
    KanbanColumn.reorder_columns(ids, project_id=project_id)
    return jsonify({"message": "Columns reordered successfully"})


# ==================== Saved Filters ====================


@api_v1_bp.route("/saved-filters", methods=["GET"])
@require_api_token("read:filters")
def list_saved_filters():
    """List saved filters for current user
    ---
    tags:
      - SavedFilters
    """
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = SavedFilter.query.options(joinedload(SavedFilter.user))
    query = query.filter(SavedFilter.user_id == g.api_user.id)
    query = query.order_by(SavedFilter.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"filters": [f.to_dict() for f in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/saved-filters/<int:filter_id>", methods=["GET"])
@require_api_token("read:filters")
def get_saved_filter(filter_id):
    """Get saved filter
    ---
    tags:
      - SavedFilters
    """
    from sqlalchemy.orm import joinedload
    
    sf = SavedFilter.query.options(joinedload(SavedFilter.user)).filter_by(id=filter_id).first_or_404()
    
    if sf.user_id != g.api_user.id and not (sf.is_shared or g.api_user.is_admin):
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"filter": sf.to_dict()})


@api_v1_bp.route("/saved-filters", methods=["POST"])
@require_api_token("write:filters")
def create_saved_filter():
    """Create saved filter
    ---
    tags:
      - SavedFilters
    """
    data = request.get_json() or {}
    required = ["name", "scope", "payload"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    sf = SavedFilter(
        user_id=g.api_user.id,
        name=data["name"],
        scope=data["scope"],
        payload=data["payload"],
        is_shared=bool(data.get("is_shared", False)),
    )
    db.session.add(sf)
    db.session.commit()
    return jsonify({"message": "Saved filter created successfully", "filter": sf.to_dict()}), 201


@api_v1_bp.route("/saved-filters/<int:filter_id>", methods=["PUT", "PATCH"])
@require_api_token("write:filters")
def update_saved_filter(filter_id):
    """Update saved filter
    ---
    tags:
      - SavedFilters
    """
    from sqlalchemy.orm import joinedload
    
    sf = SavedFilter.query.options(joinedload(SavedFilter.user)).filter_by(id=filter_id).first_or_404()
    
    if sf.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    for field in ("name", "scope", "payload", "is_shared"):
        if field in data:
            setattr(sf, field, data[field])
    db.session.commit()
    return jsonify({"message": "Saved filter updated successfully", "filter": sf.to_dict()})


@api_v1_bp.route("/saved-filters/<int:filter_id>", methods=["DELETE"])
@require_api_token("write:filters")
def delete_saved_filter(filter_id):
    """Delete saved filter
    ---
    tags:
      - SavedFilters
    """
    from sqlalchemy.orm import joinedload
    
    sf = SavedFilter.query.options(joinedload(SavedFilter.user)).filter_by(id=filter_id).first_or_404()
    
    if sf.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(sf)
    db.session.commit()
    return jsonify({"message": "Saved filter deleted successfully"})


# ==================== Time Entry Templates ====================


@api_v1_bp.route("/time-entry-templates", methods=["GET"])
@require_api_token("read:time_entries")
def list_time_entry_templates():
    """List time entry templates for current user
    ---
    tags:
      - TimeEntryTemplates
    """
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = TimeEntryTemplate.query.options(
        joinedload(TimeEntryTemplate.user),
        joinedload(TimeEntryTemplate.project)
    )
    query = query.filter(TimeEntryTemplate.user_id == g.api_user.id)
    query = query.order_by(TimeEntryTemplate.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"templates": [t.to_dict() for t in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/time-entry-templates/<int:tpl_id>", methods=["GET"])
@require_api_token("read:time_entries")
def get_time_entry_template(tpl_id):
    """Get time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    from sqlalchemy.orm import joinedload
    
    tpl = TimeEntryTemplate.query.options(
        joinedload(TimeEntryTemplate.user),
        joinedload(TimeEntryTemplate.project)
    ).filter_by(id=tpl_id).first_or_404()
    
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({"template": tpl.to_dict()})


@api_v1_bp.route("/time-entry-templates", methods=["POST"])
@require_api_token("write:time_entries")
def create_time_entry_template():
    """Create time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    data = request.get_json() or {}
    required = ["name"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    tpl = TimeEntryTemplate(
        user_id=g.api_user.id,
        name=data["name"],
        description=data.get("description"),
        project_id=data.get("project_id"),
        task_id=data.get("task_id"),
        default_duration_minutes=data.get("default_duration_minutes"),
        default_notes=data.get("default_notes"),
        tags=data.get("tags"),
        billable=bool(data.get("billable", True)),
    )
    db.session.add(tpl)
    db.session.commit()
    return jsonify({"message": "Template created successfully", "template": tpl.to_dict()}), 201


@api_v1_bp.route("/time-entry-templates/<int:tpl_id>", methods=["PUT", "PATCH"])
@require_api_token("write:time_entries")
def update_time_entry_template(tpl_id):
    """Update time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    from sqlalchemy.orm import joinedload
    
    tpl = TimeEntryTemplate.query.options(
        joinedload(TimeEntryTemplate.user),
        joinedload(TimeEntryTemplate.project)
    ).filter_by(id=tpl_id).first_or_404()
    
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    for field in (
        "name",
        "description",
        "project_id",
        "task_id",
        "default_duration_minutes",
        "default_notes",
        "tags",
        "billable",
    ):
        if field in data:
            setattr(tpl, field, data[field])
    db.session.commit()
    return jsonify({"message": "Template updated successfully", "template": tpl.to_dict()})


@api_v1_bp.route("/time-entry-templates/<int:tpl_id>", methods=["DELETE"])
@require_api_token("write:time_entries")
def delete_time_entry_template(tpl_id):
    """Delete time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    from sqlalchemy.orm import joinedload
    
    tpl = TimeEntryTemplate.query.options(
        joinedload(TimeEntryTemplate.user),
        joinedload(TimeEntryTemplate.project)
    ).filter_by(id=tpl_id).first_or_404()
    
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({"message": "Template deleted successfully"})


# ==================== Comments ====================


@api_v1_bp.route("/comments", methods=["GET"])
@require_api_token("read:comments")
def list_comments():
    """List comments by project or task
    ---
    tags:
      - Comments
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: task_id
        in: query
        type: integer
    """
    project_id = request.args.get("project_id", type=int)
    task_id = request.args.get("task_id", type=int)
    if not project_id and not task_id:
        return jsonify({"error": "project_id or task_id is required"}), 400
    if project_id:
        comments = Comment.get_project_comments(project_id)
    else:
        comments = Comment.get_task_comments(task_id)
    return jsonify({"comments": [c.to_dict() for c in comments]})


@api_v1_bp.route("/comments", methods=["POST"])
@require_api_token("write:comments")
def create_comment():
    """Create comment
    ---
    tags:
      - Comments
    """
    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    if not content:
        return jsonify({"error": "content is required"}), 400
    if (not project_id and not task_id) or (project_id and task_id):
        return jsonify({"error": "Provide either project_id or task_id"}), 400
    cmt = Comment(
        content=content, user_id=g.api_user.id, project_id=project_id, task_id=task_id, parent_id=data.get("parent_id")
    )
    db.session.add(cmt)
    db.session.commit()
    return jsonify({"message": "Comment created successfully", "comment": cmt.to_dict()}), 201


@api_v1_bp.route("/quotes", methods=["GET"])
@require_api_token("read:quotes")
def list_quotes():
    """List quotes
    ---
    tags:
      - Quotes
    """
    from app.models import Quote

    from app.services import QuoteService
    from sqlalchemy.orm import joinedload
    
    status = request.args.get("status")
    client_id = request.args.get("client_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Use service layer with eager loading
    quote_service = QuoteService()
    result = quote_service.list_quotes(
        user_id=g.api_user.id if not g.api_user.is_admin else None,
        is_admin=g.api_user.is_admin,
        status=status,
        search=None,
        include_analytics=False,
    )
    
    quotes = result["quotes"]
    
    # Apply client filter if needed
    if client_id:
        quotes = [q for q in quotes if q.client_id == client_id]
    
    # Paginate manually (service doesn't paginate yet)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_quotes = quotes[start:end]
    
    pagination_dict = {
        "page": page,
        "per_page": per_page,
        "total": len(quotes),
        "pages": (len(quotes) + per_page - 1) // per_page,
        "has_next": end < len(quotes),
        "has_prev": page > 1,
        "next_page": page + 1 if end < len(quotes) else None,
        "prev_page": page - 1 if page > 1 else None,
    }
    
    return jsonify({"quotes": [q.to_dict() for q in paginated_quotes], "pagination": pagination_dict}), 200


@api_v1_bp.route("/quotes/<int:quote_id>", methods=["GET"])
@require_api_token("read:quotes")
def get_quote(quote_id):
    """Get quote
    ---
    tags:
      - Quotes
    """
    from app.models import Quote

    from app.services import QuoteService
    
    quote_service = QuoteService()
    quote = quote_service.get_quote_with_details(
        quote_id=quote_id,
        user_id=g.api_user.id if not g.api_user.is_admin else None,
        is_admin=g.api_user.is_admin
    )
    
    if not quote:
        return jsonify({"error": "Quote not found"}), 404
    
    return jsonify({"quote": quote.to_dict()}), 200


@api_v1_bp.route("/quotes", methods=["POST"])
@require_api_token("write:quotes")
def create_quote():
    """Create quote
    ---
    tags:
      - Quotes
    """
    from app.services import QuoteService
    from app.models import QuoteItem
    from decimal import Decimal
    from datetime import date

    data = request.get_json() or {}
    client_id = data.get("client_id")
    title = data.get("title", "").strip()

    if not client_id or not title:
        return jsonify({"error": "client_id and title are required"}), 400

    # Parse valid_until if provided
    valid_until = None
    if data.get("valid_until"):
        valid_until = _parse_date(data.get("valid_until"))

    # Use service layer to create quote
    quote_service = QuoteService()
    result = quote_service.create_quote(
        client_id=client_id,
        title=title,
        created_by=g.api_user.id,
        description=data.get("description"),
        total_amount=Decimal(str(data.get("total_amount", 0))) if data.get("total_amount") else None,
        hourly_rate=Decimal(str(data.get("hourly_rate"))) if data.get("hourly_rate") else None,
        estimated_hours=data.get("estimated_hours"),
        tax_rate=Decimal(str(data.get("tax_rate", 0))) if data.get("tax_rate") else None,
        currency_code=data.get("currency_code", "EUR"),
        valid_until=valid_until,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create quote")}), 400

    quote = result["quote"]

    # Add items
    items = data.get("items", [])
    for item_data in items:
        item = QuoteItem(
            quote_id=quote.id,
            description=item_data.get("description", ""),
            quantity=Decimal(str(item_data.get("quantity", 1))),
            unit_price=Decimal(str(item_data.get("unit_price", 0))),
            unit=item_data.get("unit"),
        )
        db.session.add(item)

    quote.calculate_totals()
    db.session.commit()

    return jsonify({"message": "Quote created successfully", "quote": quote.to_dict()}), 201


@api_v1_bp.route("/quotes/<int:quote_id>", methods=["PUT", "PATCH"])
@require_api_token("write:quotes")
def update_quote(quote_id):
    """Update quote
    ---
    tags:
      - Quotes
    """
    from app.models import Quote, QuoteItem
    from decimal import Decimal

    from app.services import QuoteService
    from app.models import QuoteItem
    from decimal import Decimal

    data = request.get_json() or {}

    # Use service layer to update quote
    quote_service = QuoteService()
    
    # Prepare update kwargs
    update_kwargs = {}
    if "title" in data:
        update_kwargs["title"] = data["title"].strip()
    if "description" in data:
        update_kwargs["description"] = data["description"].strip() if data["description"] else None
    if "tax_rate" in data:
        update_kwargs["tax_rate"] = Decimal(str(data["tax_rate"]))
    if "currency_code" in data:
        update_kwargs["currency_code"] = data["currency_code"]
    if "status" in data:
        update_kwargs["status"] = data["status"]
    if "payment_terms" in data:
        update_kwargs["payment_terms"] = data["payment_terms"]
    if "valid_until" in data:
        valid_until = _parse_date(data["valid_until"])
        if valid_until:
            update_kwargs["valid_until"] = valid_until

    result = quote_service.update_quote(
        quote_id=quote_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        **update_kwargs
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update quote")}), 400

    quote = result["quote"]

    # Update items if provided
    if "items" in data:
        # Delete existing items
        for item in quote.items:
            db.session.delete(item)

        # Add new items
        for item_data in data["items"]:
            item = QuoteItem(
                quote_id=quote.id,
                description=item_data.get("description", ""),
                quantity=Decimal(str(item_data.get("quantity", 1))),
                unit_price=Decimal(str(item_data.get("unit_price", 0))),
                unit=item_data.get("unit"),
            )
            db.session.add(item)

        quote.calculate_totals()
        db.session.commit()

    return jsonify({"message": "Quote updated successfully", "quote": quote.to_dict()}), 200


@api_v1_bp.route("/quotes/<int:quote_id>", methods=["DELETE"])
@require_api_token("write:quotes")
def delete_quote(quote_id):
    """Delete quote
    ---
    tags:
      - Quotes
    """
    from app.models import Quote

    from app.services import QuoteService
    from sqlalchemy.orm import joinedload
    
    # Use service layer with eager loading
    quote_service = QuoteService()
    quote = quote_service.get_quote_with_details(
        quote_id=quote_id,
        user_id=g.api_user.id if not g.api_user.is_admin else None,
        is_admin=g.api_user.is_admin
    )
    
    if not quote:
        return jsonify({"error": "Quote not found"}), 404
    
    # Check permissions
    if not g.api_user.is_admin and quote.created_by != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(quote)
    db.session.commit()
    return jsonify({"message": "Quote deleted successfully"}), 200


@api_v1_bp.route("/comments/<int:comment_id>", methods=["PUT", "PATCH"])
@require_api_token("write:comments")
def update_comment(comment_id):
    """Update comment
    ---
    tags:
      - Comments
    """
    from sqlalchemy.orm import joinedload
    
    cmt = Comment.query.options(
        joinedload(Comment.user),
        joinedload(Comment.project),
        joinedload(Comment.task)
    ).filter_by(id=comment_id).first_or_404()
    
    if cmt.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.get_json() or {}
    new_content = (data.get("content") or "").strip()
    if not new_content:
        return jsonify({"error": "content is required"}), 400
    try:
        cmt.edit_content(new_content, g.api_user)
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"message": "Comment updated successfully", "comment": cmt.to_dict()})


@api_v1_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@require_api_token("write:comments")
def delete_comment(comment_id):
    """Delete comment
    ---
    tags:
      - Comments
    """
    from sqlalchemy.orm import joinedload
    
    cmt = Comment.query.options(
        joinedload(Comment.user),
        joinedload(Comment.project),
        joinedload(Comment.task)
    ).filter_by(id=comment_id).first_or_404()
    
    try:
        cmt.delete_comment(g.api_user)
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"message": "Comment deleted successfully"})


# ==================== Client Notes ====================


@api_v1_bp.route("/clients/<int:client_id>/notes", methods=["GET"])
@require_api_token("read:clients")
def list_client_notes(client_id):
    """List client notes (paginated, important first)"""
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = ClientNote.query.options(
        joinedload(ClientNote.client),
        joinedload(ClientNote.created_by_user)
    )
    query = query.filter(ClientNote.client_id == client_id)
    query = query.order_by(ClientNote.is_important.desc(), ClientNote.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"notes": [n.to_dict() for n in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/clients/<int:client_id>/notes", methods=["POST"])
@require_api_token("write:clients")
def create_client_note(client_id):
    """Create client note"""
    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400
    note = ClientNote(
        content=content, user_id=g.api_user.id, client_id=client_id, is_important=bool(data.get("is_important", False))
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({"message": "Client note created successfully", "note": note.to_dict()}), 201


@api_v1_bp.route("/client-notes/<int:note_id>", methods=["GET"])
@require_api_token("read:clients")
def get_client_note(note_id):
    from sqlalchemy.orm import joinedload
    
    note = ClientNote.query.options(
        joinedload(ClientNote.client),
        joinedload(ClientNote.created_by_user)
    ).filter_by(id=note_id).first_or_404()
    
    return jsonify({"note": note.to_dict()})


@api_v1_bp.route("/client-notes/<int:note_id>", methods=["PUT", "PATCH"])
@require_api_token("write:clients")
def update_client_note(note_id):
    from sqlalchemy.orm import joinedload
    
    note = ClientNote.query.options(
        joinedload(ClientNote.client),
        joinedload(ClientNote.created_by_user)
    ).filter_by(id=note_id).first_or_404()
    
    data = request.get_json() or {}
    new_content = (data.get("content") or "").strip()
    if not new_content:
        return jsonify({"error": "content is required"}), 400
    if not (g.api_user.is_admin or note.user_id == g.api_user.id):
        return jsonify({"error": "Access denied"}), 403
    note.content = new_content
    if "is_important" in data:
        note.is_important = bool(data["is_important"])
    db.session.commit()
    return jsonify({"message": "Client note updated successfully", "note": note.to_dict()})


@api_v1_bp.route("/client-notes/<int:note_id>", methods=["DELETE"])
@require_api_token("write:clients")
def delete_client_note(note_id):
    from sqlalchemy.orm import joinedload
    
    note = ClientNote.query.options(
        joinedload(ClientNote.client),
        joinedload(ClientNote.created_by_user)
    ).filter_by(id=note_id).first_or_404()
    
    if not (g.api_user.is_admin or note.user_id == g.api_user.id):
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Client note deleted successfully"})


# ==================== Project Costs ====================


@api_v1_bp.route("/projects/<int:project_id>/costs", methods=["GET"])
@require_api_token("read:projects")
def list_project_costs(project_id):
    """List project costs (paginated)"""
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    user_id = request.args.get("user_id", type=int)
    billable_only = request.args.get("billable_only", "false").lower() == "true"
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = ProjectCost.query.options(
        joinedload(ProjectCost.project),
        joinedload(ProjectCost.user)
    )
    query = query.filter(ProjectCost.project_id == project_id)
    
    if start_date:
        query = query.filter(ProjectCost.cost_date >= start_date)
    if end_date:
        query = query.filter(ProjectCost.cost_date <= end_date)
    if user_id:
        query = query.filter(ProjectCost.user_id == user_id)
    if billable_only:
        query = query.filter(ProjectCost.billable == True)
    
    query = query.order_by(ProjectCost.cost_date.desc(), ProjectCost.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"costs": [c.to_dict() for c in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/projects/<int:project_id>/costs", methods=["POST"])
@require_api_token("write:projects")
def create_project_cost(project_id):
    """Create project cost"""
    data = request.get_json() or {}
    required = ["description", "category", "amount", "cost_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal

    try:
        amount = Decimal(str(data["amount"]))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    cost_date = _parse_date(data.get("cost_date"))
    if not cost_date:
        return jsonify({"error": "Invalid cost_date"}), 400
    cost = ProjectCost(
        project_id=project_id,
        user_id=g.api_user.id,
        description=data["description"],
        category=data["category"],
        amount=amount,
        cost_date=cost_date,
        billable=bool(data.get("billable", True)),
        notes=data.get("notes"),
        currency_code=data.get("currency_code", "EUR"),
    )
    db.session.add(cost)
    db.session.commit()
    return jsonify({"message": "Project cost created successfully", "cost": cost.to_dict()}), 201


@api_v1_bp.route("/project-costs/<int:cost_id>", methods=["GET"])
@require_api_token("read:projects")
def get_project_cost(cost_id):
    from sqlalchemy.orm import joinedload
    
    cost = ProjectCost.query.options(
        joinedload(ProjectCost.project),
        joinedload(ProjectCost.user)
    ).filter_by(id=cost_id).first_or_404()
    
    return jsonify({"cost": cost.to_dict()})


@api_v1_bp.route("/project-costs/<int:cost_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_project_cost(cost_id):
    from sqlalchemy.orm import joinedload
    
    cost = ProjectCost.query.options(
        joinedload(ProjectCost.project),
        joinedload(ProjectCost.user)
    ).filter_by(id=cost_id).first_or_404()
    data = request.get_json() or {}
    for field in ("description", "category", "currency_code", "notes", "billable"):
        if field in data:
            setattr(cost, field, data[field])
    if "amount" in data:
        try:
            from decimal import Decimal

            cost.amount = Decimal(str(data["amount"]))
        except Exception:
            pass
    if "cost_date" in data:
        parsed = _parse_date(data["cost_date"])
        if parsed:
            cost.cost_date = parsed
    db.session.commit()
    return jsonify({"message": "Project cost updated successfully", "cost": cost.to_dict()})


@api_v1_bp.route("/project-costs/<int:cost_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_project_cost(cost_id):
    from sqlalchemy.orm import joinedload
    
    cost = ProjectCost.query.options(
        joinedload(ProjectCost.project),
        joinedload(ProjectCost.user)
    ).filter_by(id=cost_id).first_or_404()
    
    db.session.delete(cost)
    db.session.commit()
    return jsonify({"message": "Project cost deleted successfully"})


# ==================== Tax Rules (Admin) ====================


@api_v1_bp.route("/tax-rules", methods=["GET"])
@require_api_token("admin:all")
def list_tax_rules():
    """List tax rules (admin)"""
    rules = TaxRule.query.order_by(TaxRule.created_at.desc()).all()
    return jsonify(
        {
            "tax_rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "country": r.country,
                    "region": r.region,
                    "client_id": r.client_id,
                    "project_id": r.project_id,
                    "tax_code": r.tax_code,
                    "rate_percent": float(r.rate_percent),
                    "compound": r.compound,
                    "inclusive": r.inclusive,
                    "start_date": r.start_date.isoformat() if r.start_date else None,
                    "end_date": r.end_date.isoformat() if r.end_date else None,
                    "active": r.active,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rules
            ]
        }
    )


@api_v1_bp.route("/tax-rules", methods=["POST"])
@require_api_token("admin:all")
def create_tax_rule():
    data = request.get_json() or {}
    required = ["name", "rate_percent"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal

    try:
        rate = Decimal(str(data["rate_percent"]))
    except Exception:
        return jsonify({"error": "Invalid rate_percent"}), 400
    rule = TaxRule(
        name=data["name"],
        country=data.get("country"),
        region=data.get("region"),
        client_id=data.get("client_id"),
        project_id=data.get("project_id"),
        tax_code=data.get("tax_code"),
        rate_percent=rate,
        compound=bool(data.get("compound", False)),
        inclusive=bool(data.get("inclusive", False)),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        active=bool(data.get("active", True)),
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({"message": "Tax rule created successfully", "tax_rule": {"id": rule.id}}), 201


@api_v1_bp.route("/tax-rules/<int:rule_id>", methods=["PUT", "PATCH"])
@require_api_token("admin:all")
def update_tax_rule(rule_id):
    from sqlalchemy.orm import joinedload
    
    rule = TaxRule.query.options(
        joinedload(TaxRule.client),
        joinedload(TaxRule.project)
    ).filter_by(id=rule_id).first_or_404()
    
    data = request.get_json() or {}
    for field in (
        "name",
        "country",
        "region",
        "client_id",
        "project_id",
        "tax_code",
        "compound",
        "inclusive",
        "active",
    ):
        if field in data:
            setattr(rule, field, data[field])
    if "rate_percent" in data:
        try:
            from decimal import Decimal

            rule.rate_percent = Decimal(str(data["rate_percent"]))
        except Exception:
            pass
    if "start_date" in data:
        rule.start_date = _parse_date(data["start_date"])
    if "end_date" in data:
        rule.end_date = _parse_date(data["end_date"])
    db.session.commit()
    return jsonify({"message": "Tax rule updated successfully"})


@api_v1_bp.route("/tax-rules/<int:rule_id>", methods=["DELETE"])
@require_api_token("admin:all")
def delete_tax_rule(rule_id):
    rule = TaxRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "Tax rule deleted successfully"})


# ==================== Currencies & Exchange Rates ====================


@api_v1_bp.route("/currencies", methods=["GET"])
@require_api_token("read:invoices")
def list_currencies():
    cur_list = Currency.query.order_by(Currency.code.asc()).all()
    return jsonify(
        {
            "currencies": [
                {
                    "code": c.code,
                    "name": c.name,
                    "symbol": c.symbol,
                    "decimal_places": c.decimal_places,
                    "is_active": c.is_active,
                }
                for c in cur_list
            ]
        }
    )


@api_v1_bp.route("/currencies", methods=["POST"])
@require_api_token("admin:all")
def create_currency():
    data = request.get_json() or {}
    required = ["code", "name"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    code = data["code"].upper().strip()
    if Currency.query.get(code):
        return jsonify({"error": "Currency already exists"}), 400
    cur = Currency(
        code=code,
        name=data["name"],
        symbol=data.get("symbol"),
        decimal_places=int(data.get("decimal_places", 2)),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(cur)
    db.session.commit()
    return jsonify({"message": "Currency created successfully", "currency": {"code": cur.code}}), 201


@api_v1_bp.route("/currencies/<string:code>", methods=["PUT", "PATCH"])
@require_api_token("admin:all")
def update_currency(code):
    cur = Currency.query.get_or_404(code.upper())
    data = request.get_json() or {}
    for field in ("name", "symbol", "decimal_places", "is_active"):
        if field in data:
            setattr(cur, field, data[field])
    db.session.commit()
    return jsonify({"message": "Currency updated successfully"})


@api_v1_bp.route("/exchange-rates", methods=["GET"])
@require_api_token("read:invoices")
def list_exchange_rates():
    base = request.args.get("base_code")
    quote = request.args.get("quote_code")
    date_str = request.args.get("date")
    q = ExchangeRate.query
    if base:
        q = q.filter(ExchangeRate.base_code == base.upper())
    if quote:
        q = q.filter(ExchangeRate.quote_code == quote.upper())
    if date_str:
        d = _parse_date(date_str)
        if d:
            q = q.filter(ExchangeRate.date == d)
    rates = q.order_by(ExchangeRate.date.desc()).limit(200).all()
    return jsonify(
        {
            "exchange_rates": [
                {
                    "id": r.id,
                    "base_code": r.base_code,
                    "quote_code": r.quote_code,
                    "rate": float(r.rate),
                    "date": r.date.isoformat(),
                    "source": r.source,
                }
                for r in rates
            ]
        }
    )


@api_v1_bp.route("/exchange-rates", methods=["POST"])
@require_api_token("admin:all")
def create_exchange_rate():
    data = request.get_json() or {}
    required = ["base_code", "quote_code", "rate", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal

    try:
        rate_val = Decimal(str(data["rate"]))
    except Exception:
        return jsonify({"error": "Invalid rate"}), 400
    d = _parse_date(data["date"])
    if not d:
        return jsonify({"error": "Invalid date"}), 400
    er = ExchangeRate(
        base_code=data["base_code"].upper(),
        quote_code=data["quote_code"].upper(),
        rate=rate_val,
        date=d,
        source=data.get("source"),
    )
    db.session.add(er)
    db.session.commit()
    return jsonify({"message": "Exchange rate created successfully", "exchange_rate": {"id": er.id}}), 201


@api_v1_bp.route("/exchange-rates/<int:rate_id>", methods=["PUT", "PATCH"])
@require_api_token("admin:all")
def update_exchange_rate(rate_id):
    er = ExchangeRate.query.get_or_404(rate_id)
    data = request.get_json() or {}
    if "rate" in data:
        try:
            from decimal import Decimal

            er.rate = Decimal(str(data["rate"]))
        except Exception:
            pass
    if "date" in data:
        d = _parse_date(data["date"])
        if d:
            er.date = d
    if "source" in data:
        er.source = data["source"]
    db.session.commit()
    return jsonify({"message": "Exchange rate updated successfully"})


# ==================== Favorites ====================


@api_v1_bp.route("/users/me/favorites/projects", methods=["GET"])
@require_api_token("read:projects")
def list_favorite_projects():
    favs = UserFavoriteProject.query.filter_by(user_id=g.api_user.id).all()
    return jsonify({"favorites": [f.to_dict() for f in favs]})


@api_v1_bp.route("/users/me/favorites/projects", methods=["POST"])
@require_api_token("write:projects")
def add_favorite_project():
    data = request.get_json() or {}
    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    # Prevent duplicates due to unique constraint
    existing = UserFavoriteProject.query.filter_by(user_id=g.api_user.id, project_id=project_id).first()
    if existing:
        return jsonify({"message": "Already favorited", "favorite": existing.to_dict()}), 200
    fav = UserFavoriteProject(user_id=g.api_user.id, project_id=project_id)
    db.session.add(fav)
    db.session.commit()
    return jsonify({"message": "Project favorited successfully", "favorite": fav.to_dict()}), 201


@api_v1_bp.route("/users/me/favorites/projects/<int:project_id>", methods=["DELETE"])
@require_api_token("write:projects")
def remove_favorite_project(project_id):
    fav = UserFavoriteProject.query.filter_by(user_id=g.api_user.id, project_id=project_id).first_or_404()
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"message": "Favorite removed successfully"})


# ==================== Audit Logs (Admin) ====================


@api_v1_bp.route("/audit-logs", methods=["GET"])
@require_api_token("admin:all")
def list_audit_logs():
    """List audit logs (admin)"""
    entity_type = request.args.get("entity_type")
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action")
    limit = request.args.get("limit", type=int) or 100
    q = AuditLog.query
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({"audit_logs": [l.to_dict() for l in logs]})


# ==================== Activities ====================


@api_v1_bp.route("/activities", methods=["GET"])
@require_api_token("read:reports")
def list_activities():
    """List activities"""
    user_id = request.args.get("user_id", type=int)
    entity_type = request.args.get("entity_type")
    limit = request.args.get("limit", type=int) or 50
    acts = Activity.get_recent(user_id=user_id, limit=limit, entity_type=entity_type)
    return jsonify({"activities": [a.to_dict() for a in acts]})


# ==================== Invoice PDF Templates (Admin) ====================


@api_v1_bp.route("/invoice-pdf-templates", methods=["GET"])
@require_api_token("admin:all")
def list_invoice_pdf_templates():
    templates = InvoicePDFTemplate.get_all_templates()
    return jsonify({"templates": [t.to_dict() for t in templates]})


@api_v1_bp.route("/invoice-pdf-templates/<string:page_size>", methods=["GET"])
@require_api_token("admin:all")
def get_invoice_pdf_template(page_size):
    tpl = InvoicePDFTemplate.get_template(page_size)
    return jsonify({"template": tpl.to_dict()})


# ==================== Invoice Templates (Admin) ====================


@api_v1_bp.route("/invoice-templates", methods=["GET"])
@require_api_token("admin:all")
def list_invoice_templates():
    """List invoice templates (admin)"""
    templates = InvoiceTemplate.query.order_by(InvoiceTemplate.name.asc()).all()
    return jsonify(
        {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "html": t.html or "",
                    "css": t.css or "",
                    "is_default": t.is_default,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in templates
            ]
        }
    )


@api_v1_bp.route("/invoice-templates/<int:template_id>", methods=["GET"])
@require_api_token("admin:all")
def get_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    return jsonify(
        {
            "template": {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "html": t.html or "",
                "css": t.css or "",
                "is_default": t.is_default,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
        }
    )


@api_v1_bp.route("/invoice-templates", methods=["POST"])
@require_api_token("admin:all")
def create_invoice_template():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    # Enforce unique name
    if InvoiceTemplate.query.filter_by(name=name).first():
        return jsonify({"error": "Template name already exists"}), 400
    is_default = bool(data.get("is_default", False))
    if is_default:
        InvoiceTemplate.query.update({InvoiceTemplate.is_default: False})
    t = InvoiceTemplate(
        name=name,
        description=(data.get("description") or "").strip() or None,
        html=(data.get("html") or "").strip() or None,
        css=(data.get("css") or "").strip() or None,
        is_default=is_default,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"message": "Invoice template created successfully", "template": {"id": t.id}}), 201


@api_v1_bp.route("/invoice-templates/<int:template_id>", methods=["PUT", "PATCH"])
@require_api_token("admin:all")
def update_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    data = request.get_json() or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        # Check duplicate name
        existing = InvoiceTemplate.query.filter(InvoiceTemplate.name == name, InvoiceTemplate.id != template_id).first()
        if existing:
            return jsonify({"error": "Template name already exists"}), 400
        t.name = name
    for field in ("description", "html", "css"):
        if field in data:
            setattr(t, field, (data.get(field) or "").strip() or None)
    if "is_default" in data and bool(data["is_default"]):
        # set this as default, unset others
        InvoiceTemplate.query.filter(InvoiceTemplate.id != template_id).update({InvoiceTemplate.is_default: False})
        t.is_default = True
    db.session.commit()
    return jsonify({"message": "Invoice template updated successfully"})


@api_v1_bp.route("/invoice-templates/<int:template_id>", methods=["DELETE"])
@require_api_token("admin:all")
def delete_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    # In a stricter implementation, we could prevent deletion if referenced
    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "Invoice template deleted successfully"})


# ==================== Recurring Invoices ====================


@api_v1_bp.route("/recurring-invoices", methods=["GET"])
@require_api_token("read:recurring_invoices")
def list_recurring_invoices():
    """List recurring invoice templates
    ---
    tags:
      - RecurringInvoices
    """
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = RecurringInvoice.query.options(
        joinedload(RecurringInvoice.project),
        joinedload(RecurringInvoice.client)
    )
    
    is_active = request.args.get("is_active")
    if is_active is not None:
        query = query.filter(RecurringInvoice.is_active == (is_active.lower() == "true"))
    client_id = request.args.get("client_id", type=int)
    if client_id:
        query = query.filter(RecurringInvoice.client_id == client_id)
    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter(RecurringInvoice.project_id == project_id)
    
    query = query.order_by(RecurringInvoice.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify({"recurring_invoices": [ri.to_dict() for ri in pagination.items], "pagination": pagination_dict})


@api_v1_bp.route("/recurring-invoices/<int:ri_id>", methods=["GET"])
@require_api_token("read:recurring_invoices")
def get_recurring_invoice(ri_id):
    """Get a recurring invoice template"""
    from sqlalchemy.orm import joinedload
    
    ri = RecurringInvoice.query.options(
        joinedload(RecurringInvoice.project),
        joinedload(RecurringInvoice.client)
    ).filter_by(id=ri_id).first_or_404()
    
    return jsonify({"recurring_invoice": ri.to_dict()})


@api_v1_bp.route("/recurring-invoices", methods=["POST"])
@require_api_token("write:recurring_invoices")
def create_recurring_invoice():
    """Create a recurring invoice template
    ---
    tags:
      - RecurringInvoices
    """
    data = request.get_json() or {}
    required = ["name", "project_id", "client_id", "client_name", "frequency", "next_run_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    freq = (data.get("frequency") or "").lower()
    if freq not in ("daily", "weekly", "monthly", "yearly"):
        return jsonify({"error": "Invalid frequency"}), 400
    next_date = _parse_date(data.get("next_run_date"))
    if not next_date:
        return jsonify({"error": "Invalid next_run_date (YYYY-MM-DD)"}), 400
    ri = RecurringInvoice(
        name=data["name"],
        project_id=data["project_id"],
        client_id=data["client_id"],
        frequency=freq,
        next_run_date=next_date,
        created_by=g.api_user.id,
        interval=data.get("interval", 1),
        end_date=_parse_date(data.get("end_date")),
        client_name=data["client_name"],
        client_email=data.get("client_email"),
        client_address=data.get("client_address"),
        due_date_days=data.get("due_date_days", 30),
        tax_rate=data.get("tax_rate", 0),
        currency_code=data.get("currency_code", "EUR"),
        notes=data.get("notes"),
        terms=data.get("terms"),
        template_id=data.get("template_id"),
        auto_send=bool(data.get("auto_send", False)),
        auto_include_time_entries=bool(data.get("auto_include_time_entries", True)),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(ri)
    db.session.commit()
    return jsonify({"message": "Recurring invoice created successfully", "recurring_invoice": ri.to_dict()}), 201


@api_v1_bp.route("/recurring-invoices/<int:ri_id>", methods=["PUT", "PATCH"])
@require_api_token("write:recurring_invoices")
def update_recurring_invoice(ri_id):
    """Update a recurring invoice template"""
    from sqlalchemy.orm import joinedload
    
    ri = RecurringInvoice.query.options(
        joinedload(RecurringInvoice.project),
        joinedload(RecurringInvoice.client)
    ).filter_by(id=ri_id).first_or_404()
    
    data = request.get_json() or {}
    for field in ("name", "client_name", "client_email", "client_address", "notes", "terms", "currency_code"):
        if field in data:
            setattr(ri, field, data[field])
    if "frequency" in data and data["frequency"] in ("daily", "weekly", "monthly", "yearly"):
        ri.frequency = data["frequency"]
    if "interval" in data:
        try:
            ri.interval = int(data["interval"])
        except Exception:
            pass
    if "next_run_date" in data:
        parsed = _parse_date(data["next_run_date"])
        if parsed:
            ri.next_run_date = parsed
    if "end_date" in data:
        ri.end_date = _parse_date(data["end_date"])
    for bfield in ("auto_send", "auto_include_time_entries", "is_active"):
        if bfield in data:
            setattr(ri, bfield, bool(data[bfield]))
    if "due_date_days" in data:
        try:
            ri.due_date_days = int(data["due_date_days"])
        except Exception:
            pass
    if "tax_rate" in data:
        try:
            from decimal import Decimal

            ri.tax_rate = Decimal(str(data["tax_rate"]))
        except Exception:
            pass
    db.session.commit()
    return jsonify({"message": "Recurring invoice updated successfully", "recurring_invoice": ri.to_dict()})


@api_v1_bp.route("/recurring-invoices/<int:ri_id>", methods=["DELETE"])
@require_api_token("write:recurring_invoices")
def delete_recurring_invoice(ri_id):
    """Deactivate a recurring invoice template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    ri.is_active = False
    db.session.commit()
    return jsonify({"message": "Recurring invoice deactivated successfully"})


@api_v1_bp.route("/recurring-invoices/<int:ri_id>/generate", methods=["POST"])
@require_api_token("write:recurring_invoices")
def generate_from_recurring_invoice(ri_id):
    """Generate an invoice from a recurring template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    invoice = ri.generate_invoice()
    if not invoice:
        return jsonify({"message": "No invoice generated (not due yet or inactive)"}), 200
    db.session.commit()
    return jsonify({"message": "Invoice generated successfully", "invoice": invoice.to_dict()}), 201


# ==================== Credit Notes ====================


@api_v1_bp.route("/credit-notes", methods=["GET"])
@require_api_token("read:invoices")
def list_credit_notes():
    """List credit notes
    ---
    tags:
      - CreditNotes
    """
    from sqlalchemy.orm import joinedload
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = CreditNote.query.options(joinedload(CreditNote.invoice))
    
    invoice_id = request.args.get("invoice_id", type=int)
    if invoice_id:
        query = query.filter(CreditNote.invoice_id == invoice_id)
    
    query = query.order_by(CreditNote.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    
    return jsonify(
        {
            "credit_notes": [
                {
                    "id": cn.id,
                    "invoice_id": cn.invoice_id,
                    "credit_number": cn.credit_number,
                    "amount": float(cn.amount),
                    "reason": cn.reason,
                    "created_by": cn.created_by,
                    "created_at": cn.created_at.isoformat() if cn.created_at else None,
                }
                for cn in pagination.items
            ],
            "pagination": pagination_dict,
        }
    )


@api_v1_bp.route("/credit-notes/<int:cn_id>", methods=["GET"])
@require_api_token("read:invoices")
def get_credit_note(cn_id):
    """Get credit note"""
    from sqlalchemy.orm import joinedload
    
    cn = CreditNote.query.options(joinedload(CreditNote.invoice)).filter_by(id=cn_id).first_or_404()
    
    return jsonify(
        {
            "credit_note": {
                "id": cn.id,
                "invoice_id": cn.invoice_id,
                "credit_number": cn.credit_number,
                "amount": float(cn.amount),
                "reason": cn.reason,
                "created_by": cn.created_by,
                "created_at": cn.created_at.isoformat() if cn.created_at else None,
            }
        }
    )


@api_v1_bp.route("/credit-notes", methods=["POST"])
@require_api_token("write:invoices")
def create_credit_note():
    """Create credit note"""
    data = request.get_json() or {}
    required = ["invoice_id", "amount"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    inv = Invoice.query.get(data["invoice_id"])
    if not inv:
        return jsonify({"error": "Invalid invoice_id"}), 400
    from decimal import Decimal

    try:
        amt = Decimal(str(data["amount"]))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    # Generate credit number (simple: CN-<invoice_id>-<timestamp>)
    credit_number = f"CN-{inv.id}-{int(datetime.utcnow().timestamp())}"
    cn = CreditNote(
        invoice_id=inv.id,
        credit_number=credit_number,
        amount=amt,
        reason=data.get("reason"),
        created_by=g.api_user.id,
    )
    db.session.add(cn)
    db.session.commit()
    return (
        jsonify(
            {
                "message": "Credit note created successfully",
                "credit_note": {
                    "id": cn.id,
                    "invoice_id": cn.invoice_id,
                    "credit_number": cn.credit_number,
                    "amount": float(cn.amount),
                    "reason": cn.reason,
                    "created_by": cn.created_by,
                    "created_at": cn.created_at.isoformat() if cn.created_at else None,
                },
            }
        ),
        201,
    )


@api_v1_bp.route("/credit-notes/<int:cn_id>", methods=["PUT", "PATCH"])
@require_api_token("write:invoices")
def update_credit_note(cn_id):
    """Update credit note"""
    from sqlalchemy.orm import joinedload
    
    cn = CreditNote.query.options(joinedload(CreditNote.invoice)).filter_by(id=cn_id).first_or_404()
    
    data = request.get_json() or {}
    if "reason" in data:
        cn.reason = data["reason"]
    if "amount" in data:
        try:
            from decimal import Decimal

            cn.amount = Decimal(str(data["amount"]))
        except Exception:
            pass
    db.session.commit()
    return jsonify({"message": "Credit note updated successfully"})


@api_v1_bp.route("/credit-notes/<int:cn_id>", methods=["DELETE"])
@require_api_token("write:invoices")
def delete_credit_note(cn_id):
    """Delete credit note"""
    from sqlalchemy.orm import joinedload
    
    cn = CreditNote.query.options(joinedload(CreditNote.invoice)).filter_by(id=cn_id).first_or_404()
    
    db.session.delete(cn)
    db.session.commit()
    return jsonify({"message": "Credit note deleted successfully"})


# ==================== Reports ====================


@api_v1_bp.route("/reports/summary", methods=["GET"])
@require_api_token("read:reports")
def report_summary():
    """Get time tracking summary report
    ---
    tags:
      - Reports
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: project_id
        in: query
        type: integer
      - name: user_id
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: Summary report
    """
    # Date range (default to last 30 days)
    end_date = request.args.get("end_date")
    start_date = request.args.get("start_date")

    if not end_date:
        end_dt = datetime.utcnow()
    else:
        end_dt = parse_datetime(end_date) or datetime.utcnow()

    if not start_date:
        start_dt = end_dt - timedelta(days=30)
    else:
        start_dt = parse_datetime(start_date) or (end_dt - timedelta(days=30))

    # Build query with eager loading
    from sqlalchemy.orm import joinedload
    
    query = TimeEntry.query.options(
        joinedload(TimeEntry.project),
        joinedload(TimeEntry.user),
        joinedload(TimeEntry.task)
    ).filter(
        TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_dt, TimeEntry.start_time <= end_dt
    )

    # Filter by user
    user_id = request.args.get("user_id", type=int)
    if user_id:
        if g.api_user.is_admin or user_id == g.api_user.id:
            query = query.filter_by(user_id=user_id)
        else:
            return jsonify({"error": "Access denied"}), 403
    elif not g.api_user.is_admin:
        query = query.filter_by(user_id=g.api_user.id)

    # Filter by project
    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)

    entries = query.all()

    # Calculate summary
    total_hours = sum(e.duration_hours or 0 for e in entries)
    billable_hours = sum(e.duration_hours or 0 for e in entries if e.billable)
    total_entries = len(entries)

    # Group by project
    by_project = {}
    for entry in entries:
        if entry.project_id:
            if entry.project_id not in by_project:
                by_project[entry.project_id] = {
                    "project_id": entry.project_id,
                    "project_name": entry.project.name if entry.project else "Unknown",
                    "hours": 0,
                    "entries": 0,
                }
            by_project[entry.project_id]["hours"] += entry.duration_hours or 0
            by_project[entry.project_id]["entries"] += 1

    return jsonify(
        {
            "summary": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "total_hours": round(total_hours, 2),
                "billable_hours": round(billable_hours, 2),
                "total_entries": total_entries,
                "by_project": list(by_project.values()),
            }
        }
    )


# ==================== Users ====================


@api_v1_bp.route("/users/me", methods=["GET"])
@require_api_token("read:users")
def get_current_user():
    """Get current authenticated user information
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Current user information
    """
    return jsonify({"user": g.api_user.to_dict()})


@api_v1_bp.route("/users", methods=["GET"])
@require_api_token("admin:all")
def list_users():
    """List all users (admin only)
    ---
    tags:
      - Users
    parameters:
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of users
    """
    query = User.query.filter_by(is_active=True).order_by(User.username)

    # Paginate
    result = paginate_query(query)

    return jsonify({"users": [u.to_dict() for u in result["items"]], "pagination": result["pagination"]})


# ==================== Webhooks ====================


@api_v1_bp.route("/webhooks", methods=["GET"])
@require_api_token("read:webhooks")
def list_webhooks():
    """List all webhooks
    ---
    tags:
      - Webhooks
    parameters:
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
      - name: is_active
        in: query
        type: boolean
    security:
      - Bearer: []
    responses:
      200:
        description: List of webhooks
    """
    query = Webhook.query

    # Filter by active status
    is_active = request.args.get("is_active")
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == "true")

    # Filter by user (non-admins can only see their own)
    if not g.api_user.is_admin:
        query = query.filter_by(user_id=g.api_user.id)

    query = query.order_by(Webhook.created_at.desc())

    # Paginate
    result = paginate_query(query)

    return jsonify({"webhooks": [w.to_dict() for w in result["items"]], "pagination": result["pagination"]})


@api_v1_bp.route("/webhooks", methods=["POST"])
@require_api_token("write:webhooks")
def create_webhook():
    """Create a new webhook
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    responses:
      201:
        description: Webhook created successfully
      400:
        description: Invalid input
    """
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    if not data.get("url"):
        return jsonify({"error": "url is required"}), 400
    if not data.get("events") or not isinstance(data.get("events"), list):
        return jsonify({"error": "events must be a non-empty list"}), 400

    # Validate URL
    try:
        from urllib.parse import urlparse

        parsed = urlparse(data["url"])
        if not parsed.scheme or not parsed.netloc:
            return jsonify({"error": "Invalid URL format"}), 400
        if parsed.scheme not in ["http", "https"]:
            return jsonify({"error": "URL must use http or https"}), 400
    except Exception:
        return jsonify({"error": "Invalid URL format"}), 400

    # Validate events
    from app.utils.webhook_service import WebhookService

    available_events = WebhookService.get_available_events()
    for event in data["events"]:
        if event != "*" and event not in available_events:
            return jsonify({"error": f"Invalid event type: {event}"}), 400

    # Create webhook
    webhook = Webhook(
        name=data["name"],
        description=data.get("description"),
        url=data["url"],
        events=data["events"],
        http_method=data.get("http_method", "POST"),
        content_type=data.get("content_type", "application/json"),
        headers=data.get("headers"),
        is_active=data.get("is_active", True),
        user_id=g.api_user.id,
        max_retries=data.get("max_retries", 3),
        retry_delay_seconds=data.get("retry_delay_seconds", 60),
        timeout_seconds=data.get("timeout_seconds", 30),
    )

    # Generate secret if requested
    if data.get("generate_secret", True):
        webhook.set_secret()

    db.session.add(webhook)
    db.session.commit()

    return jsonify({"webhook": webhook.to_dict(include_secret=True), "message": "Webhook created successfully"}), 201


@api_v1_bp.route("/webhooks/<int:webhook_id>", methods=["GET"])
@require_api_token("read:webhooks")
def get_webhook(webhook_id):
    """Get a specific webhook
    ---
    tags:
      - Webhooks
    parameters:
      - name: webhook_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Webhook details
      404:
        description: Webhook not found
    """
    from sqlalchemy.orm import joinedload
    
    webhook = Webhook.query.options(joinedload(Webhook.user)).filter_by(id=webhook_id).first_or_404()

    # Check permissions
    if not g.api_user.is_admin and webhook.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"webhook": webhook.to_dict()})


@api_v1_bp.route("/webhooks/<int:webhook_id>", methods=["PUT", "PATCH"])
@require_api_token("write:webhooks")
def update_webhook(webhook_id):
    """Update a webhook
    ---
    tags:
      - Webhooks
    parameters:
      - name: webhook_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Webhook updated successfully
      404:
        description: Webhook not found
    """
    from sqlalchemy.orm import joinedload
    
    webhook = Webhook.query.options(joinedload(Webhook.user)).filter_by(id=webhook_id).first_or_404()

    # Check permissions
    if not g.api_user.is_admin and webhook.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}

    # Update fields
    if "name" in data:
        webhook.name = data["name"]
    if "description" in data:
        webhook.description = data["description"]
    if "url" in data:
        # Validate URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(data["url"])
            if not parsed.scheme or not parsed.netloc:
                return jsonify({"error": "Invalid URL format"}), 400
            if parsed.scheme not in ["http", "https"]:
                return jsonify({"error": "URL must use http or https"}), 400
        except Exception:
            return jsonify({"error": "Invalid URL format"}), 400
        webhook.url = data["url"]
    if "events" in data:
        if not isinstance(data["events"], list):
            return jsonify({"error": "events must be a list"}), 400
        # Validate events
        from app.utils.webhook_service import WebhookService

        available_events = WebhookService.get_available_events()
        for event in data["events"]:
            if event != "*" and event not in available_events:
                return jsonify({"error": f"Invalid event type: {event}"}), 400
        webhook.events = data["events"]
    if "http_method" in data:
        if data["http_method"] not in ["POST", "PUT", "PATCH"]:
            return jsonify({"error": "http_method must be POST, PUT, or PATCH"}), 400
        webhook.http_method = data["http_method"]
    if "content_type" in data:
        webhook.content_type = data["content_type"]
    if "headers" in data:
        webhook.headers = data["headers"]
    if "is_active" in data:
        webhook.is_active = bool(data["is_active"])
    if "max_retries" in data:
        webhook.max_retries = int(data["max_retries"])
    if "retry_delay_seconds" in data:
        webhook.retry_delay_seconds = int(data["retry_delay_seconds"])
    if "timeout_seconds" in data:
        webhook.timeout_seconds = int(data["timeout_seconds"])
    if "generate_secret" in data and data["generate_secret"]:
        webhook.set_secret()

    db.session.commit()

    return jsonify({"webhook": webhook.to_dict(), "message": "Webhook updated successfully"})


@api_v1_bp.route("/webhooks/<int:webhook_id>", methods=["DELETE"])
@require_api_token("write:webhooks")
def delete_webhook(webhook_id):
    """Delete a webhook
    ---
    tags:
      - Webhooks
    parameters:
      - name: webhook_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Webhook deleted successfully
      404:
        description: Webhook not found
    """
    from sqlalchemy.orm import joinedload
    
    webhook = Webhook.query.options(joinedload(Webhook.user)).filter_by(id=webhook_id).first_or_404()

    # Check permissions
    if not g.api_user.is_admin and webhook.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(webhook)
    db.session.commit()

    return jsonify({"message": "Webhook deleted successfully"})


@api_v1_bp.route("/webhooks/<int:webhook_id>/deliveries", methods=["GET"])
@require_api_token("read:webhooks")
def list_webhook_deliveries(webhook_id):
    """List deliveries for a webhook
    ---
    tags:
      - Webhooks
    parameters:
      - name: webhook_id
        in: path
        type: integer
        required: true
      - name: status
        in: query
        type: string
        enum: [pending, success, failed, retrying]
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of deliveries
    """
    from sqlalchemy.orm import joinedload
    
    webhook = Webhook.query.options(joinedload(Webhook.user)).filter_by(id=webhook_id).first_or_404()

    # Check permissions
    if not g.api_user.is_admin and webhook.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    query = WebhookDelivery.query.filter_by(webhook_id=webhook_id)

    # Filter by status
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    query = query.order_by(WebhookDelivery.started_at.desc())

    # Paginate
    result = paginate_query(query)

    return jsonify({"deliveries": [d.to_dict() for d in result["items"]], "pagination": result["pagination"]})


@api_v1_bp.route("/webhooks/events", methods=["GET"])
@require_api_token("read:webhooks")
def list_webhook_events():
    """Get list of available webhook event types
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    responses:
      200:
        description: List of available event types
    """
    from app.utils.webhook_service import WebhookService

    events = WebhookService.get_available_events()

    return jsonify({"events": events})


# ==================== Inventory ====================


@api_v1_bp.route("/inventory/items", methods=["GET"])
@require_api_token("read:projects")  # Use existing scope for now
def list_stock_items_api():
    """List stock items"""
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "")
    active_only = request.args.get("active_only", "true").lower() == "true"

    query = StockItem.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(StockItem.sku.ilike(like), StockItem.name.ilike(like), StockItem.barcode.ilike(like)))

    if category:
        query = query.filter_by(category=category)

    result = paginate_query(query.order_by(StockItem.name))
    result["items"] = [item.to_dict() for item in result["items"]]

    return jsonify(result)


@api_v1_bp.route("/inventory/items/<int:item_id>", methods=["GET"])
@require_api_token("read:projects")
def get_stock_item_api(item_id):
    """Get stock item details"""
    item = StockItem.query.get_or_404(item_id)
    return jsonify({"item": item.to_dict()})


@api_v1_bp.route("/inventory/items/<int:item_id>/availability", methods=["GET"])
@require_api_token("read:projects")
def get_stock_availability_api(item_id):
    """Get stock availability for an item across warehouses"""
    item = StockItem.query.get_or_404(item_id)
    warehouse_id = request.args.get("warehouse_id", type=int)

    query = WarehouseStock.query.filter_by(stock_item_id=item_id)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    stock_levels = query.all()

    availability = []
    for stock in stock_levels:
        availability.append(
            {
                "warehouse_id": stock.warehouse_id,
                "warehouse_code": stock.warehouse.code,
                "warehouse_name": stock.warehouse.name,
                "quantity_on_hand": float(stock.quantity_on_hand),
                "quantity_reserved": float(stock.quantity_reserved),
                "quantity_available": float(stock.quantity_available),
                "location": stock.location,
            }
        )

    return jsonify({"item_id": item_id, "item_sku": item.sku, "item_name": item.name, "availability": availability})


@api_v1_bp.route("/inventory/warehouses", methods=["GET"])
@require_api_token("read:projects")
def list_warehouses_api():
    """List warehouses"""
    active_only = request.args.get("active_only", "true").lower() == "true"

    query = Warehouse.query
    if active_only:
        query = query.filter_by(is_active=True)

    result = paginate_query(query.order_by(Warehouse.code))
    result["items"] = [wh.to_dict() for wh in result["items"]]

    return jsonify(result)


@api_v1_bp.route("/inventory/stock-levels", methods=["GET"])
@require_api_token("read:projects")
def get_stock_levels_api():
    """Get stock levels"""
    warehouse_id = request.args.get("warehouse_id", type=int)
    stock_item_id = request.args.get("stock_item_id", type=int)
    category = request.args.get("category", "")

    query = WarehouseStock.query.join(StockItem).join(Warehouse)

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if stock_item_id:
        query = query.filter_by(stock_item_id=stock_item_id)

    if category:
        query = query.filter(StockItem.category == category)

    stock_levels = query.order_by(Warehouse.code, StockItem.name).all()

    levels = []
    for stock in stock_levels:
        levels.append(
            {
                "warehouse": stock.warehouse.to_dict(),
                "stock_item": stock.stock_item.to_dict(),
                "quantity_on_hand": float(stock.quantity_on_hand),
                "quantity_reserved": float(stock.quantity_reserved),
                "quantity_available": float(stock.quantity_available),
                "location": stock.location,
            }
        )

    return jsonify({"stock_levels": levels})


@api_v1_bp.route("/inventory/movements", methods=["POST"])
@require_api_token("write:projects")
def create_stock_movement_api():
    """Create a stock movement"""
    data = request.get_json() or {}

    movement_type = data.get("movement_type", "adjustment")
    stock_item_id = data.get("stock_item_id")
    warehouse_id = data.get("warehouse_id")
    quantity = data.get("quantity")
    reason = data.get("reason")
    notes = data.get("notes")
    reference_type = data.get("reference_type")
    reference_id = data.get("reference_id")
    unit_cost = data.get("unit_cost")

    if not stock_item_id or not warehouse_id or quantity is None:
        return jsonify({"error": "stock_item_id, warehouse_id, and quantity are required"}), 400

    try:
        from decimal import Decimal

        movement, updated_stock = StockMovement.record_movement(
            movement_type=movement_type,
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            quantity=Decimal(str(quantity)),
            moved_by=g.api_user.id,
            reference_type=reference_type,
            reference_id=reference_id,
            unit_cost=Decimal(str(unit_cost)) if unit_cost else None,
            reason=reason,
            notes=notes,
            update_stock=True,
        )

        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Stock movement recorded successfully",
                    "movement": movement.to_dict(),
                    "updated_stock": updated_stock.to_dict() if updated_stock else None,
                }
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# ==================== Suppliers API ====================


@api_v1_bp.route("/inventory/suppliers", methods=["GET"])
@require_api_token("read:projects")
def list_suppliers_api():
    """List suppliers"""
    from app.models import Supplier
    from sqlalchemy import or_

    search = request.args.get("search", "").strip()
    active_only = request.args.get("active_only", "true").lower() == "true"

    query = Supplier.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Supplier.code.ilike(like), Supplier.name.ilike(like)))

    result = paginate_query(query.order_by(Supplier.name))
    result["items"] = [supplier.to_dict() for supplier in result["items"]]

    return jsonify(result)


@api_v1_bp.route("/inventory/suppliers/<int:supplier_id>", methods=["GET"])
@require_api_token("read:projects")
def get_supplier_api(supplier_id):
    """Get supplier details"""
    from app.models import Supplier

    supplier = Supplier.query.get_or_404(supplier_id)
    return jsonify({"supplier": supplier.to_dict()})


@api_v1_bp.route("/inventory/suppliers/<int:supplier_id>/stock-items", methods=["GET"])
@require_api_token("read:projects")
def get_supplier_stock_items_api(supplier_id):
    """Get stock items from a supplier"""
    from app.models import Supplier, SupplierStockItem

    supplier = Supplier.query.get_or_404(supplier_id)
    supplier_items = (
        SupplierStockItem.query.join(Supplier)
        .filter(Supplier.id == supplier_id, SupplierStockItem.is_active == True)
        .all()
    )

    items = []
    for si in supplier_items:
        item_dict = si.to_dict()
        item_dict["stock_item"] = si.stock_item.to_dict() if si.stock_item else None
        items.append(item_dict)

    return jsonify({"items": items})


# ==================== Purchase Orders API ====================


@api_v1_bp.route("/inventory/purchase-orders", methods=["GET"])
@require_api_token("read:projects")
def list_purchase_orders_api():
    """List purchase orders"""
    from app.models import PurchaseOrder
    from sqlalchemy import or_

    status = request.args.get("status", "")
    supplier_id = request.args.get("supplier_id", type=int)

    query = PurchaseOrder.query

    if status:
        query = query.filter_by(status=status)

    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)

    result = paginate_query(query.order_by(PurchaseOrder.order_date.desc()))
    result["items"] = [po.to_dict() for po in result["items"]]

    return jsonify(result)


@api_v1_bp.route("/inventory/purchase-orders/<int:po_id>", methods=["GET"])
@require_api_token("read:projects")
def get_purchase_order_api(po_id):
    """Get purchase order details"""
    from app.models import PurchaseOrder

    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    return jsonify({"purchase_order": purchase_order.to_dict()})


@api_v1_bp.route("/inventory/purchase-orders", methods=["POST"])
@require_api_token("write:projects")
def create_purchase_order_api():
    """Create a purchase order"""
    from app.models import PurchaseOrder, PurchaseOrderItem, Supplier
    from datetime import datetime
    from decimal import Decimal

    data = request.get_json() or {}

    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return jsonify({"error": "supplier_id is required"}), 400

    try:
        # Generate PO number
        last_po = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).first()
        next_id = (last_po.id + 1) if last_po else 1
        po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{next_id:04d}"

        order_date = (
            datetime.strptime(data.get("order_date"), "%Y-%m-%d").date()
            if data.get("order_date")
            else datetime.now().date()
        )
        expected_delivery_date = (
            datetime.strptime(data.get("expected_delivery_date"), "%Y-%m-%d").date()
            if data.get("expected_delivery_date")
            else None
        )

        purchase_order = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier_id,
            order_date=order_date,
            created_by=g.api_user.id,
            expected_delivery_date=expected_delivery_date,
            notes=data.get("notes"),
            internal_notes=data.get("internal_notes"),
            currency_code=data.get("currency_code", "EUR"),
        )
        db.session.add(purchase_order)
        db.session.flush()

        # Handle items
        items = data.get("items", [])
        for item_data in items:
            item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                description=item_data.get("description", ""),
                quantity_ordered=Decimal(str(item_data.get("quantity_ordered", 1))),
                unit_cost=Decimal(str(item_data.get("unit_cost", 0))),
                stock_item_id=item_data.get("stock_item_id"),
                supplier_stock_item_id=item_data.get("supplier_stock_item_id"),
                supplier_sku=item_data.get("supplier_sku"),
                warehouse_id=item_data.get("warehouse_id"),
                currency_code=purchase_order.currency_code,
            )
            db.session.add(item)

        purchase_order.calculate_totals()
        db.session.commit()

        return (
            jsonify({"message": "Purchase order created successfully", "purchase_order": purchase_order.to_dict()}),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/purchase-orders/<int:po_id>/receive", methods=["POST"])
@require_api_token("write:projects")
def receive_purchase_order_api(po_id):
    """Receive a purchase order"""
    from app.models import PurchaseOrder
    from datetime import datetime

    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    data = request.get_json() or {}

    try:
        from decimal import Decimal

        # Update received quantities if provided
        items_data = data.get("items", [])
        if items_data:
            for item_data in items_data:
                item_id = item_data.get("item_id")
                quantity_received = item_data.get("quantity_received")
                if item_id and quantity_received is not None:
                    item = purchase_order.items.filter_by(id=item_id).first()
                    if item:
                        item.quantity_received = Decimal(str(quantity_received))

        received_date_str = data.get("received_date")
        received_date = (
            datetime.strptime(received_date_str, "%Y-%m-%d").date() if received_date_str else datetime.now().date()
        )
        purchase_order.mark_as_received(received_date)

        db.session.commit()

        return (
            jsonify({"message": "Purchase order received successfully", "purchase_order": purchase_order.to_dict()}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# ==================== Error Handlers ====================


@api_v1_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Resource not found"}), 404


@api_v1_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
