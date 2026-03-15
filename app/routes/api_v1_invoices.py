"""
API v1 - Invoices sub-blueprint.
Routes under /api/v1/invoices.
"""

from flask import Blueprint, jsonify, request, g, current_app
from app import db
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, validation_error_response
from app.routes.api_v1_common import _parse_date

api_v1_invoices_bp = Blueprint("api_v1_invoices", __name__, url_prefix="/api/v1")


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
    """Get invoice by id."""
    from sqlalchemy.orm import joinedload
    from app.models import Invoice

    invoice = (
        Invoice.query.options(joinedload(Invoice.project), joinedload(Invoice.client))
        .filter_by(id=invoice_id)
        .first_or_404()
    )
    return jsonify({"invoice": invoice.to_dict()})


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
    from app.services import InvoiceService
    from decimal import Decimal, InvalidOperation

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
            current_app.logger.warning("Invalid amount_paid value in invoice update: %s - %s", data.get("amount_paid"), e)
    invoice_service = InvoiceService()
    result = invoice_service.update_invoice(invoice_id=invoice_id, user_id=g.api_user.id, **update_kwargs)
    if not result.get("success"):
        return error_response(result.get("message", "Could not update invoice"), status_code=400)
    if "amount_paid" in data:
        result["invoice"].update_payment_status()
        db.session.commit()
    return jsonify({"message": "Invoice updated successfully", "invoice": result["invoice"].to_dict()})


@api_v1_invoices_bp.route("/invoices/<int:invoice_id>", methods=["DELETE"])
@require_api_token("write:invoices")
def delete_invoice(invoice_id):
    """Cancel an invoice (soft-delete)."""
    from app.services import InvoiceService

    invoice_service = InvoiceService()
    result = invoice_service.update_invoice(invoice_id=invoice_id, user_id=g.api_user.id, status="cancelled")
    if not result.get("success"):
        return error_response(result.get("message", "Could not cancel invoice"), status_code=400)
    return jsonify({"message": "Invoice cancelled successfully"})
