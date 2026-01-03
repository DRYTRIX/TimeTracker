"""
Settings Routes
Handles user and system settings
"""

import re
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, jsonify, g
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db, track_page_view
from app.utils.db import safe_commit
from app.models import Settings, Tenant, TenantBilling, TenantMember

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


@settings_bp.route("/settings/tenants")
@login_required
def tenants():
    """List tenants the current user belongs to and provide switch links."""
    track_page_view("settings_tenants")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    # Build "internal" dashboard path without current script_root (/t/<current>)
    dashboard_url = url_for("main.dashboard")
    script_root = (request.script_root or "").rstrip("/")
    if script_root and dashboard_url.startswith(script_root + "/"):
        internal_path = dashboard_url[len(script_root) :]
    elif script_root and dashboard_url == script_root:
        internal_path = "/"
    else:
        internal_path = dashboard_url

    prefix = (current_app.config.get("TENANT_PATH_PREFIX") or "/t").rstrip("/") or "/t"

    memberships = (
        TenantMember.query.join(Tenant, Tenant.id == TenantMember.tenant_id)
        .filter(TenantMember.user_id == current_user.id)
        .order_by(Tenant.slug.asc())
        .all()
    )

    current_tenant_id = getattr(getattr(g, "tenant", None), "id", None)
    items = []
    for m in memberships:
        t = m.tenant
        if not t:
            continue
        switch_url = f"{prefix}/{t.slug}{internal_path}"
        owners_count = 0
        try:
            owners_count = TenantMember.query.filter_by(tenant_id=t.id, role="owner").count()
        except Exception:
            owners_count = 0
        can_leave = True
        if m.role == "owner" and owners_count <= 1:
            can_leave = False
        items.append(
            {
                "tenant": t,
                "role": m.role,
                "is_current": bool(current_tenant_id and t.id == current_tenant_id),
                "switch_url": switch_url,
                "leave_url": url_for("settings.leave_tenant", tenant_id=t.id),
                "can_leave": can_leave,
            }
        )

    return render_template("settings/tenants.html", items=items, current_tenant_id=current_tenant_id)


def _slugify(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


@settings_bp.route("/settings/tenants/new", methods=["GET", "POST"])
@login_required
def create_tenant():
    track_page_view("settings_tenants_create")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    if request.method == "GET":
        return render_template("settings/tenants_new.html")

    name = (request.form.get("name") or "").strip()
    slug = Tenant.normalize_slug(request.form.get("slug") or "")
    if not slug:
        slug = _slugify(name)
    if not name:
        flash(_("Tenant name is required."), "error")
        return redirect(url_for("settings.create_tenant"))

    if not slug:
        slug = f"t-{uuid4().hex[:8]}"

    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    if len(slug) < 3:
        flash(_("Tenant slug must be at least 3 characters."), "error")
        return redirect(url_for("settings.create_tenant"))

    existing = Tenant.query.filter_by(slug=slug).first()
    if existing:
        flash(_("That tenant slug is already taken."), "error")
        return redirect(url_for("settings.create_tenant"))

    tenant = Tenant(
        slug=slug,
        name=name,
        created_by_user_id=current_user.id,
        primary_owner_user_id=current_user.id,
    )
    db.session.add(tenant)
    db.session.commit()

    # Create owner membership
    if not TenantMember.query.filter_by(tenant_id=tenant.id, user_id=current_user.id).first():
        db.session.add(TenantMember(tenant_id=tenant.id, user_id=current_user.id, role="owner"))

    # Bootstrap tenant settings row
    if not Settings.query.filter_by(tenant_id=tenant.id).first():
        db.session.add(Settings(tenant_id=tenant.id))

    # Bootstrap billing row (status empty => gated by grace days / checkout)
    if not TenantBilling.query.filter_by(tenant_id=tenant.id).first():
        db.session.add(TenantBilling(tenant_id=tenant.id, tier="basic", seat_quantity=1, status=None))

    db.session.commit()

    # Targeted audit log (best-effort)
    try:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=current_user.id,
            action="created",
            entity_type="tenant",
            entity_id=tenant.id,
            entity_name=tenant.slug,
            change_description=f"Created tenant '{tenant.slug}'",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            request_path=request.path,
        )
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    try:
        flash(_("Tenant created."), "success")
    except Exception:
        pass

    prefix = (current_app.config.get("TENANT_PATH_PREFIX") or "/t").rstrip("/") or "/t"
    return redirect(f"{prefix}/{tenant.slug}/billing/org-size")


