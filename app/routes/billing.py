"""SaaS tenant billing (Stripe subscriptions)."""

import json
from datetime import datetime

import stripe
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import StripeEvent, TenantBilling, TenantInvite, TenantMember, User


def _owners_count(tenant_id: int) -> int:
    try:
        return TenantMember.query.filter_by(tenant_id=tenant_id, role="owner").count()
    except Exception:
        return 0


billing_bp = Blueprint("billing", __name__)


def _require_saas_enabled():
    if not (current_app.config.get("SAAS_MODE") and current_app.config.get("TENANCY_MODE") == "multi"):
        return jsonify({"error": "saas_mode_disabled"}), 400
    return None


def _require_tenant_admin():
    from flask import g

    if not getattr(g, "tenant", None):
        return jsonify({"error": "tenant_missing"}), 400
    # Global admin can always manage billing
    if getattr(current_user, "is_admin", False):
        return None
    m = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
    if not m or m.role not in ("owner", "admin"):
        return jsonify({"error": "tenant_admin_required"}), 403
    return None


def _require_tenant_member():
    """Require that the current user is at least a member of the current tenant."""
    from flask import g

    if not getattr(g, "tenant", None):
        return jsonify({"error": "tenant_missing"}), 400
    if getattr(current_user, "is_admin", False):
        return None
    m = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
    if not m:
        return jsonify({"error": "tenant_member_required"}), 403
    return None


def _stripe_config():
    secret = current_app.config.get("STRIPE_SECRET_KEY") or ""
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET") or ""
    prices = {
        "basic": current_app.config.get("STRIPE_PRICE_BASIC") or "",
        "team": current_app.config.get("STRIPE_PRICE_TEAM") or "",
        "pro": current_app.config.get("STRIPE_PRICE_PRO") or "",
    }
    return secret, webhook_secret, prices


def _tier_from_price_id(price_id: str) -> str | None:
    try:
        _secret, _whsec, prices = _stripe_config()
        for tier, pid in prices.items():
            if pid and pid == price_id:
                return tier
    except Exception:
        pass
    return None


def _wants_json() -> bool:
    try:
        return bool(
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.accept_mimetypes["application/json"] >= request.accept_mimetypes["text/html"]
        )
    except Exception:
        return False


@billing_bp.route("/billing", methods=["GET"])
@login_required
def billing_home():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g
    from app.utils.saas_limits import get_effective_seat_limit

    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    members_count = TenantMember.query.filter_by(tenant_id=g.tenant.id).count()
    seat_limit = get_effective_seat_limit(g.tenant.id)

    payload = {
        "tenant": g.tenant.slug,
        "billing": None
        if not billing
        else {
            "tier": billing.tier,
            "seat_quantity": billing.seat_quantity,
            "status": billing.status,
            "current_period_end": billing.current_period_end.isoformat() if billing.current_period_end else None,
            "cancel_at_period_end": billing.cancel_at_period_end,
        },
        "members": members_count,
        "seat_limit": seat_limit,
    }

    if _wants_json():
        return jsonify(payload)

    # First-time onboarding: require choosing org size / plan before using billing index.
    # (Billing status is finalized by webhooks; status None means checkout not completed yet.)
    if not billing or not (billing.status or "").strip():
        return render_template(
            "billing/org_size.html",
            tenant=g.tenant,
            billing=billing,
            members_count=members_count,
            seat_limit=seat_limit,
            mode="onboarding",
        )

    return render_template(
        "billing/index.html",
        tenant=g.tenant,
        billing=billing,
        members_count=members_count,
        seat_limit=seat_limit,
    )


@billing_bp.route("/billing/org-size", methods=["GET"])
@login_required
def billing_org_size():
    """Choose/upgrade org size (maps to plan + seat quantity)."""
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g
    from app.utils.saas_limits import get_effective_seat_limit

    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    members_count = TenantMember.query.filter_by(tenant_id=g.tenant.id).count()
    seat_limit = get_effective_seat_limit(g.tenant.id)

    return render_template(
        "billing/org_size.html",
        tenant=g.tenant,
        billing=billing,
        members_count=members_count,
        seat_limit=seat_limit,
        mode="upgrade",
    )


