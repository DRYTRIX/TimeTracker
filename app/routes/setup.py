"""
Initial setup routes for TimeTracker

Handles first-time setup and telemetry opt-in.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from flask_babel import _
from app.utils.installation import get_installation_config
from app import log_event, track_event, db
from app.models import Settings, Tenant, TenantMember
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

        # In SaaS multi-tenant mode, integration credentials are tenant-scoped and should
        # be configured per-tenant (not during global installation setup).
        saas_enabled = bool(current_app.config.get("SAAS_MODE")) and (current_app.config.get("TENANCY_MODE") == "multi")
        google_client_id = ""
        if not saas_enabled:
            # Save OAuth credentials if provided (single-tenant installs only)
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

        # In SaaS multi-tenant mode, send users to the tenant picker/creation flow.
        if saas_enabled:
            return redirect(url_for("setup.tenants_setup"))
        return redirect(url_for("main.dashboard"))

    return render_template("setup/initial_setup.html")


@setup_bp.route("/setup/tenants", methods=["GET"])
@login_required
def tenants_setup():
    """Tenant setup/picker page for SaaS multi-tenant deployments."""
    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("main.dashboard"))

    prefix = (current_app.config.get("TENANT_PATH_PREFIX") or "/t").rstrip("/") or "/t"
    memberships = (
        TenantMember.query.join(Tenant, Tenant.id == TenantMember.tenant_id)
        .filter(TenantMember.user_id == current_user.id)
        .order_by(Tenant.slug.asc())
        .all()
    )

    # Target internal dashboard path (no script_root)
    dashboard_url = url_for("main.dashboard")
    script_root = (request.script_root or "").rstrip("/")
    if script_root and dashboard_url.startswith(script_root + "/"):
        internal_path = dashboard_url[len(script_root) :]
    elif script_root and dashboard_url == script_root:
        internal_path = "/"
    else:
        internal_path = dashboard_url

    items = []
    for m in memberships:
        t = m.tenant
        if not t:
            continue
        items.append(
            {
                "tenant": t,
                "role": m.role,
                "switch_url": f"{prefix}/{t.slug}{internal_path}",
            }
        )

    # Show if this is the first tenant in the whole system (useful for system admin)
    has_any_tenant = True
    try:
        has_any_tenant = Tenant.query.first() is not None
    except Exception:
        has_any_tenant = True

    return render_template("setup/tenants.html", items=items, has_any_tenant=has_any_tenant)
