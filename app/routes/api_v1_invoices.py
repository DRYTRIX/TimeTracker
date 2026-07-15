"""
API v1 - Invoices sub-blueprint.
Routes under /api/v1/invoices.
"""

import io

from flask import Blueprint, current_app, g, jsonify, request, send_file

from app import db
from app.routes.api_v1_common import _parse_date
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, validation_error_response

api_v1_invoices_bp = Blueprint("api_v1_invoices", __name__, url_prefix="/api/v1")


def _invoice_service():
    from app.services import InvoiceService

    return InvoiceService()


@api_v1_invoices_bp.route("/invoices", methods=["GET"])
@require_api_token("read:invoices")
def list_invoices():
    """List invoices."""
    from app.services import InvoiceService

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    invoice_service = InvoiceService()
    result = invoice_service.list_invoices(
        status=status,
        user_id=g.api_user.id if not g.api_user.is_admin else None,
        is_admin=g.api_user.is_admin,
        page=page,
        per_page=per_page,
    )
    pagination = result["pagination"]
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    return jsonify({"invoices": [inv.to_dict() for inv in result["invoices"]], "pagination": pagination_dict})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@require_api_token("read:invoices")
def get_invoice(invoice_id):
    """Get invoice by id with line items and payments."""
    result = _invoice_service().get_invoice_detail(invoice_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin)
    if not result.get("success"):
        status = 404 if result.get("error") == "not_found" else 403
        return error_response(result.get("message", "Error"), status_code=status)
    return jsonify({"invoice": result["invoice"]})


