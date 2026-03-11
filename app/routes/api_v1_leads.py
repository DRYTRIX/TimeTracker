"""
API v1 - Leads (CRM) sub-blueprint.
Routes under /api/v1/leads.
"""

from flask import Blueprint, jsonify, request, g
from decimal import Decimal
from sqlalchemy import or_
from app import db
from app.models import Lead
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response
from app.routes.api_v1_common import _require_module_enabled_for_api

api_v1_leads_bp = Blueprint("api_v1_leads", __name__, url_prefix="/api/v1")


@api_v1_leads_bp.route("/leads", methods=["GET"])
@require_api_token("read:leads")
def list_leads():
    """List leads with optional filters."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    status = request.args.get("status", "")
    source = request.args.get("source", "")
    owner_id = request.args.get("owner", type=int)
    search = (request.args.get("search") or "").strip()
    query = Lead.query
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(~Lead.status.in_(["converted", "lost"]))
    if source:
        query = query.filter_by(source=source)
    if owner_id and not g.api_user.is_admin:
        query = query.filter_by(owner_id=g.api_user.id)
    elif owner_id:
        query = query.filter_by(owner_id=owner_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Lead.first_name.ilike(like),
                Lead.last_name.ilike(like),
                Lead.company_name.ilike(like),
                Lead.email.ilike(like),
            )
        )
    query = query.order_by(Lead.score.desc(), Lead.created_at.desc())
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
    return jsonify({"leads": [l.to_dict() for l in pagination.items], "pagination": pagination_dict})


@api_v1_leads_bp.route("/leads/<int:lead_id>", methods=["GET"])
@require_api_token("read:leads")
def get_lead(lead_id):
    """Get a lead by id."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    return jsonify({"lead": lead.to_dict()})


@api_v1_leads_bp.route("/leads", methods=["POST"])
@require_api_token("write:leads")
def create_lead():
    """Create a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    data = request.get_json() or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name or not last_name:
        return error_response("first_name and last_name are required", status_code=400)
    estimated_value = None
    if data.get("estimated_value") is not None:
        try:
            estimated_value = Decimal(str(data["estimated_value"]))
        except Exception:
            pass
    lead = Lead(
        first_name=first_name,
        last_name=last_name,
        created_by=g.api_user.id,
        company_name=(data.get("company_name") or "").strip() or None,
        email=(data.get("email") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        title=(data.get("title") or "").strip() or None,
        source=(data.get("source") or "").strip() or None,
        status=(data.get("status") or "new").strip(),
        score=int(data.get("score", 0)),
        estimated_value=estimated_value,
        currency_code=(data.get("currency_code") or "EUR").strip(),
        notes=(data.get("notes") or "").strip() or None,
        tags=(data.get("tags") or "").strip() or None,
        owner_id=data.get("owner_id") or g.api_user.id,
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"message": "Lead created successfully", "lead": lead.to_dict()}), 201


@api_v1_leads_bp.route("/leads/<int:lead_id>", methods=["PUT", "PATCH"])
@require_api_token("write:leads")
def update_lead(lead_id):
    """Update a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    for field in ("first_name", "last_name", "company_name", "email", "phone", "title", "source", "status", "notes", "tags"):
        if field in data and data[field] is not None:
            setattr(lead, field, str(data[field]).strip() if isinstance(data[field], str) else data[field])
    if "score" in data:
        lead.score = int(data["score"])
    if "estimated_value" in data:
        try:
            lead.estimated_value = Decimal(str(data["estimated_value"])) if data["estimated_value"] is not None else None
        except Exception:
            pass
    if "owner_id" in data:
        lead.owner_id = data["owner_id"]
    db.session.commit()
    return jsonify({"message": "Lead updated successfully", "lead": lead.to_dict()})


@api_v1_leads_bp.route("/leads/<int:lead_id>", methods=["DELETE"])
@require_api_token("write:leads")
def delete_lead(lead_id):
    """Delete a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"message": "Lead deleted successfully"})
