"""Short-lived tokens for API password login when TOTP 2FA is required."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import Config

API_2FA_TEMP_TOKEN_MAX_AGE_SECONDS = 300
_API_2FA_SALT = "timetracker:api-2fa:v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(Config.SECRET_KEY, salt=_API_2FA_SALT)


def make_api_2fa_temp_token(user_id: int) -> str:
    return _serializer().dumps({"uid": int(user_id), "purpose": "api_2fa"})


def load_api_2fa_user_id(temp_token: str, *, max_age_seconds: int | None = None) -> int | None:
    max_age = max_age_seconds if max_age_seconds is not None else API_2FA_TEMP_TOKEN_MAX_AGE_SECONDS
    try:
        data = _serializer().loads(temp_token, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    if (data.get("purpose") or "") != "api_2fa":
        return None
    try:
        return int(data.get("uid"))
    except (TypeError, ValueError):
        return None
