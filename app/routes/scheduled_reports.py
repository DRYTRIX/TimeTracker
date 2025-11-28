"""
Routes for scheduled reports management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.models import SavedReportView
from app.services.scheduled_report_service import ScheduledReportService

scheduled_reports_bp = Blueprint("scheduled_reports", __name__)


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

        if not saved_view_id or not recipients or not cadence:
            flash(_("Please fill in all required fields."), "error")
            return render_template("reports/schedule_form.html", saved_views=saved_views)

        result = service.create_schedule(
            saved_view_id=saved_view_id,
            recipients=recipients,
            cadence=cadence,
            created_by=current_user.id,
            cron=cron,
            timezone=timezone,
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