@billing_bp.route("/billing/required", methods=["GET"])
@login_required
def billing_required():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_member()
    if err:
        return err

    from flask import g

    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    is_tenant_admin = False
    try:
        if getattr(current_user, "is_admin", False):
            is_tenant_admin = True
        else:
            m = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
            is_tenant_admin = bool(m and m.role in ("owner", "admin"))
    except Exception:
        is_tenant_admin = False
    return render_template("billing/required.html", tenant=g.tenant, billing=billing, is_tenant_admin=is_tenant_admin)


@billing_bp.route("/billing/members", methods=["GET"])
@login_required
def billing_members():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g

    members = (
        TenantMember.query.filter_by(tenant_id=g.tenant.id)
        .order_by(TenantMember.role.asc(), TenantMember.created_at.asc())
        .all()
    )
    invites = (
        TenantInvite.query.filter_by(tenant_id=g.tenant.id)
        .order_by(TenantInvite.created_at.desc())
        .limit(50)
        .all()
    )
    owners_count = _owners_count(g.tenant.id)
    current_membership = None
    try:
        for m in members:
            if m.user_id == getattr(current_user, "id", None):
                current_membership = m
                break
    except Exception:
        current_membership = None
    current_member_role = getattr(current_membership, "role", None)
    transfer_candidates = []
    try:
        for m in members:
            if getattr(m, "user_id", None) != getattr(current_user, "id", None):
                label = None
                try:
                    if m.user and m.user.username:
                        label = m.user.username
                    elif m.user and m.user.email:
                        label = m.user.email
                except Exception:
                    label = None
                if not label:
                    label = f"user_id={m.user_id}"
                transfer_candidates.append({"member_id": m.id, "label": label, "role": m.role})
    except Exception:
        transfer_candidates = []
    return render_template(
        "billing/members.html",
        tenant=g.tenant,
        members=members,
        invites=invites,
        owners_count=owners_count,
        current_user_id=getattr(current_user, "id", None),
        current_member_role=current_member_role,
        transfer_candidates=transfer_candidates,
    )


@billing_bp.route("/billing/members/transfer-ownership", methods=["POST"])
@login_required
def transfer_ownership():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g

    # Must be owner (or global admin) to transfer ownership
    if not getattr(current_user, "is_admin", False):
        me = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
        if not me or me.role != "owner":
            return jsonify({"error": "tenant_owner_required"}), 403

    target_member_id = request.form.get("new_owner_member_id")
    try:
        target_member_id = int(target_member_id)
    except Exception:
        flash("Select a valid new owner.", "error")
        return redirect(url_for("billing.billing_members"))

    new_owner = TenantMember.query.filter_by(id=target_member_id, tenant_id=g.tenant.id).first()
    if not new_owner:
        flash("New owner not found.", "error")
        return redirect(url_for("billing.billing_members"))
    if new_owner.user_id == getattr(current_user, "id", None):
        flash("You are already the owner.", "info")
        return redirect(url_for("billing.billing_members"))

    # Promote target
    new_owner.role = "owner"

    # Demote current user from owner to admin (if applicable)
    if not getattr(current_user, "is_admin", False):
        me = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
        if me and me.role == "owner":
            me.role = "admin"

    # Update tenant metadata
    try:
        g.tenant.primary_owner_user_id = new_owner.user_id
    except Exception:
        pass

    # Capture old owner id before commit may mutate it
    old_owner_user_id = None
    try:
        old_owner_user_id = getattr(g.tenant, "primary_owner_user_id", None)
    except Exception:
        old_owner_user_id = None

    db.session.commit()

    # Targeted audit log (best-effort)
    try:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=getattr(current_user, "id", None),
            action="updated",
            entity_type="tenant",
            entity_id=g.tenant.id,
            field_name="primary_owner_user_id",
            old_value=old_owner_user_id,
            new_value=new_owner.user_id,
            entity_name=g.tenant.slug,
            change_description=f"Transferred ownership of tenant '{g.tenant.slug}' to user_id={new_owner.user_id}",
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

    flash("Ownership transferred.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/invite/<token>", methods=["GET", "POST"])
