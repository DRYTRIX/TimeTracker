"""Admin routes for API token management (registered on admin_bp)."""

from datetime import datetime

from flask import current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models import User
from app.routes.admin import admin_bp
from app.utils.permissions import admin_or_permission_required


@admin_bp.route("/admin/api-tokens")
@login_required
@admin_or_permission_required("manage_api_tokens")
def api_tokens():
    """API tokens management page"""
    from app.models import ApiToken

    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()

    return render_template("admin/api_tokens.html", tokens=tokens, users=users, now=datetime.utcnow())


@admin_bp.route("/admin/api-tokens", methods=["POST"])
@login_required
@admin_or_permission_required("manage_api_tokens")
def create_api_token():
    """Create a new API token"""
    from app.models import ApiToken

    data = request.get_json() or {}

    # Validate input
    if not data.get("name"):
        return jsonify({"error": "Token name is required"}), 400
    if not data.get("user_id"):
        return jsonify({"error": "User ID is required"}), 400
    if not data.get("scopes"):
        return jsonify({"error": "At least one scope is required"}), 400

    # Verify user exists
    user = User.query.get(data["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user:
        return jsonify({"error": "Invalid user"}), 400

    # Create token
    try:
        api_token, plain_token = ApiToken.create_token(
            user_id=data["user_id"],
            name=data["name"],
            description=data.get("description", ""),
            scopes=data["scopes"],
            expires_days=data.get("expires_days"),
        )

        db.session.add(api_token)
        db.session.commit()

        current_app.logger.info(
            f"API token '{data['name']}' created for user {user.username} by {current_user.username}"
        )

        return (
            jsonify({"message": "API token created successfully", "token": plain_token, "token_id": api_token.id}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create API token: {e}")
        return jsonify({"error": "Failed to create token"}), 500


@admin_bp.route("/admin/api-tokens/<int:token_id>/toggle", methods=["POST"])
@login_required
@admin_or_permission_required("manage_api_tokens")
def toggle_api_token(token_id):
    """Toggle API token active status"""
    from app.models import ApiToken

    token = ApiToken.query.get_or_404(token_id)
    token.is_active = not token.is_active

    try:
        db.session.commit()
        status = "activated" if token.is_active else "deactivated"
        current_app.logger.info(f"API token '{token.name}' {status} by {current_user.username}")
        return jsonify({"message": f"Token {status} successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to toggle API token: {e}")
        return jsonify({"error": "Failed to update token"}), 500


@admin_bp.route("/admin/api-tokens/<int:token_id>", methods=["DELETE"])
@login_required
@admin_or_permission_required("manage_api_tokens")
def delete_api_token(token_id):
    """Delete an API token"""
    from app.models import ApiToken

    token = ApiToken.query.get_or_404(token_id)
    token_name = token.name

    try:
        db.session.delete(token)
        db.session.commit()
        current_app.logger.info(f"API token '{token_name}' deleted by {current_user.username}")
        return jsonify({"message": "Token deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete API token: {e}")
        return jsonify({"error": "Failed to delete token"}), 500
