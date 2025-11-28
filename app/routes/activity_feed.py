"""
Activity Feed routes
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Activity
from flask_babel import gettext as _
from sqlalchemy import and_
from datetime import datetime, timedelta

activity_feed_bp = Blueprint("activity_feed", __name__)


@activity_feed_bp.route("/activity")
@login_required
def activity_feed():
    """Main activity feed page"""
    # Get query parameters
    limit = request.args.get("limit", 50, type=int)
    page = request.args.get("page", 1, type=int)
    user_id = request.args.get("user_id", type=int)
    entity_type = request.args.get("entity_type", "").strip()
    action = request.args.get("action", "").strip()
    
    # Build query
    query = Activity.query

    # Apply filters
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    
    if action:
        query = query.filter_by(action=action)

    # Date filters
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Activity.created_at >= start_dt)
        except Exception:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Activity.created_at <= end_dt)
        except Exception:
            pass

    # Paginate
    per_page = min(limit, 100)  # Max 100 per page
    paginated = query.order_by(Activity.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    entity_types = db.session.query(Activity.entity_type).distinct().all() if hasattr(db, 'session') else []
    actions = db.session.query(Activity.action).distinct().all() if hasattr(db, 'session') else []

    return render_template(
        "activity/feed.html",
        activities=paginated.items,
        pagination=paginated,
        entity_types=[e[0] for e in entity_types],
        actions=[a[0] for a in actions],
        filters={
            "user_id": user_id,
            "entity_type": entity_type,
            "action": action,
            "start_date": start_date,
            "end_date": end_date,
        }
    )


@activity_feed_bp.route("/api/activity")
@login_required
def api_activity_feed():
    """API endpoint for activity feed"""
    # Get query parameters
    limit = request.args.get("limit", 50, type=int)
    page = request.args.get("page", 1, type=int)
    user_id = request.args.get("user_id", type=int)
    entity_type = request.args.get("entity_type", "").strip()
    action = request.args.get("action", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Build query
    query = Activity.query

    # Apply filters
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    
    if action:
        query = query.filter_by(action=action)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Activity.created_at >= start_dt)
        except Exception:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Activity.created_at <= end_dt)
        except Exception:
            pass

    # Paginate
    per_page = min(limit, 100)
    paginated = query.order_by(Activity.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "activities": [a.to_dict() for a in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        }
    })

