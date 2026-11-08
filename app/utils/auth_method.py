"""Helpers for AUTH_METHOD parsing (none | local | oidc | ldap | saml | both | all)."""

from __future__ import annotations

_VALID = frozenset({"none", "local", "oidc", "ldap", "saml", "both", "all"})


def normalize_auth_method(raw: str | None) -> str:
    """Return a valid auth method string; unknown values become 'local' in non-production via caller."""
    s = (raw or "local").strip().lower()
    return s if s in _VALID else "local"


def auth_includes_local(auth_method: str | None) -> bool:
    m = normalize_auth_method(auth_method)
    return m in ("local", "both", "all")


def auth_includes_oidc(auth_method: str | None) -> bool:
    m = normalize_auth_method(auth_method)
    return m in ("oidc", "both", "all")


def auth_includes_ldap(auth_method: str | None) -> bool:
    m = normalize_auth_method(auth_method)
    return m in ("ldap", "all")


def auth_includes_saml(auth_method: str | None) -> bool:
    m = normalize_auth_method(auth_method)
    return m in ("saml", "all")


def requires_password_form(auth_method: str | None) -> bool:
    """True when login form should collect a password (local, ldap, or combined modes)."""
    m = normalize_auth_method(auth_method)
    return m in ("local", "both", "ldap", "all")


def forgot_password_available(auth_method: str | None) -> bool:
    """Forgot-password link when any local-password account may exist."""
    return auth_includes_local(auth_method)


def ldap_enabled_from_auth_method(auth_method: str | None) -> bool:
    """LDAP auth is active for this AUTH_METHOD (same as Config LDAP_ENABLED)."""
    return auth_includes_ldap(auth_method)

