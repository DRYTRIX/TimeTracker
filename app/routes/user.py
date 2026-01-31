"""User profile and settings routes"""

import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Activity
from app.utils.db import safe_commit
from flask_babel import gettext as _
import pytz
from app.utils.timezone import get_available_timezones

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

user_bp = Blueprint("user", __name__)


@user_bp.route("/profile")
@login_required
def profile():
    """User profile page"""
    # Get user statistics
    total_hours = current_user.total_hours
    active_timer = current_user.active_timer
    recent_entries = current_user.get_recent_entries(limit=10)

    # Get recent activities
    recent_activities = Activity.get_recent(user_id=current_user.id, limit=20)

    return render_template(
        "user/profile.html",
        user=current_user,
        total_hours=total_hours,
        active_timer=active_timer,
        recent_entries=recent_entries,
        recent_activities=recent_activities,
    )


@user_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings and preferences page"""
    if request.method == "POST":
        try:
            # Notification preferences
            current_user.email_notifications = "email_notifications" in request.form
            current_user.notification_overdue_invoices = "notification_overdue_invoices" in request.form
            current_user.notification_task_assigned = "notification_task_assigned" in request.form
            current_user.notification_task_comments = "notification_task_comments" in request.form
            current_user.notification_weekly_summary = "notification_weekly_summary" in request.form

            # Profile information
            full_name = request.form.get("full_name", "").strip()
            if full_name:
                current_user.full_name = full_name

            email = request.form.get("email", "").strip()
            if email:
                current_user.email = email

            # Display preferences
            theme_preference = request.form.get("theme_preference")
            if theme_preference in ["light", "dark", None, ""]:
                current_user.theme_preference = theme_preference if theme_preference else None

            # Regional settings
            timezone = request.form.get("timezone")
            if timezone is not None:
                timezone = timezone.strip()
                if timezone == "":
                    current_user.timezone = None
                else:
                    try:
                        # Validate timezone
                        pytz.timezone(timezone)
                        current_user.timezone = timezone
                    except pytz.exceptions.UnknownTimeZoneError:
                        flash(_("Invalid timezone selected"), "error")
                        return redirect(url_for("user.settings"))

            date_format = request.form.get("date_format")
            if date_format:
                current_user.date_format = date_format

            time_format = request.form.get("time_format")
            if time_format in ["12h", "24h"]:
                current_user.time_format = time_format

            week_start_day = request.form.get("week_start_day", type=int)
            if week_start_day is not None and 0 <= week_start_day <= 6:
                current_user.week_start_day = week_start_day

            # Language preference
            preferred_language = request.form.get("preferred_language")
            if preferred_language is not None:  # Allow empty string to clear preference
                current_user.preferred_language = preferred_language if preferred_language else None
                # Also update session for immediate effect
                from flask import session
                if preferred_language:
                    session["preferred_language"] = preferred_language
                    session.permanent = True
                    session.modified = True
                else:
                    session.pop("preferred_language", None)
                    session.modified = True

            # Time rounding preferences
            current_user.time_rounding_enabled = "time_rounding_enabled" in request.form

            time_rounding_minutes = request.form.get("time_rounding_minutes", type=int)
            if time_rounding_minutes and time_rounding_minutes in [1, 5, 10, 15, 30, 60]:
                current_user.time_rounding_minutes = time_rounding_minutes

            time_rounding_method = request.form.get("time_rounding_method")
            if time_rounding_method in ["nearest", "up", "down"]:
                current_user.time_rounding_method = time_rounding_method

            # Overtime settings
            standard_hours_per_day = request.form.get("standard_hours_per_day", type=float)
            if standard_hours_per_day is not None:
                # Validate range (0.5 to 24 hours)
                if 0.5 <= standard_hours_per_day <= 24:
                    current_user.standard_hours_per_day = standard_hours_per_day
                else:
                    flash(_("Standard hours per day must be between 0.5 and 24"), "error")
                    return redirect(url_for("user.settings"))

            # Save changes
            if safe_commit(db.session):
                # Log activity
                Activity.log(
                    user_id=current_user.id,
                    action="updated",
                    entity_type="user",
                    entity_id=current_user.id,
                    entity_name=current_user.username,
                    description="Updated user settings",
                )

                flash(_("Settings saved successfully"), "success")
            else:
                flash(_("Error saving settings"), "error")

        except Exception as e:
            flash(_("Error saving settings: %(error)s", error=str(e)), "error")
            db.session.rollback()

        return redirect(url_for("user.settings"))

    # Get all available timezones
    timezones = get_available_timezones()

    # Get available languages from config
    from flask import current_app

    languages = current_app.config.get(
        "LANGUAGES",
        {"en": "English", "nl": "Nederlands", "de": "Deutsch", "fr": "Français", "it": "Italiano", "fi": "Suomi"},
    )

    # Get time rounding options
    from app.utils.time_rounding import get_available_rounding_intervals, get_available_rounding_methods

    rounding_intervals = get_available_rounding_intervals()
    rounding_methods = get_available_rounding_methods()

    return render_template(
        "user/settings.html",
        user=current_user,
        timezones=timezones,
        languages=languages,
        rounding_intervals=rounding_intervals,
        rounding_methods=rounding_methods,
    )


@user_bp.route("/api/preferences", methods=["PATCH"])
@login_required
def update_preferences():
    """API endpoint to update user preferences (for AJAX calls)"""
    try:
        data = request.get_json()

        if "theme_preference" in data:
            theme = data["theme_preference"]
            if theme in ["light", "dark", "system", None, ""]:
                current_user.theme_preference = theme if theme and theme != "system" else None

        if "email_notifications" in data:
            current_user.email_notifications = bool(data["email_notifications"])

        if "timezone" in data:
            tz_value = data["timezone"]
            if tz_value in [None, "", "system"]:
                current_user.timezone = None
            else:
                try:
                    pytz.timezone(tz_value)
                    current_user.timezone = tz_value
                except pytz.exceptions.UnknownTimeZoneError:
                    return jsonify({"error": "Invalid timezone"}), 400

        for key, attr in (
            ("calendar_color_events", "calendar_color_events"),
            ("calendar_color_tasks", "calendar_color_tasks"),
            ("calendar_color_time_entries", "calendar_color_time_entries"),
        ):
            if key in data:
                val = data[key]
                if val is None or val == "":
                    setattr(current_user, attr, None)
                elif isinstance(val, str) and HEX_COLOR_RE.match(val):
                    setattr(current_user, attr, val)
                else:
                    return jsonify({"error": f"Invalid {key}: must be null or hex color (#RRGGBB)"}), 400

        db.session.commit()

        return jsonify({"success": True, "message": _("Preferences updated")})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@user_bp.route("/api/theme", methods=["POST"])
@login_required
def set_theme():
    """Quick API endpoint to set theme (for theme switcher)"""
    try:
        data = request.get_json()
        theme = data.get("theme")

        if theme in ["light", "dark", None, ""]:
            current_user.theme_preference = theme if theme else None
            db.session.commit()

            return jsonify({"success": True, "theme": current_user.theme_preference or "system"})

        return jsonify({"error": "Invalid theme"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@user_bp.route("/api/language", methods=["POST"])
@login_required
def set_language():
    """Quick API endpoint to set language (for language switcher)"""
    from flask import current_app, session

    try:
        data = request.get_json()
        language = data.get("language")

        # Get available languages from config
        available_languages = current_app.config.get("LANGUAGES", {})

        if language in available_languages:
            # Update user preference
            current_user.preferred_language = language
            db.session.commit()

            # Also set in session for immediate effect
            session["preferred_language"] = language

            return jsonify({"success": True, "language": language, "message": _("Language updated successfully")})

        return jsonify({"error": _("Invalid language")}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@user_bp.route("/set-language/<language>")
def set_language_direct(language):
    """Direct route to set language (for non-JS fallback)"""
    from flask import current_app, session

    # Get available languages from config
    available_languages = current_app.config.get("LANGUAGES", {})

    if language in available_languages:
        # Set in session for immediate effect
        session["preferred_language"] = language

        # If user is logged in, update their preference
        if current_user.is_authenticated:
            current_user.preferred_language = language
            db.session.commit()
            flash(_("Language updated to %(language)s", language=available_languages[language]), "success")

        # Redirect back to referring page or dashboard
        next_page = request.referrer or url_for("main.dashboard")
        return redirect(next_page)

    flash(_("Invalid language"), "error")
    return redirect(url_for("main.dashboard"))
