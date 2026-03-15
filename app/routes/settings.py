"""
Settings Routes
Handles user and system settings
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db, track_page_view
from app.utils.db import safe_commit

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
@login_required
def index():
    """Main settings page"""
    track_page_view("settings_index")
    return render_template("settings/index.html")


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
    """User preferences"""
    track_page_view("settings_preferences")
    return render_template("settings/preferences.html")
