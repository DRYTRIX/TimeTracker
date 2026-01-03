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
import re
from uuid import uuid4

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
def tenants_setup():
    """Tenant setup/picker page for SaaS multi-tenant deployments."""
    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("main.dashboard"))

    # If not authenticated, show a public landing that guides users to login/self-register.
    if not (current_user and getattr(current_user, "is_authenticated", False)):
        try:
            from app.config import Config
            from app.utils.config_manager import ConfigManager

            allow_self_register = ConfigManager.get_setting("allow_self_register", Config.ALLOW_SELF_REGISTER)
        except Exception:
            allow_self_register = True

        login_url = url_for("auth.login", next=url_for("setup.tenants_setup"))
        return render_template(
            "setup/tenants.html",
            items=[],
            has_any_tenant=True,
            login_url=login_url,
            allow_self_register=allow_self_register,
        )

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

    return render_template("setup/tenants.html", items=items, has_any_tenant=has_any_tenant, login_url=None, allow_self_register=None)


def _slugify(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


@setup_bp.route("/setup/workspaces/new", methods=["GET", "POST"])
@login_required
def create_workspace():
    """Create a new workspace (tenant) in SaaS multi-tenant mode."""
    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        return render_template("setup/workspace_new.html")

    name = (request.form.get("name") or "").strip()
    slug = Tenant.normalize_slug(request.form.get("slug") or "")
    if not slug:
        slug = _slugify(name)
    if not name:
        flash(_("Workspace name is required."), "error")
        return redirect(url_for("setup.create_workspace"))

    if not slug:
        slug = f"w-{uuid4().hex[:8]}"
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    if len(slug) < 3:
        flash(_("Workspace slug must be at least 3 characters."), "error")
        return redirect(url_for("setup.create_workspace"))

    existing = Tenant.query.filter_by(slug=slug).first()
    if existing:
        flash(_("That workspace slug is already taken."), "error")
        return redirect(url_for("setup.create_workspace"))

    tenant = Tenant(
        slug=slug,
        name=name,
        created_by_user_id=current_user.id,
        primary_owner_user_id=current_user.id,
    )
    db.session.add(tenant)
    db.session.commit()

    # Owner membership
    if not TenantMember.query.filter_by(tenant_id=tenant.id, user_id=current_user.id).first():
        db.session.add(TenantMember(tenant_id=tenant.id, user_id=current_user.id, role="owner"))

    # Bootstrap tenant settings
    if not Settings.query.filter_by(tenant_id=tenant.id).first():
        db.session.add(Settings(tenant_id=tenant.id))

    # Bootstrap billing row (status finalized by Stripe webhook)
    from app.models import TenantBilling

    if not TenantBilling.query.filter_by(tenant_id=tenant.id).first():
        db.session.add(TenantBilling(tenant_id=tenant.id, tier="basic", seat_quantity=1, status=None))

    db.session.commit()

    prefix = (current_app.config.get("TENANT_PATH_PREFIX") or "/t").rstrip("/") or "/t"
    # Go to org-size selection (Toggl-like onboarding step)
    return redirect(f"{prefix}/{tenant.slug}/billing/org-size")