@settings_bp.route("/settings/tenants/<int:tenant_id>/leave", methods=["POST"])
@login_required
def leave_tenant(tenant_id: int):
    track_page_view("settings_tenants_leave")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    membership = TenantMember.query.filter_by(tenant_id=tenant_id, user_id=current_user.id).first()
    if not membership:
        return redirect("/settings/tenants")

    if membership.role == "owner":
        owners_count = 0
        try:
            owners_count = TenantMember.query.filter_by(tenant_id=tenant_id, role="owner").count()
        except Exception:
            owners_count = 0
        if owners_count <= 1:
            flash(_("You cannot leave as the last owner. Transfer ownership first."), "error")
            return redirect("/settings/tenants")

    # Audit before delete
    try:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=current_user.id,
            action="deleted",
            entity_type="tenant_member",
            entity_id=membership.id,
            entity_name=str(tenant_id),
            change_description=f"Left tenant_id={tenant_id}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            request_path=request.path,
        )
    except Exception:
        pass

    db.session.delete(membership)
    db.session.commit()
    flash(_("You left the tenant."), "success")
    return redirect("/settings/tenants")


@settings_bp.route("/settings/tenants/<int:tenant_id>/danger", methods=["GET"])
@login_required
def tenant_danger(tenant_id: int):
    track_page_view("settings_tenants_danger")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    tenant = Tenant.query.filter_by(id=tenant_id).first()
    if not tenant:
        return redirect("/settings/tenants")

    # Only owners (or global admins) can delete
    is_global_admin = bool(getattr(current_user, "is_admin", False))
    if not getattr(current_user, "is_admin", False):
        m = TenantMember.query.filter_by(tenant_id=tenant_id, user_id=current_user.id).first()
        if not m or m.role != "owner":
            return redirect("/settings/tenants")

    billing = TenantBilling.query.filter_by(tenant_id=tenant_id).first()
    prefix = (current_app.config.get("TENANT_PATH_PREFIX") or "/t").rstrip("/") or "/t"
    billing_url = f"{prefix}/{tenant.slug}/billing"
    return render_template(
        "settings/tenant_danger.html",
        tenant=tenant,
        billing=billing,
        billing_url=billing_url,
        is_global_admin=is_global_admin,
    )


@settings_bp.route("/settings/tenants/<int:tenant_id>/restore", methods=["POST"])
@login_required
def restore_tenant(tenant_id: int):
    track_page_view("settings_tenants_restore")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    # Admin-only restore
    if not getattr(current_user, "is_admin", False):
        return redirect("/settings/tenants")

    tenant = Tenant.query.filter_by(id=tenant_id).first()
    if not tenant:
        return redirect("/settings/tenants")

    confirm = (request.form.get("confirm_slug") or "").strip().lower()
    if confirm != (tenant.slug or "").strip().lower():
        flash(_("Type the tenant slug to confirm restore."), "error")
        return redirect(url_for("settings.tenant_danger", tenant_id=tenant_id))

    old_status = tenant.status
    tenant.status = "active"
    db.session.commit()

    try:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=current_user.id,
            action="updated",
            entity_type="tenant",
            entity_id=tenant.id,
            field_name="status",
            old_value=old_status,
            new_value=tenant.status,
            entity_name=tenant.slug,
            change_description=f"Restored tenant '{tenant.slug}'",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            request_path=request.path,
        )
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    flash(_("Tenant restored."), "success")
    return redirect("/settings/tenants")


