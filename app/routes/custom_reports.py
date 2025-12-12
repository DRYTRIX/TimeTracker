"""
Routes for custom report builder.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import SavedReportView, TimeEntry, Project, Task, User, Client
from app.utils.db import safe_commit
from app.services.unpaid_hours_service import UnpaidHoursService
import json
from datetime import datetime, timedelta

custom_reports_bp = Blueprint("custom_reports", __name__)


@custom_reports_bp.route("/reports/builder")
@custom_reports_bp.route("/reports/builder/<int:view_id>/edit")
@login_required
def report_builder(view_id=None):
    """Custom report builder page. If view_id is provided, load that saved view for editing."""
    saved_views = SavedReportView.query.filter_by(owner_id=current_user.id).all()
    
    # Load saved view if editing
    saved_view = None
    if view_id:
        saved_view = SavedReportView.query.get_or_404(view_id)
        # Check access
        if saved_view.owner_id != current_user.id and saved_view.scope == "private":
            flash(_("You do not have permission to edit this report."), "error")
            return redirect(url_for("custom_reports.report_builder"))
        
        # Parse config
        try:
            config = json.loads(saved_view.config_json)
        except:
            config = {}
    else:
        config = {}

    # Get available data sources
    data_sources = [
        {"id": "time_entries", "name": "Time Entries", "icon": "clock"},
        {"id": "projects", "name": "Projects", "icon": "folder"},
        {"id": "tasks", "name": "Tasks", "icon": "tasks"},
        {"id": "invoices", "name": "Invoices", "icon": "file-invoice"},
        {"id": "expenses", "name": "Expenses", "icon": "receipt"},
    ]

    # Get available clients for custom field filtering
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    
    # Extract unique custom field keys from clients
    custom_field_keys = set()
    for client in clients:
        if client.custom_fields:
            custom_field_keys.update(client.custom_fields.keys())

    return render_template(
        "reports/builder.html",
        saved_views=saved_views,
        data_sources=data_sources,
        custom_field_keys=sorted(list(custom_field_keys)),
        saved_view=saved_view,
        config=config,
    )


@custom_reports_bp.route("/reports/builder/save", methods=["POST"])
@login_required
def save_report_view():
    """Save a custom report view."""
    try:
        # Check if request has JSON data
        if not request.is_json:
            return jsonify({"success": False, "message": "Request must be JSON"}), 400
        
        data = request.get_json(silent=False)
        if data is None:
            return jsonify({"success": False, "message": "Invalid JSON in request body"}), 400
        
        name = data.get("name")
        config = data.get("config", {})
        scope = data.get("scope", "private")
        view_id = data.get("view_id")  # For editing existing reports

        if not name or not name.strip():
            return jsonify({"success": False, "message": "Report name is required"}), 400

        name = name.strip()

        # Validate config is a dictionary
        if not isinstance(config, dict):
            return jsonify({"success": False, "message": "Config must be a dictionary"}), 400

        # Extract iterative report generation settings
        iterative_report_generation = data.get("iterative_report_generation", False)
        iterative_custom_field_name = data.get("iterative_custom_field_name", "").strip() or None
        
        # If view_id is provided, update existing report
        if view_id:
            existing = SavedReportView.query.get(view_id)
            if not existing:
                return jsonify({"success": False, "message": "Report not found"}), 404
            
            # Check permission
            if existing.owner_id != current_user.id and existing.scope == "private":
                return jsonify({"success": False, "message": "You do not have permission to edit this report"}), 403
            
            # Update existing
            existing.name = name
            existing.config_json = json.dumps(config)
            existing.scope = scope
            existing.iterative_report_generation = iterative_report_generation
            existing.iterative_custom_field_name = iterative_custom_field_name
            existing.updated_at = datetime.utcnow()
            saved_view = existing
            action = "updated"
        else:
            # Check if name already exists (for new reports)
            existing = SavedReportView.query.filter_by(name=name, owner_id=current_user.id).first()
            if existing:
                # Update existing with same name
                existing.config_json = json.dumps(config)
                existing.scope = scope
                existing.updated_at = datetime.utcnow()
                saved_view = existing
                action = "updated"
            else:
                # Create new
                saved_view = SavedReportView(
                    name=name,
                    owner_id=current_user.id,
                    scope=scope,
                    config_json=json.dumps(config),
                    iterative_report_generation=iterative_report_generation,
                    iterative_custom_field_name=iterative_custom_field_name,
                )
                db.session.add(saved_view)
                action = "created"

        if safe_commit("save_report_view", {"user_id": current_user.id}):
            return jsonify({
                "success": True, 
                "message": _("Report %(action)s successfully", action=action),
                "view_id": saved_view.id,
                "action": action
            })
        else:
            db.session.rollback()
            return jsonify({"success": False, "message": "Failed to save report due to a database error"}), 500

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "message": f"Invalid JSON: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Error saving report view: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Error saving report: {str(e)}"}), 500


@custom_reports_bp.route("/reports/builder/<int:view_id>")
@login_required
def view_custom_report(view_id):
    """View a custom report. Supports iterative generation if enabled."""
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

    # Check if iterative report generation is enabled
    if saved_view.iterative_report_generation and saved_view.iterative_custom_field_name:
        # Generate reports for each custom field value
        return _generate_iterative_reports(saved_view, config, current_user.id)
    
    # Generate single report data based on config
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
        # Check if unpaid hours filter is enabled
        unpaid_only = filters.get("unpaid_only", False)
        custom_field_filter = filters.get("custom_field_filter")  # e.g., {"salesman": "MM"}

        if unpaid_only:
            # Use unpaid hours service
            unpaid_service = UnpaidHoursService()
            entries = unpaid_service.get_unpaid_time_entries(
                start_date=start_dt,
                end_date=end_dt,
                project_id=filters.get("project_id"),
                client_id=filters.get("client_id"),
                user_id=filters.get("user_id") or user_id,
                custom_field_filter=custom_field_filter,
            )
        else:
            # Standard query
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

            # Apply custom field filter if provided
            if custom_field_filter:
                # Get all entries first, then filter by custom fields
                all_entries = query.all()
                entries = []
                for entry in all_entries:
                    client = None
                    if entry.project and entry.project.client_obj:
                        client = entry.project.client_obj
                    elif entry.client:
                        client = entry.client

                    if client and client.custom_fields:
                        matches = True
                        for field_name, field_value in custom_field_filter.items():
                            client_value = client.custom_fields.get(field_name)
                            if str(client_value).upper().strip() != str(field_value).upper().strip():
                                matches = False
                                break
                        if matches:
                            entries.append(entry)
            else:
                entries = query.all()

        # Build response data
        client_data = {}
        data_list = []
        
        for e in entries:
            client = None
            if e.project and e.project.client_obj:
                client = e.project.client_obj
            elif e.client:
                client = e.client
            
            client_name = client.name if client else "Unknown"
            salesman = None
            if client and client.custom_fields:
                salesman = client.custom_fields.get("salesman")

            entry_data = {
                "id": e.id,
                "date": e.start_time.strftime("%Y-%m-%d") if e.start_time else "",
                "project": e.project.name if e.project else "",
                "client": client_name,
                "salesman": salesman or "",
                "user": e.user.username if e.user else "",
                "duration": e.duration_hours,
                "notes": e.notes or "",
                "billable": e.billable,
                "paid": e.paid,
            }
            
            data_list.append(entry_data)
            
            # Group by client for summary
            if client_name not in client_data:
                client_data[client_name] = {"hours": 0, "entries": []}
            client_data[client_name]["hours"] += e.duration_hours or 0
            client_data[client_name]["entries"].append(entry_data)

        return {
            "data": data_list,
            "summary": {
                "total_entries": len(entries),
                "total_hours": round(sum(e.duration_hours or 0 for e in entries), 2),
                "unpaid_only": unpaid_only,
                "by_client": client_data,
            },
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
                    "client": p.client_obj.name if p.client_obj else "",
                    "status": p.status,
                    "total_hours": sum(e.duration_hours or 0 for e in p.time_entries if e.end_time),
                }
                for p in projects
            ],
            "summary": {"total_projects": len(projects)},
        }

    # Add more data sources as needed
    return {"data": [], "summary": {}}


@custom_reports_bp.route("/reports/builder/saved")
@login_required
def list_saved_views():
    """List all saved report views for the current user."""
    from app.utils.timezone import convert_app_datetime_to_user
    saved_views = SavedReportView.query.filter_by(owner_id=current_user.id).order_by(SavedReportView.created_at.desc()).all()
    return render_template("reports/saved_views_list.html", saved_views=saved_views, convert_app_datetime_to_user=convert_app_datetime_to_user)


@custom_reports_bp.route("/reports/builder/<int:view_id>/edit", methods=["GET"])
@login_required
def edit_saved_view(view_id):
    """Edit a saved report view - redirects to builder with view_id."""
    saved_view = SavedReportView.query.get_or_404(view_id)
    
    # Check permission
    if saved_view.owner_id != current_user.id and saved_view.scope == "private":
        flash(_("You do not have permission to edit this report."), "error")
        return redirect(url_for("custom_reports.list_saved_views"))
    
    # Redirect to builder with edit mode
    return redirect(url_for("custom_reports.report_builder", view_id=view_id))


@custom_reports_bp.route("/api/reports/builder/custom-field-values", methods=["GET"])
@login_required
def get_custom_field_values():
    """Get unique values for a custom field from clients."""
    custom_field_name = request.args.get("field_name")
    if not custom_field_name:
        return jsonify({"success": False, "message": "field_name parameter is required"}), 400
    
    # Get all active clients
    clients = Client.query.filter_by(status="active").all()
    unique_values = set()
    
    for client in clients:
        if client.custom_fields and custom_field_name in client.custom_fields:
            value = client.custom_fields[custom_field_name]
            if value:
                unique_values.add(str(value).strip())
    
    return jsonify({
        "success": True,
        "field_name": custom_field_name,
        "values": sorted(list(unique_values))
    })


@custom_reports_bp.route("/reports/builder/<int:view_id>/delete", methods=["POST"])
@login_required
def delete_saved_view(view_id):
    """Delete a saved report view."""
    saved_view = SavedReportView.query.get_or_404(view_id)
    
    # Check permission
    if saved_view.owner_id != current_user.id and not current_user.is_admin:
        flash(_("You do not have permission to delete this report view."), "error")
        return redirect(url_for("custom_reports.list_saved_views"))
    
    view_name = saved_view.name
    
    # Check if it's used in any schedules
    from app.models import ReportEmailSchedule
    schedules = ReportEmailSchedule.query.filter_by(saved_view_id=view_id).all()
    if schedules:
        flash(_("Cannot delete report view: it is used in %(count)d scheduled report(s).", count=len(schedules)), "error")
        return redirect(url_for("custom_reports.list_saved_views"))
    
    db.session.delete(saved_view)
    if safe_commit("delete_saved_view", {"view_id": view_id}):
        flash(_('Report view "%(name)s" deleted successfully.', name=view_name), "success")
    else:
        flash(_("Could not delete report view due to a database error"), "error")
    
    return redirect(url_for("custom_reports.list_saved_views"))


def _generate_iterative_reports(saved_view: SavedReportView, config: dict, user_id: int):
    """
    Generate multiple reports, one per custom field value.
    
    Returns a template with all reports grouped by custom field value.
    """
    from app.models import Client, TimeEntry
    from flask import render_template
    
    custom_field_name = saved_view.iterative_custom_field_name
    
    # Get date range from config
    filters = config.get("filters", {})
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    
    try:
        if start_date and isinstance(start_date, str) and start_date.strip():
            start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d")
        else:
            start_dt = datetime.utcnow() - timedelta(days=30)
    except (ValueError, AttributeError):
        start_dt = datetime.utcnow() - timedelta(days=30)
    
    try:
        if end_date and isinstance(end_date, str) and end_date.strip():
            end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        else:
            end_dt = datetime.utcnow()
    except (ValueError, AttributeError):
        end_dt = datetime.utcnow()
    
    # Get all unique values for the custom field
    clients = Client.query.filter_by(status="active").all()
    unique_values = set()
    
    # Collect unique values from clients
    for client in clients:
        if client.custom_fields and custom_field_name in client.custom_fields:
            value = client.custom_fields[custom_field_name]
            if value:
                unique_values.add(str(value).strip())
    
    # Also check from time entries in the date range
    time_entries = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    ).all()
    
    for entry in time_entries:
        client = None
        if entry.project and entry.project.client_obj:
            client = entry.project.client_obj
        elif entry.client:
            client = entry.client
        
        if client and client.custom_fields and custom_field_name in client.custom_fields:
            value = client.custom_fields[custom_field_name]
            if value:
                unique_values.add(str(value).strip())
    
    # Generate report for each value
    iterative_reports = {}
    for field_value in sorted(unique_values):
        # Create modified config with custom field filter
        modified_config = config.copy()
        if "filters" not in modified_config:
            modified_config["filters"] = {}
        modified_config["filters"]["custom_field_filter"] = {custom_field_name: field_value}
        
        # Generate report data
        report_data = generate_report_data(modified_config, user_id)
        iterative_reports[field_value] = report_data
    
    return render_template(
        "reports/iterative_view.html",
        saved_view=saved_view,
        config=config,
        iterative_reports=iterative_reports,
        custom_field_name=custom_field_name,
    )
