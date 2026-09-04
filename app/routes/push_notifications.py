"""
Routes for push notification management.
"""

from flask import Blueprint, current_app, g, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models import PushSubscription
from app.utils.api_auth import require_api_token
from app.utils.db import safe_commit
from app.utils.timezone import now_in_app_timezone

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
            existing.platform = existing.platform or "web"
            existing.updated_at = now_in_app_timezone()
            existing.update_last_used()
        else:
            # Create new subscription
            subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                keys=keys,
                user_agent=user_agent,
                platform="web",
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
        return jsonify({"success": True, "subscriptions": [sub.to_dict() for sub in subscriptions]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def _register_device_token_for_user(user_id: int):
    """Shared handler for session and API-token device registration."""
    data = request.get_json(silent=True) or {}
    device_token = (data.get("device_token") or data.get("token") or "").strip()
    platform = (data.get("platform") or "").strip().lower()
    user_agent = request.headers.get("User-Agent", "")

    if not device_token:
        return jsonify({"success": False, "error": "device_token is required"}), 400
    if platform and platform not in ("android", "ios"):
        return jsonify({"success": False, "error": "platform must be android or ios"}), 400
    if not platform:
        platform = "android"

    if len(device_token) > 512:
        return jsonify({"success": False, "error": "device_token too long"}), 400

    try:
        PushSubscription.upsert_device_token(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            user_agent=user_agent,
        )
        if safe_commit("register_device_push", {"user_id": user_id}):
            return jsonify({"success": True, "message": "Device registered for push"})
        return jsonify({"success": False, "error": "Failed to save device token"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning("register device push failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@push_bp.route("/api/push/register-device", methods=["POST"])
@login_required
def register_device_session():
    """Register an FCM device token (session auth)."""
    return _register_device_token_for_user(current_user.id)


@push_bp.route("/api/v1/push/register-device", methods=["POST"])
@require_api_token("write:time_entries")
def register_device_api():
    """Register an FCM device token (API token auth for mobile/desktop)."""
    user = getattr(g, "api_user", None)
    if user is None:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return _register_device_token_for_user(user.id)
