"""Shared provisioning for external identity providers (OIDC, SAML)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from flask import current_app

from app import db
from app.config import Config
from app.models import Role, User
from app.utils.config_manager import ConfigManager
from app.utils.db import safe_commit
from app.utils.deleted_usernames import is_username_reserved
from app.utils.posthog_funnels import track_onboarding_started


@dataclass
class ProvisionResult:
    user: User | None
    created: bool = False
    error: str | None = None
    error_flash: str | None = None


def _normalize_username(username: str | None, email: str | None, subject: str) -> str:
    username = (username or "").strip()
    if username:
        return username
    if email and "@" in email:
        return email.split("@", 1)[0]
    return f"user-{(subject or 'unknown')[-8:]}"


def _apply_admin_mapping(
    user: User,
    *,
    email: str | None,
    groups: Sequence[str] | None,
    admin_emails: Iterable[str] | None,
    admin_groups: Iterable[str] | None,
) -> bool:
    """Promote user.role to admin when email/group matches. Returns True if changed."""
    admin_set = False
    group_list = list(groups or [])
    emails = [e.strip().lower() for e in (admin_emails or []) if e and str(e).strip()]
    group_names = [g for g in (admin_groups or []) if g]

    for g in group_names:
        if g in group_list and user.role != "admin":
            user.role = "admin"
            admin_set = True
            break

    if email and email.lower() in emails and user.role != "admin":
        user.role = "admin"
        admin_set = True

    return admin_set


def provision_external_user(
    provider: str,
    subject: str,
    issuer: str,
    email: str | None = None,
    full_name: str | None = None,
    groups: Sequence[str] | None = None,
    admin_emails: Iterable[str] | None = None,
    admin_groups: Iterable[str] | None = None,
    username: str | None = None,
) -> ProvisionResult:
    """Find or create a User linked to an external IdP subject.

    For ``provider='oidc'`` also sets legacy ``oidc_sub`` / ``oidc_issuer``.
    For ``provider='saml'`` sets ``auth_provider='saml'`` and external_* fields.

    Returns a :class:`ProvisionResult`. On failure ``user`` is None and
    ``error`` / ``error_flash`` explain why (caller decides redirect/flash).
    """
    provider = (provider or "").strip().lower() or "oidc"
    subject = (subject or "").strip()
    issuer = (issuer or "").strip()
    email = (email or "").strip() or None
    full_name = (full_name or "").strip() or None

    if not subject or not issuer:
        return ProvisionResult(user=None, error="missing_subject_or_issuer", error_flash="Invalid identity assertion.")

    username = _normalize_username(username, email, subject)

    # Lookup order: external pair → oidc pair (legacy) → email → username
    user = User.query.filter_by(external_issuer=issuer, external_subject=subject).first()
    if not user and provider == "oidc":
        user = User.query.filter_by(oidc_issuer=issuer, oidc_sub=subject).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()
    if not user:
        user = User.query.filter_by(username=username).first()

    created = False
    if not user:
        if current_app.config.get("DEMO_MODE"):
            return ProvisionResult(
                user=None,
                error="demo_mode_no_create",
                error_flash="Demo mode: only the demo account can be used. Please use the credentials on the login page.",
            )
        allow_self_register = ConfigManager.get_setting("allow_self_register", Config.ALLOW_SELF_REGISTER)
        if not allow_self_register:
            return ProvisionResult(
                user=None,
                error="self_registration_disabled",
                error_flash="User account does not exist and self-registration is disabled.",
            )
        if is_username_reserved(username):
            return ProvisionResult(
                user=None,
                error="deleted_username_reserved",
                error_flash="User account does not exist and self-registration is disabled.",
            )

        role_name = "user"
        try:
            user = User(username=username, role=role_name, email=email, full_name=full_name)
            user.is_active = True
            user.auth_provider = provider
            user.external_issuer = issuer
            user.external_subject = subject
            if provider == "oidc":
                user.oidc_issuer = issuer
                user.oidc_sub = subject
            try:
                from app.models import Settings

                settings = Settings.get_settings()
                user.standard_hours_per_day = float(getattr(settings, "default_daily_working_hours", 8.0) or 8.0)
            except Exception:
                current_app.logger.debug(
                    "Could not apply default daily working hours for external user", exc_info=True
                )

            role_obj = Role.query.filter_by(name=role_name).first()
            if role_obj:
                user.roles.append(role_obj)

            db.session.add(user)
            if not safe_commit(f"{provider}_create_user", {"username": username, "email": email}):
                raise RuntimeError("db commit failed on user create")

            track_onboarding_started(
                user.id,
                {
                    "auth_method": provider,
                    "self_registered": True,
                    "is_admin": role_name == "admin",
                    "has_email": bool(email),
                },
            )
            created = True
        except Exception as e:
            current_app.logger.exception("Failed to create user from %s claims: %s", provider, e)
            return ProvisionResult(
                user=None,
                error="db_create_user_failed",
                error_flash="Could not create your account due to a database error.",
            )
    else:
        changed = False
        if getattr(user, "auth_provider", "local") != provider:
            user.auth_provider = provider
            changed = True
        if not user.external_issuer or not user.external_subject:
            user.external_issuer = issuer
            user.external_subject = subject
            changed = True
        if provider == "oidc" and (not user.oidc_issuer or not user.oidc_sub):
            user.oidc_issuer = issuer
            user.oidc_sub = subject
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            if not safe_commit(f"{provider}_update_user", {"user_id": user.id}):
                current_app.logger.warning("DB commit failed updating user from %s; continuing", provider)

    # Admin role mapping
    try:
        if _apply_admin_mapping(
            user,
            email=email,
            groups=groups,
            admin_emails=admin_emails,
            admin_groups=admin_groups,
        ):
            if not safe_commit(f"{provider}_promote_admin", {"user_id": user.id}):
                current_app.logger.warning("DB commit failed promoting user to admin from %s; continuing", provider)
    except Exception:
        current_app.logger.warning("%s admin role mapping failed", provider, exc_info=True)

    return ProvisionResult(user=user, created=created)