@login_required
def accept_invite(token: str):
    err = _require_saas_enabled()
    if err:
        return err

    from flask import g
    from app.utils.saas_limits import can_add_member

    invite = TenantInvite.query.filter_by(token=token).first()
    if not invite:
        abort(404)
    # Ensure invite belongs to current tenant context
    if not getattr(g, "tenant", None) or invite.tenant_id != g.tenant.id:
        return jsonify({"error": "invite_not_found"}), 404
    if invite.is_revoked:
        flash("This invite was revoked.", "error")
        return redirect(url_for("main.dashboard"))
    if invite.is_expired:
        flash("This invite has expired.", "error")
        return redirect(url_for("main.dashboard"))
    if invite.is_accepted:
        flash("Invite already accepted.", "info")
        return redirect(url_for("billing.billing_members"))

    # Seat enforcement
    if not can_add_member(g.tenant.id) and not getattr(current_user, "is_admin", False):
        flash("Seat limit reached for this tenant. Please upgrade your plan.", "error")
        return redirect(url_for("billing.billing_home"))

    if request.method == "GET":
        return render_template("billing/accept_invite.html", tenant=g.tenant, invite=invite)

    # Create membership (if missing)
    membership = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=current_user.id).first()
    if not membership:
        role = (invite.role or "member").strip().lower()
        if role not in ("admin", "member"):
            role = "member"
        db.session.add(TenantMember(tenant_id=g.tenant.id, user_id=current_user.id, role=role))

    invite.accepted_at = datetime.utcnow()
    invite.accepted_by_user_id = current_user.id
    db.session.commit()
    flash("Welcome! You have joined the tenant.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/billing/invites", methods=["POST"])
@login_required
def create_invite():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g
    from app.utils.saas_limits import can_add_member

    email = (request.form.get("email") or "").strip().lower()
    role = (request.form.get("role") or "member").strip().lower()
    if role not in ("admin", "member"):
        role = "member"
    if not email or "@" not in email:
        flash("Valid email is required.", "error")
        return redirect(url_for("billing.billing_members"))

    # If the user is already a member, don't invite.
    existing_user = User.query.filter(db.func.lower(User.email) == email).first()
    if existing_user:
        existing_member = TenantMember.query.filter_by(tenant_id=g.tenant.id, user_id=existing_user.id).first()
        if existing_member:
            flash("That user is already a member of this tenant.", "info")
            return redirect(url_for("billing.billing_members"))

    # Seat enforcement (invite creation)
    if not can_add_member(g.tenant.id) and not getattr(current_user, "is_admin", False):
        flash("Seat limit reached for this tenant. Please upgrade your plan.", "error")
        return redirect(url_for("billing.billing_home"))

    # Revoke any existing active invite for this email
    try:
        active_invites = (
            TenantInvite.query.filter_by(tenant_id=g.tenant.id, email=email, accepted_at=None, revoked_at=None).all()
        )
        for inv in active_invites:
            inv.revoked_at = datetime.utcnow()
            inv.revoked_by_user_id = current_user.id
    except Exception:
        pass

    invite = TenantInvite.new_invite(g.tenant.id, email=email, role=role, created_by_user_id=current_user.id)
    db.session.add(invite)
    db.session.commit()

    # Best-effort email (will no-op if mail is not configured).
    try:
        from app.utils.email import check_email_configuration, send_email

        invite_url = url_for("billing.accept_invite", token=invite.token, _external=True)
        subject = f"You're invited to join {g.tenant.slug} on TimeTracker"
        text_body = (
            f"You have been invited to join the tenant '{g.tenant.slug}' on TimeTracker.\n\n"
            f"Accept invite: {invite_url}\n\n"
            f"This invite expires on: {invite.expires_at.strftime('%Y-%m-%d %H:%M')} UTC\n"
        )
        send_email(subject, [email], text_body)
        cfg = check_email_configuration()
        if cfg.get("configured"):
            flash("Invite created and email queued.", "success")
        else:
            flash("Invite created. Share the link below with the user.", "success")
    except Exception:
        flash("Invite created. Share the link below with the user.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/billing/invites/<int:invite_id>/revoke", methods=["POST"])
