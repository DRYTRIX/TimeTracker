from flask import Blueprint, render_template, request, jsonify, abort
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models.audit_log import AuditLog
from app.models import User
from app.utils.permissions import admin_or_permission_required
from app.utils.audit import check_audit_table_exists, reset_audit_table_cache
from sqlalchemy import inspect as sqlalchemy_inspect
from datetime import datetime, timedelta

audit_logs_bp = Blueprint("audit_logs", __name__)


@audit_logs_bp.route("/audit-logs")
@login_required
@admin_or_permission_required("view_audit_logs")
def list_audit_logs():
    """List audit logs with filtering options"""
    # Check if table exists first
    reset_audit_table_cache()
    if not check_audit_table_exists(force_check=True):
        from flask import flash

        flash(_("Audit logs table does not exist. Please run: flask db upgrade"), "warning")
        return render_template(
            "audit_logs/list.html",
            audit_logs=[],
            pagination=None,
            entity_type="",
            entity_id=None,
            user_id=None,
            action="",
            days=30,
            entity_types=[],
            users=[],
        )

    page = request.args.get("page", 1, type=int)
    entity_type = request.args.get("entity_type", "").strip()
    entity_id = request.args.get("entity_id", type=int)
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "").strip()
    days = request.args.get("days", 30, type=int)

    # Build query
    query = AuditLog.query

    # Filter by entity type
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    # Filter by entity ID
    if entity_id:
        query = query.filter_by(entity_id=entity_id)

    # Filter by user
    if user_id:
        query = query.filter_by(user_id=user_id)

    # Filter by action
    if action:
        query = query.filter_by(action=action)

    # Filter by date range
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= cutoff_date)

    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=50, error_out=False)

    # Get unique entity types for filter dropdown
    try:
        entity_types = db.session.query(AuditLog.entity_type).distinct().all()
        entity_types = [et[0] for et in entity_types]
        entity_types.sort()
    except Exception:
        # Table might not exist yet
        entity_types = []

    # Get users for filter dropdown
    try:
        users_with_logs = db.session.query(User).join(AuditLog).distinct().all()
    except Exception:
        # Table might not exist yet or no logs yet
        users_with_logs = []

    return render_template(
        "audit_logs/list.html",
        audit_logs=pagination.items,
        pagination=pagination,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        days=days,
        entity_types=entity_types,
        users=users_with_logs,
    )


@audit_logs_bp.route("/audit-logs/<int:log_id>")
@login_required
@admin_or_permission_required("view_audit_logs")
def view_audit_log(log_id):
    """View details of a specific audit log entry"""
    audit_log = AuditLog.query.get_or_404(log_id)

    return render_template(
        "audit_logs/view.html",
        audit_log=audit_log,
    )


@audit_logs_bp.route("/audit-logs/entity/<entity_type>/<int:entity_id>")
@login_required
@admin_or_permission_required("view_audit_logs")
def entity_history(entity_type, entity_id):
    """View audit history for a specific entity"""
    page = request.args.get("page", 1, type=int)

    # Get audit logs for this entity
    query = AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id).order_by(AuditLog.created_at.desc())

    pagination = query.paginate(page=page, per_page=50, error_out=False)

    # Try to get the entity name
    entity_name = None
    try:
        # Import models dynamically
        from app.models import (
            Project,
            Task,
            TimeEntry,
            Invoice,
            Client,
            User,
            Expense,
            Payment,
            Comment,
            ProjectCost,
            KanbanColumn,
            TimeEntryTemplate,
            ClientNote,
            WeeklyTimeGoal,
            CalendarEvent,
            BudgetAlert,
        )

        model_map = {
            "Project": Project,
            "Task": Task,
            "TimeEntry": TimeEntry,
            "Invoice": Invoice,
            "Client": Client,
            "User": User,
            "Expense": Expense,
            "Payment": Payment,
            "Comment": Comment,
            "ProjectCost": ProjectCost,
            "KanbanColumn": KanbanColumn,
            "TimeEntryTemplate": TimeEntryTemplate,
            "ClientNote": ClientNote,
            "WeeklyTimeGoal": WeeklyTimeGoal,
            "CalendarEvent": CalendarEvent,
            "BudgetAlert": BudgetAlert,
        }

        model_class = model_map.get(entity_type)
        if model_class:
            entity = model_class.query.get(entity_id)
            if entity:
                entity_name = (
                    getattr(entity, "name", None)
                    or getattr(entity, "title", None)
                    or getattr(entity, "username", None)
                    or str(entity)
                )
    except Exception:
        pass

    return render_template(
        "audit_logs/entity_history.html",
        audit_logs=pagination.items,
        pagination=pagination,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
    )


@audit_logs_bp.route("/api/audit-logs")
@login_required
@admin_or_permission_required("view_audit_logs")
def api_audit_logs():
    """API endpoint for audit logs (JSON)"""
    page = request.args.get("page", 1, type=int)
    entity_type = request.args.get("entity_type", "").strip()
    entity_id = request.args.get("entity_id", type=int)
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "").strip()
    limit = request.args.get("limit", 100, type=int)

    query = AuditLog.query

    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)

    audit_logs = query.all()

    return jsonify({"audit_logs": [log.to_dict() for log in audit_logs], "count": len(audit_logs)})


@audit_logs_bp.route("/api/audit-logs/status")
@login_required
@admin_or_permission_required("view_audit_logs")
def audit_logs_status():
    """Check audit logs table status and reset cache if needed"""
    try:
        # Force check table existence
        reset_audit_table_cache()
        table_exists = check_audit_table_exists(force_check=True)

        status = {"table_exists": table_exists, "enabled": table_exists}

        if table_exists:
            try:
                count = AuditLog.query.count()
                status["total_logs"] = count

                # Check recent activity
                recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()
                status["recent_logs"] = [log.to_dict() for log in recent]
            except Exception as e:
                status["error"] = str(e)
        else:
            # Check what tables do exist
            try:
                inspector = sqlalchemy_inspect(db.engine)
                tables = inspector.get_table_names()
                status["available_tables"] = sorted(tables)
                status["message"] = "audit_logs table does not exist. Run: flask db upgrade"
            except Exception as e:
                status["error"] = f"Could not check tables: {e}"

        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
