"""
API v1 - Mileage sub-blueprint.
Routes under /api/v1/mileage.
"""

from flask import Blueprint, jsonify, request, g
from decimal import Decimal
from app import db
from app.models import Mileage
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response, validation_error_response
from app.routes.api_v1_common import _parse_date

api_v1_mileage_bp = Blueprint("api_v1_mileage", __name__, url_prefix="/api/v1")


@api_v1_mileage_bp.route("/mileage", methods=["GET"])
@require_api_token("read:mileage")
def list_mileage():
    """List mileage entries."""
    from sqlalchemy.orm import joinedload

    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return forbidden_response("Access denied")
    else:
        if not g.api_user.is_admin:
            user_id = g.api_user.id
    project_id = request.args.get("project_id", type=int)
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    query = Mileage.query.options(
        joinedload(Mileage.user), joinedload(Mileage.project), joinedload(Mileage.client)
    )
    if user_id:
        query = query.filter(Mileage.user_id == user_id)
    if project_id:
        query = query.filter(Mileage.project_id == project_id)
    if start_date:
        query = query.filter(Mileage.trip_date >= start_date)
    if end_date:
        query = query.filter(Mileage.trip_date <= end_date)
    query = query.order_by(Mileage.trip_date.desc(), Mileage.created_at.desc())
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
    return jsonify({"mileage": [m.to_dict() for m in pagination.items], "pagination": pagination_dict})


@api_v1_mileage_bp.route("/mileage/<int:entry_id>", methods=["GET"])
@require_api_token("read:mileage")
def get_mileage(entry_id):
    """Get a mileage entry."""
    from sqlalchemy.orm import joinedload

    entry = (
        Mileage.query.options(
            joinedload(Mileage.user), joinedload(Mileage.project), joinedload(Mileage.client)
        )
        .filter_by(id=entry_id)
        .first_or_404()
    )
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return forbidden_response("Access denied")
    return jsonify({"mileage": entry.to_dict()})


@api_v1_mileage_bp.route("/mileage", methods=["POST"])
@require_api_token("write:mileage")
def create_mileage():
    """Create a mileage entry."""
    data = request.get_json() or {}
    errors = {}
    required = ["trip_date", "purpose", "start_location", "end_location", "distance_km", "rate_per_km"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        for f in missing:
            errors[f] = [f"{f} is required"]
        return validation_error_response(errors=errors, message=f"Missing required fields: {', '.join(missing)}")
    trip_date = _parse_date(data.get("trip_date"))
    if not trip_date:
        return validation_error_response(
            errors={"trip_date": ["Invalid trip_date format, expected YYYY-MM-DD"]},
            message="Invalid trip_date format, expected YYYY-MM-DD",
        )
    try:
        distance_km = Decimal(str(data["distance_km"]))
        rate_per_km = Decimal(str(data["rate_per_km"]))
    except Exception:
        return validation_error_response(
            errors={"distance_km": ["Invalid distance_km or rate_per_km"], "rate_per_km": ["Invalid distance_km or rate_per_km"]},
            message="Invalid distance_km or rate_per_km",
        )
    entry = Mileage(
        user_id=g.api_user.id,
        trip_date=trip_date,
        purpose=data["purpose"],
        start_location=data["start_location"],
        end_location=data["end_location"],
        distance_km=distance_km,
        rate_per_km=rate_per_km,
        project_id=data.get("project_id"),
        client_id=data.get("client_id"),
        is_round_trip=bool(data.get("is_round_trip", False)),
        description=data.get("description"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "Mileage entry created successfully", "mileage": entry.to_dict()}), 201


@api_v1_mileage_bp.route("/mileage/<int:entry_id>", methods=["PUT", "PATCH"])
@require_api_token("write:mileage")
def update_mileage(entry_id):
    """Update a mileage entry."""
    from sqlalchemy.orm import joinedload

    entry = (
        Mileage.query.options(
            joinedload(Mileage.user), joinedload(Mileage.project), joinedload(Mileage.client)
        )
        .filter_by(id=entry_id)
        .first_or_404()
    )
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return forbidden_response("Access denied")
    data = request.get_json() or {}
    for field in (
        "purpose", "start_location", "end_location", "description",
        "vehicle_type", "vehicle_description", "license_plate", "currency_code", "status", "notes",
    ):
        if field in data:
            setattr(entry, field, data[field])
    if "trip_date" in data:
        parsed = _parse_date(data["trip_date"])
        if parsed:
            entry.trip_date = parsed
    for numfield in ("distance_km", "rate_per_km", "start_odometer", "end_odometer"):
        if numfield in data:
            try:
                setattr(entry, numfield, Decimal(str(data[numfield])))
            except Exception:
                pass
    if "is_round_trip" in data:
        entry.is_round_trip = bool(data["is_round_trip"])
    if "distance_km" in data or "rate_per_km" in data:
        entry.calculated_amount = entry.distance_km * entry.rate_per_km
        if entry.is_round_trip:
            entry.calculated_amount *= Decimal("2")
    db.session.commit()
    return jsonify({"message": "Mileage entry updated successfully", "mileage": entry.to_dict()})


@api_v1_mileage_bp.route("/mileage/<int:entry_id>", methods=["DELETE"])
@require_api_token("write:mileage")
def delete_mileage(entry_id):
    """Reject a mileage entry."""
    from sqlalchemy.orm import joinedload

    entry = (
        Mileage.query.options(
            joinedload(Mileage.user), joinedload(Mileage.project), joinedload(Mileage.client)
        )
        .filter_by(id=entry_id)
        .first_or_404()
    )
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return forbidden_response("Access denied")
    entry.status = "rejected"
    db.session.commit()
    return jsonify({"message": "Mileage entry rejected successfully"})
