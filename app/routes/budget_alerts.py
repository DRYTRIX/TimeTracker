"""
Budget Alerts Routes

This module provides API endpoints for managing budget alerts and forecasting.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import _
from app import db, log_event, track_event
from app.models import Project, BudgetAlert, User
from app.utils.budget_forecasting import (
    calculate_burn_rate,
    estimate_completion_date,
    analyze_resource_allocation,
    analyze_cost_trends,
    get_budget_status,
    check_budget_alerts,
)
from datetime import datetime, timedelta
from sqlalchemy import func
from app.utils.module_helpers import module_enabled

budget_alerts_bp = Blueprint("budget_alerts", __name__)


@budget_alerts_bp.route("/budget/dashboard")
@login_required
@module_enabled("budget_alerts")
def budget_dashboard():
    """Budget alerts and forecasting dashboard"""
    # Get projects with budgets
    user_project_ids = None
    if current_user.is_admin:
        projects = (
            Project.query.filter(Project.budget_amount.isnot(None), Project.status == "active")
            .order_by(Project.name)
            .all()
        )
    else:
        # For non-admin users, show only projects they've worked on
        from sqlalchemy import distinct
        from app.models import TimeEntry

        user_project_ids_result = (
            db.session.query(distinct(TimeEntry.project_id)).filter(TimeEntry.user_id == current_user.id).all()
        )
        user_project_ids = [pid[0] for pid in user_project_ids_result]

        projects = (
            Project.query.filter(
                Project.id.in_(user_project_ids), Project.budget_amount.isnot(None), Project.status == "active"
            )
            .order_by(Project.name)
            .all()
        )

    # Get budget status for each project
    project_budgets = []
    for project in projects:
        budget_status = get_budget_status(project.id)
        if budget_status:
            project_budgets.append(budget_status)

    # Get active alerts
    if current_user.is_admin:
        active_alerts = BudgetAlert.get_active_alerts(acknowledged=False)
    else:
        # For non-admin, get alerts for their projects
        if user_project_ids:
            active_alerts = (
                BudgetAlert.query.filter(
                    BudgetAlert.is_acknowledged == False, BudgetAlert.project_id.in_(user_project_ids)
                )
                .order_by(BudgetAlert.created_at.desc())
                .all()
            )
        else:
            active_alerts = []

    # Get alert statistics
    alert_stats = {
        "total_unacknowledged": len(active_alerts),
        "critical_alerts": len([a for a in active_alerts if a.alert_level == "critical"]),
        "warning_alerts": len([a for a in active_alerts if a.alert_level == "warning"]),
    }

    log_event("budget_dashboard_viewed", user_id=current_user.id)

    return render_template(
        "budget/dashboard.html", projects=project_budgets, active_alerts=active_alerts, alert_stats=alert_stats
    )


@budget_alerts_bp.route("/api/budget/burn-rate/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def get_burn_rate(project_id):
    """Get burn rate for a project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        # Check if user has worked on this project
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    days = request.args.get("days", 30, type=int)
    burn_rate = calculate_burn_rate(project_id, days)

    if burn_rate is None:
        return jsonify({"error": "Project not found or no data available"}), 404

    log_event("budget_burn_rate_viewed", user_id=current_user.id, project_id=project_id)

    return jsonify(burn_rate)


