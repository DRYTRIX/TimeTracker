"""Web routes for workday clock-in/out and working time limit justifications."""

from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.models import WorkingTimeViolation
from app.models.attendance_compliance import AttendanceCorrection, AttendanceCorrectionStatus
from app.services.attendance_compliance_service import AttendanceComplianceService
from app.services.workday_session_service import WorkdaySessionService
from app.services.working_time_limit_service import WorkingTimeLimitService

workday_bp = Blueprint("workday", __name__)


@workday_bp.route("/workday/start", methods=["POST"])
@login_required
def start_workday():
    notes = request.form.get("notes", "").strip() or None
    result = WorkdaySessionService().start_workday(current_user.id, notes=notes, source="manual")
    if result["success"]:
        flash(_("Workday started"), "success")
    else:
        flash(result.get("message", _("Could not start workday")), "error")
    return redirect(request.referrer or url_for("main.dashboard"))


@workday_bp.route("/workday/end", methods=["POST"])
@login_required
def end_workday():
    notes = request.form.get("notes", "").strip() or None
    result = WorkdaySessionService().end_workday(current_user.id, notes=notes)
    if result["success"]:
        flash(_("Workday ended"), "success")
    else:
        flash(result.get("message", _("Could not end workday")), "error")
    return redirect(request.referrer or url_for("main.dashboard"))


@workday_bp.route("/workday/break/start", methods=["POST"])
@login_required
def start_break():
    break_type = request.form.get("break_type", "rest").strip() or "rest"
    result = AttendanceComplianceService().start_break(current_user.id, break_type=break_type)
    if result["success"]:
        flash(_("Break started"), "success")
    else:
        flash(result.get("message", _("Could not start break")), "error")
    return redirect(request.referrer or url_for("main.dashboard"))


@workday_bp.route("/workday/break/end", methods=["POST"])
@login_required
def end_break():
    result = AttendanceComplianceService().end_break(current_user.id)
    if result["success"]:
        flash(_("Break ended"), "success")
    else:
        flash(result.get("message", _("Could not end break")), "error")
    return redirect(request.referrer or url_for("main.dashboard"))


@workday_bp.route("/workday/status")
@login_required
def workday_status():
    status = AttendanceComplianceService().get_status(current_user.id)
    session = WorkdaySessionService().get_active_session(current_user.id)
    status["legacy_session"] = session.to_dict() if session else None
    status["active"] = status.get("work_active", False)
    status["session"] = status.get("work_period")
    return jsonify(status)


