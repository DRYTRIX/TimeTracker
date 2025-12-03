"""
Routes for salesman-based report generation and email mapping management.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import SalesmanEmailMapping, Client
from app.services.unpaid_hours_service import UnpaidHoursService
from app.services.scheduled_report_service import ScheduledReportService
from app.utils.db import safe_commit
from app.utils.email import send_email
from datetime import datetime, timedelta
import json


salesman_reports_bp = Blueprint("salesman_reports", __name__)


@salesman_reports_bp.route("/admin/salesman-email-mappings")
@login_required
def list_email_mappings():
    """List all salesman email mappings (Admin only)"""
    if not current_user.is_admin:
        flash(_("You do not have permission to access this page."), "error")
        return redirect(url_for("reports.reports"))

    mappings = SalesmanEmailMapping.query.order_by(SalesmanEmailMapping.salesman_initial).all()
    return render_template("admin/salesman_email_mappings.html", mappings=mappings)


@salesman_reports_bp.route("/api/salesman-email-mappings", methods=["GET"])
@login_required
def get_email_mappings_api():
    """Get all salesman email mappings (API)"""
    if not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    mappings = SalesmanEmailMapping.query.order_by(SalesmanEmailMapping.salesman_initial).all()
    return jsonify({"success": True, "mappings": [m.to_dict() for m in mappings]})


@salesman_reports_bp.route("/api/salesman-email-mappings", methods=["POST"])
@login_required
def create_email_mapping():
    """Create a new salesman email mapping"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    try:
        data = request.json
        salesman_initial = data.get("salesman_initial")
        email_address = data.get("email_address")
        email_pattern = data.get("email_pattern")
        domain = data.get("domain")
        notes = data.get("notes")

        if not salesman_initial:
            return jsonify({"success": False, "message": "Salesman initial is required"}), 400

        # Check if mapping already exists
        existing = SalesmanEmailMapping.query.filter_by(salesman_initial=salesman_initial.upper().strip()).first()
        if existing:
            return jsonify({"success": False, "message": "Mapping for this initial already exists"}), 400

        mapping = SalesmanEmailMapping(
            salesman_initial=salesman_initial,
            email_address=email_address,
            email_pattern=email_pattern,
            domain=domain,
            notes=notes,
        )

        db.session.add(mapping)
        if safe_commit("create_salesman_email_mapping", {"user_id": current_user.id}):
            return jsonify({"success": True, "message": "Mapping created successfully", "mapping": mapping.to_dict()})
        else:
            return jsonify({"success": False, "message": "Failed to create mapping"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@salesman_reports_bp.route("/api/salesman-email-mappings/<int:mapping_id>", methods=["PUT"])
@login_required
def update_email_mapping(mapping_id):
    """Update a salesman email mapping"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    try:
        mapping = SalesmanEmailMapping.query.get_or_404(mapping_id)
        data = request.json

        if "email_address" in data:
            mapping.email_address = data["email_address"]
        if "email_pattern" in data:
            mapping.email_pattern = data["email_pattern"]
        if "domain" in data:
            mapping.domain = data["domain"]
        if "notes" in data:
            mapping.notes = data["notes"]
        if "is_active" in data:
            mapping.is_active = bool(data["is_active"])

        mapping.updated_at = datetime.utcnow()

        if safe_commit("update_salesman_email_mapping", {"user_id": current_user.id, "mapping_id": mapping_id}):
            return jsonify({"success": True, "message": "Mapping updated successfully", "mapping": mapping.to_dict()})
        else:
            return jsonify({"success": False, "message": "Failed to update mapping"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@salesman_reports_bp.route("/api/salesman-email-mappings/<int:mapping_id>", methods=["DELETE"])
@login_required
def delete_email_mapping(mapping_id):
    """Delete a salesman email mapping"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    try:
        mapping = SalesmanEmailMapping.query.get_or_404(mapping_id)
        db.session.delete(mapping)

        if safe_commit("delete_salesman_email_mapping", {"user_id": current_user.id, "mapping_id": mapping_id}):
            return jsonify({"success": True, "message": "Mapping deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to delete mapping"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@salesman_reports_bp.route("/api/unpaid-hours/by-salesman", methods=["GET"])
@login_required
def get_unpaid_hours_by_salesman():
    """Get unpaid hours grouped by salesman"""
    if not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        salesman_field_name = request.args.get("salesman_field_name", "salesman")

        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        unpaid_service = UnpaidHoursService()
        result = unpaid_service.get_unpaid_hours_by_salesman(
            start_date=start_dt,
            end_date=end_dt,
            salesman_field_name=salesman_field_name,
        )

        # Convert entries to dict format for JSON serialization
        formatted_result = {}
        for salesman_initial, data in result.items():
            formatted_result[salesman_initial] = {
                "total_hours": data["total_hours"],
                "total_entries": data["total_entries"],
                "clients": data["clients"],
                "projects": data["projects"],
                "entries": [
                    {
                        "id": e.id,
                        "date": e.start_time.strftime("%Y-%m-%d") if e.start_time else "",
                        "project": e.project.name if e.project else "",
                        "client": (e.project.client.name if e.project and e.project.client else (e.client.name if e.client else "Unknown")),
                        "user": e.user.username if e.user else "",
                        "duration": e.duration_hours,
                        "notes": e.notes or "",
                    }
                    for e in data["entries"]
                ],
            }

        return jsonify({"success": True, "data": formatted_result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@salesman_reports_bp.route("/api/salesman-reports/preview-email", methods=["POST"])
@login_required
def preview_salesman_email():
    """Preview email address for a salesman initial"""
    if not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    try:
        data = request.json
        salesman_initial = data.get("salesman_initial")
        email_pattern = data.get("email_pattern")
        domain = data.get("domain")

        if not salesman_initial:
            return jsonify({"error": "Salesman initial is required"}), 400

        salesman_initial = salesman_initial.strip().upper()

        # Try to get existing mapping
        mapping = SalesmanEmailMapping.query.filter_by(salesman_initial=salesman_initial).first()
        if mapping:
            email = mapping.get_email()
        else:
            # Preview with provided pattern/domain
            if email_pattern:
                email = email_pattern.replace("{value}", salesman_initial)
            elif domain:
                email = f"{salesman_initial}@{domain}"
            else:
                email = None

        return jsonify({"success": True, "email": email, "salesman_initial": salesman_initial})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@salesman_reports_bp.route("/api/salesman-reports/generate", methods=["POST"])
@login_required
def generate_salesman_reports():
    """Generate and optionally send reports for each salesman"""
    if not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    try:
        data = request.json
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        salesman_field_name = data.get("salesman_field_name", "salesman")
        send_emails = data.get("send_emails", False)

        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

        unpaid_service = UnpaidHoursService()
        result = unpaid_service.get_unpaid_hours_by_salesman(
            start_date=start_dt,
            end_date=end_dt,
            salesman_field_name=salesman_field_name,
        )

        reports = {}
        emails_sent = []

        for salesman_initial, data in result.items():
            if salesman_initial == "_UNASSIGNED_":
                continue

            # Get email for this salesman
            email = SalesmanEmailMapping.get_email_for_initial(salesman_initial)
            if not email and send_emails:
                continue  # Skip if no email mapping and we're sending emails

            # Format report data
            report_data = {
                "salesman_initial": salesman_initial,
                "total_hours": data["total_hours"],
                "total_entries": data["total_entries"],
                "clients": data["clients"],
                "projects": data["projects"],
                "entries": [
                    {
                        "id": e.id,
                        "date": e.start_time.strftime("%Y-%m-%d") if e.start_time else "",
                        "project": e.project.name if e.project else "",
                        "client": (e.project.client.name if e.project and e.project.client else (e.client.name if e.client else "Unknown")),
                        "user": e.user.username if e.user else "",
                        "duration": e.duration_hours,
                        "notes": e.notes or "",
                    }
                    for e in data["entries"]
                ],
            }

            reports[salesman_initial] = report_data

            # Send email if requested
            if send_emails and email:
                try:
                    subject = f"Unpaid Hours Report - {salesman_initial}"
                    text_body = f"""
Unpaid Hours Report for {salesman_initial}

Total Hours: {data['total_hours']}
Total Entries: {data['total_entries']}

Clients: {', '.join(data['clients'])}

Projects: {', '.join(data['projects'])}

Please review the attached report for details.
"""
                    send_email(
                        to=email,
                        subject=subject,
                        text_body=text_body,
                        template="email/unpaid_hours_report.html",
                        salesman_initial=salesman_initial,
                        report_data=report_data,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    emails_sent.append({"salesman": salesman_initial, "email": email, "status": "sent"})
                except Exception as e:
                    emails_sent.append({"salesman": salesman_initial, "email": email, "status": "error", "error": str(e)})

        return jsonify({
            "success": True,
            "reports": reports,
            "emails_sent": emails_sent,
            "total_salesmen": len(reports),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

