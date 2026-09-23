"""Unit tests for LDAP service helpers and connection diagnostics (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import ldap_service

pytestmark = [pytest.mark.unit]


def test_user_search_base_combines_user_and_base_dn():
    cfg = {"LDAP_USER_DN": "ou=users", "LDAP_BASE_DN": "dc=example,dc=com"}
    assert ldap_service._user_search_base(cfg) == "ou=users,dc=example,dc=com"


def test_user_search_base_user_dn_only():
    cfg = {"LDAP_USER_DN": "ou=users", "LDAP_BASE_DN": ""}
    assert ldap_service._user_search_base(cfg) == "ou=users"


def test_group_search_base_combines_group_and_base_dn():
    cfg = {"LDAP_GROUP_DN": "ou=groups", "LDAP_BASE_DN": "dc=example,dc=com"}
    assert ldap_service._group_search_base(cfg) == "ou=groups,dc=example,dc=com"


def test_authenticate_empty_credentials_returns_none(app):
    with app.app_context():
        from app.services.ldap_service import LDAPService

        assert LDAPService.authenticate("", "") is None
        assert LDAPService.authenticate("user", "") is None


@patch("app.services.ldap_service.Connection", None)
@patch("app.services.ldap_service.Server", None)
def test_test_connection_without_ldap3(app):
    with app.app_context():
        from app.services.ldap_service import LDAPService

        result = LDAPService.test_connection(
            {
                "LDAP_HOST": "ldap.test",
                "LDAP_PORT": 389,
                "LDAP_BIND_DN": "cn=svc,dc=example,dc=com",
                "LDAP_BIND_PASSWORD": "x",
                "LDAP_BASE_DN": "dc=example,dc=com",
            }
        )
    assert result["success"] is False
    assert "ldap3" in result["message"].lower()


@patch("app.services.ldap_service._service_connection")
def test_test_connection_bind_failure(mock_svc, app):
    from ldap3.core.exceptions import LDAPException

    mock_svc.side_effect = LDAPException("bind failed")

    with app.app_context():
        from app.services.ldap_service import LDAPService

        result = LDAPService.test_connection(
            {
                "LDAP_HOST": "ldap.test",
                "LDAP_PORT": 389,
                "LDAP_BIND_DN": "cn=svc,dc=example,dc=com",
                "LDAP_BIND_PASSWORD": "x",
                "LDAP_BASE_DN": "dc=example,dc=com",
                "LDAP_USER_DN": "ou=users",
                "LDAP_USER_OBJECT_CLASS": "inetOrgPerson",
            }
        )

    assert result["success"] is False
    assert "LDAP" in result["message"]
    assert result["user_count"] is None


@patch("app.services.ldap_service._service_connection")
def test_test_connection_success_counts_users(mock_svc, app):
    conn = MagicMock()
    conn.entries = [MagicMock(), MagicMock()]
    mock_svc.return_value = conn

    with app.app_context():
        from app.services.ldap_service import LDAPService

        result = LDAPService.test_connection(
            {
                "LDAP_HOST": "ldap.test",
                "LDAP_PORT": 389,
                "LDAP_BIND_DN": "cn=svc,dc=example,dc=com",
                "LDAP_BIND_PASSWORD": "x",
                "LDAP_BASE_DN": "dc=example,dc=com",
                "LDAP_USER_DN": "ou=users",
                "LDAP_USER_OBJECT_CLASS": "inetOrgPerson",
            }
        )

    assert result["success"] is True
    assert result["user_count"] == 2
    conn.unbind.assert_called()
