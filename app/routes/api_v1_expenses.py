"""
API v1 - Expenses sub-blueprint.
Routes under /api/v1/expenses.
"""

from flask import Blueprint, jsonify, request, g
from decimal import Decimal
from app.utils.api_auth import require_api_token
from app.routes.api_v1_common import _parse_date

api_v1_expenses_bp = Blueprint("api_v1_expenses", __name__, url_prefix="/api/v1")


@api_v1_expenses_bp.route("/expenses", methods=["GET"])
@require_api_token("read:expenses")
def list_expenses():
    """List expenses."""
    from app.services import ExpenseService

    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if not g.api_user.is_admin:
            user_id = g.api_user.id
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    status = request.args.get("status")
    category = request.args.get("category")
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    expense_service = ExpenseService()
    result = expense_service.list_expenses(
        user_id=user_id,
        project_id=project_id,
        client_id=client_id,
        status=status,
        category=category,
        start_date=start_date,
        end_date=end_date,
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
    return jsonify({"expenses": [e.to_dict() for e in result["expenses"]], "pagination": pagination_dict})


@api_v1_expenses_bp.route("/expenses/<int:expense_id>", methods=["GET"])
@require_api_token("read:expenses")
def get_expense(expense_id):
    """Get an expense."""
    from sqlalchemy.orm import joinedload
    from app.models import Expense

    expense = (
        Expense.query.options(joinedload(Expense.project), joinedload(Expense.user), joinedload(Expense.client))
        .filter_by(id=expense_id)
        .first_or_404()
    )
    if not g.api_user.is_admin and expense.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"expense": expense.to_dict()})


@api_v1_expenses_bp.route("/expenses", methods=["POST"])
@require_api_token("write:expenses")
def create_expense():
    """Create a new expense."""
    from app.services import ExpenseService

    data = request.get_json() or {}
    required = ["title", "category", "amount", "expense_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    exp_date = _parse_date(data.get("expense_date"))
    if not exp_date:
        return jsonify({"error": "Invalid expense_date format, expected YYYY-MM-DD"}), 400
    pay_date = _parse_date(data.get("payment_date")) if data.get("payment_date") else None
    try:
        amount = Decimal(str(data["amount"]))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    expense_service = ExpenseService()
    result = expense_service.create_expense(
        amount=amount,
        expense_date=exp_date,
        created_by=g.api_user.id,
        title=data["title"],
        description=data.get("description"),
        project_id=data.get("project_id"),
        client_id=data.get("client_id"),
        category=data["category"],
        billable=data.get("billable", False),
        reimbursable=data.get("reimbursable", True),
        currency_code=data.get("currency_code", "EUR"),
        tax_amount=Decimal(str(data.get("tax_amount", 0))) if data.get("tax_amount") else None,
        tax_rate=Decimal(str(data.get("tax_rate", 0))) if data.get("tax_rate") else None,
        payment_method=data.get("payment_method"),
        payment_date=pay_date,
        tags=data.get("tags"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create expense")}), 400
    return jsonify({"message": "Expense created successfully", "expense": result["expense"].to_dict()}), 201


@api_v1_expenses_bp.route("/expenses/<int:expense_id>", methods=["PUT", "PATCH"])
@require_api_token("write:expenses")
def update_expense(expense_id):
    """Update an expense."""
    from app.services import ExpenseService

    data = request.get_json() or {}
    update_kwargs = {}
    for field in ("title", "description", "category", "currency_code", "payment_method", "status", "tags"):
        if field in data:
            update_kwargs[field] = data[field]
    if "amount" in data:
        try:
            update_kwargs["amount"] = Decimal(str(data["amount"]))
        except Exception:
            pass
    if "expense_date" in data:
        parsed = _parse_date(data["expense_date"])
        if parsed:
            update_kwargs["expense_date"] = parsed
    if "payment_date" in data:
        update_kwargs["payment_date"] = _parse_date(data["payment_date"])
    for bfield in ("billable", "reimbursable", "reimbursed", "invoiced"):
        if bfield in data:
            update_kwargs[bfield] = bool(data[bfield])
    expense_service = ExpenseService()
    result = expense_service.update_expense(
        expense_id=expense_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin, **update_kwargs
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update expense")}), 400
    return jsonify({"message": "Expense updated successfully", "expense": result["expense"].to_dict()})


@api_v1_expenses_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@require_api_token("write:expenses")
def delete_expense(expense_id):
    """Reject an expense (soft-delete)."""
    from app.services import ExpenseService

    expense_service = ExpenseService()
    result = expense_service.delete_expense(
        expense_id=expense_id, user_id=g.api_user.id, is_admin=g.api_user.is_admin
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not reject expense")}), 400
    return jsonify({"message": "Expense rejected successfully"})