@login_required
def revoke_invite(invite_id: int):
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g

    invite = TenantInvite.query.filter_by(id=invite_id, tenant_id=g.tenant.id).first()
    if not invite:
        abort(404)
    invite.revoked_at = datetime.utcnow()
    invite.revoked_by_user_id = current_user.id
    db.session.commit()
    flash("Invite revoked.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/billing/members/<int:member_id>/role", methods=["POST"])
@login_required
def update_member_role(member_id: int):
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g

    member = TenantMember.query.filter_by(id=member_id, tenant_id=g.tenant.id).first()
    if not member:
        abort(404)

    new_role = (request.form.get("role") or "member").strip().lower()
    if new_role not in ("owner", "admin", "member"):
        flash("Invalid role.", "error")
        return redirect(url_for("billing.billing_members"))

    # Prevent demoting the last owner
    if member.role == "owner" and new_role != "owner":
        if _owners_count(g.tenant.id) <= 1:
            flash("You must keep at least one owner.", "error")
            return redirect(url_for("billing.billing_members"))
        if member.user_id == current_user.id:
            flash("You cannot demote yourself from owner. Transfer ownership first.", "error")
            return redirect(url_for("billing.billing_members"))

    member.role = new_role
    db.session.commit()
    flash("Member role updated.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/billing/members/<int:member_id>/remove", methods=["POST"])
@login_required
def remove_member(member_id: int):
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    from flask import g

    member = TenantMember.query.filter_by(id=member_id, tenant_id=g.tenant.id).first()
    if not member:
        abort(404)

    # Prevent removing the last owner
    if member.role == "owner" and _owners_count(g.tenant.id) <= 1:
        flash("You cannot remove the last owner.", "error")
        return redirect(url_for("billing.billing_members"))

    if member.user_id == current_user.id:
        flash("You cannot remove yourself here. Ask another owner/admin to remove you.", "error")
        return redirect(url_for("billing.billing_members"))

    db.session.delete(member)
    db.session.commit()
    flash("Member removed.", "success")
    return redirect(url_for("billing.billing_members"))


@billing_bp.route("/billing/checkout/start", methods=["POST"])
@login_required
def start_checkout():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    secret, _, prices = _stripe_config()
    if not secret:
        return jsonify({"error": "stripe_not_configured"}), 400
    stripe.api_key = secret

    from flask import g

    data = request.get_json(silent=True) or {}
    if not data:
        data = dict(request.form or {})
    tier = (data.get("tier") or "").strip().lower()
    if tier not in ("basic", "team", "pro"):
        if _wants_json():
            return jsonify({"error": "invalid_tier"}), 400
        flash("Invalid tier", "error")
        return redirect(url_for("billing.billing_home"))

    price_id = prices.get(tier) or ""
    if not price_id:
        if _wants_json():
            return jsonify({"error": "stripe_price_missing", "tier": tier}), 400
        flash("Stripe price is not configured for this tier", "error")
        return redirect(url_for("billing.billing_home"))

    # Seats: Basic is always 1; others default to current setting or 1.
    seats = 1
    if tier in ("team", "pro"):
        try:
            seats = int(data.get("seats") or 1)
        except Exception:
            seats = 1
        seats = max(1, seats)
        if tier == "team":
            seats = min(5, seats)
    else:
        seats = 1

    # Create or reuse customer
    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    customer_id = billing.stripe_customer_id if billing and billing.stripe_customer_id else None
    if not customer_id:
        customer = stripe.Customer.create(
            metadata={"tenant_id": str(g.tenant.id), "tenant_slug": g.tenant.slug},
        )
        customer_id = customer.id

    # Success/cancel URLs (use tenant-prefixed URLs)
    success_target = (data.get("success") or "").strip().lower()
    if success_target == "members":
        success_url = url_for("billing.billing_members", _external=True)
    else:
        success_url = url_for("billing.billing_home", _external=True)
    cancel_url = url_for("billing.billing_org_size", _external=True)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": seats}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "tenant_id": str(g.tenant.id),
            "tenant_slug": g.tenant.slug,
            "requested_tier": tier,
            "requested_seats": str(seats),
            "started_by_user_id": str(current_user.id),
        },
    )

    # Upsert a local billing row (status finalized by webhooks)
    if not billing:
        billing = TenantBilling(tenant_id=g.tenant.id)
        db.session.add(billing)
    billing.tier = tier
    billing.seat_quantity = seats
    billing.stripe_customer_id = customer_id
    billing.stripe_price_id = price_id
    db.session.commit()

    if _wants_json():
        return jsonify({"checkout_url": session.url})
    return redirect(session.url)