@settings_bp.route("/settings/tenants/<int:tenant_id>/suspend", methods=["POST"])
@login_required
def suspend_tenant(tenant_id: int):
    track_page_view("settings_tenants_suspend")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    tenant = Tenant.query.filter_by(id=tenant_id).first()
    if not tenant:
        return redirect("/settings/tenants")

    if not getattr(current_user, "is_admin", False):
        m = TenantMember.query.filter_by(tenant_id=tenant_id, user_id=current_user.id).first()
        if not m or m.role != "owner":
            return redirect("/settings/tenants")

    confirm = (request.form.get("confirm_slug") or "").strip().lower()
    if confirm != (tenant.slug or "").strip().lower():
        flash(_("Type the tenant slug to confirm suspension."), "error")
        return redirect(url_for("settings.tenant_danger", tenant_id=tenant_id))

    old_status = tenant.status
    if (tenant.status or "").lower() != "deleted":
        tenant.status = "suspended"
        db.session.commit()

        try:
            from app.models.audit_log import AuditLog

            AuditLog.log_change(
                user_id=current_user.id,
                action="updated",
                entity_type="tenant",
                entity_id=tenant.id,
                field_name="status",
                old_value=old_status,
                new_value=tenant.status,
                entity_name=tenant.slug,
                change_description=f"Suspended tenant '{tenant.slug}'",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                request_path=request.path,
            )
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        flash(_("Tenant suspended."), "success")
    return redirect("/settings/tenants")


@settings_bp.route("/settings/tenants/<int:tenant_id>/reactivate", methods=["POST"])
@login_required
def reactivate_tenant(tenant_id: int):
    track_page_view("settings_tenants_reactivate")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    tenant = Tenant.query.filter_by(id=tenant_id).first()
    if not tenant:
        return redirect("/settings/tenants")

    if not getattr(current_user, "is_admin", False):
        m = TenantMember.query.filter_by(tenant_id=tenant_id, user_id=current_user.id).first()
        if not m or m.role != "owner":
            return redirect("/settings/tenants")

    old_status = tenant.status
    if (tenant.status or "").lower() != "deleted":
        tenant.status = "active"
        db.session.commit()

        try:
            from app.models.audit_log import AuditLog

            AuditLog.log_change(
                user_id=current_user.id,
                action="updated",
                entity_type="tenant",
                entity_id=tenant.id,
                field_name="status",
                old_value=old_status,
                new_value=tenant.status,
                entity_name=tenant.slug,
                change_description=f"Reactivated tenant '{tenant.slug}'",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                request_path=request.path,
            )
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        flash(_("Tenant reactivated."), "success")
    return redirect("/settings/tenants")


@settings_bp.route("/settings/tenants/<int:tenant_id>/delete", methods=["POST"])
@login_required
def delete_tenant(tenant_id: int):
    track_page_view("settings_tenants_delete")

    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return redirect(url_for("settings.index"))

    tenant = Tenant.query.filter_by(id=tenant_id).first()
    if not tenant:
        return redirect("/settings/tenants")

    # Only owners (or global admins) can delete
    if not getattr(current_user, "is_admin", False):
        m = TenantMember.query.filter_by(tenant_id=tenant_id, user_id=current_user.id).first()
        if not m or m.role != "owner":
            return redirect("/settings/tenants")

    confirm = (request.form.get("confirm_slug") or "").strip().lower()
    if confirm != (tenant.slug or "").strip().lower():
        flash(_("Type the tenant slug to confirm deletion."), "error")
        return redirect(url_for("settings.tenant_danger", tenant_id=tenant_id))

    billing = TenantBilling.query.filter_by(tenant_id=tenant_id).first()
    # Safety: don't allow deletion while a paid period is active.
    try:
        if billing and billing.current_period_end and billing.current_period_end > datetime.utcnow():
            flash(_("Cancel the subscription and wait for the period to end before deleting."), "error")
            return redirect(url_for("settings.tenant_danger", tenant_id=tenant_id))
    except Exception:
        pass

    old_status = tenant.status
    tenant.status = "deleted"
    db.session.commit()

    try:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=current_user.id,
            action="updated",
            entity_type="tenant",
            entity_id=tenant.id,
            field_name="status",
            old_value=old_status,
            new_value="deleted",
            entity_name=tenant.slug,
            change_description=f"Deleted tenant '{tenant.slug}'",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            request_path=request.path,
        )
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    flash(_("Tenant deleted."), "success")
    return redirect("/settings/tenants")
