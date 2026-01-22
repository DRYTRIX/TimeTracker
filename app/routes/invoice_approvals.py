"""
Routes for invoice approval workflow.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.models import Invoice, InvoiceApproval, User
from app.services.invoice_approval_service import InvoiceApprovalService
from app.utils.permissions import admin_or_permission_required
import json
from app.utils.module_helpers import module_enabled

invoice_approvals_bp = Blueprint("invoice_approvals", __name__)


@invoice_approvals_bp.route("/invoices/<int:invoice_id>/request-approval", methods=["GET", "POST"])
@login_required
@module_enabled("invoice_approvals")
@admin_or_permission_required("create_invoices")
def request_approval(invoice_id):
    """Request approval for an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    service = InvoiceApprovalService()

    # Check if approval already exists
    existing = service.get_invoice_approval(invoice_id)
    if existing and existing.status == "pending":
        flash(_("An approval request is already pending for this invoice."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    if request.method == "POST":
        # Get approvers from form
        approvers_json = request.form.get("approvers", "[]")
        try:
            approvers = json.loads(approvers_json)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            current_app.logger.warning(f"Could not parse approvers JSON, using fallback: {e}")
            approvers = [int(request.form.get("approver_id", 0))]

        if not approvers or not any(approvers):
            flash(_("Please select at least one approver."), "error")
            return render_template(
                "invoice_approvals/request.html", invoice=invoice, users=User.query.filter_by(is_active=True).all()
            )

        result = service.request_approval(invoice_id=invoice_id, requested_by=current_user.id, approvers=approvers)

        if result["success"]:
            flash(_("Approval request created successfully."), "success")
            return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
        else:
            flash(result["message"], "error")

    users = User.query.filter_by(is_active=True).all()
    return render_template("invoice_approvals/request.html", invoice=invoice, users=users)


@invoice_approvals_bp.route("/invoice-approvals")
@login_required
@module_enabled("invoice_approvals")
def list_approvals():
    """List pending approvals"""
    service = InvoiceApprovalService()
    pending_approvals = service.list_pending_approvals(user_id=current_user.id)

    return render_template("invoice_approvals/list.html", approvals=pending_approvals)


@invoice_approvals_bp.route("/invoice-approvals/<int:approval_id>/approve", methods=["POST"])
@login_required
@module_enabled("invoice_approvals")
def approve(approval_id):
    """Approve an invoice"""
    service = InvoiceApprovalService()
    comments = request.form.get("comments", "").strip() or None

    result = service.approve(approval_id=approval_id, approver_id=current_user.id, comments=comments)

    if result["success"]:
        flash(_("Invoice approved successfully."), "success")
    else:
        flash(result["message"], "error")

    approval = service.get_approval(approval_id)
    return redirect(url_for("invoices.view_invoice", invoice_id=approval.invoice_id))


@invoice_approvals_bp.route("/invoice-approvals/<int:approval_id>/reject", methods=["POST"])
@login_required
@module_enabled("invoice_approvals")
def reject(approval_id):
    """Reject an invoice approval"""
    service = InvoiceApprovalService()
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash(_("Please provide a reason for rejection."), "error")
        approval = service.get_approval(approval_id)
        return redirect(url_for("invoices.view_invoice", invoice_id=approval.invoice_id))

    result = service.reject(approval_id=approval_id, rejector_id=current_user.id, reason=reason)

    if result["success"]:
        flash(_("Invoice approval rejected."), "info")
    else:
        flash(result["message"], "error")

    approval = service.get_approval(approval_id)
    return redirect(url_for("invoices.view_invoice", invoice_id=approval.invoice_id))


@invoice_approvals_bp.route("/invoice-approvals/<int:approval_id>")
@login_required
@module_enabled("invoice_approvals")
def view_approval(approval_id):
    """View approval details"""
    service = InvoiceApprovalService()
    approval = service.get_approval(approval_id)

    if not approval:
        flash(_("Approval not found."), "error")
        return redirect(url_for("invoice_approvals.list_approvals"))

    return render_template("invoice_approvals/view.html", approval=approval)
