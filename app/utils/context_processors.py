import json
from datetime import datetime

from flask import current_app, g, request, session, url_for
from flask_babel import get_locale
from flask_babel import gettext as _
from flask_login import current_user

from app.models import Settings
from app.utils.license_utils import is_license_activated
from app.utils.timezone import (
    get_resolved_date_format_key,
    get_resolved_time_format_key,
    get_resolved_week_start_day,
    get_timezone_offset_for_timezone,
)


def register_context_processors(app):
    """Register context processors for the application"""

    # Register permission helpers for templates
    from app.utils.permissions import init_permission_helpers

    init_permission_helpers(app)

    @app.context_processor
    def inject_settings():
        """Inject settings into all templates"""
        try:
            from app import db

            # Check if we have an active database session
            if db.session.is_active:
                settings = Settings.get_settings()
                resolved_date = get_resolved_date_format_key()
                resolved_time = get_resolved_time_format_key()
                resolved_week_start = get_resolved_week_start_day()
                return {
                    "settings": settings,
                    "currency": settings.currency,
                    "timezone": settings.timezone,
                    "resolved_date_format_key": resolved_date,
                    "resolved_time_format_key": resolved_time,
                    "resolved_week_start_day": resolved_week_start,
                    "is_license_activated": is_license_activated(settings),
                }
        except Exception as e:
            # Log the error but continue with defaults
            print(f"Warning: Could not inject settings: {e}")
            # Rollback the failed transaction
            try:
                from app import db

                db.session.rollback()
            except Exception:
                pass
            pass

        # Return defaults if settings not available (resolved keys still work without db)
        try:
            resolved_date = get_resolved_date_format_key()
            resolved_time = get_resolved_time_format_key()
            resolved_week_start = get_resolved_week_start_day()
        except Exception:
            resolved_date = "YYYY-MM-DD"
            resolved_time = "24h"
            resolved_week_start = 1
        return {
            "settings": None,
            "currency": "EUR",
            "timezone": "Europe/Rome",
            "resolved_date_format_key": resolved_date,
            "resolved_time_format_key": resolved_time,
            "resolved_week_start_day": resolved_week_start,
            "is_license_activated": False,
        }

    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates"""
        try:
            from app import db

            # Check if we have an active database session
            if db.session.is_active:
                settings = Settings.get_settings()
                timezone_name = settings.timezone if settings else "Europe/Rome"
            else:
                timezone_name = "Europe/Rome"
        except Exception as e:
            # Log the error but continue with defaults
            print(f"Warning: Could not inject globals: {e}")
            # Rollback the failed transaction
            try:
                from app import db

                db.session.rollback()
            except Exception:
                pass
            timezone_name = "Europe/Rome"

        # Resolve user-specific timezone, falling back to application timezone
        user_timezone = timezone_name
        try:
            if (
                current_user
                and getattr(current_user, "is_authenticated", False)
                and getattr(current_user, "timezone", None)
            ):
                user_timezone = current_user.timezone
        except Exception:
            pass

        # Determine app version from setup.py (single source of truth)
        try:
            import os

            from app.config.analytics_defaults import get_version_from_setup

            # Get version from setup.py
            version_value = get_version_from_setup()

            # If version is "unknown", fall back to environment variable for dev mode
            if version_value == "unknown":
                env_version = os.getenv("APP_VERSION")
                if env_version:
                    version_value = env_version
                else:
                    # Last resort: use "dev-0" for development
                    version_value = "dev-0"

            # Strip any leading 'v' prefix to avoid double 'v' in template (e.g., vv3.5.0)
            if version_value and version_value.startswith("v"):
                version_value = version_value[1:]
        except Exception:
            # Fallback if anything goes wrong
            version_value = "dev-0"

        # Current locale code (e.g., 'en', 'de')
        try:
            current_locale = str(get_locale())
        except Exception:
            current_locale = "en"
        # Normalize to short code for comparisons (e.g., 'en' from 'en_US')
        short_locale = current_locale.split("_", 1)[0] if current_locale else "en"

        # Reverse-map normalized locale codes back to config keys for label lookup
        # 'nb' (used by Flask-Babel) should map back to 'no' (used in LANGUAGES config)
        display_locale = short_locale
        if short_locale == "nb":
            display_locale = "no"

        available_languages = current_app.config.get("LANGUAGES", {}) or {}
        current_language_label = available_languages.get(display_locale, short_locale.upper())

        # Check if current language is RTL
        rtl_languages = current_app.config.get("RTL_LANGUAGES", set())
        is_rtl = short_locale in rtl_languages

        support_purchase_url = current_app.config.get(
            "SUPPORT_PURCHASE_URL", "https://timetracker.drytrix.com/support.html"
        )

        # User stats and support banner suppression for smart prompts (authenticated users only)
        user_stats = None
        support_banner_suppressed = False
        support_ab_variant = "control"
        if getattr(current_user, "is_authenticated", False):
            try:
                from app.models import DonationInteraction

                user_stats = DonationInteraction.get_user_engagement_metrics(current_user.id)
                support_banner_suppressed = DonationInteraction.has_recent_donation_click(current_user.id, days=30)
                # Stable A/B variant per user for support CTA experiments (control | key_first | cta_alt)
                support_ab_variant = ("control", "key_first", "cta_alt")[current_user.id % 3]
            except Exception:
                user_stats = {}
                support_banner_suppressed = False

        is_admin_user = bool(
            getattr(current_user, "is_authenticated", False) and getattr(current_user, "is_admin", False)
        )

        support_ui_json = None
        layout_support_prompt = None
        support_usage_stats_modal = None
        if getattr(current_user, "is_authenticated", False):
            try:
                from app.config.support_ui import (
                    build_support_checkout_urls,
                    get_long_session_minutes,
                    get_social_proof_text,
                )
                from app.models import Settings
                from app.services.support_prompt_service import SupportPromptService
                from app.services.usage_stats_service import UsageStatsService
                from app.utils.license_utils import is_license_activated

                settings_obj = Settings.get_settings()
                is_supporter_instance = bool(settings_obj and is_license_activated(settings_obj))
                ui_show_donate = bool(getattr(current_user, "ui_show_donate", True))

                layout_support_prompt = SupportPromptService.consume_layout_prompt(
                    session,
                    ui_show_donate=ui_show_donate,
                    is_supporter=is_supporter_instance,
                    support_banner_suppressed=support_banner_suppressed,
                )

                usage_stats = UsageStatsService.get_for_user(current_user.id)
                support_usage_stats_modal = usage_stats
                checkout_urls = build_support_checkout_urls(current_app.config)
                social_line = get_social_proof_text(current_app.config)
                long_session_minutes = get_long_session_minutes()

                if not session.get("support_session_started_at"):
                    session["support_session_started_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

                lp_message = ""
                lp_action = _("Support")
                if layout_support_prompt:
                    v = layout_support_prompt.get("variant")
                    if v == SupportPromptService.VARIANT_AFTER_REPORT:
                        lp_message = _(
                            "That report was quick to generate. If TimeTracker saves you time, "
                            "consider supporting its development."
                        )

                support_ui_json = json.dumps(
                    {
                        "urls": checkout_urls,
                        "stats": usage_stats,
                        "socialProofLine": social_line,
                        "longSessionMinutes": long_session_minutes,
                        "isSupporter": is_supporter_instance,
                        "sessionStartedAt": session.get("support_session_started_at"),
                        "shareUrl": url_for("main.about", _external=True),
                        "trackUrl": url_for("main.track_support_event"),
                        "softPromptUrl": url_for("main.request_soft_support_prompt"),
                        "layoutPrompt": (
                            {
                                "variant": layout_support_prompt.get("variant"),
                                "message": lp_message,
                                "actionLabel": lp_action,
                            }
                            if layout_support_prompt
                            else None
                        ),
                        "i18n": {
                            "offlineNote": _("You appear to be offline. Reconnect to open donation or checkout links."),
                            "shareSuccess": _("Link copied to clipboard"),
                            "shareFail": _("Could not copy link"),
                            "supportAction": _("Support"),
                            "longSessionToast": _(
                                "You have been using TimeTracker actively for a while. "
                                "If it helps your work, consider supporting its development."
                            ),
                        },
                    },
                    ensure_ascii=False,
                )
            except Exception:
                support_ui_json = None
                layout_support_prompt = None
                support_usage_stats_modal = None

        return {
            "app_name": "Time Tracker",
            "app_version": version_value,
            "is_admin_user": is_admin_user,
            "timezone": timezone_name,
            "timezone_offset": get_timezone_offset_for_timezone(timezone_name),
            "user_timezone": user_timezone,
            "current_locale": current_locale,
            "current_language_code": display_locale,  # Use display locale (e.g., 'no' not 'nb')
            "current_language_label": current_language_label,
            "is_rtl": is_rtl,
            "available_languages": available_languages,
            "config": current_app.config,
            "support_purchase_url": support_purchase_url,
            "user_stats": user_stats,
            "support_banner_suppressed": support_banner_suppressed,
            "support_ab_variant": support_ab_variant,
            "support_ui_json": support_ui_json,
            "layout_support_prompt": layout_support_prompt,
            "support_usage_stats_modal": support_usage_stats_modal,
        }

    @app.context_processor
    def inject_keyboard_shortcuts_config():
        """Inject keyboard shortcut config for logged-in users (for keyboard-shortcuts-advanced.js)."""
        try:
            if getattr(current_user, "is_authenticated", False):
                from app.utils.keyboard_shortcuts_defaults import merge_overrides

                overrides = getattr(current_user, "keyboard_shortcuts_overrides", None) or {}
                shortcuts = merge_overrides(overrides)
                return {"keyboard_shortcuts_config": {"shortcuts": shortcuts, "overrides": overrides}}
        except Exception:
            pass
        return {"keyboard_shortcuts_config": None}

    @app.before_request
    def before_request():
        """Set up request-specific data"""
        g.request_start_time = request.start_time if hasattr(request, "start_time") else None
