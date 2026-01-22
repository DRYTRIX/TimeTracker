"""
Saved Filters Routes

This module provides routes for managing saved filters/searches.
Users can save commonly used filters for quick access.
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import _
from app import db
from app.models import SavedFilter
from app.utils.db import safe_commit
from app import log_event, track_event
from app.models import Activity
import logging
import json
from app.utils.module_helpers import module_enabled

logger = logging.getLogger(__name__)

saved_filters_bp = Blueprint("saved_filters", __name__)


@saved_filters_bp.route("/filters")
@login_required
@module_enabled("saved_filters")
def list_filters():
    """List all saved filters for the current user."""
    filters = SavedFilter.query.filter_by(user_id=current_user.id).order_by(SavedFilter.created_at.desc()).all()

    # Group by scope
    grouped_filters = {}
    for filter_obj in filters:
        if filter_obj.scope not in grouped_filters:
            grouped_filters[filter_obj.scope] = []
        grouped_filters[filter_obj.scope].append(filter_obj)

    return render_template("saved_filters/list.html", filters=filters, grouped_filters=grouped_filters)


@saved_filters_bp.route("/api/filters", methods=["GET"])
@login_required
@module_enabled("saved_filters")
def get_filters_api():
    """Get saved filters for the current user (API endpoint)."""
    scope = request.args.get("scope")  # Optional filter by scope

    query = SavedFilter.query.filter_by(user_id=current_user.id)

    if scope:
        query = query.filter_by(scope=scope)

    filters = query.order_by(SavedFilter.created_at.desc()).all()

    return jsonify({"filters": [f.to_dict() for f in filters]})


@saved_filters_bp.route("/api/filters", methods=["POST"])
@login_required
@module_enabled("saved_filters")
def create_filter_api():
    """Create a new saved filter (API endpoint)."""
    try:
        data = request.get_json()

        name = data.get("name", "").strip()
        scope = data.get("scope", "").strip()
        payload = data.get("payload", {})
        is_shared = data.get("is_shared", False)

        # Validation
        if not name:
            return jsonify({"error": "Filter name is required"}), 400

        if not scope:
            return jsonify({"error": "Filter scope is required"}), 400

        # Check for duplicate
        existing = SavedFilter.query.filter_by(user_id=current_user.id, name=name, scope=scope).first()

        if existing:
            return jsonify({"error": f'Filter "{name}" already exists for {scope}'}), 409

        # Create filter
        saved_filter = SavedFilter(
            user_id=current_user.id, name=name, scope=scope, payload=payload, is_shared=is_shared
        )

        db.session.add(saved_filter)
        if not safe_commit("create_saved_filter", {"name": name, "scope": scope}):
            return jsonify({"error": "Could not save filter due to a database error"}), 500

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="created",
            entity_type="saved_filter",
            entity_id=saved_filter.id,
            entity_name=saved_filter.name,
            description=f'Created saved filter "{saved_filter.name}" for {scope}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Track event
        log_event(
            "saved_filter.created", user_id=current_user.id, filter_id=saved_filter.id, filter_name=name, scope=scope
        )
        track_event(
            current_user.id,
            "saved_filter.created",
            {"filter_id": saved_filter.id, "filter_name": name, "scope": scope, "is_shared": is_shared},
        )

        return jsonify({"success": True, "filter": saved_filter.to_dict()}), 201

    except Exception as e:
        logger.error(f"Error creating saved filter: {e}")
        return jsonify({"error": "An error occurred while creating the filter"}), 500


@saved_filters_bp.route("/api/filters/<int:filter_id>", methods=["GET"])
@login_required
@module_enabled("saved_filters")
def get_filter_api(filter_id):
    """Get a specific saved filter (API endpoint)."""
    saved_filter = SavedFilter.query.filter_by(id=filter_id, user_id=current_user.id).first_or_404()

    return jsonify(saved_filter.to_dict())


@saved_filters_bp.route("/api/filters/<int:filter_id>", methods=["PUT"])
@login_required
@module_enabled("saved_filters")
def update_filter_api(filter_id):
    """Update a saved filter (API endpoint)."""
    try:
        saved_filter = SavedFilter.query.filter_by(id=filter_id, user_id=current_user.id).first_or_404()

        data = request.get_json()

        name = data.get("name", "").strip()
        payload = data.get("payload")
        is_shared = data.get("is_shared")

        if name:
            # Check for duplicate (excluding current filter)
            existing = SavedFilter.query.filter(
                SavedFilter.user_id == current_user.id,
                SavedFilter.name == name,
                SavedFilter.scope == saved_filter.scope,
                SavedFilter.id != filter_id,
            ).first()

            if existing:
                return jsonify({"error": f'Filter "{name}" already exists'}), 409

            saved_filter.name = name

        if payload is not None:
            saved_filter.payload = payload

        if is_shared is not None:
            saved_filter.is_shared = is_shared

        if not safe_commit("update_saved_filter", {"filter_id": filter_id}):
            return jsonify({"error": "Could not update filter due to a database error"}), 500

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="updated",
            entity_type="saved_filter",
            entity_id=saved_filter.id,
            entity_name=saved_filter.name,
            description=f'Updated saved filter "{saved_filter.name}"',
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Track event
        log_event("saved_filter.updated", user_id=current_user.id, filter_id=saved_filter.id)
        track_event(
            current_user.id, "saved_filter.updated", {"filter_id": saved_filter.id, "filter_name": saved_filter.name}
        )

        return jsonify({"success": True, "filter": saved_filter.to_dict()})

    except Exception as e:
        logger.error(f"Error updating saved filter: {e}")
        return jsonify({"error": "An error occurred while updating the filter"}), 500


@saved_filters_bp.route("/api/filters/<int:filter_id>", methods=["DELETE"])
@login_required
@module_enabled("saved_filters")
def delete_filter_api(filter_id):
    """Delete a saved filter (API endpoint)."""
    try:
        saved_filter = SavedFilter.query.filter_by(id=filter_id, user_id=current_user.id).first_or_404()

        filter_name = saved_filter.name
        filter_scope = saved_filter.scope

        db.session.delete(saved_filter)
        if not safe_commit("delete_saved_filter", {"filter_id": filter_id}):
            return jsonify({"error": "Could not delete filter due to a database error"}), 500

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="deleted",
            entity_type="saved_filter",
            entity_id=filter_id,
            entity_name=filter_name,
            description=f'Deleted saved filter "{filter_name}"',
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Track event
        log_event("saved_filter.deleted", user_id=current_user.id, filter_id=filter_id, filter_name=filter_name)
        track_event(
            current_user.id,
            "saved_filter.deleted",
            {"filter_id": filter_id, "filter_name": filter_name, "scope": filter_scope},
        )

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error(f"Error deleting saved filter: {e}")
        return jsonify({"error": "An error occurred while deleting the filter"}), 500


@saved_filters_bp.route("/filters/<int:filter_id>/delete", methods=["POST"])
@login_required
@module_enabled("saved_filters")
def delete_filter(filter_id):
    """Delete a saved filter (web form)."""
    saved_filter = SavedFilter.query.filter_by(id=filter_id, user_id=current_user.id).first_or_404()

    filter_name = saved_filter.name

    db.session.delete(saved_filter)
    if not safe_commit("delete_saved_filter", {"filter_id": filter_id}):
        flash(_("Could not delete filter due to a database error"), "error")
        return redirect(url_for("saved_filters.list_filters"))

    # Log activity
    Activity.log(
        user_id=current_user.id,
        action="deleted",
        entity_type="saved_filter",
        entity_id=filter_id,
        entity_name=filter_name,
        description=f'Deleted saved filter "{filter_name}"',
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    flash(f'Filter "{filter_name}" deleted successfully', "success")
    return redirect(url_for("saved_filters.list_filters"))
