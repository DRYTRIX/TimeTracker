"""
Initial setup routes for TimeTracker

Handles first-time setup and telemetry opt-in.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from flask_babel import _
from app.utils.installation import get_installation_config
from app import log_event, track_event, db
from app.models import Settings
from app.utils.db import safe_commit

setup_bp = Blueprint("setup", __name__)


@setup_bp.route("/setup", methods=["GET", "POST"])
def initial_setup():
    """Initial setup page for first-time users"""
    installation_config = get_installation_config()

    # If setup is already complete, redirect to dashboard
    if installation_config.is_setup_complete():
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Get telemetry preference
        telemetry_enabled = request.form.get("telemetry_enabled") == "on"

        # Save OAuth credentials if provided
        settings = Settings.get_settings()
        
        # Google Calendar OAuth credentials
        google_client_id = request.form.get("google_calendar_client_id", "").strip()
        google_client_secret = request.form.get("google_calendar_client_secret", "").strip()
        if google_client_id:
            settings.google_calendar_client_id = google_client_id
        if google_client_secret:
            settings.google_calendar_client_secret = google_client_secret

        # Save settings if any OAuth credentials were provided
        if google_client_id or google_client_secret:
            safe_commit("setup_oauth_credentials", {"provider": "google_calendar"})

        # Save preference
        installation_config.mark_setup_complete(telemetry_enabled=telemetry_enabled)

        # Log the setup completion
        log_event("setup.completed", telemetry_enabled=telemetry_enabled, oauth_configured=bool(google_client_id))

        # Show success message
        if telemetry_enabled:
            flash(_("Setup complete! Thank you for helping us improve TimeTracker."), "success")
        else:
            flash(_("Setup complete! Telemetry is disabled."), "success")
        
        if google_client_id:
            flash(_("Google Calendar OAuth credentials have been configured."), "success")

        return redirect(url_for("main.dashboard"))

    return render_template("setup/initial_setup.html")
