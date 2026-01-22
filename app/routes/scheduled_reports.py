"""
Routes for scheduled reports management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.models import SavedReportView, ReportEmailSchedule
from app.services.scheduled_report_service import ScheduledReportService
import logging
from app.utils.module_helpers import module_enabled

logger = logging.getLogger(__name__)

scheduled_reports_bp = Blueprint("scheduled_reports", __name__)


@scheduled_reports_bp.route("/api/reports/scheduled", methods=["GET"])
@login_required
@module_enabled("scheduled_reports")
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
@module_enabled("scheduled_reports")
def list_scheduled():
    """List scheduled reports with error handling"""
    try:
        service = ScheduledReportService()
        schedules = service.list_schedules(user_id=current_user.id)
        
        # Validate schedules and filter out invalid ones
        valid_schedules = []
        for schedule in schedules:
            try:
                # Check if saved_view exists and is valid
                if schedule.saved_view:
                    # Try to parse config to validate
                    import json
                    try:
                        config = json.loads(schedule.saved_view.config_json) if isinstance(schedule.saved_view.config_json, str) else schedule.saved_view.config_json
                        if not isinstance(config, dict):
                            logger.warning(f"Invalid config for schedule {schedule.id}, skipping")
                            continue
                    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
                        logger.warning(f"Could not parse config for schedule {schedule.id}, skipping: {e}")
                        continue
                else:
                    logger.warning(f"Schedule {schedule.id} has no saved_view, skipping")
                    continue
                
                valid_schedules.append(schedule)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Error validating schedule {schedule.id}: {e}", exc_info=True)
                continue
        
        return render_template("reports/scheduled.html", schedules=valid_schedules)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error loading scheduled reports: {e}", exc_info=True)
        flash(_("Error loading scheduled reports. Please check the logs."), "error")
        return render_template("reports/scheduled.html", schedules=[])


@scheduled_reports_bp.route("/reports/scheduled/create", methods=["GET", "POST"])
@login_required
@module_enabled("scheduled_reports")
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
        email_distribution_mode = request.form.get("email_distribution_mode", "").strip() or None
        recipient_email_template = request.form.get("recipient_email_template", "").strip() or None
        use_last_month_dates = request.form.get("use_last_month_dates") == "1"

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
            email_distribution_mode=email_distribution_mode,
            recipient_email_template=recipient_email_template,
            use_last_month_dates=use_last_month_dates,
        )

        if result["success"]:
            flash(_("Scheduled report created successfully."), "success")
            return redirect(url_for("scheduled_reports.list_scheduled"))
        else:
            flash(result["message"], "error")

    return render_template("reports/schedule_form.html", saved_views=saved_views)


@scheduled_reports_bp.route("/reports/scheduled/<int:schedule_id>/delete", methods=["POST"])
@login_required
@module_enabled("scheduled_reports")
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
@module_enabled("scheduled_reports")
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
    email_distribution_mode = data.get("email_distribution_mode", "").strip() or None
    recipient_email_template = data.get("recipient_email_template", "").strip() or None
    use_last_month_dates = data.get("use_last_month_dates", False)

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
        email_distribution_mode=email_distribution_mode,
        recipient_email_template=recipient_email_template,
        use_last_month_dates=use_last_month_dates,
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
@module_enabled("scheduled_reports")
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
@module_enabled("scheduled_reports")
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
@module_enabled("scheduled_reports")
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


@scheduled_reports_bp.route("/reports/scheduled/<int:schedule_id>/fix", methods=["POST"])
@login_required
@module_enabled("scheduled_reports")
def fix_scheduled(schedule_id):
    """Fix or remove an invalid scheduled report"""
    from app import db
    import json
    
    schedule = ReportEmailSchedule.query.get_or_404(schedule_id)
    
    # Check permission
    if schedule.created_by != current_user.id and not current_user.is_admin:
        flash(_("You do not have permission to fix this schedule."), "error")
        return redirect(url_for("scheduled_reports.list_scheduled"))
    
    # Try to validate the saved view
    if not schedule.saved_view:
        # Saved view doesn't exist - delete the schedule
        db.session.delete(schedule)
        db.session.commit()
        flash(_("Scheduled report deleted: saved view no longer exists."), "success")
        return redirect(url_for("scheduled_reports.list_scheduled"))
    
    # Try to parse config
    try:
        config = json.loads(schedule.saved_view.config_json) if isinstance(schedule.saved_view.config_json, str) else schedule.saved_view.config_json
        if not isinstance(config, dict):
            # Invalid config - deactivate the schedule
            schedule.active = False
            db.session.commit()
            flash(_("Scheduled report deactivated: invalid configuration."), "warning")
            return redirect(url_for("scheduled_reports.list_scheduled"))
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
        # Could not parse config - deactivate
        current_app.logger.warning(f"Could not parse scheduled report config: {e}")
        schedule.active = False
        db.session.commit()
        flash(_("Scheduled report deactivated: could not parse configuration."), "warning")
        return redirect(url_for("scheduled_reports.list_scheduled"))
    
    # If we get here, the schedule is valid - reactivate it
    schedule.active = True
    db.session.commit()
    flash(_("Scheduled report validated and reactivated."), "success")
    return redirect(url_for("scheduled_reports.list_scheduled"))


@scheduled_reports_bp.route("/api/reports/scheduled/<int:schedule_id>/trigger", methods=["POST"])
@login_required
@module_enabled("scheduled_reports")
def api_trigger_scheduled(schedule_id):
    """Manually trigger a scheduled report for testing"""
    service = ScheduledReportService()
    
    schedule = ReportEmailSchedule.query.get_or_404(schedule_id)
    
    # Check permission
    if schedule.created_by != current_user.id and not current_user.is_admin:
        return jsonify({"success": False, "error": _("Permission denied")}), 403
    
    # Check if schedule is valid
    if not schedule.saved_view:
        return jsonify({"success": False, "error": _("Saved report view not found")}), 400
    
    # Trigger the report generation
    result = service.generate_and_send_report(schedule_id)
    
    if result["success"]:
        return jsonify({
            "success": True,
            "message": result["message"],
            "sent_count": result.get("sent_count", 0)
        })
    else:
        return jsonify({"success": False, "error": result["message"]}), 400
