"""REST API v1 - Comprehensive API endpoints with token authentication"""

from flask import Blueprint, jsonify, request, current_app, g, Response
from app import db, limiter
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
    ApiToken,
    Deal,
    Lead,
    Contact,
)
from app.models.time_entry_approval import TimeEntryApproval, ApprovalStatus
from app.utils.api_auth import require_api_token
from app.utils.api_responses import (
    success_response,
    error_response,
    paginated_response,
    forbidden_response,
    not_found_response,
)
from datetime import datetime, timedelta, date
from sqlalchemy import func, or_
from app.utils.timezone import get_app_timezone, parse_local_datetime, utc_to_local
from app.models.time_entry import local_now

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Shared helpers for API v1 (used here and in api_v1_time_entries)
from app.routes.api_v1_common import (
    paginate_query,
    parse_datetime,
    _parse_date,
    _parse_date_range,
    _require_module_enabled_for_api,
)


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
    # Get app version from setup.py (single source of truth)
    from app.config.analytics_defaults import get_version_from_setup
    app_version = get_version_from_setup()
    if app_version == "unknown":
        # Fallback to config or default
        app_version = current_app.config.get("APP_VERSION", "1.0.0")
    
    return jsonify(
        {
            "api_version": "v1",
            "app_version": app_version,
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
                "deals": "/api/v1/deals",
                "leads": "/api/v1/leads",
                "contacts": "/api/v1/clients/<client_id>/contacts",
                "time_entry_approvals": "/api/v1/time-entry-approvals",
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
                "timesheet_periods": "/api/v1/timesheet-periods",
                "timesheet_policy": "/api/v1/timesheet-policy",
                "time_off": {
                    "leave_types": "/api/v1/time-off/leave-types",
                    "requests": "/api/v1/time-off/requests",
                    "balances": "/api/v1/time-off/balances",
                    "holidays": "/api/v1/time-off/holidays",
                },
                "payroll_export": "/api/v1/exports/payroll",
                "capacity_report": "/api/v1/reports/capacity",
                "compliance_reports": {
                    "locked_periods": "/api/v1/reports/compliance/locked-periods",
                    "audit_events": "/api/v1/reports/compliance/audit-events",
                },
                "mileage_gps": "/api/v1/mileage/gps",
                "search": "/api/v1/search",
                "inventory": {
                    "items": "/api/v1/inventory/items",
                    "warehouses": "/api/v1/inventory/warehouses",
                    "stock_levels": "/api/v1/inventory/stock-levels",
                    "movements": "/api/v1/inventory/movements",
                    "suppliers": "/api/v1/inventory/suppliers",
                    "purchase_orders": "/api/v1/inventory/purchase-orders",
                },
            },
            "timezone": get_app_timezone(),
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


# ==================== Auth (unauthenticated) ====================


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute", methods=["POST"])
def auth_login():
    """Login with username and password; returns an API token for mobile/app use.

    Accepts JSON: { "username": "...", "password": "..." }.
    Returns 200 with { "token": "tt_..." } or 401 with { "error": "..." }.
    The token has scopes for basics: read:projects, read:tasks, read:time_entries, write:time_entries.
    """
    current_app.logger.info(
        "POST /api/v1/auth/login from %s",
        request.remote_addr or request.headers.get("X-Forwarded-For", "unknown"),
    )
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Invalid username or password"}), 401

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    scopes = "read:projects,read:tasks,read:time_entries,write:time_entries"
    expiry_days = current_app.config.get("API_TOKEN_DEFAULT_EXPIRY_DAYS", 90)
    api_token, plain_token = ApiToken.create_token(
        user_id=user.id,
        name=f"Mobile app - {user.username}",
        description="Token issued via mobile/app login",
        scopes=scopes,
        expires_days=expiry_days if expiry_days else None,
    )
    db.session.add(api_token)
    db.session.commit()

    return jsonify({"token": plain_token})


# Projects and Tasks routes are in api_v1_projects.py and api_v1_tasks.py (sub-blueprints)


# Clients and Invoices routes are in api_v1_clients.py and api_v1_invoices.py (sub-blueprints)


# Expenses, Payments, Mileage, Deals, Leads, Contacts are in api_v1_* sub-blueprints


# ==================== Time Entry Approvals ====================


@api_v1_bp.route("/time-entry-approvals", methods=["GET"])
@require_api_token("read:time_approvals")
def list_time_entry_approvals():
    """List pending time entry approvals for the current user (as approver)."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    approvals = service.get_pending_approvals(g.api_user.id)
    return jsonify({"approvals": [a.to_dict() for a in approvals]})


@api_v1_bp.route("/time-entry-approvals/<int:approval_id>", methods=["GET"])
@require_api_token("read:time_approvals")
def get_time_entry_approval(approval_id):
    """Get a time entry approval by id."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    approval = TimeEntryApproval.query.filter_by(id=approval_id).first_or_404()
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    approver_ids = service._get_approvers_for_entry(approval.time_entry)
    if approval.requested_by != g.api_user.id and (approval.approved_by or 0) != g.api_user.id:
        if g.api_user.id not in approver_ids and not g.api_user.is_admin:
            return forbidden_response("Access denied")
    return jsonify({"approval": approval.to_dict()})


@api_v1_bp.route("/time-entry-approvals/<int:approval_id>/approve", methods=["POST"])
@require_api_token("write:time_approvals")
def approve_time_entry(approval_id):
    """Approve a time entry."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    data = request.get_json(silent=True) or {}
    result = service.approve(approval_id=approval_id, approver_id=g.api_user.id, comment=data.get("comment"))
    if not result.get("success"):
        return error_response(result.get("message", "Approval failed"), status_code=400)
    return jsonify(result)


@api_v1_bp.route("/time-entry-approvals/<int:approval_id>/reject", methods=["POST"])
@require_api_token("write:time_approvals")
def reject_time_entry(approval_id):
    """Reject a time entry."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or data.get("rejection_reason")
    if not reason:
        return error_response("Rejection reason required", status_code=400)
    result = service.reject(approval_id=approval_id, approver_id=g.api_user.id, reason=reason)
    if not result.get("success"):
        return error_response(result.get("message", "Rejection failed"), status_code=400)
    return jsonify(result)


@api_v1_bp.route("/time-entry-approvals/<int:approval_id>/cancel", methods=["POST"])
@require_api_token("write:time_approvals")
def cancel_time_entry_approval(approval_id):
    """Cancel an approval request (requester only)."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    result = service.cancel_approval(approval_id=approval_id, user_id=g.api_user.id)
    if not result.get("success"):
        return error_response(result.get("message", "Cancellation failed"), status_code=400)
    return jsonify(result)


@api_v1_bp.route("/time-entries/<int:entry_id>/request-approval", methods=["POST"])
@require_api_token("write:time_approvals")
def request_time_entry_approval(entry_id):
    """Request approval for a time entry."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    data = request.get_json(silent=True) or {}
    result = service.request_approval(
        time_entry_id=entry_id,
        requested_by=g.api_user.id,
        comment=data.get("comment"),
        approver_ids=data.get("approver_ids"),
    )
    if not result.get("success"):
        return error_response(result.get("message", "Request failed"), status_code=400)
    return jsonify(result)


@api_v1_bp.route("/time-entry-approvals/bulk-approve", methods=["POST"])
@require_api_token("write:time_approvals")
def bulk_approve_time_entries():
    """Bulk approve multiple time entry approvals."""
    blocked = _require_module_enabled_for_api("time_approvals")
    if blocked:
        return blocked
    from app.services.time_approval_service import TimeApprovalService
    service = TimeApprovalService()
    data = request.get_json(silent=True) or {}
    approval_ids = data.get("approval_ids", [])
    if not approval_ids:
        return error_response("approval_ids required", status_code=400)
    result = service.bulk_approve(approval_ids=approval_ids, approver_id=g.api_user.id, comment=data.get("comment"))
    return jsonify(result)


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
    query = BudgetAlert.query.options(joinedload(BudgetAlert.project))

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

    query = TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.user), joinedload(TimeEntryTemplate.project))
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

    tpl = (
        TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.user), joinedload(TimeEntryTemplate.project))
        .filter_by(id=tpl_id)
        .first_or_404()
    )

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

    tpl = (
        TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.user), joinedload(TimeEntryTemplate.project))
        .filter_by(id=tpl_id)
        .first_or_404()
    )

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

    tpl = (
        TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.user), joinedload(TimeEntryTemplate.project))
        .filter_by(id=tpl_id)
        .first_or_404()
    )

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
        quote_id=quote_id, user_id=g.api_user.id if not g.api_user.is_admin else None, is_admin=g.api_user.is_admin
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
        quote_id=quote_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin, **update_kwargs
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
        quote_id=quote_id, user_id=g.api_user.id if not g.api_user.is_admin else None, is_admin=g.api_user.is_admin
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

    cmt = (
        Comment.query.options(joinedload(Comment.user), joinedload(Comment.project), joinedload(Comment.task))
        .filter_by(id=comment_id)
        .first_or_404()
    )

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

    cmt = (
        Comment.query.options(joinedload(Comment.user), joinedload(Comment.project), joinedload(Comment.task))
        .filter_by(id=comment_id)
        .first_or_404()
    )

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
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from sqlalchemy.orm import joinedload

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = ClientNote.query.options(joinedload(ClientNote.client), joinedload(ClientNote.created_by_user))
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
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
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
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from sqlalchemy.orm import joinedload

    note = (
        ClientNote.query.options(joinedload(ClientNote.client), joinedload(ClientNote.created_by_user))
        .filter_by(id=note_id)
        .first_or_404()
    )

    return jsonify({"note": note.to_dict()})


