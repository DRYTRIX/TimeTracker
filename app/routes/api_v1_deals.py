"""
API v1 - Deals (CRM) sub-blueprint.
Routes under /api/v1/deals.
"""

from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from app import db
from app.models import Deal
from app.routes.api_v1_common import _parse_date, _require_module_enabled_for_api
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response, validation_error_response

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
    old_stage = deal.stage
    for field in ("name", "description", "stage", "status", "loss_reason", "notes", "currency_code"):
        if field in data and data[field] is not None:
            setattr(deal, field, str(data[field]).strip() if isinstance(data[field], str) else data[field])
    for field in (
        "client_id",
        "contact_id",
        "lead_id",
        "probability",
        "related_quote_id",
        "related_project_id",
        "owner_id",
    ):
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
    if "stage" in data and deal.stage != old_stage:
        from app.models import DealActivity

        stage_snapshot = deal.stage
        db.session.add(
            DealActivity(
                deal_id=deal.id,
                type="stage_change",
                created_by=g.api_user.id,
                subject=f"Stage changed from {old_stage} to {stage_snapshot}",
                description=f"{old_stage} → {stage_snapshot}",
                status="completed",
            )
        )
        deal.stage = stage_snapshot
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


PIPELINE_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]


@api_v1_deals_bp.route("/deals/<int:deal_id>/activities", methods=["GET"])
@require_api_token("read:deals")
def list_deal_activities(deal_id):
    """List activities for a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    from app.models import DealActivity

    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    activities = (
        DealActivity.query.filter_by(deal_id=deal_id).order_by(DealActivity.activity_date.desc()).limit(100).all()
    )
    return jsonify({"activities": [a.to_dict() for a in activities]})


@api_v1_deals_bp.route("/deals/<int:deal_id>/activities", methods=["POST"])
@require_api_token("write:deals")
def create_deal_activity(deal_id):
    """Create an activity for a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    from app.models import DealActivity
    from app.routes.api_v1_common import parse_datetime

    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    subject = (data.get("subject") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    due_date = parse_datetime(data.get("due_date"))
    activity = DealActivity(
        deal_id=deal_id,
        type=(data.get("type") or "note").strip(),
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
            title=subject or f"Deal activity: {deal.name}",
            due_date=due_date,
            description=description,
            client_id=deal.client_id,
        )
    db.session.commit()
    return jsonify({"message": "Activity created", "activity": activity.to_dict()}), 201


@api_v1_deals_bp.route("/deals/<int:deal_id>/stage", methods=["PUT", "PATCH"])
@require_api_token("write:deals")
def update_deal_stage(deal_id):
    """Move a deal to a pipeline stage (supports drag-and-drop clients)."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    from app.models import DealActivity

    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    new_stage = (data.get("stage") or "").strip()
    if new_stage not in PIPELINE_STAGES:
        return validation_error_response(
            errors={"stage": [f"stage must be one of: {', '.join(PIPELINE_STAGES)}"]},
            message="Invalid stage",
        )
    old_stage = deal.stage
    if old_stage != new_stage:
        deal.stage = new_stage
        if new_stage == "closed_won":
            deal.close_won()
        elif new_stage == "closed_lost":
            deal.close_lost(reason=data.get("loss_reason"))
        elif deal.status in ("won", "lost") and new_stage not in ("closed_won", "closed_lost"):
            deal.status = "open"
            deal.closed_at = None
            deal.actual_close_date = None
        # Snapshot after stage/status mutations; DealActivity sync can clobber parent attrs
        stage_snapshot = deal.stage
        status_snapshot = deal.status
        closed_at_snapshot = deal.closed_at
        actual_close_snapshot = deal.actual_close_date
        loss_reason_snapshot = deal.loss_reason
        db.session.add(
            DealActivity(
                deal_id=deal.id,
                type="stage_change",
                created_by=g.api_user.id,
                subject=f"Stage changed from {old_stage} to {new_stage}",
                description=f"{old_stage} → {new_stage}",
                status="completed",
            )
        )
        deal.stage = stage_snapshot
        deal.status = status_snapshot
        deal.closed_at = closed_at_snapshot
        deal.actual_close_date = actual_close_snapshot
        deal.loss_reason = loss_reason_snapshot
        db.session.commit()
    return jsonify({"message": "Deal stage updated", "deal": deal.to_dict()})


@api_v1_deals_bp.route("/deals/forecast", methods=["GET"])
@require_api_token("read:deals")
def deals_forecast():
    """Weighted pipeline forecast by stage for open deals."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    query = Deal.query.filter_by(status="open")
    if not g.api_user.is_admin:
        query = query.filter_by(owner_id=g.api_user.id)
    deals = query.all()
    by_stage = {}
    total_value = 0.0
    total_weighted = 0.0
    for stage in PIPELINE_STAGES:
        if stage.startswith("closed_"):
            continue
        stage_deals = [d for d in deals if d.stage == stage]
        value = sum(float(d.value or 0) for d in stage_deals)
        weighted = sum(float(d.weighted_value) for d in stage_deals)
        by_stage[stage] = {
            "count": len(stage_deals),
            "value": value,
            "weighted_value": weighted,
        }
        total_value += value
        total_weighted += weighted
    return jsonify(
        {
            "forecast": {
                "by_stage": by_stage,
                "total_open_value": total_value,
                "total_weighted_value": total_weighted,
                "open_deal_count": len(deals),
            }
        }
    )


@api_v1_deals_bp.route("/deals/<int:deal_id>/email-threads", methods=["GET"])
@require_api_token("read:deals")
def list_deal_email_threads(deal_id):
    """List synced email threads linked to a deal."""
    blocked = _require_module_enabled_for_api("deals")
    if blocked:
        return blocked
    deal = Deal.query.filter_by(id=deal_id).first_or_404()
    if not g.api_user.is_admin and deal.owner_id != g.api_user.id:
        return forbidden_response("Access denied")
    from app.services.email_sync_service import EmailSyncService

    threads = EmailSyncService().threads_for_deal(deal_id)
    return jsonify({"email_threads": [t.to_dict() for t in threads]})
