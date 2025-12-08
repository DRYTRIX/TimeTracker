"""
Routes for scheduled reports management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.models import SavedReportView, ReportEmailSchedule
from app.services.scheduled_report_service import ScheduledReportService

scheduled_reports_bp = Blueprint("scheduled_reports", __name__)


@scheduled_reports_bp.route("/api/reports/scheduled", methods=["GET"])
@login_required
def api_list_scheduled():
    """Get scheduled reports as JSON"""
    from sqlalchemy.orm import joinedload
    from app.models import ReportEmailSchedule
    from app import db

    # Query with eager loading
    query = db.session.query(ReportEmailSchedule).options(joinedload(ReportEmailSchedule.saved_view))

    if not current_user.is_admin:
        query = query.filter_by(created_by=current_user.id)

    schedules = query.order_by(ReportEmailSchedule.next_run_at.asc()).all()

    return jsonify(
        {
            "schedules": [
                {
                    "id": s.id,
                    "saved_view_id": s.saved_view_id,
                    "saved_view_name": s.saved_view.name if s.saved_view else "Unknown",
                    "recipients": s.recipients,
                    "cadence": s.cadence,
                    "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                    "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                    "active": s.active,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in schedules
            ]
        }
    )


@scheduled_reports_bp.route("/reports/scheduled")
@login_required
def list_scheduled():
    """List scheduled reports"""
    service = ScheduledReportService()
    schedules = service.list_schedules(user_id=current_user.id)

    return render_template("reports/scheduled.html", schedules=schedules)


@scheduled_reports_bp.route("/reports/scheduled/create", methods=["GET", "POST"])
@login_required
def create_scheduled():
    """Create a scheduled report"""
    service = ScheduledReportService()
    saved_views = SavedReportView.query.filter_by(owner_id=current_user.id).all()

    if request.method == "POST":
        saved_view_id = request.form.get("saved_view_id", type=int)
        recipients = request.form.get("recipients", "").strip()
        cadence = request.form.get("cadence", "").strip()
        cron = request.form.get("cron", "").strip() or None
        timezone = request.form.get("timezone", "").strip() or None
        split_by_custom_field = request.form.get("split_by_custom_field") == "1"
        custom_field_name = request.form.get("custom_field_name", "").strip() or None

        if not saved_view_id or not recipients or not cadence:
            flash(_("Please fill in all required fields."), "error")
            return render_template("reports/schedule_form.html", saved_views=saved_views)

        if split_by_custom_field and not custom_field_name:
            flash(_("Please specify a custom field name when enabling report iteration."), "error")
            return render_template("reports/schedule_form.html", saved_views=saved_views)

        result = service.create_schedule(
            saved_view_id=saved_view_id,
            recipients=recipients,
            cadence=cadence,
            created_by=current_user.id,
            cron=cron,
            timezone=timezone,
            split_by_custom_field=split_by_custom_field,
            custom_field_name=custom_field_name,
        )

        if result["success"]:
            flash(_("Scheduled report created successfully."), "success")
            return redirect(url_for("scheduled_reports.list_scheduled"))
        else:
            flash(result["message"], "error")

    return render_template("reports/schedule_form.html", saved_views=saved_views)


@scheduled_reports_bp.route("/reports/scheduled/<int:schedule_id>/delete", methods=["POST"])
@login_required
def delete_scheduled(schedule_id):
    """Delete a scheduled report"""
    service = ScheduledReportService()
    result = service.delete_schedule(schedule_id, current_user.id)

    if result["success"]:
        flash(_("Scheduled report deleted successfully."), "success")
    else:
        flash(result["message"], "error")

    return redirect(url_for("scheduled_reports.list_scheduled"))


@scheduled_reports_bp.route("/api/reports/scheduled", methods=["POST"])
@login_required
def api_create_scheduled():
    """Create scheduled report via API"""
    service = ScheduledReportService()
    data = request.get_json()

    saved_view_id = data.get("saved_view_id", type=int)
    recipients = data.get("recipients", "").strip()
    cadence = data.get("cadence", "").strip()
    cron = data.get("cron", "").strip() or None
    timezone = data.get("timezone", "").strip() or None
    split_by_custom_field = data.get("split_by_custom_field", False)
    custom_field_name = data.get("custom_field_name", "").strip() or None

    if not saved_view_id or not recipients or not cadence:
        return jsonify({"success": False, "error": _("Please fill in all required fields.")}), 400

    if split_by_custom_field and not custom_field_name:
        return jsonify({"success": False, "error": _("Please specify a custom field name when enabling report iteration.")}), 400

    result = service.create_schedule(
        saved_view_id=saved_view_id,
        recipients=recipients,
        cadence=cadence,
        created_by=current_user.id,
        cron=cron,
        timezone=timezone,
        split_by_custom_field=split_by_custom_field,
        custom_field_name=custom_field_name,
    )

    if result["success"]:
        return jsonify(
            {
                "success": True,
                "schedule": {
                    "id": result["schedule"].id,
                    "saved_view_name": (
                        result["schedule"].saved_view.name if result["schedule"].saved_view else "Unknown"
                    ),
                    "recipients": result["schedule"].recipients,
                    "cadence": result["schedule"].cadence,
                    "next_run_at": (
                        result["schedule"].next_run_at.isoformat() if result["schedule"].next_run_at else None
                    ),
                },
            }
        )
    else:
        return jsonify({"success": False, "error": result["message"]}), 400


@scheduled_reports_bp.route("/api/reports/scheduled/<int:schedule_id>/toggle", methods=["POST"])
@login_required
def api_toggle_scheduled(schedule_id):
    """Toggle active status of scheduled report"""
    from app import db

    schedule = ReportEmailSchedule.query.get_or_404(schedule_id)

    if schedule.created_by != current_user.id and not current_user.is_admin:
        return jsonify({"success": False, "error": _("Permission denied")}), 403

    schedule.active = not schedule.active
    db.session.commit()

    return jsonify({"success": True, "active": schedule.active})


@scheduled_reports_bp.route("/api/reports/scheduled/<int:schedule_id>", methods=["DELETE"])
@login_required
def api_delete_scheduled(schedule_id):
    """Delete scheduled report via API"""
    service = ScheduledReportService()
    result = service.delete_schedule(schedule_id, current_user.id)

    if result["success"]:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": result["message"]}), 400


@scheduled_reports_bp.route("/api/reports/saved-views", methods=["GET"])
@login_required
def api_saved_views():
    """Get saved report views for current user"""
    saved_views = SavedReportView.query.filter_by(owner_id=current_user.id).all()
    return jsonify(
        {
            "saved_views": [
                {
                    "id": sv.id,
                    "name": sv.name,
                    "scope": sv.scope,
                }
                for sv in saved_views
            ]
        }
    )