@api_v1_bp.route("/client-notes/<int:note_id>", methods=["PUT", "PATCH"])
@require_api_token("write:clients")
def update_client_note(note_id):
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from sqlalchemy.orm import joinedload

    note = (
        ClientNote.query.options(joinedload(ClientNote.client), joinedload(ClientNote.created_by_user))
        .filter_by(id=note_id)
        .first_or_404()
    )

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
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from sqlalchemy.orm import joinedload

    note = (
        ClientNote.query.options(joinedload(ClientNote.client), joinedload(ClientNote.created_by_user))
        .filter_by(id=note_id)
        .first_or_404()
    )

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

    query = ProjectCost.query.options(joinedload(ProjectCost.project), joinedload(ProjectCost.user))
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

    cost = (
        ProjectCost.query.options(joinedload(ProjectCost.project), joinedload(ProjectCost.user))
        .filter_by(id=cost_id)
        .first_or_404()
    )

    return jsonify({"cost": cost.to_dict()})


@api_v1_bp.route("/project-costs/<int:cost_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_project_cost(cost_id):
    from sqlalchemy.orm import joinedload

    cost = (
        ProjectCost.query.options(joinedload(ProjectCost.project), joinedload(ProjectCost.user))
        .filter_by(id=cost_id)
        .first_or_404()
    )
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

    cost = (
        ProjectCost.query.options(joinedload(ProjectCost.project), joinedload(ProjectCost.user))
        .filter_by(id=cost_id)
        .first_or_404()
    )

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

    rule = (
        TaxRule.query.options(joinedload(TaxRule.client), joinedload(TaxRule.project))
        .filter_by(id=rule_id)
        .first_or_404()
    )

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

    query = RecurringInvoice.query.options(joinedload(RecurringInvoice.project), joinedload(RecurringInvoice.client))

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

    ri = (
        RecurringInvoice.query.options(joinedload(RecurringInvoice.project), joinedload(RecurringInvoice.client))
        .filter_by(id=ri_id)
        .first_or_404()
    )

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

    ri = (
        RecurringInvoice.query.options(joinedload(RecurringInvoice.project), joinedload(RecurringInvoice.client))
        .filter_by(id=ri_id)
        .first_or_404()
    )

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
        joinedload(TimeEntry.project), joinedload(TimeEntry.user), joinedload(TimeEntry.task)
    ).filter(TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_dt, TimeEntry.start_time <= end_dt)

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
    from app.models import Settings

    response = {"user": g.api_user.to_dict()}
    settings = Settings.get_settings()
    response["time_entry_requirements"] = {
        "require_task": getattr(settings, "time_entry_require_task", False),
        "require_description": getattr(settings, "time_entry_require_description", False),
        "description_min_length": getattr(settings, "time_entry_description_min_length", 20),
    }
    return jsonify(response)


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
    items = result["items"]
    if not items:
        return jsonify({"users": [], "pagination": result["pagination"]})

    # Single aggregate query for total_hours to avoid N+1
    user_ids = [u.id for u in items]
    rows = (
        db.session.query(TimeEntry.user_id, db.func.sum(TimeEntry.duration_seconds))
        .filter(
            TimeEntry.user_id.in_(user_ids),
            TimeEntry.end_time.isnot(None),
        )
        .group_by(TimeEntry.user_id)
        .all()
    )
    total_hours_by_user = {uid: round((total_seconds or 0) / 3600, 2) for uid, total_seconds in rows}
    return jsonify({
        "users": [u.to_dict(total_hours_override=total_hours_by_user.get(u.id)) for u in items],
        "pagination": result["pagination"],
    })


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


