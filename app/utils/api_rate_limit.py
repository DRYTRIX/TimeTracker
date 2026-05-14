"""
Per API token rate limiting (minute + hour windows).

Uses Redis INCR when REDIS_URL is reachable; otherwise a process-local fallback
(suitable for single-worker dev; production should set Redis).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from flask import current_app

logger = logging.getLogger(__name__)

_LOCAL_LOCK = threading.Lock()
_LOCAL_MINUTE: Dict[tuple, tuple] = {}  # (token_id, minute_epoch) -> (count, reset_ts)
_LOCAL_HOUR: Dict[tuple, tuple] = {}  # (token_id, hour_epoch) -> (count, reset_ts)


def _limits_from_config() -> Tuple[int, int]:
    try:
        per_min = int(current_app.config.get("API_TOKEN_RATE_LIMIT_PER_MINUTE", 100))
        per_hour = int(current_app.config.get("API_TOKEN_RATE_LIMIT_PER_HOUR", 1000))
    except Exception:
        per_min, per_hour = 100, 1000
    return max(1, per_min), max(1, per_hour)


def _redis_client():
    try:
        from urllib.parse import urlparse

        import redis

        if not current_app.config.get("REDIS_ENABLED", True):
            return None
        url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
        parsed = urlparse(url)
        password = parsed.password or None
        client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=password,
            db=int(parsed.path.lstrip("/")) if parsed.path else 0,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            retry_on_timeout=False,
        )
        client.ping()
        return client
    except Exception as e:
        logger.debug("API rate limit Redis unavailable: %s", e)
        return None


def _cleanup_local(now: float) -> None:
    """Drop expired local buckets (best-effort)."""
    with _LOCAL_LOCK:
        for d in (_LOCAL_MINUTE, _LOCAL_HOUR):
            dead = [k for k, (_, exp) in d.items() if exp <= now]
            for k in dead:
                del d[k]


def consume_api_token_rate_limit(token_id: int) -> Tuple[bool, Dict[str, Any]]:
    """
    Increment counters for this token and return whether the request is allowed.

    Returns:
        (allowed, info) where info may include limit_minute, limit_hour, remaining_minute,
        remaining_hour, retry_after_seconds (when not allowed).
    """
    per_min, per_hour = _limits_from_config()
    now = time.time()
    minute_epoch = int(now // 60)
    hour_epoch = int(now // 3600)

    r = _redis_client()
    if r is not None:
        try:
            km = f"tt:api_rl:{token_id}:m:{minute_epoch}"
            kh = f"tt:api_rl:{token_id}:h:{hour_epoch}"
            pipe = r.pipeline()
            pipe.incr(km)
            pipe.expire(km, 120)
            pipe.incr(kh)
            pipe.expire(kh, 7200)
            c_min, _, c_hour, _ = pipe.execute()
            c_min = int(c_min)
            c_hour = int(c_hour)
            if c_min > per_min:
                return False, {
                    "limit_minute": per_min,
                    "limit_hour": per_hour,
                    "remaining_minute": 0,
                    "remaining_hour": max(0, per_hour - c_hour),
                    "retry_after_seconds": 60 - int(now % 60) or 60,
                }
            if c_hour > per_hour:
                return False, {
                    "limit_minute": per_min,
                    "limit_hour": per_hour,
                    "remaining_minute": max(0, per_min - c_min),
                    "remaining_hour": 0,
                    "retry_after_seconds": 3600 - int(now % 3600) or 3600,
                }
            return True, {
                "limit_minute": per_min,
                "limit_hour": per_hour,
                "remaining_minute": max(0, per_min - c_min),
                "remaining_hour": max(0, per_hour - c_hour),
            }
        except Exception as e:
            logger.warning("Redis rate limit failed, using local fallback: %s", e)

    _cleanup_local(now)
    with _LOCAL_LOCK:
        mk = (token_id, minute_epoch)
        hk = (token_id, hour_epoch)
        exp_m = (minute_epoch + 1) * 60
        exp_h = (hour_epoch + 1) * 3600
        cm, _ = _LOCAL_MINUTE.get(mk, (0, exp_m))
        ch, _ = _LOCAL_HOUR.get(hk, (0, exp_h))
        cm += 1
        ch += 1
        _LOCAL_MINUTE[mk] = (cm, exp_m)
        _LOCAL_HOUR[hk] = (ch, exp_h)
        if cm > per_min:
            return False, {
                "limit_minute": per_min,
                "limit_hour": per_hour,
                "remaining_minute": 0,
                "remaining_hour": max(0, per_hour - ch),
                "retry_after_seconds": 60 - int(now % 60) or 60,
            }
        if ch > per_hour:
            return False, {
                "limit_minute": per_min,
                "limit_hour": per_hour,
                "remaining_minute": max(0, per_min - cm),
                "remaining_hour": 0,
                "retry_after_seconds": 3600 - int(now % 3600) or 3600,
            }
        return True, {
            "limit_minute": per_min,
            "limit_hour": per_hour,
            "remaining_minute": max(0, per_min - cm),
            "remaining_hour": max(0, per_hour - ch),
        }
