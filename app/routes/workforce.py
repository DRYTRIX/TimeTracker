import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models.time_off import CompanyHoliday, LeaveType, TimeOffRequest
from app.services.workforce_governance_service import WorkforceGovernanceService

workforce_bp = Blueprint("workforce", __name__)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _can_approve() -> bool:
    if current_user.is_admin:
        return True
    policy = WorkforceGovernanceService().get_or_create_default_policy()
    return current_user.id in policy.get_approver_ids()


@workforce_bp.route("/workforce")
@login_required
def dashboard():
    service = WorkforceGovernanceService()

    # Run auto-lock policy opportunistically for admins
    if current_user.is_admin:
        try:
            service.apply_auto_lock(actor_id=current_user.id)
        except Exception:
            pass

    selected_user_id = request.args.get("user_id", type=int)
    if not current_user.is_admin or not selected_user_id:
        selected_user_id = current_user.id

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))

    periods = service.list_periods(user_id=selected_user_id, period_start=start, period_end=end)

    leave_requests_query = TimeOffRequest.query
    if not (current_user.is_admin or _can_approve()):
        leave_requests_query = leave_requests_query.filter(TimeOffRequest.user_id == current_user.id)
    leave_requests = leave_requests_query.order_by(TimeOffRequest.start_date.desc()).limit(40).all()

    leave_types = service.list_leave_types(enabled_only=False)
    holidays = CompanyHoliday.query.order_by(CompanyHoliday.start_date.desc()).limit(30).all()

    policy = service.get_or_create_default_policy() if (current_user.is_admin or _can_approve()) else None

    # default capacity window: current week
    today = date.today()
    cap_start = start or (today - timedelta(days=today.weekday()))
    cap_end = end or (cap_start + timedelta(days=6))
    capacity = service.capacity_report(
        start_date=cap_start, end_date=cap_end, team_user_ids=None if current_user.is_admin else [current_user.id]
    )

    balances = service.get_leave_balance(selected_user_id)

    from app.models import User
    from app.utils.overtime import get_overtime_ytd

    users = []
    if current_user.is_admin:
        users = User.query.order_by(User.username.asc()).all()

    # Accumulated overtime (YTD) for selected user and overtime leave type for "Take as paid leave"
    selected_user = User.query.get(selected_user_id)
    overtime_ytd_hours = 0.0
    overtime_leave_type = service.get_overtime_leave_type()
    overtime_leave_type_id = overtime_leave_type.id if overtime_leave_type else None
    if selected_user:
        overtime_ytd = get_overtime_ytd(selected_user)
        overtime_ytd_hours = float(overtime_ytd.get("overtime_hours", 0) or 0)

    return render_template(
        "workforce/dashboard.html",
        periods=periods,
        leave_requests=leave_requests,
        leave_types=leave_types,
        holidays=holidays,
        policy=policy,
        selected_user_id=selected_user_id,
        users=users,
        can_approve=_can_approve(),
        balances=balances,
        capacity=capacity,
        cap_start=cap_start,
        cap_end=cap_end,
        overtime_ytd_hours=overtime_ytd_hours,
        overtime_leave_type_id=overtime_leave_type_id,
    )


@workforce_bp.route("/workforce/periods/create", methods=["POST"])
@login_required
def create_period():
    ref = _parse_date(request.form.get("reference_date")) or date.today()
    period = WorkforceGovernanceService().get_or_create_period_for_date(
        user_id=current_user.id,
        reference=ref,
        period_type="weekly",
    )
    flash(
        _(
            "Timesheet period ready: %(start)s to %(end)s",
            start=period.period_start.isoformat(),
            end=period.period_end.isoformat(),
        ),
        "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/periods/<int:period_id>/submit", methods=["POST"])