@workday_bp.route("/workday/history")
@login_required
def workday_history():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    days = request.args.get("days", 30, type=int)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    service = AttendanceComplianceService()
    records = service.list_days(current_user.id, start_date, end_date)
    warnings_by_date = {r.work_date: service.get_compliance_warnings(current_user.id, r.work_date) for r in records}

    total = len(records)
    start_idx = (page - 1) * per_page
    page_records = records[start_idx : start_idx + per_page]

    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = max(1, (total + per_page - 1) // per_page)
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

    pagination = SimplePagination(page_records, page, per_page, total)

    return render_template(
        "workday/history.html",
        records=page_records,
        pagination=pagination,
        warnings_by_date=warnings_by_date,
        compliance_cfg=service.get_compliance_settings(current_user),
    )


@workday_bp.route("/workday/corrections/request", methods=["POST"])
@login_required
def request_correction():
    service = AttendanceComplianceService()
    entity_type = request.form.get("entity_type")
    if entity_type == "AddWorkPeriod":
        work_date_str = request.form.get("work_date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")
        try:
            work_date = datetime.strptime(work_date_str, "%Y-%m-%d").date()
            start_time = datetime.fromisoformat(start_str) if start_str else None
            end_time = datetime.fromisoformat(end_str) if end_str else None
        except (ValueError, TypeError):
            flash(_("Invalid date or time"), "error")
            return redirect(request.referrer or url_for("workday.workday_history"))
        if not start_time:
            flash(_("Start time is required"), "error")
            return redirect(request.referrer or url_for("workday.workday_history"))
        result = service.request_missing_work_period(
            user_id=current_user.id,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            reason=request.form.get("reason", ""),
            notes=request.form.get("notes") or None,
        )
    else:
        result = service.request_correction(
            attendance_day_id=request.form.get("attendance_day_id", type=int),
            entity_type=entity_type,
            entity_id=request.form.get("entity_id", type=int),
            corrected_values={
                "start_time": request.form.get("start_time") or None,
                "end_time": request.form.get("end_time") or None,
                "status": request.form.get("status") or None,
                "compliance_notes": request.form.get("compliance_notes") or None,
            },
            reason=request.form.get("reason", ""),
            requested_by=current_user.id,
        )
    if result["success"]:
        flash(_("Correction request submitted for review"), "success")
    else:
        flash(result.get("message", _("Could not submit correction")), "error")
    return redirect(request.referrer or url_for("workday.workday_history"))


@workday_bp.route("/admin/attendance/corrections")
@login_required
def admin_corrections_list():
    if not current_user.is_admin:
        flash(_("Admin access required"), "error")
        return redirect(url_for("main.dashboard"))

    corrections = (
        AttendanceCorrection.query.filter_by(status=AttendanceCorrectionStatus.PENDING)
        .order_by(AttendanceCorrection.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template("workday/admin_corrections.html", corrections=corrections)


@workday_bp.route("/admin/attendance/corrections/<int:correction_id>/review", methods=["POST"])
@login_required
def admin_review_correction(correction_id):
    if not current_user.is_admin:
        flash(_("Admin access required"), "error")
        return redirect(url_for("main.dashboard"))

    approve = request.form.get("action") == "approve"
    result = AttendanceComplianceService().review_correction(
        correction_id,
        current_user.id,
        approve=approve,
        review_comment=request.form.get("review_comment"),
    )
    if result["success"]:
        flash(_("Correction approved and applied") if approve else _("Correction rejected"), "success")
    else:
        flash(result.get("message", _("Could not review correction")), "error")
    return redirect(url_for("workday.admin_corrections_list"))


@workday_bp.route("/working-time/violations")
@login_required
def violations_list():
    violations = WorkingTimeLimitService().get_pending_violations_for_user(current_user.id)
    return render_template("workday/violations_list.html", violations=violations)


@workday_bp.route("/working-time/violations/<int:violation_id>", methods=["GET", "POST"])
@login_required
def violation_justify(violation_id):
    violation = WorkingTimeViolation.query.filter_by(id=violation_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        justification = request.form.get("justification", "").strip()
        result = WorkingTimeLimitService().submit_justification(violation_id, current_user.id, justification)
        if result["success"]:
            flash(_("Thank you. Your justification has been submitted."), "success")
            return redirect(url_for("workday.violations_list"))
        flash(result.get("message", _("Could not submit justification")), "error")

    return render_template("workday/violation_justify.html", violation=violation)


@workday_bp.route("/admin/working-time")
@login_required
def admin_working_time_list():
    if not current_user.is_admin:
        flash(_("Admin access required"), "error")
        return redirect(url_for("main.dashboard"))

    from app.models import User, WorkingTimeViolation

    status_filter = request.args.get("status", "submitted")
    query = WorkingTimeViolation.query
    if status_filter and status_filter != "all":
        query = query.filter_by(status=status_filter)
    violations = query.order_by(WorkingTimeViolation.created_at.desc()).limit(200).all()
    users = (
        {u.id: u for u in User.query.filter(User.id.in_({v.user_id for v in violations})).all()} if violations else {}
    )

    return render_template(
        "workday/admin_violations.html",
        violations=violations,
        users=users,
        status_filter=status_filter,
    )


@workday_bp.route("/admin/working-time/<int:violation_id>/acknowledge", methods=["POST"])
@login_required
def admin_acknowledge_violation(violation_id):
    if not current_user.is_admin:
        flash(_("Admin access required"), "error")
        return redirect(url_for("main.dashboard"))

    result = WorkingTimeLimitService().acknowledge_violation(violation_id, current_user.id)
    if result["success"]:
        flash(_("Violation acknowledged"), "success")
    else:
        flash(result.get("message", _("Could not acknowledge")), "error")
    return redirect(url_for("workday.admin_working_time_list"))