@api_v1_bp.route("/inventory/items", methods=["POST"])
@require_api_token("write:projects")
def create_stock_item_api():
    """Create a stock item"""
    from decimal import Decimal
    data = request.get_json() or {}
    
    required_fields = ["sku", "name"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    try:
        item = StockItem(
            sku=data["sku"],
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            unit=data.get("unit", "pcs"),
            default_price=Decimal(str(data["default_price"])) if data.get("default_price") else None,
            default_cost=Decimal(str(data["default_cost"])) if data.get("default_cost") else None,
            barcode=data.get("barcode"),
            is_trackable=data.get("is_trackable", True),
            currency_code=data.get("currency_code", "EUR"),
            is_active=data.get("is_active", True),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Stock item created successfully", "item": item.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating stock item: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/items/<int:item_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_stock_item_api(item_id):
    """Update a stock item"""
    from decimal import Decimal
    item = StockItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    
    try:
        # Update fields
        if "name" in data:
            item.name = data["name"]
        if "description" in data:
            item.description = data.get("description")
        if "category" in data:
            item.category = data.get("category")
        if "unit" in data:
            item.unit = data["unit"]
        if "default_price" in data:
            item.default_price = Decimal(str(data["default_price"])) if data["default_price"] else None
        if "default_cost" in data:
            item.default_cost = Decimal(str(data["default_cost"])) if data["default_cost"] else None
        if "barcode" in data:
            item.barcode = data.get("barcode")
        if "is_trackable" in data:
            item.is_trackable = bool(data["is_trackable"])
        if "currency_code" in data:
            item.currency_code = data["currency_code"]
        if "is_active" in data:
            item.is_active = bool(data["is_active"])
        
        db.session.commit()
        return jsonify({"message": "Stock item updated successfully", "item": item.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating stock item: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/items/<int:item_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_stock_item_api(item_id):
    """Delete (deactivate) a stock item"""
    item = StockItem.query.get_or_404(item_id)
    
    try:
        # Soft delete by deactivating
        item.is_active = False
        db.session.commit()
        return jsonify({"message": "Stock item deactivated successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating stock item: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


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
    """Create a stock movement with optional devaluation support for return/waste movements"""
    from app.models import StockItem, WarehouseStock
    from decimal import Decimal, InvalidOperation
    
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

    # Devaluation parameters for return/waste movements
    devalue_enabled = data.get("devalue_enabled", False)
    devalue_method = data.get("devalue_method", "percent").strip().lower()
    devalue_percent = data.get("devalue_percent")
    devalue_unit_cost = data.get("devalue_unit_cost")

    if not stock_item_id or not warehouse_id or quantity is None:
        return jsonify({"error": "stock_item_id, warehouse_id, and quantity are required"}), 400

    try:
        quantity = Decimal(str(quantity))
        
        # Initialize variables
        lot_type = None
        unit_cost_override = None
        consume_from_lot_id = None

        # Get stock item for validation
        item = StockItem.query.get(stock_item_id)
        if not item:
            return jsonify({"error": "Stock item not found"}), 404

        # Handle manual devaluation movement type
        if movement_type == "devaluation":
            # Devaluation requires trackable items
            if not item.is_trackable:
                return jsonify({"error": "Stock item is not trackable. Devaluation requires trackable items."}), 400
            if quantity <= 0:
                return jsonify({"error": "Devaluation quantity must be positive"}), 400

            base_cost = item.default_cost or Decimal("0")
            if base_cost <= 0:
                return jsonify({"error": "Stock item must have a default cost to perform devaluation"}), 400

            # Calculate devaluation cost
            if devalue_method == "percent":
                if devalue_percent is None:
                    return jsonify({"error": "Devaluation percent is required when using percent method"}), 400
                try:
                    pct = Decimal(str(devalue_percent))
                except (ValueError, InvalidOperation):
                    return jsonify({"error": "Invalid devaluation percent value"}), 400
                if pct < 0 or pct > 100:
                    return jsonify({"error": "Devaluation percent must be between 0 and 100"}), 400
                unit_cost_override = (base_cost * (Decimal("100") - pct) / Decimal("100")).quantize(Decimal("0.01"))
            elif devalue_method == "fixed":
                if devalue_unit_cost is None:
                    return jsonify({"error": "New unit cost is required when using fixed cost method"}), 400
                try:
                    unit_cost_override = Decimal(str(devalue_unit_cost)).quantize(Decimal("0.01"))
                except (ValueError, InvalidOperation):
                    return jsonify({"error": "Invalid unit cost value"}), 400
                if unit_cost_override < 0:
                    return jsonify({"error": "Unit cost cannot be negative"}), 400
            else:
                return jsonify({"error": "Invalid devaluation method. Must be 'percent' or 'fixed'"}), 400

            # Check stock availability
            warehouse_stock = WarehouseStock.query.filter_by(
                warehouse_id=warehouse_id, stock_item_id=stock_item_id
            ).first()
            available_qty = warehouse_stock.quantity_on_hand if warehouse_stock else Decimal("0")
            if available_qty < quantity:
                return jsonify({
                    "error": f"Insufficient stock to devalue. Available: {float(available_qty)}, Requested: {float(quantity)}"
                }), 400

            StockMovement.record_devaluation(
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                moved_by=g.api_user.id,
                new_unit_cost=unit_cost_override,
                reason=reason or "Manual devaluation via API",
                notes=notes,
            )

            db.session.commit()
            return jsonify({"message": "Stock devaluation recorded successfully"}), 201

        # Handle return and waste movements with optional devaluation
        if movement_type in ["return", "waste"]:
            # Validate quantity
            if movement_type == "return" and quantity <= 0:
                return jsonify({"error": "Return movements must use a positive quantity"}), 400
            if movement_type == "waste" and quantity >= 0:
                return jsonify({"error": "Waste movements must use a negative quantity"}), 400

            # Process devaluation if enabled
            if devalue_enabled:
                if not item.is_trackable:
                    return jsonify({"error": "Stock item is not trackable. Devaluation requires trackable items."}), 400
                
                base_cost = item.default_cost or Decimal("0")
                if base_cost <= 0:
                    return jsonify({"error": "Stock item must have a default cost to perform devaluation"}), 400

                # Calculate devaluation cost
                if devalue_method == "percent":
                    if devalue_percent is None:
                        return jsonify({"error": "Devaluation percent is required when devaluation is enabled"}), 400
                    try:
                        pct = Decimal(str(devalue_percent))
                    except (ValueError, InvalidOperation):
                        return jsonify({"error": "Invalid devaluation percent value"}), 400
                    if pct < 0 or pct > 100:
                        return jsonify({"error": "Devaluation percent must be between 0 and 100"}), 400
                    unit_cost_override = (base_cost * (Decimal("100") - pct) / Decimal("100")).quantize(Decimal("0.01"))
                elif devalue_method == "fixed":
                    if devalue_unit_cost is None:
                        return jsonify({"error": "New unit cost is required when devaluation is enabled"}), 400
                    try:
                        unit_cost_override = Decimal(str(devalue_unit_cost)).quantize(Decimal("0.01"))
                    except (ValueError, InvalidOperation):
                        return jsonify({"error": "Invalid unit cost value"}), 400
                    if unit_cost_override < 0:
                        return jsonify({"error": "Unit cost cannot be negative"}), 400
                else:
                    return jsonify({"error": "Invalid devaluation method. Must be 'percent' or 'fixed'"}), 400

                # Validate devaluation cost is not greater than original
                if unit_cost_override > base_cost:
                    return jsonify({
                        "error": f"Devaluation cost ({float(unit_cost_override)}) cannot be greater than original cost ({float(base_cost)})"
                    }), 400

                # Returns: book inbound directly into a devalued lot
                if movement_type == "return":
                    lot_type = "devalued"
                    # unit_cost_override is already set above

                # Waste: devalue existing stock first, then waste from the devalued lot
                elif movement_type == "waste":
                    qty_to_waste = abs(quantity)
                    
                    # Check stock availability
                    warehouse_stock = WarehouseStock.query.filter_by(
                        warehouse_id=warehouse_id, stock_item_id=stock_item_id
                    ).first()
                    available_qty = warehouse_stock.quantity_on_hand if warehouse_stock else Decimal("0")
                    if available_qty < qty_to_waste:
                        return jsonify({
                            "error": f"Insufficient stock to waste. Available: {float(available_qty)}, Requested: {float(qty_to_waste)}"
                        }), 400

                    # Devalue the quantity first (creates a devalued lot)
                    try:
                        _deval_move, deval_lot = StockMovement.record_devaluation(
                            stock_item_id=stock_item_id,
                            warehouse_id=warehouse_id,
                            quantity=qty_to_waste,
                            moved_by=g.api_user.id,
                            new_unit_cost=unit_cost_override,
                            reason=reason or "Devaluation before waste via API",
                            notes=notes,
                        )
                        consume_from_lot_id = deval_lot.id
                    except Exception as e:
                        db.session.rollback()
                        return jsonify({"error": f"Failed to devalue stock before waste: {str(e)}"}), 400

        # Record the movement
        try:
            movement, updated_stock = StockMovement.record_movement(
                movement_type=movement_type,
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                moved_by=g.api_user.id,
                reference_type=reference_type,
                reference_id=reference_id,
                unit_cost=unit_cost_override if unit_cost_override is not None else (Decimal(str(unit_cost)) if unit_cost else None),
                reason=reason,
                notes=notes,
                lot_type=lot_type,
                consume_from_lot_id=consume_from_lot_id,
                update_stock=True,
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to record movement: {str(e)}"}), 400

        db.session.commit()

        message = "Stock movement recorded successfully"
        if movement_type == "return" and devalue_enabled:
            message = "Return movement recorded successfully with devaluation applied"
        elif movement_type == "waste" and devalue_enabled:
            message = "Waste movement recorded successfully with devaluation applied"

        return (
            jsonify(
                {
                    "message": message,
                    "movement": movement.to_dict(),
                    "updated_stock": updated_stock.to_dict() if updated_stock else None,
                }
            ),
            201,
        )
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error recording stock movement via API: {e}", exc_info=True)
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


@api_v1_bp.route("/inventory/suppliers", methods=["POST"])
@require_api_token("write:projects")
def create_supplier_api():
    """Create a supplier"""
    from app.models import Supplier
    data = request.get_json() or {}
    
    required_fields = ["code", "name"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    try:
        # Check for duplicate code
        existing = Supplier.query.filter_by(code=data["code"]).first()
        if existing:
            return jsonify({"error": f"Supplier with code '{data['code']}' already exists"}), 400
        
        supplier = Supplier(
            code=data["code"],
            name=data["name"],
            contact_person=data.get("contact_person"),
            email=data.get("email"),
            phone=data.get("phone"),
            address=data.get("address"),
            website=data.get("website"),
            notes=data.get("notes"),
            is_active=data.get("is_active", True),
        )
        db.session.add(supplier)
        db.session.commit()
        return jsonify({"message": "Supplier created successfully", "supplier": supplier.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating supplier: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/suppliers/<int:supplier_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_supplier_api(supplier_id):
    """Update a supplier"""
    from app.models import Supplier
    supplier = Supplier.query.get_or_404(supplier_id)
    data = request.get_json() or {}
    
    try:
        # Check for duplicate code if changing
        if "code" in data and data["code"] != supplier.code:
            existing = Supplier.query.filter_by(code=data["code"]).first()
            if existing:
                return jsonify({"error": f"Supplier with code '{data['code']}' already exists"}), 400
            supplier.code = data["code"]
        
        if "name" in data:
            supplier.name = data["name"]
        if "contact_person" in data:
            supplier.contact_person = data.get("contact_person")
        if "email" in data:
            supplier.email = data.get("email")
        if "phone" in data:
            supplier.phone = data.get("phone")
        if "address" in data:
            supplier.address = data.get("address")
        if "website" in data:
            supplier.website = data.get("website")
        if "notes" in data:
            supplier.notes = data.get("notes")
        if "is_active" in data:
            supplier.is_active = bool(data["is_active"])
        
        db.session.commit()
        return jsonify({"message": "Supplier updated successfully", "supplier": supplier.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating supplier: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/suppliers/<int:supplier_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_supplier_api(supplier_id):
    """Delete (deactivate) a supplier"""
    from app.models import Supplier
    supplier = Supplier.query.get_or_404(supplier_id)
    
    try:
        # Soft delete by deactivating
        supplier.is_active = False
        db.session.commit()
        return jsonify({"message": "Supplier deactivated successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating supplier: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


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


@api_v1_bp.route("/inventory/purchase-orders/<int:po_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_purchase_order_api(po_id):
    """Update a purchase order (only if status is 'draft')"""
    from app.models import PurchaseOrder, PurchaseOrderItem
    from datetime import datetime
    from decimal import Decimal
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    data = request.get_json() or {}
    
    # Only allow updates to draft purchase orders
    if purchase_order.status != "draft":
        return jsonify({"error": f"Cannot update purchase order with status '{purchase_order.status}'. Only draft orders can be updated."}), 400
    
    try:
        # Update basic fields
        if "order_date" in data:
            purchase_order.order_date = datetime.strptime(data["order_date"], "%Y-%m-%d").date()
        if "expected_delivery_date" in data:
            purchase_order.expected_delivery_date = datetime.strptime(data["expected_delivery_date"], "%Y-%m-%d").date() if data["expected_delivery_date"] else None
        if "notes" in data:
            purchase_order.notes = data.get("notes")
        if "internal_notes" in data:
            purchase_order.internal_notes = data.get("internal_notes")
        if "currency_code" in data:
            purchase_order.currency_code = data["currency_code"]
        
        # Update items if provided
        if "items" in data:
            # Remove existing items
            for item in purchase_order.items:
                db.session.delete(item)
            
            # Add new items
            for item_data in data["items"]:
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
        return jsonify({"message": "Purchase order updated successfully", "purchase_order": purchase_order.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating purchase order: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/inventory/purchase-orders/<int:po_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_purchase_order_api(po_id):
    """Delete (cancel) a purchase order (only if status is 'draft')"""
    from app.models import PurchaseOrder
    
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    # Only allow deletion of draft purchase orders
    if purchase_order.status != "draft":
        return jsonify({"error": f"Cannot delete purchase order with status '{purchase_order.status}'. Only draft orders can be deleted."}), 400
    
    try:
        # Delete associated items first
        for item in purchase_order.items:
            db.session.delete(item)
        
        # Delete the purchase order
        db.session.delete(purchase_order)
        db.session.commit()
        return jsonify({"message": "Purchase order deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting purchase order: {e}", exc_info=True)
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
        current_app.logger.error(f"Error receiving purchase order: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


# ==================== Search ====================


@api_v1_bp.route("/search", methods=["GET"])
@require_api_token("read:projects")
def search():
    """Global search endpoint across projects, tasks, clients, and time entries
    ---
    tags:
      - Search
    parameters:
      - name: q
        in: query
        type: string
        required: true
        description: Search query (minimum 2 characters)
      - name: limit
        in: query
        type: integer
        default: 10
        description: Maximum number of results per category (max 50)
      - name: types
        in: query
        type: string
        description: Comma-separated list of types to search (project, task, client, entry)
    security:
      - Bearer: []
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            results:
              type: array
              items:
                type: object
                properties:
                  type:
                    type: string
                    enum: [project, task, client, entry]
                  category:
                    type: string
                  id:
                    type: integer
                  title:
                    type: string
                  description:
                    type: string
                  url:
                    type: string
                  badge:
                    type: string
            query:
              type: string
            count:
              type: integer
      400:
        description: Invalid query (too short)
    """
    query = request.args.get("q", "").strip()
    limit = min(request.args.get("limit", 10, type=int), 50)  # Cap at 50
    types_filter = request.args.get("types", "").strip().lower()
    
    if not query or len(query) < 2:
        return jsonify({"error": "Query must be at least 2 characters", "results": []}), 400

    # Parse types filter
    allowed_types = {"project", "task", "client", "entry"}
    if types_filter:
        requested_types = {t.strip() for t in types_filter.split(",") if t.strip()}
        search_types = requested_types.intersection(allowed_types)
    else:
        search_types = allowed_types

    results = []
    search_pattern = f"%{query}%"
    
    # Get authenticated user from API token
    user = g.api_user

    # Search projects (scoped for subcontractors)
    if "project" in search_types:
        try:
            from app.utils.scope_filter import apply_project_scope_to_model
            projects_query = Project.query.filter(
                Project.status == "active",
                or_(Project.name.ilike(search_pattern), Project.description.ilike(search_pattern)),
            )
            scope_p = apply_project_scope_to_model(Project, user)
            if scope_p is not None:
                projects_query = projects_query.filter(scope_p)
            projects = projects_query.limit(limit).all()

            for project in projects:
                results.append(
                    {
                        "type": "project",
                        "category": "project",
                        "id": project.id,
                        "title": project.name,
                        "description": project.description or "",
                        "url": f"/projects/{project.id}",
                        "badge": "Project",
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error searching projects: {e}")

    # Search tasks
    if "task" in search_types:
        try:
            tasks = (
                Task.query.join(Project)
                .filter(
                    Project.status == "active",
                    or_(Task.name.ilike(search_pattern), Task.description.ilike(search_pattern))
                )
                .limit(limit)
                .all()
            )

            for task in tasks:
                results.append(
                    {
                        "type": "task",
                        "category": "task",
                        "id": task.id,
                        "title": task.name,
                        "description": f"{task.project.name if task.project else 'No Project'}",
                        "url": f"/tasks/{task.id}",
                        "badge": task.status.replace("_", " ").title() if task.status else "Task",
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error searching tasks: {e}")

    # Search clients (scoped for subcontractors)
    if "client" in search_types:
        try:
            from app.utils.scope_filter import apply_client_scope_to_model
            clients_query = Client.query.filter(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.email.ilike(search_pattern),
                    Client.company.ilike(search_pattern),
                )
            )
            scope_c = apply_client_scope_to_model(Client, user)
            if scope_c is not None:
                clients_query = clients_query.filter(scope_c)
            clients = clients_query.limit(limit).all()

            for client in clients:
                results.append(
                    {
                        "type": "client",
                        "category": "client",
                        "id": client.id,
                        "title": client.name,
                        "description": client.company or client.email or "",
                        "url": f"/clients/{client.id}",
                        "badge": "Client",
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error searching clients: {e}")

    # Search time entries (notes and tags)
    # Non-admin users can only see their own entries
    if "entry" in search_types:
        try:
            entries_query = TimeEntry.query.filter(
                TimeEntry.end_time.isnot(None),
                or_(TimeEntry.notes.ilike(search_pattern), TimeEntry.tags.ilike(search_pattern)),
            )
            
            # Restrict to user's entries if not admin
            if not user.is_admin:
                entries_query = entries_query.filter(TimeEntry.user_id == user.id)
            
            entries = (
                entries_query
                .order_by(TimeEntry.start_time.desc())
                .limit(limit)
                .all()
            )

            for entry in entries:
                title_parts = []
                if entry.project:
                    title_parts.append(entry.project.name)
                if entry.task:
                    title_parts.append(f"• {entry.task.name}")
                title = " ".join(title_parts) if title_parts else "Time Entry"

                description = entry.notes[:100] if entry.notes else ""
                if entry.tags:
                    description += f" [{entry.tags}]"

                results.append(
                    {
                        "type": "entry",
                        "category": "entry",
                        "id": entry.id,
                        "title": title,
                        "description": description,
                        "url": f"/timer/edit/{entry.id}",
                        "badge": entry.duration_formatted,
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error searching time entries: {e}")

    return jsonify({"results": results, "query": query, "count": len(results)})


# ==================== Timesheet Governance ====================


def _is_api_approver(user) -> bool:
    if user.is_admin:
        return True
    try:
        from app.services.workforce_governance_service import WorkforceGovernanceService

        policy = WorkforceGovernanceService().get_or_create_default_policy()
        return user.id in policy.get_approver_ids()
    except Exception:
        return False


@api_v1_bp.route("/timesheet-periods", methods=["GET"])
@require_api_token("read:time_entries")
def list_timesheet_periods():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    service = WorkforceGovernanceService()
    user_id = request.args.get("user_id", type=int)
    if not g.api_user.is_admin:
        user_id = g.api_user.id

    status = request.args.get("status")
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))

    periods = service.list_periods(user_id=user_id, status=status, period_start=start, period_end=end)
    return jsonify({"timesheet_periods": [p.to_dict() for p in periods]})


@api_v1_bp.route("/timesheet-periods", methods=["POST"])
@require_api_token("write:time_entries")
def create_or_get_timesheet_period():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    data = request.get_json() or {}
    ref = _parse_date(data.get("reference_date")) or date.today()
    period_type = (data.get("period_type") or "weekly").strip().lower()

    user_id = data.get("user_id") if g.api_user.is_admin else g.api_user.id
    user_id = int(user_id)

    period = WorkforceGovernanceService().get_or_create_period_for_date(user_id=user_id, reference=ref, period_type=period_type)
    return jsonify({"timesheet_period": period.to_dict()}), 201


@api_v1_bp.route("/timesheet-periods/<int:period_id>/submit", methods=["POST"])
@require_api_token("write:time_entries")
def submit_timesheet_period(period_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    result = WorkforceGovernanceService().submit_period(period_id=period_id, actor_id=g.api_user.id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not submit period")}), 400
    return jsonify({"message": "Timesheet period submitted", "timesheet_period": result["period"].to_dict()})


@api_v1_bp.route("/timesheet-periods/<int:period_id>/approve", methods=["POST"])
@require_api_token("write:time_entries")
def approve_timesheet_period(period_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    result = WorkforceGovernanceService().approve_period(period_id=period_id, approver_id=g.api_user.id, comment=data.get("comment"))
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not approve period")}), 400
    return jsonify({"message": "Timesheet period approved", "timesheet_period": result["period"].to_dict()})


@api_v1_bp.route("/timesheet-periods/<int:period_id>/reject", methods=["POST"])
@require_api_token("write:time_entries")
def reject_timesheet_period(period_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "reason is required"}), 400

    result = WorkforceGovernanceService().reject_period(period_id=period_id, approver_id=g.api_user.id, reason=reason)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not reject period")}), 400
    return jsonify({"message": "Timesheet period rejected", "timesheet_period": result["period"].to_dict()})


@api_v1_bp.route("/timesheet-periods/<int:period_id>/close", methods=["POST"])
@require_api_token("write:time_entries")
def close_timesheet_period(period_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not g.api_user.is_admin:
        return jsonify({"error": "Only admins can close periods"}), 403

    data = request.get_json() or {}
    result = WorkforceGovernanceService().close_period(period_id=period_id, closer_id=g.api_user.id, reason=data.get("reason"))
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not close period")}), 400
    return jsonify({"message": "Timesheet period closed", "timesheet_period": result["period"].to_dict()})


@api_v1_bp.route("/timesheet-periods/<int:period_id>", methods=["DELETE"])
@require_api_token("write:time_entries")
def delete_timesheet_period_api(period_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    result = WorkforceGovernanceService().delete_period(period_id=period_id, actor_id=g.api_user.id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete period")}), 400
    return jsonify({"message": "Timesheet period deleted"})


@api_v1_bp.route("/timesheet-policy", methods=["GET"])
@require_api_token("read:time_entries")
def get_timesheet_policy():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403
    policy = WorkforceGovernanceService().get_or_create_default_policy()
    return jsonify({"timesheet_policy": policy.to_dict()})


@api_v1_bp.route("/timesheet-policy", methods=["PUT", "PATCH"])
@require_api_token("write:time_entries")
def update_timesheet_policy():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    service = WorkforceGovernanceService()
    policy = service.get_or_create_default_policy()
    data = request.get_json() or {}

    if "default_period_type" in data:
        policy.default_period_type = (data.get("default_period_type") or "weekly").strip().lower()
    if "auto_lock_days" in data:
        policy.auto_lock_days = data.get("auto_lock_days")
    if "approver_user_ids" in data:
        ids = data.get("approver_user_ids") or []
        if isinstance(ids, list):
            policy.approver_user_ids = ",".join(str(int(x)) for x in ids if str(x).strip())
    if "enable_multi_level_approval" in data:
        policy.enable_multi_level_approval = bool(data.get("enable_multi_level_approval"))
    if "require_rejection_comment" in data:
        policy.require_rejection_comment = bool(data.get("require_rejection_comment"))
    if "enable_admin_override" in data:
        policy.enable_admin_override = bool(data.get("enable_admin_override"))

    db.session.commit()
    return jsonify({"message": "Timesheet policy updated", "timesheet_policy": policy.to_dict()})


# ==================== Time Off ====================


@api_v1_bp.route("/time-off/leave-types", methods=["GET"])
@require_api_token("read:reports")
def list_leave_types_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    enabled_only = request.args.get("enabled_only", "true").lower() == "true"
    items = WorkforceGovernanceService().list_leave_types(enabled_only=enabled_only)
    return jsonify({"leave_types": [i.to_dict() for i in items]})


@api_v1_bp.route("/time-off/leave-types", methods=["POST"])
@require_api_token("write:reports")
def create_leave_type_api():
    from app.models.time_off import LeaveType

    if not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().lower()
    if not name or not code:
        return jsonify({"error": "name and code are required"}), 400

    leave_type = LeaveType(
        name=name,
        code=code,
        is_paid=bool(data.get("is_paid", True)),
        annual_allowance_hours=data.get("annual_allowance_hours"),
        accrual_hours_per_month=data.get("accrual_hours_per_month"),
        enabled=bool(data.get("enabled", True)),
    )
    db.session.add(leave_type)
    db.session.commit()
    return jsonify({"message": "Leave type created", "leave_type": leave_type.to_dict()}), 201


@api_v1_bp.route("/time-off/leave-types/<int:leave_type_id>", methods=["DELETE"])
@require_api_token("write:reports")
def delete_leave_type_api(leave_type_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    result = WorkforceGovernanceService().delete_leave_type(leave_type_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete leave type")}), 400
    return jsonify({"message": "Leave type deleted"})


@api_v1_bp.route("/time-off/requests", methods=["GET"])
@require_api_token("read:time_entries")
def list_time_off_requests_api():
    from app.models.time_off import TimeOffRequest

    q = TimeOffRequest.query
    if not g.api_user.is_admin:
        q = q.filter(TimeOffRequest.user_id == g.api_user.id)
    else:
        user_id = request.args.get("user_id", type=int)
        if user_id:
            q = q.filter(TimeOffRequest.user_id == user_id)

    status = request.args.get("status")
    if status:
        q = q.filter(TimeOffRequest.status == status)

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if start:
        q = q.filter(TimeOffRequest.end_date >= start)
    if end:
        q = q.filter(TimeOffRequest.start_date <= end)

    items = q.order_by(TimeOffRequest.start_date.desc()).all()
    return jsonify({"time_off_requests": [i.to_dict() for i in items]})


@api_v1_bp.route("/time-off/requests", methods=["POST"])
@require_api_token("write:time_entries")
def create_time_off_request_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    data = request.get_json() or {}
    leave_type_id = data.get("leave_type_id")
    start = _parse_date(data.get("start_date"))
    end = _parse_date(data.get("end_date"))
    if not leave_type_id or not start or not end:
        return jsonify({"error": "leave_type_id, start_date and end_date are required"}), 400

    requested_hours = data.get("requested_hours")
    if requested_hours is not None:
        try:
            from decimal import Decimal

            requested_hours = Decimal(str(requested_hours))
        except Exception:
            return jsonify({"error": "requested_hours must be numeric"}), 400

    result = WorkforceGovernanceService().create_leave_request(
        user_id=g.api_user.id,
        leave_type_id=int(leave_type_id),
        start_date=start,
        end_date=end,
        requested_hours=requested_hours,
        comment=data.get("comment"),
        submit_now=bool(data.get("submit", True)),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create request")}), 400
    return jsonify({"message": "Time-off request created", "time_off_request": result["request"].to_dict()}), 201


@api_v1_bp.route("/time-off/requests/<int:request_id>/approve", methods=["POST"])
@require_api_token("write:time_entries")
def approve_time_off_request_api(request_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    result = WorkforceGovernanceService().review_leave_request(
        request_id=request_id, reviewer_id=g.api_user.id, approve=True, comment=data.get("comment")
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not approve request")}), 400
    return jsonify({"message": "Time-off request approved", "time_off_request": result["request"].to_dict()})


@api_v1_bp.route("/time-off/requests/<int:request_id>/reject", methods=["POST"])
@require_api_token("write:time_entries")
def reject_time_off_request_api(request_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    result = WorkforceGovernanceService().review_leave_request(
        request_id=request_id, reviewer_id=g.api_user.id, approve=False, comment=data.get("comment")
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not reject request")}), 400
    return jsonify({"message": "Time-off request rejected", "time_off_request": result["request"].to_dict()})


@api_v1_bp.route("/time-off/requests/<int:request_id>", methods=["DELETE"])
@require_api_token("write:time_entries")
def delete_time_off_request_api(request_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    result = WorkforceGovernanceService().delete_leave_request(
        request_id=request_id,
        actor_id=g.api_user.id,
        actor_can_approve=_is_api_approver(g.api_user),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete request")}), 400
    return jsonify({"message": "Time-off request deleted"})


@api_v1_bp.route("/time-off/balances", methods=["GET"])
@require_api_token("read:time_entries")
def time_off_balances_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    user_id = request.args.get("user_id", type=int)
    if not user_id or not g.api_user.is_admin:
        user_id = g.api_user.id
    balances = WorkforceGovernanceService().get_leave_balance(user_id=user_id)
    return jsonify({"balances": balances})


@api_v1_bp.route("/time-off/holidays", methods=["GET"])
@require_api_token("read:reports")
def list_holidays_api():
    from app.models.time_off import CompanyHoliday

    q = CompanyHoliday.query
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if start:
        q = q.filter(CompanyHoliday.end_date >= start)
    if end:
        q = q.filter(CompanyHoliday.start_date <= end)
    items = q.order_by(CompanyHoliday.start_date.asc()).all()
    return jsonify({"holidays": [i.to_dict() for i in items]})


@api_v1_bp.route("/time-off/holidays", methods=["POST"])
@require_api_token("write:reports")
def create_holiday_api():
    from app.models.time_off import CompanyHoliday

    if not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    start = _parse_date(data.get("start_date"))
    end = _parse_date(data.get("end_date"))
    if not name or not start or not end:
        return jsonify({"error": "name, start_date and end_date are required"}), 400

    holiday = CompanyHoliday(name=name, start_date=start, end_date=end, region=data.get("region"), enabled=bool(data.get("enabled", True)))
    db.session.add(holiday)
    db.session.commit()
    return jsonify({"message": "Holiday created", "holiday": holiday.to_dict()}), 201


@api_v1_bp.route("/time-off/holidays/<int:holiday_id>", methods=["DELETE"])
@require_api_token("write:reports")
def delete_holiday_api(holiday_id):
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not g.api_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    result = WorkforceGovernanceService().delete_holiday(holiday_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete holiday")}), 400
    return jsonify({"message": "Holiday deleted"})


# ==================== Payroll Export ====================


@api_v1_bp.route("/exports/payroll", methods=["GET"])
@require_api_token("read:reports")
def export_payroll_csv():
    from app.services.workforce_governance_service import WorkforceGovernanceService
    import csv
    import io

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required (YYYY-MM-DD)"}), 400

    user_id = request.args.get("user_id", type=int)
    if not g.api_user.is_admin:
        user_id = g.api_user.id

    approved_only = request.args.get("approved_only", "false").lower() == "true"
    closed_only = request.args.get("closed_only", "false").lower() == "true"

    rows = WorkforceGovernanceService().payroll_rows(
        start_date=start,
        end_date=end,
        user_id=user_id,
        approved_only=approved_only,
        closed_only=closed_only,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "user_id",
            "username",
            "week_year",
            "week_number",
            "period_start",
            "period_end",
            "hours",
            "billable_hours",
            "non_billable_hours",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("user_id"),
                row.get("username"),
                row.get("week_year"),
                row.get("week_number"),
                row.get("period_start"),
                row.get("period_end"),
                row.get("hours"),
                row.get("billable_hours"),
                row.get("non_billable_hours"),
            ]
        )

    filename = f"payroll_export_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==================== Capacity and Compliance ====================


@api_v1_bp.route("/reports/capacity", methods=["GET"])
@require_api_token("read:reports")
def capacity_report_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required"}), 400

    team_user_ids = request.args.get("user_ids")
    parsed_user_ids = None
    if team_user_ids:
        parsed_user_ids = []
        for raw in team_user_ids.split(","):
            raw = raw.strip()
            if raw:
                try:
                    parsed_user_ids.append(int(raw))
                except ValueError:
                    pass

    if not g.api_user.is_admin:
        parsed_user_ids = [g.api_user.id]

    rows = WorkforceGovernanceService().capacity_report(start_date=start, end_date=end, team_user_ids=parsed_user_ids)
    return jsonify({"capacity": rows, "start_date": start.isoformat(), "end_date": end.isoformat()})


@api_v1_bp.route("/reports/compliance/locked-periods", methods=["GET"])
@require_api_token("read:reports")
def compliance_locked_periods_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    rows = WorkforceGovernanceService().locked_periods_report(start_date=start, end_date=end)
    return jsonify({"locked_periods": rows})


@api_v1_bp.route("/reports/compliance/audit-events", methods=["GET"])
@require_api_token("read:reports")
def compliance_audit_events_api():
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if not _is_api_approver(g.api_user):
        return jsonify({"error": "Access denied"}), 403

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    user_id = request.args.get("user_id", type=int)

    rows = WorkforceGovernanceService().compliance_audit_events(start_date=start, end_date=end, user_id=user_id)
    return jsonify({"audit_events": rows})


# ==================== GPS Mileage Tracking ====================


@api_v1_bp.route("/mileage/gps/start", methods=["POST"])
@require_api_token("write:expenses")
def mileage_gps_start_api():
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().start_tracking(
        user_id=g.api_user.id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        location=data.get("location"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not start GPS tracking")}), 400
    return jsonify(result), 201


@api_v1_bp.route("/mileage/gps/<int:track_id>/point", methods=["POST"])
@require_api_token("write:expenses")
def mileage_gps_add_point_api(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if latitude is None or longitude is None:
        return jsonify({"error": "latitude and longitude are required"}), 400

    result = GPSTrackingService().add_track_point(track_id=track_id, latitude=latitude, longitude=longitude)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not add GPS point")}), 400
    return jsonify(result)


@api_v1_bp.route("/mileage/gps/<int:track_id>/stop", methods=["POST"])
@require_api_token("write:expenses")
def mileage_gps_stop_api(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().stop_tracking(
        track_id=track_id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        location=data.get("location"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not stop GPS tracking")}), 400
    return jsonify(result)


@api_v1_bp.route("/mileage/gps/<int:track_id>/expense", methods=["POST"])
@require_api_token("write:expenses")
def mileage_gps_create_expense_api(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().create_expense_from_track(
        track_id=track_id,
        project_id=data.get("project_id"),
        rate_per_km=data.get("rate_per_km"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create expense from GPS track")}), 400
    return jsonify(result)


@api_v1_bp.route("/mileage/gps", methods=["GET"])
@require_api_token("read:expenses")
def mileage_gps_list_api():
    from app.services.gps_tracking_service import GPSTrackingService

    start = parse_datetime(request.args.get("start_date")) if request.args.get("start_date") else None
    end = parse_datetime(request.args.get("end_date")) if request.args.get("end_date") else None

    user_id = request.args.get("user_id", type=int)
    if not user_id or not g.api_user.is_admin:
        user_id = g.api_user.id

    tracks = GPSTrackingService().get_user_tracks(user_id=user_id, start_date=start, end_date=end)
    return jsonify({"tracks": tracks})


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
