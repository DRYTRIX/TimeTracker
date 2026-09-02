"""Optional Firebase Cloud Messaging helpers for mobile idle wake-up (Issue #722).

Configured via ``FIREBASE_SERVICE_ACCOUNT_JSON`` (raw JSON string or path to a
service-account JSON file). When unset or invalid, FCM is a no-op so self-hosted
installs without Firebase keep working.
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_firebase_app = None
_init_attempted = False


def init_firebase_admin(app=None) -> bool:
    """Initialize firebase_admin once from app config / env. Returns True if ready."""
    global _firebase_app, _init_attempted
    if _firebase_app is not None:
        return True
    if _init_attempted and _firebase_app is None:
        return False
    _init_attempted = True

    raw = ""
    if app is not None:
        raw = (app.config.get("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    if not raw:
        raw = (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    if not raw:
        logger.debug("FIREBASE_SERVICE_ACCOUNT_JSON not set; FCM disabled")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception as e:
        logger.debug("firebase_admin not installed; FCM disabled: %s", e)
        return False

    try:
        if firebase_admin._apps:  # already initialized elsewhere
            _firebase_app = firebase_admin.get_app()
            return True
    except Exception:
        pass

    try:
        cred_dict = None
        if raw.startswith("{"):
            cred_dict = json.loads(raw)
        elif os.path.isfile(raw):
            with open(raw, "r", encoding="utf-8") as fh:
                cred_dict = json.load(fh)
        else:
            logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON is neither JSON nor a readable file path")
            return False

        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized for FCM")
        return True
    except Exception as e:
        logger.warning("Failed to initialize Firebase Admin: %s", e)
        _firebase_app = None
        return False


def send_fcm_to_tokens(
    tokens: Sequence[str],
    *,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> Tuple[int, List[str]]:
    """Send a notification+data FCM message to each token.

    Returns ``(delivered_count, invalid_tokens)``. Invalid tokens should be removed
    from the database by the caller.
    """
    if not tokens:
        return 0, []
    if not init_firebase_admin():
        return 0, []

    try:
        from firebase_admin import messaging
    except Exception as e:
        logger.debug("firebase_admin.messaging unavailable: %s", e)
        return 0, []

    delivered = 0
    invalid: List[str] = []
    payload_data = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

    for token in tokens:
        if not token:
            continue
        try:
            message = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=payload_data,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="idle_reminder",
                        priority="high",
                    ),
                ),
                apns=messaging.APNSConfig(
                    headers={"apns-priority": "10"},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(title=title, body=body),
                            sound="default",
                            content_available=True,
                        )
                    ),
                ),
            )
            messaging.send(message)
            delivered += 1
        except Exception as e:
            err_name = type(e).__name__
            err_text = str(e).lower()
            # Unregistered / invalid token — tell caller to drop it
            if (
                "unregistered" in err_text
                or "not-found" in err_text
                or "invalid-argument" in err_text
                or "registration-token-not-registered" in err_text
                or err_name in ("UnregisteredError", "SenderIdMismatchError", "NotFoundError")
            ):
                invalid.append(token)
            else:
                logger.debug("FCM send to token failed: %s", e)

    return delivered, invalid
