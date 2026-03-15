"""
API v1 - Deals (CRM) sub-blueprint.
Routes under /api/v1/deals.
"""

from flask import Blueprint, jsonify, request, g
from decimal import Decimal
from app import db
from app.models import Deal
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response, validation_error_response
from app.routes.api_v1_common import _parse_date, _require_module_enabled_for_api

api_v1_deals_bp = Blueprint("api_v1_deals", __name__, url_prefix="/api/v1")


@api_v1_deals_bp.route("/deals", methods=["GET"])
@require_api_token("read:deals")
def list_deals():
    """List deals with optional filters."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    status = request.args.get("status", "open")
    stage = request.args.get("stage", "")
    owner_id = request.args.get("owner", type=int)
    query = Deal.query
    if status == "open":
        query = query.filter_by(status="open")
    elif status == "won":
        query = query.filter_by(status="won")
    elif status == "lost":
        query = query.filter_by(status="lost")
    if stage:
        query = query.filter_by(stage=stage)
    if owner_id and not g.api_user.is_admin:
        query = query.filter_by(owner_id=g.api_user.id)
    elif owner_id:
        query = query.filter_by(owner_id=owner_id)
    query = query.order_by(Deal.expected_close_date, Deal.created_at.desc())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
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
    return jsonify({"deals": [d.to_dict() for d in pagination.items], "pagination": pagination_dict})


@api_v1_deals_bp.route("/deals/<int:deal_id>", methods=["GET"])
@require_api_token("read:deals")
def get_deal(deal_id):
    """Get a deal by id."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    return jsonify({"deal": deal.to_dict()})


@api_v1_deals_bp.route("/deals", methods=["POST"])
@require_api_token("write:deals")
def create_deal():
    """Create a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return validation_error_response(
            errors={"name": ["name is required"]},
            message="name is required",
        )
    value = None
    if data.get("value") is not None:
        try:
            value = Decimal(str(data["value"]))
        except Exception:
            return error_response("Invalid value", status_code=400)
    expected_close_date = _parse_date(data.get("expected_close_date"))
    deal = Deal(
        name=name,
        created_by=g.api_user.id,
        client_id=data.get("client_id"),
        contact_id=data.get("contact_id"),
        lead_id=data.get("lead_id"),
        description=(data.get("description") or "").strip() or None,
        stage=(data.get("stage") or "prospecting").strip(),
        value=value,
        currency_code=(data.get("currency_code") or "EUR").strip(),
        probability=int(data.get("probability", 50)),
        expected_close_date=expected_close_date,
        status=(data.get("status") or "open").strip(),
        loss_reason=(data.get("loss_reason") or "").strip() or None,
        notes=(data.get("notes") or "").strip() or None,
        owner_id=data.get("owner_id") or g.api_user.id,
        related_quote_id=data.get("related_quote_id"),
        related_project_id=data.get("related_project_id"),
    )
    db.session.add(deal)
    db.session.commit()
    return jsonify({"message": "Deal created successfully", "deal": deal.to_dict()}), 201


@api_v1_deals_bp.route("/deals/<int:deal_id>", methods=["PUT", "PATCH"])
@require_api_token("write:deals")
def update_deal(deal_id):
    """Update a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    for field in ("name", "description", "stage", "status", "loss_reason", "notes", "currency_code"):
        if field in data and data[field] is not None:
            setattr(deal, field, str(data[field]).strip() if isinstance(data[field], str) else data[field])
    for field in ("client_id", "contact_id", "lead_id", "probability", "related_quote_id", "related_project_id", "owner_id"):
        if field in data:
            setattr(deal, field, data[field])
    if "value" in data:
        try:
            deal.value = Decimal(str(data["value"])) if data["value"] is not None else None
        except Exception:
            pass
    if "expected_close_date" in data:
        deal.expected_close_date = _parse_date(data["expected_close_date"])
    if "actual_close_date" in data:
        deal.actual_close_date = _parse_date(data["actual_close_date"])
    db.session.commit()
    return jsonify({"message": "Deal updated successfully", "deal": deal.to_dict()})


@api_v1_deals_bp.route("/deals/<int:deal_id>", methods=["DELETE"])
@require_api_token("write:deals")
def delete_deal(deal_id):
    """Delete (or cancel) a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    db.session.delete(deal)
    db.session.commit()
    return jsonify({"message": "Deal deleted successfully"})
