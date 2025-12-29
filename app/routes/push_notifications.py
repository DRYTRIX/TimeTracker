"""
Routes for push notification management.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import User, PushSubscription
from app.utils.db import safe_commit
import json

push_bp = Blueprint("push", __name__)


@push_bp.route("/api/push/subscribe", methods=["POST"])
@login_required
def subscribe_push():
    """Subscribe user to push notifications."""
    try:
        subscription_data = request.json
        
        if not subscription_data:
            return jsonify({"success": False, "message": "Invalid subscription data"}), 400
        
        # Extract subscription details
        endpoint = subscription_data.get("endpoint")
        keys = subscription_data.get("keys", {})
        user_agent = request.headers.get("User-Agent", "")
        
        if not endpoint:
            return jsonify({"success": False, "message": "Endpoint is required"}), 400
        
        # Check if subscription already exists for this user and endpoint
        existing = PushSubscription.find_by_endpoint(current_user.id, endpoint)
        
        if existing:
            # Update existing subscription
            existing.keys = keys
            existing.user_agent = user_agent
            from app.utils.timezone import now_in_app_timezone
            existing.updated_at = now_in_app_timezone()
            existing.update_last_used()
        else:
            # Create new subscription
            subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                keys=keys,
                user_agent=user_agent
            )
            db.session.add(subscription)
        
        if safe_commit("subscribe_push", {"user_id": current_user.id}):
            return jsonify({"success": True, "message": "Subscribed to push notifications"})
        else:
            return jsonify({"success": False, "message": "Failed to save subscription"}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@push_bp.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def unsubscribe_push():
    """Unsubscribe user from push notifications."""
    try:
        subscription_data = request.json
        endpoint = subscription_data.get("endpoint") if subscription_data else None
        
        if endpoint:
            # Remove specific subscription by endpoint
            subscription = PushSubscription.find_by_endpoint(current_user.id, endpoint)
            if subscription:
                db.session.delete(subscription)
                if safe_commit("unsubscribe_push", {"user_id": current_user.id}):
                    return jsonify({"success": True, "message": "Unsubscribed from push notifications"})
        else:
            # Remove all subscriptions for user
            subscriptions = PushSubscription.get_user_subscriptions(current_user.id)
            for subscription in subscriptions:
                db.session.delete(subscription)
            
            if safe_commit("unsubscribe_push_all", {"user_id": current_user.id}):
                return jsonify({"success": True, "message": "Unsubscribed from all push notifications"})

        return jsonify({"success": False, "message": "No subscription found"}), 404

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@push_bp.route("/api/push/subscriptions", methods=["GET"])
@login_required
def list_subscriptions():
    """Get all push subscriptions for the current user."""
    try:
        subscriptions = PushSubscription.get_user_subscriptions(current_user.id)
        return jsonify({
            "success": True,
            "subscriptions": [sub.to_dict() for sub in subscriptions]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
