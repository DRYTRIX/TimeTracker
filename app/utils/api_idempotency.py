"""Idempotency-Key header handling for API v1 writes."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from flask import Response, jsonify

from app import db
from app.models.api_idempotency_key import ApiIdempotencyKey
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_HOURS = 24
MAX_KEY_LEN = 128
SCOPE_POST_TIME_ENTRY = "post:time_entries"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_idempotency_key(header_value: Optional[str]) -> Optional[str]:
    if not header_value or not isinstance(header_value, str):
        return None
    s = header_value.strip()
    if not s or len(s) > MAX_KEY_LEN:
        return None
    return s


def lookup_idempotent_response(api_token_id: int, scope: str, key: str) -> Optional[Tuple[int, str]]:
    row = ApiIdempotencyKey.query.filter_by(
        api_token_id=api_token_id,
        scope=scope,
        key_hash=_hash_key(key),
    ).first()
    if not row:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=IDEMPOTENCY_TTL_HOURS)
    if row.created_at < cutoff:
        try:
            db.session.delete(row)
            safe_commit("idempotency_expired_cleanup", {})
        except Exception as e:
            logger.debug("Idempotency cleanup: %s", e)
        return None
    return row.response_status, row.response_body


def store_idempotent_response(api_token_id: int, scope: str, key: str, status_code: int, body_dict: Any) -> None:
    body_json = json.dumps(body_dict, default=str)
    row = ApiIdempotencyKey(
        api_token_id=api_token_id,
        scope=scope,
        key_hash=_hash_key(key),
        response_status=status_code,
        response_body=body_json,
    )
    db.session.add(row)
    if not safe_commit("api_idempotency_store", {"scope": scope}):
        logger.warning("Failed to store idempotency key (scope=%s)", scope)


def replay_response(status_code: int, body_json: str) -> Response:
    try:
        data = json.loads(body_json)
    except Exception:
        data = {"message": body_json}
    resp = jsonify(data)
    resp.status_code = status_code
    return resp
