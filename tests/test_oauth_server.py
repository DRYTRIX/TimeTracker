"""OAuth 2.0 authorization server: code+PKCE, bad verifier, revoked token."""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from app import db
from app.models import OAuthAccessToken, OAuthApplication
from app.utils.api_auth import authenticate_token


def _pkce_pair():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@pytest.fixture
def oauth_app_record(app, user):
    with app.app_context():
        rec, secret = OAuthApplication.create_application(
            owner_user_id=user.id,
            name="Test App",
            redirect_uris=["https://client.example/callback"],
            allowed_scopes="read:projects,write:time_entries",
            is_confidential=True,
        )
        db.session.add(rec)
        db.session.commit()
        db.session.refresh(rec)
        return rec, secret


def test_oauth_code_pkce_happy_path(authenticated_client, app, user, oauth_app_record):
    app_rec, secret = oauth_app_record
    verifier, challenge = _pkce_pair()
    client = authenticated_client

    resp = client.post(
        "/oauth/authorize",
        data={
            "decision": "approve",
            "client_id": app_rec.client_id,
            "redirect_uri": "https://client.example/callback",
            "scope": "read:projects",
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    loc = resp.headers["Location"]
    assert loc.startswith("https://client.example/callback")
    qs = parse_qs(urlparse(loc).query)
    assert "code" in qs
    code = qs["code"][0]

    basic = base64.b64encode(f"{app_rec.client_id}:{secret}".encode()).decode()
    token_resp = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://client.example/callback",
            "code_verifier": verifier,
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert token_resp.status_code == 200
    body = token_resp.get_json()
    assert body["access_token"].startswith("tto_")
    assert body["token_type"] == "Bearer"
    assert "refresh_token" in body

    with app.app_context():
        u, tok, err = authenticate_token(body["access_token"])
        assert err is None
        assert u.id == user.id
        assert tok.has_scope("read:projects")


def test_oauth_bad_code_verifier(authenticated_client, app, user, oauth_app_record):
    app_rec, secret = oauth_app_record
    _, challenge = _pkce_pair()
    client = authenticated_client

    resp = client.post(
        "/oauth/authorize",
        data={
            "decision": "approve",
            "client_id": app_rec.client_id,
            "redirect_uri": "https://client.example/callback",
            "scope": "read:projects",
            "state": "s",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    code = parse_qs(urlparse(resp.headers["Location"]).query)["code"][0]

    basic = base64.b64encode(f"{app_rec.client_id}:{secret}".encode()).decode()
    token_resp = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://client.example/callback",
            "code_verifier": "totally-wrong-verifier-value-xxxxxxxx",
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert token_resp.status_code == 400
    assert token_resp.get_json()["error"] == "invalid_grant"


def test_oauth_revoked_token(app, user, oauth_app_record):
    app_rec, _secret = oauth_app_record
    with app.app_context():
        rec, plain, _refresh = OAuthAccessToken.create_token(
            application_id=app_rec.id,
            user_id=user.id,
            scopes="read:projects",
        )
        db.session.add(rec)
        db.session.commit()

        u, tok, err = authenticate_token(plain)
        assert err is None
        assert u is not None

        tok.revoke()
        db.session.commit()

        u2, _tok2, err2 = authenticate_token(plain)
        assert u2 is None
        assert err2 == "Token has been revoked"


def test_well_known_metadata(client):
    resp = client.get("/.well-known/oauth-authorization-server")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "S256" in data["code_challenge_methods_supported"]