@login_required
def submit_period(period_id):
    result = WorkforceGovernanceService().submit_period(period_id=period_id, actor_id=current_user.id)
    flash(
        (
            _(result.get("message", "Timesheet period submitted"))
            if not result.get("success")
            else _("Timesheet period submitted")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/periods/<int:period_id>/approve", methods=["POST"])
@login_required
def approve_period(period_id):
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))
    result = WorkforceGovernanceService().approve_period(
        period_id=period_id,
        approver_id=current_user.id,
        comment=request.form.get("comment"),
    )
    flash(
        (
            _(result.get("message", "Timesheet period approved"))
            if not result.get("success")
            else _("Timesheet period approved")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/periods/<int:period_id>/reject", methods=["POST"])
@login_required
def reject_period(period_id):
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash(_("Rejection reason is required"), "error")
        return redirect(url_for("workforce.dashboard"))
    result = WorkforceGovernanceService().reject_period(period_id=period_id, approver_id=current_user.id, reason=reason)
    flash(
        (
            _(result.get("message", "Timesheet period rejected"))
            if not result.get("success")
            else _("Timesheet period rejected")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/periods/<int:period_id>/close", methods=["POST"])
@login_required
def close_period(period_id):
    if not current_user.is_admin:
        flash(_("Only admins can close periods"), "error")
        return redirect(url_for("workforce.dashboard"))
    result = WorkforceGovernanceService().close_period(
        period_id=period_id,
        closer_id=current_user.id,
        reason=request.form.get("reason"),
    )
    flash(
        (
            _(result.get("message", "Timesheet period closed"))
            if not result.get("success")
            else _("Timesheet period closed")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/periods/<int:period_id>/delete", methods=["POST"])
@login_required
def delete_period(period_id):
    result = WorkforceGovernanceService().delete_period(period_id=period_id, actor_id=current_user.id)
    flash(
        (
            _(result.get("message", "Period deleted"))
            if result.get("success")
            else _(result.get("message", "Could not delete period"))
        ),
        "success" if result.get("success") else "error",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/policy", methods=["POST"])
@login_required
def update_policy():
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    service = WorkforceGovernanceService()
    policy = service.get_or_create_default_policy()

    policy.auto_lock_days = request.form.get("auto_lock_days", type=int)
    policy.enable_multi_level_approval = bool(request.form.get("enable_multi_level_approval"))
    policy.require_rejection_comment = bool(request.form.get("require_rejection_comment"))
    policy.enable_admin_override = bool(request.form.get("enable_admin_override"))

    approver_ids = request.form.get("approver_user_ids", "")
    policy.approver_user_ids = ",".join([part.strip() for part in approver_ids.split(",") if part.strip()])

    db.session.commit()
    flash(_("Timesheet policy updated"), "success")
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/leave-types/create", methods=["POST"])
@login_required
def create_leave_type():
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    name = (request.form.get("name") or "").strip()
    code = (request.form.get("code") or "").strip().lower()
    if not name or not code:
        flash(_("Name and code are required"), "error")
        return redirect(url_for("workforce.dashboard"))

    leave_type = LeaveType(
        name=name,
        code=code,
        is_paid=bool(request.form.get("is_paid")),
        annual_allowance_hours=request.form.get("annual_allowance_hours", type=float),
        accrual_hours_per_month=request.form.get("accrual_hours_per_month", type=float),
        enabled=True,
    )
    db.session.add(leave_type)
    db.session.commit()
    flash(_("Leave type created"), "success")
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/leave-types/<int:leave_type_id>/delete", methods=["POST"])
@login_required
def delete_leave_type(leave_type_id):
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))
    result = WorkforceGovernanceService().delete_leave_type(leave_type_id)
    flash(
        (
            _(result.get("message", "Leave type deleted"))
            if result.get("success")
            else _(result.get("message", "Could not delete leave type"))
        ),
        "success" if result.get("success") else "error",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/time-off/request", methods=["POST"])
@login_required
def create_time_off_request():
    service = WorkforceGovernanceService()

    leave_type_id = request.form.get("leave_type_id", type=int)
    start = _parse_date(request.form.get("start_date"))
    end = _parse_date(request.form.get("end_date"))
    requested_hours = request.form.get("requested_hours", type=float)

    if not leave_type_id or not start or not end:
        flash(_("Leave type and date range are required"), "error")
        return redirect(url_for("workforce.dashboard"))

    result = service.create_leave_request(
        user_id=current_user.id,
        leave_type_id=leave_type_id,
        start_date=start,
        end_date=end,
        requested_hours=requested_hours,
        comment=request.form.get("comment"),
        submit_now=True,
    )

    flash(
        (
            _(result.get("message", "Time-off request submitted"))
            if not result.get("success")
            else _("Time-off request submitted")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/time-off/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_time_off_request(request_id):
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    result = WorkforceGovernanceService().review_leave_request(
        request_id=request_id,
        reviewer_id=current_user.id,
        approve=True,
        comment=request.form.get("comment"),
    )
    flash(
        (
            _(result.get("message", "Time-off request approved"))
            if not result.get("success")
            else _("Time-off request approved")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/time-off/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_time_off_request(request_id):
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    result = WorkforceGovernanceService().review_leave_request(
        request_id=request_id,
        reviewer_id=current_user.id,
        approve=False,
        comment=request.form.get("comment"),
    )
    flash(
        (
            _(result.get("message", "Time-off request rejected"))
            if not result.get("success")
            else _("Time-off request rejected")
        ),
        "error" if not result.get("success") else "success",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/time-off/<int:request_id>/delete", methods=["POST"])
@login_required
def delete_time_off_request(request_id):
    result = WorkforceGovernanceService().delete_leave_request(
        request_id=request_id,
        actor_id=current_user.id,
        actor_can_approve=_can_approve(),
    )
    flash(
        (
            _(result.get("message", "Time-off request deleted"))
            if result.get("success")
            else _(result.get("message", "Could not delete request"))
        ),
        "success" if result.get("success") else "error",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/holidays/create", methods=["POST"])
@login_required
def create_holiday():
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    name = (request.form.get("name") or "").strip()
    start = _parse_date(request.form.get("start_date"))
    end = _parse_date(request.form.get("end_date"))
    if not name or not start or not end:
        flash(_("Name and date range are required"), "error")
        return redirect(url_for("workforce.dashboard"))

    holiday = CompanyHoliday(name=name, start_date=start, end_date=end, region=request.form.get("region"), enabled=True)
    db.session.add(holiday)
    db.session.commit()
    flash(_("Holiday created"), "success")
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/holidays/<int:holiday_id>/delete", methods=["POST"])
@login_required
def delete_holiday(holiday_id):
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))
    result = WorkforceGovernanceService().delete_holiday(holiday_id)
    flash(
        (
            _(result.get("message", "Holiday deleted"))
            if result.get("success")
            else _(result.get("message", "Could not delete holiday"))
        ),
        "success" if result.get("success") else "error",
    )
    return redirect(url_for("workforce.dashboard"))


@workforce_bp.route("/workforce/reports/payroll.csv", methods=["GET"])
@login_required
def payroll_export_csv():
    service = WorkforceGovernanceService()

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        flash(_("Start date and end date are required for payroll export"), "error")
        return redirect(url_for("workforce.dashboard"))

    user_id = request.args.get("user_id", type=int)
    if not current_user.is_admin or not user_id:
        user_id = current_user.id

    approved_only = request.args.get("approved_only", "false").lower() == "true"
    closed_only = request.args.get("closed_only", "false").lower() == "true"

    rows = service.payroll_rows(
        start_date=start,
        end_date=end,
        user_id=user_id,
        approved_only=approved_only,
        closed_only=closed_only,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "user_id",
            "username",
            "week_year",
            "week_number",
            "period_start",
            "period_end",
            "hours",
            "billable_hours",
            "non_billable_hours",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("user_id"),
                row.get("username"),
                row.get("week_year"),
                row.get("week_number"),
                row.get("period_start"),
                row.get("period_end"),
                row.get("hours"),
                row.get("billable_hours"),
                row.get("non_billable_hours"),
            ]
        )

    filename = f"payroll_export_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@workforce_bp.route("/workforce/reports/capacity.csv", methods=["GET"])
@login_required
def capacity_export_csv():
    service = WorkforceGovernanceService()

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        flash(_("Start date and end date are required for capacity export"), "error")
        return redirect(url_for("workforce.dashboard"))

    team_user_ids = None
    user_ids_raw = request.args.get("user_ids", "")
    if user_ids_raw and current_user.is_admin:
        parsed = []
        for raw in user_ids_raw.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                parsed.append(int(raw))
            except ValueError:
                continue
        team_user_ids = parsed if parsed else None

    if not current_user.is_admin:
        team_user_ids = [current_user.id]

    rows = service.capacity_report(start_date=start, end_date=end, team_user_ids=team_user_ids)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "user_id",
            "username",
            "expected_hours",
            "allocated_hours",
            "time_off_hours",
            "available_hours",
            "utilization_pct",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("user_id"),
                row.get("username"),
                row.get("expected_hours"),
                row.get("allocated_hours"),
                row.get("time_off_hours"),
                row.get("available_hours"),
                row.get("utilization_pct"),
            ]
        )

    filename = f"capacity_report_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@workforce_bp.route("/workforce/reports/locked-periods.csv", methods=["GET"])
@login_required
def locked_periods_export_csv():
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    service = WorkforceGovernanceService()
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    rows = service.locked_periods_report(start_date=start, end_date=end)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "user_id",
            "period_type",
            "period_start",
            "period_end",
            "status",
            "closed_at",
            "closed_by",
            "close_reason",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("id"),
                row.get("user_id"),
                row.get("period_type"),
                row.get("period_start"),
                row.get("period_end"),
                row.get("status"),
                row.get("closed_at"),
                row.get("closed_by"),
                row.get("close_reason"),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=locked_periods.csv"},
    )


@workforce_bp.route("/workforce/reports/audit-events.csv", methods=["GET"])
@login_required
def audit_events_export_csv():
    if not _can_approve():
        flash(_("Access denied"), "error")
        return redirect(url_for("workforce.dashboard"))

    service = WorkforceGovernanceService()
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    user_id = request.args.get("user_id", type=int)

    if not current_user.is_admin:
        user_id = current_user.id

    rows = service.compliance_audit_events(start_date=start, end_date=end, user_id=user_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "user_id",
            "action",
            "entity_type",
            "entity_id",
            "entity_name",
            "change_description",
            "reason",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("id"),
                row.get("created_at"),
                row.get("user_id"),
                row.get("action"),
                row.get("entity_type"),
                row.get("entity_id"),
                row.get("entity_name"),
                row.get("change_description"),
                row.get("reason"),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance_audit_events.csv"},
    )
