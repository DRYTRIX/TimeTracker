"""
API v1 - Leads (CRM) sub-blueprint.
Routes under /api/v1/leads.
"""

from decimal import Decimal

from flask import Blueprint, g, jsonify, request
from sqlalchemy import or_

from app import db
from app.models import Lead
from app.routes.api_v1_common import _require_module_enabled_for_api
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response

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
    for field in (
        "first_name",
        "last_name",
        "company_name",
        "email",
        "phone",
        "title",
        "source",
        "status",
        "notes",
        "tags",
    ):
        if field in data and data[field] is not None:
            setattr(lead, field, str(data[field]).strip() if isinstance(data[field], str) else data[field])
    if "score" in data:
        new_score = int(data["score"])
        if new_score != lead.score:
            from app.models import LeadActivity

            old_score = lead.score
            lead.score = new_score
            db.session.add(
                LeadActivity(
                    lead_id=lead.id,
                    type="score_change",
                    created_by=g.api_user.id,
                    subject=f"Score changed from {old_score} to {new_score}",
                    description=f"{old_score} → {new_score}",
                    status="completed",
                )
            )
            # Relationship sync on LeadActivity can clobber dirty parent attrs
            lead.score = new_score
        else:
            lead.score = new_score
    if "estimated_value" in data:
        try:
            lead.estimated_value = (
                Decimal(str(data["estimated_value"])) if data["estimated_value"] is not None else None
            )
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


@api_v1_leads_bp.route("/leads/<int:lead_id>/activities", methods=["GET"])
@require_api_token("read:leads")
def list_lead_activities(lead_id):
    """List activities for a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    from app.models import LeadActivity

    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    activities = (
        LeadActivity.query.filter_by(lead_id=lead_id).order_by(LeadActivity.activity_date.desc()).limit(100).all()
    )
    return jsonify({"activities": [a.to_dict() for a in activities]})


@api_v1_leads_bp.route("/leads/<int:lead_id>/activities", methods=["POST"])
@require_api_token("write:leads")
def create_lead_activity(lead_id):
    """Create an activity for a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    from app.models import LeadActivity
    from app.routes.api_v1_common import parse_datetime

    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    activity_type = (data.get("type") or "note").strip()
    subject = (data.get("subject") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    due_date = parse_datetime(data.get("due_date"))
    activity = LeadActivity(
        lead_id=lead_id,
        type=activity_type,
        created_by=g.api_user.id,
        subject=subject,
        description=description,
        activity_date=parse_datetime(data.get("activity_date")) or None,
        due_date=due_date,
        status=(data.get("status") or "completed").strip() or "completed",
    )
    db.session.add(activity)
    if due_date:
        from app.utils.crm_calendar import sync_activity_to_calendar

        sync_activity_to_calendar(
            user_id=g.api_user.id,
            title=subject or f"Lead activity: {lead.display_name}",
            due_date=due_date,
            description=description,
            client_id=lead.converted_to_client_id,
        )
    db.session.commit()
    return jsonify({"message": "Activity created", "activity": activity.to_dict()}), 201


@api_v1_leads_bp.route("/leads/<int:lead_id>/convert-to-client", methods=["POST"])
@require_api_token("write:leads")
def api_convert_lead_to_client(lead_id):
    """Convert a lead to a client (and primary contact)."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    from app.models import Client, Contact

    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    if lead.is_converted:
        return error_response("Lead has already been converted", status_code=400)

    data = request.get_json() or {}
    client_name = (data.get("name") or lead.company_name or f"{lead.first_name} {lead.last_name}").strip()
    client = Client(
        name=client_name,
        contact_person=f"{lead.first_name} {lead.last_name}",
        email=lead.email,
        phone=lead.phone,
        description=f"Converted from lead: {lead.display_name}",
    )
    db.session.add(client)
    client.status = "active"
    db.session.flush()
    client_id = client.id
    contact = Contact(
        client_id=client_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        phone=lead.phone,
        title=lead.title,
        is_primary=True,
        created_by=g.api_user.id,
    )
    db.session.add(contact)
    db.session.flush()
    lead.convert_to_client(client_id, g.api_user.id)
    lead_payload = lead.to_dict()
    contact_payload = contact.to_dict()
    client_payload = {"id": client_id, "name": client.name, "email": client.email, "status": "active"}
    db.session.commit()
    return jsonify(
        {
            "message": "Lead converted to client",
            "lead": lead_payload,
            "client": client_payload,
            "contact": contact_payload,
        }
    )


@api_v1_leads_bp.route("/leads/<int:lead_id>/convert-to-deal", methods=["POST"])
@require_api_token("write:leads")
def api_convert_lead_to_deal(lead_id):
    """Convert a lead to a deal."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    from app.models import Deal
    from app.routes.api_v1_common import _parse_date

    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    if lead.is_converted:
        return error_response("Lead has already been converted", status_code=400)

    data = request.get_json() or {}
    deal_name = (data.get("name") or f"Deal: {lead.display_name}").strip()
    deal = Deal(
        name=deal_name,
        created_by=g.api_user.id,
        client_id=data.get("client_id"),
        description=(data.get("description") or "").strip() or None,
        stage=(data.get("stage") or "prospecting").strip(),
        value=lead.estimated_value,
        currency_code=lead.currency_code,
        probability=int(data.get("probability", 50)),
        expected_close_date=_parse_date(data.get("expected_close_date")),
        notes=lead.notes,
        owner_id=g.api_user.id,
    )
    db.session.add(deal)
    db.session.flush()
    deal.lead_id = lead_id
    lead.convert_to_deal(deal.id, g.api_user.id)
    db.session.commit()
    return jsonify({"message": "Lead converted to deal", "lead": lead.to_dict(), "deal": deal.to_dict()})


@api_v1_leads_bp.route("/leads/<int:lead_id>/email-threads", methods=["GET"])
@require_api_token("read:leads")
def list_lead_email_threads(lead_id):
    """List synced email threads linked to a lead."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    lead = Lead.query.filter_by(id=lead_id).first_or_404()
    if not g.api_user.is_admin and lead.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    from app.services.email_sync_service import EmailSyncService

    threads = EmailSyncService().threads_for_lead(lead_id)
    return jsonify({"email_threads": [t.to_dict() for t in threads]})


@api_v1_leads_bp.route("/leads/analytics/sources", methods=["GET"])
@require_api_token("read:leads")
def lead_source_analytics():
    """Aggregate lead counts and estimated value by source."""
    blocked = _require_module_enabled_for_api("leads")
    if blocked:
        return blocked
    from sqlalchemy import func

    query = db.session.query(
        Lead.source,
        func.count(Lead.id),
        func.coalesce(func.sum(Lead.estimated_value), 0),
        func.avg(Lead.score),
    )
    if not g.api_user.is_admin:
        query = query.filter(Lead.owner_id == g.api_user.id)
    rows = query.group_by(Lead.source).all()
    sources = []
    for source, count, total_value, avg_score in rows:
        sources.append(
            {
                "source": source or "unknown",
                "count": int(count),
                "estimated_value_total": float(total_value or 0),
                "average_score": float(avg_score or 0),
            }
        )
    sources.sort(key=lambda s: s["count"], reverse=True)
    return jsonify({"sources": sources, "total_leads": sum(s["count"] for s in sources)})
