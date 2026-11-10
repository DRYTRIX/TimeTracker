"""External identity provisioning + SAML login route."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from app import db
from app.models import User
from app.services.external_identity_service import provision_external_user
from app.utils.config_manager import ConfigManager


def test_provision_external_user_creates(app, monkeypatch):
    monkeypatch.setitem(app.config, "DEMO_MODE", False)
    with app.app_context():
        monkeypatch.setattr(
            ConfigManager,
            "get_setting",
            staticmethod(lambda key, default=None: True if key == "allow_self_register" else default),
        )
        result = provision_external_user(
            provider="saml",
            subject="saml-sub-1",
            issuer="https://idp.example/metadata",
            email="saml.user@example.com",
            full_name="SAML User",
        )
        assert result.error is None
        assert result.user is not None
        assert result.created is True
        assert result.user.auth_provider == "saml"
        assert result.user.external_subject == "saml-sub-1"
        assert result.user.external_issuer == "https://idp.example/metadata"
        assert result.user.email == "saml.user@example.com"


def test_provision_external_user_links_by_email(app, user, monkeypatch):
    monkeypatch.setitem(app.config, "DEMO_MODE", False)
    with app.app_context():
        u = User.query.filter_by(username=user.username).first()
        assert u is not None
        u.email = "linkme@example.com"
        db.session.commit()

        result = provision_external_user(
            provider="oidc",
            subject="oidc-sub-99",
            issuer="https://issuer.example",
            email="linkme@example.com",
            full_name="Linked",
        )
        assert result.error is None, result.error
        assert result.user is not None
        assert result.created is False
        assert result.user.id == u.id
        assert result.user.oidc_sub == "oidc-sub-99"
        assert result.user.external_subject == "oidc-sub-99"


def test_saml_login_redirects_when_configured(client, app, monkeypatch):
    monkeypatch.setitem(app.config, "SAML_ENABLED", True)
    monkeypatch.setitem(app.config, "AUTH_METHOD", "saml")
    monkeypatch.setitem(app.config, "SAML_IDP_SSO_URL", "https://idp.example/sso")
    monkeypatch.setitem(app.config, "SAML_IDP_ENTITY_ID", "https://idp.example/metadata")
    monkeypatch.setitem(app.config, "SAML_IDP_X509_CERT", "MIIB")

    class FakeAuth:
        def __init__(self, *a, **k):
            pass

        def login(self, return_to=None):
            return "https://idp.example/sso?SAMLRequest=abc"

    fake_auth_mod = MagicMock()
    fake_auth_mod.OneLogin_Saml2_Auth = FakeAuth
    modules = {
        "onelogin": MagicMock(),
        "onelogin.saml2": MagicMock(),
        "onelogin.saml2.auth": fake_auth_mod,
        "onelogin.saml2.settings": MagicMock(),
        "onelogin.saml2.utils": MagicMock(),
    }
    with patch.dict(sys.modules, modules):
        resp = client.get("/auth/saml/login", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "idp.example" in resp.headers.get("Location", "")
