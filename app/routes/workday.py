"""Web routes for workday clock-in/out and working time limit justifications."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.models import WorkingTimeViolation
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


@workday_bp.route("/workday/status")
@login_required
def workday_status():
    from flask import jsonify

    session = WorkdaySessionService().get_active_session(current_user.id)
    return jsonify(
        {
            "active": session is not None,
            "session": session.to_dict() if session else None,
        }
    )


@workday_bp.route("/workday/history")
@login_required
def workday_history():
    from datetime import datetime, timedelta

    page = request.args.get("page", 1, type=int)
    per_page = 20
    days = request.args.get("days", 30, type=int)
    start_date = (datetime.utcnow() - timedelta(days=days)).date()

    from app.models import WorkdaySession

    query = (
        WorkdaySession.query.filter(
            WorkdaySession.user_id == current_user.id,
            WorkdaySession.start_time >= datetime.combine(start_date, datetime.min.time()),
        )
        .order_by(WorkdaySession.start_time.desc())
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "workday/history.html",
        sessions=pagination.items,
        pagination=pagination,
    )


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
        result = WorkingTimeLimitService().submit_justification(
            violation_id, current_user.id, justification
        )
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
    users = {u.id: u for u in User.query.filter(User.id.in_({v.user_id for v in violations})).all()} if violations else {}

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
