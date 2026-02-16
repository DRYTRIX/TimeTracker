"""
Initial setup routes for TimeTracker

Handles first-time setup and telemetry opt-in.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import _
from app.utils.installation import get_installation_config
from app import log_event, db
from app.models import Settings
from app.utils.db import safe_commit
from app.utils.timezone import get_available_timezones

setup_bp = Blueprint("setup", __name__)

ALLOWED_DATE_FORMATS = ("YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY", "DD.MM.YYYY")
ROUNDING_MINUTES_MIN, ROUNDING_MINUTES_MAX = 1, 60
IDLE_TIMEOUT_MIN, IDLE_TIMEOUT_MAX = 1, 480


@setup_bp.route("/setup", methods=["GET", "POST"])
def initial_setup():
    """Initial setup page for first-time users (guided wizard)."""
    installation_config = get_installation_config()

    # If setup is already complete, redirect to dashboard
    if installation_config.is_setup_complete():
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Validation (use defaults when not provided for backwards compatibility)
        timezone = (request.form.get("timezone") or "").strip()
        if not timezone:
            timezone = "UTC"
        try:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, KeyError):
            flash(_("Invalid timezone: %(timezone)s", timezone=timezone or "(empty)"), "error")
            return _render_setup(Settings.get_settings(), get_available_timezones())

        date_fmt = request.form.get("date_format", "YYYY-MM-DD")
        if date_fmt not in ALLOWED_DATE_FORMATS:
            date_fmt = "YYYY-MM-DD"
        time_fmt = request.form.get("time_format", "24h")
        if time_fmt not in ("24h", "12h"):
            time_fmt = "24h"
        currency = (request.form.get("currency") or "").strip() or "EUR"

        try:
            rounding = int(request.form.get("rounding_minutes", 1))
            rounding = max(ROUNDING_MINUTES_MIN, min(ROUNDING_MINUTES_MAX, rounding))
        except (TypeError, ValueError):
            rounding = 1
        try:
            idle_timeout = int(request.form.get("idle_timeout_minutes", 30))
            idle_timeout = max(IDLE_TIMEOUT_MIN, min(IDLE_TIMEOUT_MAX, idle_timeout))
        except (TypeError, ValueError):
            idle_timeout = 30

        telemetry_enabled = request.form.get("telemetry_enabled") == "on"
        settings = Settings.get_settings()

        # Region & time
        settings.timezone = timezone
        settings.date_format = date_fmt
        settings.time_format = time_fmt
        settings.currency = currency

        # Company
        settings.company_name = request.form.get("company_name", "").strip() or getattr(
            settings, "company_name", "Your Company Name"
        )
        settings.company_address = request.form.get("company_address", "").strip() or getattr(
            settings, "company_address", "Your Company Address"
        )
        settings.company_email = request.form.get("company_email", "").strip() or getattr(
            settings, "company_email", "info@yourcompany.com"
        )
        settings.company_phone = (request.form.get("company_phone") or "").strip() or getattr(
            settings, "company_phone", ""
        )
        settings.company_website = (request.form.get("company_website") or "").strip() or getattr(
            settings, "company_website", ""
        )

        # System
        settings.allow_self_register = request.form.get("allow_self_register") == "on"
        settings.rounding_minutes = rounding
        settings.single_active_timer = request.form.get("single_active_timer") == "on"
        settings.idle_timeout_minutes = idle_timeout

        # Google Calendar OAuth
        google_client_id = request.form.get("google_calendar_client_id", "").strip()
        google_client_secret = request.form.get("google_calendar_client_secret", "").strip()
        if google_client_id:
            settings.google_calendar_client_id = google_client_id
        if google_client_secret:
            settings.google_calendar_client_secret = google_client_secret

        if settings not in db.session:
            db.session.add(settings)
        if not safe_commit("setup_wizard"):
            flash(_("Could not save settings. Please check server logs."), "error")
            return _render_setup(settings, get_available_timezones())

        installation_config.mark_setup_complete(telemetry_enabled=telemetry_enabled)

        log_event(
            "setup.completed",
            telemetry_enabled=telemetry_enabled,
            oauth_configured=bool(google_client_id),
        )

        if telemetry_enabled:
            flash(_("Setup complete! Thank you for helping us improve TimeTracker."), "success")
        else:
            flash(_("Setup complete! Telemetry is disabled."), "success")
        if google_client_id:
            flash(_("Google Calendar OAuth credentials have been configured."), "success")

        return redirect(url_for("main.dashboard"))

    return _render_setup(Settings.get_settings(), get_available_timezones())


def _render_setup(settings, timezones):
    """Render the setup template with settings and timezones."""
    return render_template(
        "setup/initial_setup.html",
        settings=settings,
        timezones=timezones,
    )
