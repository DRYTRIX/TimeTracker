"""Regression tests for GHSA advisory remediations."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.attachment_url import sanitize_attachment_url
from app.utils.auth_method import allows_passwordless_login, requires_password_form
from app.utils.outbound_url import UnsafeOutboundURL, validate_outbound_url
from app.utils.role_assignment import filter_assignable_roles, user_can_assign_role
from app.utils.safe_template_render import SecurityError, render_sandboxed_string


def test_passwordless_only_for_none_auth_method():
    assert allows_passwordless_login("none") is True
    assert allows_passwordless_login("saml") is False
    assert allows_passwordless_login("oidc") is False
    assert requires_password_form("saml") is False
    assert requires_password_form("local") is True


def test_role_assignment_blocks_admin_for_non_super():
    class Actor:
        is_super_admin = False
        is_admin = False

    ok, err = user_can_assign_role(Actor(), "admin")
    assert ok is False
    assert "Super Admin" in err

    class Super:
        is_super_admin = True
        is_admin = True

    ok, _ = user_can_assign_role(Super(), "admin")
    assert ok is True


def test_filter_assignable_roles_hides_admin_tier():
    class Role:
        def __init__(self, name):
            self.name = name

    roles = [Role("user"), Role("manager"), Role("admin"), Role("super_admin")]

    class Manager:
        is_super_admin = False

    filtered = filter_assignable_roles(Manager(), roles)
    assert [r.name for r in filtered] == ["user", "manager"]


def test_sandboxed_render_rejects_path():
    with pytest.raises(SecurityError):
        render_sandboxed_string("{{ Path }}", Path=Path)


def test_attachment_url_blocks_traversal():
    assert sanitize_attachment_url("../../etc/passwd") is None
    assert sanitize_attachment_url("/etc/passwd") is None
    assert sanitize_attachment_url("file:///etc/passwd") is None
    assert sanitize_attachment_url("uploads/chat/a.pdf") == "uploads/chat/a.pdf"
    assert sanitize_attachment_url("https://cdn.example.com/a.pdf") == "https://cdn.example.com/a.pdf"


def test_outbound_url_blocks_metadata_even_when_private_allowed():
    with pytest.raises(UnsafeOutboundURL):
        validate_outbound_url("http://169.254.169.254/latest/meta-data/", allow_private=True, resolve_dns=False)
    with pytest.raises(UnsafeOutboundURL):
        validate_outbound_url("http://metadata.google.internal/", allow_private=True, resolve_dns=False)


def test_dcr_redirect_rejects_lookalike_localhost():
    from app.routes.oauth_server import _redirect_uri_allowed_for_dcr

    assert _redirect_uri_allowed_for_dcr("http://localhost:8787/callback") is True
    assert _redirect_uri_allowed_for_dcr("http://127.0.0.1/cb") is True
    assert _redirect_uri_allowed_for_dcr("http://localhost.attacker.example/cb") is False
    assert _redirect_uri_allowed_for_dcr("http://127.0.0.1.attacker.example/") is False
    assert _redirect_uri_allowed_for_dcr("https://claude.ai/callback") is True


def test_cap_scopes_strips_admin_for_non_admin():
    from app.utils.api_object_auth import cap_scopes_for_user, default_app_login_scopes

    class User:
        is_admin = False
        portal_only = False
        is_client_portal_user = False

    capped = cap_scopes_for_user(User(), "read:projects,admin:all,*")
    assert "admin:all" not in capped
    assert "*" not in capped
    assert "read:projects" in capped

    scopes = default_app_login_scopes(User())
    assert "read:*" not in scopes
    assert "write:*" not in scopes
    assert "admin:all" not in scopes