@billing_bp.route("/billing/seats", methods=["POST"])
@login_required
def update_seats():
    """Manual seat quantity update (synced to Stripe subscription item)."""
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    secret, _, prices = _stripe_config()
    if not secret:
        return jsonify({"error": "stripe_not_configured"}), 400
    stripe.api_key = secret

    from flask import g

    data = request.get_json(silent=True) or {}
    if not data:
        data = dict(request.form or {})
    try:
        seats = int(data.get("seats") or 1)
    except Exception:
        if _wants_json():
            return jsonify({"error": "invalid_seats"}), 400
        flash("Invalid seats value", "error")
        return redirect(url_for("billing.billing_home"))
    seats = max(1, seats)

    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    if not billing or not billing.tier:
        if _wants_json():
            return jsonify({"error": "no_billing_record"}), 400
        flash("No billing record found for this tenant yet.", "error")
        return redirect(url_for("billing.billing_home"))

    tier = (billing.tier or "basic").lower()
    if tier == "basic":
        seats = 1
    elif tier == "team":
        seats = min(5, seats)

    # Update local
    billing.seat_quantity = seats

    # Update Stripe subscription item quantity if we have it
    if billing.stripe_subscription_id and billing.stripe_subscription_item_id:
        try:
            stripe.SubscriptionItem.modify(billing.stripe_subscription_item_id, quantity=seats)
        except Exception:
            # Non-fatal: webhook will eventually reconcile, but we still return an error for visibility.
            db.session.commit()
            if _wants_json():
                return jsonify({"error": "stripe_update_failed", "seats": seats}), 502
            flash("Stripe update failed. Please try again or use the Billing Portal.", "error")
            return redirect(url_for("billing.billing_home"))

    db.session.commit()
    if _wants_json():
        return jsonify({"tier": tier, "seats": seats})
    flash("Seat quantity updated.", "success")
    return redirect(url_for("billing.billing_home"))


@billing_bp.route("/billing/portal", methods=["POST"])
@login_required
def billing_portal():
    err = _require_saas_enabled()
    if err:
        return err
    err = _require_tenant_admin()
    if err:
        return err

    secret, _, _ = _stripe_config()
    if not secret:
        return jsonify({"error": "stripe_not_configured"}), 400
    stripe.api_key = secret

    from flask import g

    billing = TenantBilling.query.filter_by(tenant_id=g.tenant.id).first()
    if not billing or not billing.stripe_customer_id:
        return jsonify({"error": "no_stripe_customer"}), 400

    return_url = url_for("billing.billing_home", _external=True)
    portal = stripe.billing_portal.Session.create(customer=billing.stripe_customer_id, return_url=return_url)
    if _wants_json():
        return jsonify({"url": portal.url})
    return redirect(portal.url)


