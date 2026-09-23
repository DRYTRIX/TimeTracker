"""API login two-factor challenge (desktop/mobile/extension)."""

import pyotp
import pytest

from app import db

pytestmark = [pytest.mark.unit]


def _enable_totp(user):
    secret = pyotp.random_base32()
    user.set_two_factor_secret(secret)
    user.two_factor_enabled = True
    db.session.commit()
    return secret


@pytest.mark.unit
def test_api_login_returns_2fa_challenge_when_totp_enabled(client, user):
    secret = _enable_totp(user)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "password123"},
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data["requires_2fa"] is True
    assert isinstance(data.get("temp_token"), str) and data["temp_token"]
    assert "token" not in data

    totp = pyotp.TOTP(secret)
    verify = client.post(
        "/api/v1/auth/2fa/verify",
        json={"temp_token": data["temp_token"], "code": totp.now()},
    )
    assert verify.status_code == 200
    token = verify.get_json().get("token")
    assert isinstance(token, str) and token.startswith("tt_")


@pytest.mark.unit
def test_api_login_without_2fa_still_returns_token(client, user):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "password123"},
    )
    assert response.status_code == 200
    assert response.get_json()["token"].startswith("tt_")


@pytest.mark.unit
def test_api_2fa_verify_rejects_bad_code(client, user):
    _enable_totp(user)
    challenge = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "password123"},
    )
    temp = challenge.get_json()["temp_token"]

    bad = client.post(
        "/api/v1/auth/2fa/verify",
        json={"temp_token": temp, "code": "000000"},
    )
    assert bad.status_code == 401
    assert bad.get_json().get("error")


@pytest.mark.unit
def test_api_2fa_verify_rejects_invalid_temp_token(client, user):
    _enable_totp(user)
    verify_bad = client.post(
        "/api/v1/auth/2fa/verify",
        json={"temp_token": "not-a-valid-token", "code": "123456"},
    )
    assert verify_bad.status_code == 401
