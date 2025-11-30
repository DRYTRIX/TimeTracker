"""
Routes for custom report builder.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import SavedReportView, TimeEntry, Project, Task, User
from app.utils.db import safe_commit
import json
from datetime import datetime, timedelta

custom_reports_bp = Blueprint("custom_reports", __name__)


@custom_reports_bp.route("/reports/builder")
@login_required
def report_builder():
    """Custom report builder page."""
    saved_views = SavedReportView.query.filter_by(owner_id=current_user.id).all()

    # Get available data sources
    data_sources = [
        {"id": "time_entries", "name": "Time Entries", "icon": "clock"},
        {"id": "projects", "name": "Projects", "icon": "folder"},
        {"id": "tasks", "name": "Tasks", "icon": "tasks"},
        {"id": "invoices", "name": "Invoices", "icon": "file-invoice"},
        {"id": "expenses", "name": "Expenses", "icon": "receipt"},
    ]

    return render_template("reports/builder.html", saved_views=saved_views, data_sources=data_sources)


@custom_reports_bp.route("/reports/builder/save", methods=["POST"])
@login_required
def save_report_view():
    """Save a custom report view."""
    try:
        data = request.json
        name = data.get("name")
        config = data.get("config", {})
        scope = data.get("scope", "private")

        if not name:
            return jsonify({"success": False, "message": "Report name is required"}), 400

        # Check if name already exists
        existing = SavedReportView.query.filter_by(name=name, owner_id=current_user.id).first()

        if existing:
            # Update existing
            existing.config_json = json.dumps(config)
            existing.scope = scope
            existing.updated_at = datetime.utcnow()
        else:
            # Create new
            saved_view = SavedReportView(
                name=name, owner_id=current_user.id, scope=scope, config_json=json.dumps(config)
            )
            db.session.add(saved_view)

        if safe_commit("save_report_view", {"user_id": current_user.id}):
            return jsonify({"success": True, "message": "Report saved successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save report"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@custom_reports_bp.route("/reports/builder/<int:view_id>")
@login_required
def view_custom_report(view_id):
    """View a custom report."""
    saved_view = SavedReportView.query.get_or_404(view_id)

    # Check access
    if saved_view.owner_id != current_user.id and saved_view.scope == "private":
        flash(_("You do not have permission to view this report."), "error")
        return redirect(url_for("custom_reports.report_builder"))

    # Parse config
    try:
        config = json.loads(saved_view.config_json)
    except:
        config = {}

    # Generate report data based on config
    report_data = generate_report_data(config, current_user.id)

    return render_template("reports/custom_view.html", saved_view=saved_view, config=config, report_data=report_data)


@custom_reports_bp.route("/reports/builder/preview", methods=["POST"])
@login_required
def preview_report():
    """Preview report data based on configuration."""
    try:
        # Validate JSON request
        if not request.is_json:
            return jsonify({"success": False, "message": "Request must be JSON"}), 400
        
        data = request.get_json(silent=False)
        if data is None:
            return jsonify({"success": False, "message": "Invalid JSON in request body"}), 400
        
        config = data.get("config", {})
        
        # Validate that config is a dictionary
        if not isinstance(config, dict):
            return jsonify({"success": False, "message": "Config must be a dictionary"}), 400

        # Generate report data
        report_data = generate_report_data(config, current_user.id)

        return jsonify({"success": True, "data": report_data})
    except Exception as e:
        # Log the error for debugging
        from flask import current_app
        current_app.logger.error(f"Error in preview_report: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@custom_reports_bp.route("/reports/builder/<int:view_id>/data", methods=["GET"])
@login_required
def get_report_data(view_id):
    """Get report data as JSON."""
    saved_view = SavedReportView.query.get_or_404(view_id)

    # Check access
    if saved_view.owner_id != current_user.id and saved_view.scope == "private":
        return jsonify({"error": "Access denied"}), 403

    # Parse config
    try:
        config = json.loads(saved_view.config_json)
    except:
        config = {}

    # Generate report data
    report_data = generate_report_data(config, current_user.id)

    return jsonify(report_data)


def generate_report_data(config, user_id=None):
    """Generate report data based on configuration."""
    data_source = config.get("data_source", "time_entries")
    filters = config.get("filters", {})
    columns = config.get("columns", [])
    grouping = config.get("grouping", {})

    # Parse date filters
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    try:
        if start_date and isinstance(start_date, str) and start_date.strip():
            start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d")
        else:
            start_dt = datetime.utcnow() - timedelta(days=30)
    except (ValueError, AttributeError) as e:
        from flask import current_app
        current_app.logger.warning(f"Invalid start_date format: {start_date}, using default")
        start_dt = datetime.utcnow() - timedelta(days=30)

    try:
        if end_date and isinstance(end_date, str) and end_date.strip():
            end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        else:
            end_dt = datetime.utcnow()
    except (ValueError, AttributeError) as e:
        from flask import current_app
        current_app.logger.warning(f"Invalid end_date format: {end_date}, using default")
        end_dt = datetime.utcnow()

    # Generate data based on source
    if data_source == "time_entries":
        query = TimeEntry.query.filter(
            TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_dt, TimeEntry.start_time <= end_dt
        )

        # Filter by user if not admin or if user_id is specified
        if user_id:
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                query = query.filter(TimeEntry.user_id == user_id)

        project_id = filters.get("project_id")
        if project_id:
            # Convert to int if it's a string
            try:
                project_id = int(project_id) if isinstance(project_id, str) else project_id
                query = query.filter(TimeEntry.project_id == project_id)
            except (ValueError, TypeError):
                from flask import current_app
                current_app.logger.warning(f"Invalid project_id: {project_id}, ignoring filter")
        if filters.get("user_id"):
            query = query.filter(TimeEntry.user_id == filters["user_id"])

        entries = query.all()

        return {
            "data": [
                {
                    "id": e.id,
                    "date": e.start_time.strftime("%Y-%m-%d") if e.start_time else "",
                    "project": e.project.name if e.project else "",
                    "user": e.user.username if e.user else "",
                    "duration": e.duration_hours,
                    "notes": e.notes or "",
                }
                for e in entries
            ],
            "summary": {"total_entries": len(entries), "total_hours": sum(e.duration_hours or 0 for e in entries)},
        }

    elif data_source == "projects":
        query = Project.query

        if filters.get("status"):
            query = query.filter(Project.status == filters["status"])

        projects = query.all()

        return {
            "data": [
                {
                    "id": p.id,
                    "name": p.name,
                    "client": p.client.name if p.client else "",
                    "status": p.status,
                    "total_hours": sum(e.duration_hours or 0 for e in p.time_entries if e.end_time),
                }
                for p in projects
            ],
            "summary": {"total_projects": len(projects)},
        }

    # Add more data sources as needed
    return {"data": [], "summary": {}}
