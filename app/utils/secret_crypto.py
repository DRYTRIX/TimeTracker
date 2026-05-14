from __future__ import annotations

import base64
import os
from typing import Optional

_FERNET = None


def _load_key_from_env() -> str:
    """
    Return a base64 urlsafe-encoded 32-byte key suitable for cryptography.fernet.Fernet.

    Supported env vars:
    - SETTINGS_ENCRYPTION_KEY: full key string
    - SETTINGS_ENCRYPTION_KEY_FILE: file containing the key on first line
    """
    key = (os.getenv("SETTINGS_ENCRYPTION_KEY") or "").strip()
    if not key:
        key_file = (os.getenv("SETTINGS_ENCRYPTION_KEY_FILE") or "").strip()
        if key_file:
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    key = (f.read().strip().split("\n")[0] or "").strip()
            except OSError:
                key = ""
    return key


def is_configured() -> bool:
    return bool(_load_key_from_env())


def get_fernet():
    global _FERNET
    if _FERNET is not None:
        return _FERNET

    from cryptography.fernet import Fernet

    key = _load_key_from_env()
    if not key:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY is not configured")

    # Validate it looks like a Fernet key.
    try:
        raw = base64.urlsafe_b64decode(key.encode("utf-8"))
        if len(raw) != 32:
            raise ValueError("wrong key length")
    except Exception as e:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY is invalid (must be Fernet key)") from e

    _FERNET = Fernet(key.encode("utf-8"))
    return _FERNET


ENC_PREFIX = "enc:v1:"


def encrypt_if_possible(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(ENC_PREFIX):
        return value
    f = get_fernet()
    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENC_PREFIX}{token}"


def decrypt_if_needed(value: Optional[str]) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith(ENC_PREFIX):
        return value
    token = value[len(ENC_PREFIX) :]
    f = get_fernet()
    return f.decrypt(token.encode("utf-8")).decode("utf-8")