@api_v1_invoices_bp.route("/invoices", methods=["POST"])
@require_api_token("write:invoices")
def create_invoice():
    """Create a new invoice."""
    from app.services import InvoiceService

    data = request.get_json() or {}
    errors = {}
    required = ["project_id", "client_id", "client_name", "due_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        for f in missing:
            errors[f] = [f"{f} is required"]
        return validation_error_response(errors=errors, message=f"Missing required fields: {', '.join(missing)}")
    due_dt = _parse_date(data.get("due_date"))
    if not due_dt:
        return validation_error_response(
            errors={"due_date": ["Invalid due_date format, expected YYYY-MM-DD"]},
            message="Invalid due_date format, expected YYYY-MM-DD",
        )
    issue_dt = None
    if data.get("issue_date"):
        issue_dt = _parse_date(data.get("issue_date"))
        if not issue_dt:
            return validation_error_response(
                errors={"issue_date": ["Invalid issue_date format, expected YYYY-MM-DD"]},
                message="Invalid issue_date format, expected YYYY-MM-DD",
            )
    invoice_service = InvoiceService()
    result = invoice_service.create_invoice(
        project_id=data["project_id"],
        client_id=data["client_id"],
        client_name=data["client_name"],
        due_date=due_dt,
        created_by=g.api_user.id,
        invoice_number=data.get("invoice_number"),
        client_email=data.get("client_email"),
        client_address=data.get("client_address"),
        notes=data.get("notes"),
        terms=data.get("terms"),
        tax_rate=data.get("tax_rate"),
        currency_code=data.get("currency_code"),
        issue_date=issue_dt,
    )
    if not result.get("success"):
        return error_response(result.get("message", "Could not create invoice"), status_code=400)
    return jsonify({"message": "Invoice created successfully", "invoice": result["invoice"].to_dict()}), 201


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>", methods=["PUT", "PATCH"])
@require_api_token("write:invoices")
def update_invoice(invoice_id):
    """Update an invoice."""
    from decimal import Decimal, InvalidOperation

    from app.services import InvoiceService

    data = request.get_json() or {}
    update_kwargs = {}
    for field in ("client_name", "client_email", "client_address", "notes", "terms", "status", "currency_code"):
        if field in data:
            update_kwargs[field] = data[field]
    if "due_date" in data:
        parsed = _parse_date(data["due_date"])
        if parsed:
            update_kwargs["due_date"] = parsed
    if "tax_rate" in data:
        try:
            update_kwargs["tax_rate"] = float(data["tax_rate"])
        except (ValueError, TypeError) as e:
            current_app.logger.warning("Invalid tax_rate value in invoice update: %s - %s", data.get("tax_rate"), e)
    if "amount_paid" in data:
        try:
            update_kwargs["amount_paid"] = Decimal(str(data["amount_paid"]))
        except (ValueError, TypeError, InvalidOperation) as e:
            current_app.logger.warning(
                "Invalid amount_paid value in invoice update: %s - %s", data.get("amount_paid"), e
            )
    invoice_service = InvoiceService()
    result = invoice_service.update_invoice(invoice_id=invoice_id, user_id=g.api_user.id, **update_kwargs)
    if not result.get("success"):
        return error_response(result.get("message", "Could not update invoice"), status_code=400)
    if "amount_paid" in data:
        result["invoice"].update_payment_status()
        db.session.commit()
    try:
        from app.utils.integration_sync_hooks import trigger_invoice_sync

        trigger_invoice_sync(result["invoice"], event="updated")
    except Exception:
        pass
    return jsonify({"message": "Invoice updated successfully", "invoice": result["invoice"].to_dict()})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>", methods=["DELETE"])
@require_api_token("write:invoices")
def delete_invoice(invoice_id):
    """Cancel an invoice (soft-delete)."""
    result = _invoice_service().update_invoice(invoice_id=invoice_id, user_id=g.api_user.id, status="cancelled")
    if not result.get("success"):
        return error_response(result.get("message", "Could not cancel invoice"), status_code=400)
    return jsonify({"message": "Invoice cancelled successfully"})


@api_v1_invoices_bp.route("/invoices/from-time-entries", methods=["POST"])
@require_api_token("write:invoices")
def create_invoice_from_time_entries():
    """Create a draft invoice from billable time entry IDs."""
    data = request.get_json() or {}
    time_entry_ids = data.get("time_entry_ids") or []
    if not isinstance(time_entry_ids, list) or not time_entry_ids:
        return validation_error_response(
            errors={"time_entry_ids": ["time_entry_ids must be a non-empty list"]},
            message="time_entry_ids is required",
        )
    project_id = data.get("project_id")
    if not project_id:
        return validation_error_response(
            errors={"project_id": ["project_id is required"]},
            message="project_id is required",
        )
    issue_dt = _parse_date(data.get("issue_date")) if data.get("issue_date") else None
    due_dt = _parse_date(data.get("due_date")) if data.get("due_date") else None
    result = _invoice_service().create_invoice_from_time_entries(
        project_id=int(project_id),
        time_entry_ids=[int(x) for x in time_entry_ids],
        created_by=g.api_user.id,
        issue_date=issue_dt,
        due_date=due_dt,
    )
    if not result.get("success"):
        return error_response(result.get("message", "Could not create invoice"), status_code=400)
    detail = _invoice_service().get_invoice_detail(
        result["invoice"].id, user_id=g.api_user.id, is_admin=g.api_user.is_admin
    )
    return jsonify({"message": result["message"], "invoice": detail.get("invoice", result["invoice"].to_dict())}), 201


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>/generate-from-time", methods=["POST"])
@require_api_token("write:invoices")
def generate_invoice_from_time(invoice_id):
    """Generate or replace line items on an invoice from time entry IDs."""
    data = request.get_json() or {}
    time_entry_ids = data.get("time_entry_ids") or []
    if not isinstance(time_entry_ids, list) or not time_entry_ids:
        return validation_error_response(
            errors={"time_entry_ids": ["time_entry_ids must be a non-empty list"]},
            message="time_entry_ids is required",
        )
    replace_existing = data.get("replace_existing", True)
    result = _invoice_service().add_time_entries_to_invoice(
        invoice_id=invoice_id,
        user_id=g.api_user.id,
        time_entry_ids=[int(x) for x in time_entry_ids],
        is_admin=g.api_user.is_admin,
        replace_existing=bool(replace_existing),
    )
    if not result.get("success"):
        status = 403 if result.get("error") == "forbidden" else 400
        if result.get("error") == "not_found":
            status = 404
        return error_response(result.get("message", "Could not generate items"), status_code=status)
    detail = _invoice_service().get_invoice_detail(invoice_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin)
    return jsonify({"message": result["message"], "invoice": detail.get("invoice")})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>/items", methods=["PUT"])
@require_api_token("write:invoices")
def set_invoice_items(invoice_id):
    """Replace all line items on a draft invoice."""
    data = request.get_json() or {}
    items = data.get("items")
    if not isinstance(items, list):
        return validation_error_response(
            errors={"items": ["items must be a list"]},
            message="items must be a list",
        )
    result = _invoice_service().set_invoice_items(
        invoice_id=invoice_id,
        user_id=g.api_user.id,
        items=items,
        is_admin=g.api_user.is_admin,
    )
    if not result.get("success"):
        status = 403 if result.get("error") == "forbidden" else 400
        if result.get("error") == "not_found":
            status = 404
        return error_response(result.get("message", "Could not update items"), status_code=status)
    detail = _invoice_service().get_invoice_detail(invoice_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin)
    return jsonify({"message": result["message"], "invoice": detail.get("invoice")})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>/pdf", methods=["GET"])
@require_api_token("read:invoices")
def export_invoice_pdf_api(invoice_id):
    """Download invoice as PDF."""
    page_size = request.args.get("size", "A4")
    result = _invoice_service().generate_pdf_bytes(
        invoice_id=invoice_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        page_size=page_size,
    )
    if not result.get("success"):
        status = 403 if result.get("error") == "forbidden" else 400
        if result.get("error") == "not_found":
            status = 404
        return error_response(result.get("message", "Could not generate PDF"), status_code=status)
    return send_file(
        io.BytesIO(result["pdf_bytes"]),
        mimetype=result.get("mimetype", "application/pdf"),
        as_attachment=True,
        download_name=result.get("filename", f"invoice-{invoice_id}.pdf"),
    )


def _approval_to_api_dict(approval):
    """Serialize invoice approval with invoice summary for mobile clients."""
    from app.models import Invoice

    data = approval.to_dict()
    invoice = Invoice.query.get(approval.invoice_id)
    if invoice:
        data["invoice_number"] = invoice.invoice_number
        data["client_name"] = invoice.client_name
        data["total_amount"] = float(invoice.total_amount)
    return data


@api_v1_invoices_bp.route("/invoice-approvals", methods=["GET"])
@require_api_token("read:invoices")
def list_invoice_approvals():
    """List pending invoice approvals for the current user."""
    from app.services.invoice_approval_service import InvoiceApprovalService

    service = InvoiceApprovalService()
    if g.api_user.is_admin:
        approvals = service.list_pending_approvals()
    else:
        approvals = service.list_pending_approvals(user_id=g.api_user.id)
    return jsonify({"invoice_approvals": [_approval_to_api_dict(a) for a in approvals]})


@api_v1_invoices_bp.route("/invoice-approvals/<int:approval_id>", methods=["GET"])
@require_api_token("read:invoices")
def get_invoice_approval(approval_id):
    """Get invoice approval by id."""
    from app.models import InvoiceApproval
    from app.services.invoice_approval_service import InvoiceApprovalService

    approval = InvoiceApproval.query.get_or_404(approval_id)
    service = InvoiceApprovalService()
    if not g.api_user.is_admin:
        pending = service.list_pending_approvals(user_id=g.api_user.id)
        allowed_ids = {a.id for a in pending}
        if approval.id not in allowed_ids and approval.requested_by != g.api_user.id:
            return error_response("Access denied", status_code=403)
    return jsonify({"invoice_approval": _approval_to_api_dict(approval)})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>/request-approval", methods=["POST"])
@require_api_token("write:invoices")
def request_invoice_approval(invoice_id):
    """Request approval for an invoice."""
    from app.services.invoice_approval_service import InvoiceApprovalService

    data = request.get_json() or {}
    approvers = data.get("approver_ids") or data.get("approvers") or []
    if not isinstance(approvers, list) or not approvers:
        return validation_error_response(
            errors={"approver_ids": ["approver_ids must be a non-empty list"]},
            message="approver_ids is required",
        )
    service = InvoiceApprovalService()
    result = service.request_approval(
        invoice_id=invoice_id,
        requested_by=g.api_user.id,
        approvers=[int(a) for a in approvers],
    )
    if not result.get("success"):
        return error_response(result.get("message", "Request failed"), status_code=400)
    return (
        jsonify(
            {
                "message": result["message"],
                "invoice_approval": _approval_to_api_dict(result["approval"]),
            }
        ),
        201,
    )


@api_v1_invoices_bp.route("/invoice-approvals/<int:approval_id>/approve", methods=["POST"])
@require_api_token("write:invoices")
def approve_invoice_approval(approval_id):
    """Approve an invoice at the current workflow stage."""
    from app.services.invoice_approval_service import InvoiceApprovalService

    data = request.get_json(silent=True) or {}
    service = InvoiceApprovalService()
    result = service.approve(approval_id=approval_id, approver_id=g.api_user.id, comments=data.get("comment"))
    if not result.get("success"):
        return error_response(result.get("message", "Approval failed"), status_code=400)
    return jsonify(
        {
            "message": result["message"],
            "invoice_approval": _approval_to_api_dict(result["approval"]),
        }
    )


@api_v1_invoices_bp.route("/invoice-approvals/<int:approval_id>/reject", methods=["POST"])
@require_api_token("write:invoices")
def reject_invoice_approval(approval_id):
    """Reject an invoice approval."""
    from app.services.invoice_approval_service import InvoiceApprovalService

    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or data.get("rejection_reason")
    if not reason:
        return validation_error_response(
            errors={"reason": ["reason is required"]},
            message="Rejection reason required",
        )
    service = InvoiceApprovalService()
    result = service.reject(approval_id=approval_id, rejector_id=g.api_user.id, reason=reason)
    if not result.get("success"):
        return error_response(result.get("message", "Rejection failed"), status_code=400)
    return jsonify(
        {
            "message": result["message"],
            "invoice_approval": _approval_to_api_dict(result["approval"]),
        }
    )
