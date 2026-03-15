"""
API v1 - Payments sub-blueprint.
Routes under /api/v1/payments.
"""

from flask import Blueprint, jsonify, request, g
from decimal import Decimal
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, validation_error_response
from app.routes.api_v1_common import _parse_date

api_v1_payments_bp = Blueprint("api_v1_payments", __name__, url_prefix="/api/v1")


@api_v1_payments_bp.route("/payments", methods=["GET"])
@require_api_token("read:payments")
def list_payments():
    """List payments."""
    from sqlalchemy.orm import joinedload
    from app.models import Payment

    invoice_id = request.args.get("invoice_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    query = Payment.query.options(joinedload(Payment.invoice))
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    query = query.order_by(Payment.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
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
    return jsonify({"payments": [p.to_dict() for p in pagination.items], "pagination": pagination_dict})


@api_v1_payments_bp.route("/payments/<int:payment_id>", methods=["GET"])
@require_api_token("read:payments")
def get_payment(payment_id):
    """Get a payment."""
    from sqlalchemy.orm import joinedload
    from app.models import Payment

    payment = Payment.query.options(joinedload(Payment.invoice)).filter_by(id=payment_id).first_or_404()
    return jsonify({"payment": payment.to_dict()})


@api_v1_payments_bp.route("/payments", methods=["POST"])
@require_api_token("write:payments")
def create_payment():
    """Create a payment."""
    from app.services import PaymentService
    from datetime import date

    data = request.get_json() or {}
    errors = {}
    required = ["invoice_id", "amount"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        for f in missing:
            errors[f] = [f"{f} is required"]
        return validation_error_response(errors=errors, message=f"Missing required fields: {', '.join(missing)}")
    try:
        amount = Decimal(str(data["amount"]))
    except Exception:
        return validation_error_response(
            errors={"amount": ["Invalid amount"]},
            message="Invalid amount",
        )
    pay_date = _parse_date(data.get("payment_date")) if data.get("payment_date") else date.today()
    payment_service = PaymentService()
    result = payment_service.create_payment(
        invoice_id=data["invoice_id"],
        amount=amount,
        payment_date=pay_date,
        received_by=g.api_user.id,
        currency=data.get("currency"),
        method=data.get("method"),
        reference=data.get("reference"),
        notes=data.get("notes"),
        status=data.get("status", "completed"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create payment")}), 400
    return jsonify({"message": "Payment created successfully", "payment": result["payment"].to_dict()}), 201


@api_v1_payments_bp.route("/payments/<int:payment_id>", methods=["PUT", "PATCH"])
@require_api_token("write:payments")
def update_payment(payment_id):
    """Update a payment."""
    from app.services import PaymentService

    data = request.get_json() or {}
    update_kwargs = {}
    for field in ("currency", "method", "reference", "notes", "status"):
        if field in data:
            update_kwargs[field] = data[field]
    if "amount" in data:
        try:
            update_kwargs["amount"] = Decimal(str(data["amount"]))
        except Exception:
            pass
    if "payment_date" in data:
        parsed = _parse_date(data["payment_date"])
        if parsed:
            update_kwargs["payment_date"] = parsed
    payment_service = PaymentService()
    result = payment_service.update_payment(payment_id=payment_id, user_id=g.api_user.id, **update_kwargs)
    if not result.get("success"):
        return error_response(result.get("message", "Could not update payment"), status_code=400)
    return jsonify({"message": "Payment updated successfully", "payment": result["payment"].to_dict()})


@api_v1_payments_bp.route("/payments/<int:payment_id>", methods=["DELETE"])
@require_api_token("write:payments")
def delete_payment(payment_id):
    """Delete a payment."""
    from app.services import PaymentService

    payment_service = PaymentService()
    result = payment_service.delete_payment(payment_id=payment_id, user_id=g.api_user.id)
    if not result.get("success"):
        return error_response(result.get("message", "Could not delete payment"), status_code=400)
    return jsonify({"message": "Payment deleted successfully"})