@budget_alerts_bp.route("/api/budget/completion-estimate/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def get_completion_estimate(project_id):
    """Get estimated completion date for a project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    days = request.args.get("days", 30, type=int)
    estimate = estimate_completion_date(project_id, days)

    if estimate is None:
        return jsonify({"error": "Project not found or no budget set"}), 404

    log_event("budget_completion_estimate_viewed", user_id=current_user.id, project_id=project_id)

    return jsonify(estimate)


@budget_alerts_bp.route("/api/budget/resource-allocation/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def get_resource_allocation(project_id):
    """Get resource allocation analysis for a project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    days = request.args.get("days", 30, type=int)
    allocation = analyze_resource_allocation(project_id, days)

    if allocation is None:
        return jsonify({"error": "Project not found"}), 404

    log_event("budget_resource_allocation_viewed", user_id=current_user.id, project_id=project_id)

    return jsonify(allocation)


@budget_alerts_bp.route("/api/budget/cost-trends/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def get_cost_trends(project_id):
    """Get cost trend analysis for a project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    days = request.args.get("days", 90, type=int)
    granularity = request.args.get("granularity", "week")

    if granularity not in ["day", "week", "month"]:
        return jsonify({"error": "Invalid granularity. Use day, week, or month"}), 400

    trends = analyze_cost_trends(project_id, days, granularity)

    if trends is None:
        return jsonify({"error": "Project not found"}), 404

    log_event("budget_cost_trends_viewed", user_id=current_user.id, project_id=project_id)

    return jsonify(trends)


@budget_alerts_bp.route("/api/budget/status/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def get_project_budget_status(project_id):
    """Get comprehensive budget status for a project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    budget_status = get_budget_status(project_id)

    if budget_status is None:
        return jsonify({"error": "Project not found or no budget set"}), 404

    return jsonify(budget_status)


@budget_alerts_bp.route("/api/budget/alerts")
@login_required
@module_enabled("budget_alerts")
def get_alerts():
    """Get budget alerts"""
    project_id = request.args.get("project_id", type=int)
    acknowledged = request.args.get("acknowledged", "false").lower() == "true"

    if current_user.is_admin:
        alerts = BudgetAlert.get_active_alerts(project_id=project_id, acknowledged=acknowledged)
    else:
        # For non-admin, get alerts for their projects
        from sqlalchemy import distinct
        from app.models import TimeEntry

        user_project_ids = (
            db.session.query(distinct(TimeEntry.project_id)).filter(TimeEntry.user_id == current_user.id).all()
        )
        user_project_ids = [pid[0] for pid in user_project_ids]

        query = BudgetAlert.query.filter(
            BudgetAlert.is_acknowledged == acknowledged, BudgetAlert.project_id.in_(user_project_ids)
        )

        if project_id:
            query = query.filter_by(project_id=project_id)

        alerts = query.order_by(BudgetAlert.created_at.desc()).all()

    return jsonify({"alerts": [alert.to_dict() for alert in alerts], "count": len(alerts)})


@budget_alerts_bp.route("/api/budget/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@login_required
@module_enabled("budget_alerts")
def acknowledge_alert(alert_id):
    """Acknowledge a budget alert"""
    alert = BudgetAlert.query.get_or_404(alert_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=alert.project_id, user_id=current_user.id).first() is not None

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    if alert.is_acknowledged:
        return jsonify({"message": "Alert already acknowledged"}), 200

    alert.acknowledge(current_user.id)

    log_event("budget_alert_acknowledged", user_id=current_user.id, alert_id=alert_id, project_id=alert.project_id)

    return jsonify({"message": "Alert acknowledged successfully", "alert": alert.to_dict()})


@budget_alerts_bp.route("/api/budget/check-alerts/<int:project_id>", methods=["POST"])
@login_required
@module_enabled("budget_alerts")
def check_project_alerts(project_id):
    """Manually check and create alerts for a project (admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    project = Project.query.get_or_404(project_id)

    alerts_to_create = check_budget_alerts(project_id)

    created_alerts = []
    for alert_data in alerts_to_create:
        alert = BudgetAlert.create_alert(
            project_id=alert_data["project_id"],
            alert_type=alert_data["type"],
            budget_consumed_percent=alert_data["budget_consumed_percent"],
            budget_amount=alert_data["budget_amount"],
            consumed_amount=alert_data["consumed_amount"],
        )
        created_alerts.append(alert.to_dict())

    log_event("budget_alerts_checked", user_id=current_user.id, project_id=project_id)

    return jsonify(
        {
            "message": f"Checked alerts for project {project.name}",
            "alerts_created": len(created_alerts),
            "alerts": created_alerts,
        }
    )


@budget_alerts_bp.route("/budget/project/<int:project_id>")
@login_required
@module_enabled("budget_alerts")
def project_budget_detail(project_id):
    """Detailed budget view for a specific project"""
    project = Project.query.get_or_404(project_id)

    # Check permissions
    if not current_user.is_admin:
        from app.models import TimeEntry

        has_access = TimeEntry.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None

        if not has_access:
            flash(_("You do not have access to this project."), "error")
            return redirect(url_for("budget_alerts.budget_dashboard"))

    # Get budget status
    budget_status = get_budget_status(project_id)

    if not budget_status:
        flash(_("This project does not have a budget set."), "warning")
        return redirect(url_for("budget_alerts.budget_dashboard"))

    # Get burn rate
    burn_rate = calculate_burn_rate(project_id, 30)

    # Get completion estimate
    completion_estimate = estimate_completion_date(project_id, 30)

    # Get resource allocation
    resource_allocation = analyze_resource_allocation(project_id, 30)

    # Get cost trends
    cost_trends = analyze_cost_trends(project_id, 90, "week")

    # Get alerts for this project
    alerts = (
        BudgetAlert.query.filter_by(project_id=project_id, is_acknowledged=False)
        .order_by(BudgetAlert.created_at.desc())
        .all()
    )

    log_event("project_budget_detail_viewed", user_id=current_user.id, project_id=project_id)

    return render_template(
        "budget/project_detail.html",
        project=project,
        budget_status=budget_status,
        burn_rate=burn_rate,
        completion_estimate=completion_estimate,
        resource_allocation=resource_allocation,
        cost_trends=cost_trends,
        alerts=alerts,
    )


@budget_alerts_bp.route("/api/budget/summary")
@login_required
@module_enabled("budget_alerts")
def get_budget_summary():
    """Get summary of all budget alerts and project statuses"""
    if current_user.is_admin:
        projects = Project.query.filter(Project.budget_amount.isnot(None), Project.status == "active").all()
    else:
        # For non-admin, get projects they've worked on
        from sqlalchemy import distinct
        from app.models import TimeEntry

        user_project_ids = (
            db.session.query(distinct(TimeEntry.project_id)).filter(TimeEntry.user_id == current_user.id).all()
        )
        user_project_ids = [pid[0] for pid in user_project_ids]

        projects = Project.query.filter(
            Project.id.in_(user_project_ids), Project.budget_amount.isnot(None), Project.status == "active"
        ).all()

    summary = {
        "total_projects": len(projects),
        "healthy": 0,
        "warning": 0,
        "critical": 0,
        "over_budget": 0,
        "total_budget": 0,
        "total_consumed": 0,
        "projects": [],
    }

    for project in projects:
        budget_status = get_budget_status(project.id)
        if budget_status:
            summary["total_budget"] += budget_status["budget_amount"]
            summary["total_consumed"] += budget_status["consumed_amount"]
            summary[budget_status["status"]] += 1
            summary["projects"].append(budget_status)

    # Get alert statistics
    if current_user.is_admin:
        alert_stats = BudgetAlert.get_alert_summary()
    else:
        from sqlalchemy import distinct
        from app.models import TimeEntry

        user_project_ids = (
            db.session.query(distinct(TimeEntry.project_id)).filter(TimeEntry.user_id == current_user.id).all()
        )
        user_project_ids = [pid[0] for pid in user_project_ids]

        total_alerts = BudgetAlert.query.filter(BudgetAlert.project_id.in_(user_project_ids)).count()

        unacknowledged_alerts = BudgetAlert.query.filter(
            BudgetAlert.project_id.in_(user_project_ids), BudgetAlert.is_acknowledged == False
        ).count()

        critical_alerts = BudgetAlert.query.filter(
            BudgetAlert.project_id.in_(user_project_ids),
            BudgetAlert.alert_level == "critical",
            BudgetAlert.is_acknowledged == False,
        ).count()

        alert_stats = {
            "total_alerts": total_alerts,
            "unacknowledged_alerts": unacknowledged_alerts,
            "critical_alerts": critical_alerts,
        }

    summary["alert_stats"] = alert_stats

    return jsonify(summary)
