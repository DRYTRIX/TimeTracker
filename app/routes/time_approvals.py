"""
Time Entry Approval routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.time_entry_approval import TimeEntryApproval, ApprovalPolicy, ApprovalStatus
from app.models import TimeEntry
from app.services.time_approval_service import TimeApprovalService
from flask_babel import gettext as _

time_approvals_bp = Blueprint("time_approvals", __name__)


@time_approvals_bp.route("/approvals")
@login_required
def list_approvals():
    """List pending approvals"""
    service = TimeApprovalService()
    pending = service.get_pending_approvals(current_user.id)

    # Get user's pending requests
    my_requests = TimeEntryApproval.query.filter_by(
        requested_by=current_user.id,
        status=ApprovalStatus.PENDING
    ).order_by(TimeEntryApproval.requested_at.desc()).all()

    return render_template("approvals/list.html", pending_approvals=pending, my_requests=my_requests)


@time_approvals_bp.route("/approvals/<int:approval_id>")
@login_required
def view_approval(approval_id):
    """View approval details"""
    approval = TimeEntryApproval.query.get_or_404(approval_id)
    
    # Check permissions
    if approval.requested_by != current_user.id and approval.approved_by != current_user.id:
        service = TimeApprovalService()
        approver_ids = service._get_approvers_for_entry(approval.time_entry)
        if current_user.id not in approver_ids and not current_user.is_admin:
            flash(_("Access denied"), "error")
            return redirect(url_for("time_approvals.list_approvals"))

    return render_template("approvals/view.html", approval=approval)


@time_approvals_bp.route("/approvals/<int:approval_id>/approve", methods=["POST"])
@login_required
def approve_entry(approval_id):
    """Approve a time entry"""
    service = TimeApprovalService()
    data = request.get_json() if request.is_json else request.form

    result = service.approve(
        approval_id=approval_id,
        approver_id=current_user.id,
        comment=data.get("comment")
    )

    if request.is_json:
        return jsonify(result)

    if result.get("success"):
        flash(_("Time entry approved"), "success")
    else:
        flash(_(result.get("message", "Approval failed")), "error")

    return redirect(url_for("time_approvals.list_approvals"))


@time_approvals_bp.route("/approvals/<int:approval_id>/reject", methods=["POST"])
@login_required
def reject_entry(approval_id):
    """Reject a time entry"""
    service = TimeApprovalService()
    data = request.get_json() if request.is_json else request.form

    reason = data.get("reason") or data.get("rejection_reason")
    if not reason:
        if request.is_json:
            return jsonify({"success": False, "message": "Rejection reason required"}), 400
        flash(_("Rejection reason is required"), "error")
        return redirect(url_for("time_approvals.view_approval", approval_id=approval_id))

    result = service.reject(
        approval_id=approval_id,
        approver_id=current_user.id,
        reason=reason
    )

    if request.is_json:
        return jsonify(result)

    if result.get("success"):
        flash(_("Time entry rejected"), "success")
    else:
        flash(_(result.get("message", "Rejection failed")), "error")

    return redirect(url_for("time_approvals.list_approvals"))


@time_approvals_bp.route("/time-entries/<int:entry_id>/request-approval", methods=["POST"])
@login_required
def request_approval(entry_id):
    """Request approval for a time entry"""
    service = TimeApprovalService()
    data = request.get_json() if request.is_json else request.form

    result = service.request_approval(
        time_entry_id=entry_id,
        requested_by=current_user.id,
        comment=data.get("comment"),
        approver_ids=data.get("approver_ids")
    )

    if request.is_json:
        return jsonify(result)

    if result.get("success"):
        flash(_("Approval requested"), "success")
    else:
        flash(_(result.get("message", "Request failed")), "error")

    return redirect(url_for("main.dashboard"))


@time_approvals_bp.route("/approvals/<int:approval_id>/cancel", methods=["POST"])
@login_required
def cancel_approval(approval_id):
    """Cancel an approval request"""
    service = TimeApprovalService()

    result = service.cancel_approval(
        approval_id=approval_id,
        user_id=current_user.id
    )

    if request.is_json:
        return jsonify(result)

    if result.get("success"):
        flash(_("Approval cancelled"), "success")
    else:
        flash(_(result.get("message", "Cancellation failed")), "error")

    return redirect(url_for("time_approvals.list_approvals"))


@time_approvals_bp.route("/api/approvals/bulk-approve", methods=["POST"])
@login_required
def bulk_approve():
    """Bulk approve multiple time entries"""
    service = TimeApprovalService()
    data = request.get_json()

    approval_ids = data.get("approval_ids", [])
    if not approval_ids:
        return jsonify({"success": False, "message": "No approval IDs provided"}), 400

    result = service.bulk_approve(
        approval_ids=approval_ids,
        approver_id=current_user.id,
        comment=data.get("comment")
    )

    return jsonify(result)


@time_approvals_bp.route("/api/approvals/pending")
@login_required
def api_pending_approvals():
    """API: Get pending approvals"""
    service = TimeApprovalService()
    approvals = service.get_pending_approvals(current_user.id)

    return jsonify({
        "approvals": [a.to_dict() for a in approvals]
    })

