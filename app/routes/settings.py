"""
Settings Routes
Handles user and system settings
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db, track_page_view
from app.utils.db import safe_commit
from app.utils.keyboard_shortcuts_defaults import merge_overrides, validate_overrides

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
@login_required
def index():
    """Settings hub — canonical user settings are at user.settings (same path, registered first)."""
    track_page_view("settings_index")
    return redirect(url_for("user.settings"))


@settings_bp.route("/settings/keyboard-shortcuts")
@login_required
def keyboard_shortcuts():
    """Keyboard shortcuts settings"""
    track_page_view("settings_keyboard_shortcuts")
    return render_template("settings/keyboard_shortcuts.html")


@settings_bp.route("/settings/profile")
@login_required
def profile():
    """User profile settings"""
    track_page_view("settings_profile")
    return redirect(url_for("profile.index"))


@settings_bp.route("/settings/preferences")
@login_required
def preferences():
    """User preferences — canonical page is user.settings (profile, notifications, theme, etc.)."""
    track_page_view("settings_preferences")
    flash(_("Your preferences are managed on the main Settings page."), "info")
    return redirect(url_for("user.settings"))


# ----- Keyboard shortcuts API (JSON) -----


def _keyboard_shortcuts_config():
    """Build { shortcuts, overrides } for current user."""
    overrides = getattr(current_user, "keyboard_shortcuts_overrides", None) or {}
    shortcuts = merge_overrides(overrides)
    return {"shortcuts": shortcuts, "overrides": overrides}


@settings_bp.route("/api/settings/keyboard-shortcuts", methods=["GET"])
@login_required
def api_keyboard_shortcuts_get():
    """GET current keyboard shortcut config (defaults + user overrides)."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(_keyboard_shortcuts_config())


@settings_bp.route("/api/settings/keyboard-shortcuts", methods=["POST"])
@login_required
def api_keyboard_shortcuts_save():
    """POST to save user overrides. Body: { \"overrides\": { \"id\": \"key\", ... } }."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    overrides = data.get("overrides")
    if overrides is not None and not isinstance(overrides, dict):
        return jsonify({"error": "overrides must be an object"}), 400
    overrides = overrides or {}
    ok, err, merged, overrides_to_save = validate_overrides(overrides)
    if not ok:
        return jsonify({"error": err}), 400
    current_user.keyboard_shortcuts_overrides = overrides_to_save
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    return jsonify(_keyboard_shortcuts_config())


@settings_bp.route("/api/settings/keyboard-shortcuts/reset", methods=["POST"])
@login_required
def api_keyboard_shortcuts_reset():
    """POST to reset keyboard shortcuts to defaults."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    current_user.keyboard_shortcuts_overrides = None
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    return jsonify(_keyboard_shortcuts_config())