@billing_bp.route("/webhooks/stripe/billing", methods=["POST"])
def stripe_billing_webhook():
    # Note: this endpoint is intentionally NOT tenant-prefixed.
    secret, webhook_secret, _ = _stripe_config()
    if not (secret and webhook_secret):
        return jsonify({"error": "stripe_not_configured"}), 400

    payload = request.get_data(cache=False)
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        stripe.api_key = secret
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return jsonify({"error": "invalid_webhook"}), 400

    event_id = getattr(event, "id", None) or ""
    event_type = getattr(event, "type", None) or ""

    # Idempotency: store event id, ignore duplicates
    if event_id:
        existing = StripeEvent.query.filter_by(stripe_event_id=event_id).first()
        if existing and existing.processed_at:
            return jsonify({"status": "ok", "idempotent": True})

    # Best-effort parse tenant_id from metadata
    tenant_id = None
    try:
        obj = event.data.object
        meta = getattr(obj, "metadata", {}) or {}
        tenant_id = int(meta.get("tenant_id")) if meta.get("tenant_id") else None
    except Exception:
        tenant_id = None

    if event_id and not StripeEvent.query.filter_by(stripe_event_id=event_id).first():
        db.session.add(
            StripeEvent(
                stripe_event_id=event_id,
                event_type=event_type,
                tenant_id=tenant_id,
                payload_json=payload.decode("utf-8", errors="replace") if payload else None,
            )
        )
        db.session.commit()

    # Handle subscription state sync
    try:
        if event_type in ("checkout.session.completed",):
            session = event.data.object
            tenant_id = tenant_id or (int(session.metadata.get("tenant_id")) if session.metadata and session.metadata.get("tenant_id") else None)
            if tenant_id:
                billing = TenantBilling.query.filter_by(tenant_id=tenant_id).first()
                if not billing:
                    billing = TenantBilling(tenant_id=tenant_id)
                    db.session.add(billing)
                billing.stripe_customer_id = session.customer
                billing.stripe_subscription_id = session.subscription
                billing.status = "active"
                db.session.commit()

        if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            sub = event.data.object
            # Try to resolve tenant by metadata or customer id
            tenant_id = tenant_id
            if not tenant_id:
                try:
                    tenant_id = int(sub.metadata.get("tenant_id")) if sub.metadata and sub.metadata.get("tenant_id") else None
                except Exception:
                    tenant_id = None

            billing = None
            if tenant_id:
                billing = TenantBilling.query.filter_by(tenant_id=tenant_id).first()
            if not billing:
                billing = TenantBilling.query.filter_by(stripe_customer_id=sub.customer).first()
            if billing:
                billing.stripe_subscription_id = sub.id
                billing.status = sub.status
                billing.cancel_at_period_end = bool(getattr(sub, "cancel_at_period_end", False))
                try:
                    billing.current_period_end = datetime.utcfromtimestamp(int(sub.current_period_end))
                except Exception:
                    pass
                # Extract first subscription item for quantity/price
                try:
                    item = sub["items"]["data"][0]
                    billing.stripe_subscription_item_id = item.get("id")
                    price_id = item.get("price", {}).get("id")
                    billing.stripe_price_id = price_id
                    # Keep tier in sync with Stripe (portal changes, admin changes, etc.)
                    tier = _tier_from_price_id(price_id)
                    if tier:
                        billing.tier = tier
                    qty = item.get("quantity") or 1
                    billing.seat_quantity = int(qty)
                except Exception:
                    pass
                db.session.commit()

                # Sync tenant.status based on subscription state (do not resurrect deleted tenants)
                try:
                    from app.models import Tenant

                    tenant = Tenant.query.filter_by(id=billing.tenant_id).first()
                    if tenant and (tenant.status or "").lower() != "deleted":
                        status = (billing.status or "").lower()
                        if status in ("active", "trialing"):
                            if (tenant.status or "").lower() != "active":
                                tenant.status = "active"
                                db.session.commit()
                        else:
                            # If paid period ended, suspend (billing grace is handled by request gating)
                            if billing.current_period_end and billing.current_period_end <= datetime.utcnow():
                                if (tenant.status or "").lower() != "suspended":
                                    tenant.status = "suspended"
                                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

    finally:
        # Mark processed
        if event_id:
            rec = StripeEvent.query.filter_by(stripe_event_id=event_id).first()
            if rec and not rec.processed_at:
                rec.processed_at = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

    return jsonify({"status": "ok"})

