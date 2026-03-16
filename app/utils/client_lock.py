"""Client lock helpers.

This module centralizes the logic for locking the app to a single client via
`Settings.locked_client_id`. It is intentionally defensive: during migrations
or early startup, tables/columns may not exist yet.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_locked_client_id() -> Optional[int]:
    """Return the configured locked_client_id, or None if not set/available."""
    try:
        from flask import g

        cached = getattr(g, "_locked_client_id", None)
        if cached is not None:
            return cached or None
    except Exception as e:
        logger.debug("Could not get cached locked_client_id: %s", e)

    try:
        from app.models.settings import Settings

        settings = Settings.get_settings()
        locked_client_id = getattr(settings, "locked_client_id", None) or None
        try:
            from flask import g

            g._locked_client_id = locked_client_id or 0
        except Exception as e:
            logger.debug("Could not set g._locked_client_id: %s", e)
        return locked_client_id
    except Exception as e:
        logger.debug("Could not get locked_client_id from settings: %s", e)
        return None


def get_locked_client():
    """Return the locked Client row if configured and active; otherwise None."""
    try:
        from flask import g

        if hasattr(g, "_locked_client"):
            return getattr(g, "_locked_client", None)
    except Exception as e:
        logger.debug("Could not get cached locked client: %s", e)

    locked_client_id = get_locked_client_id()
    if not locked_client_id:
        return None

    try:
        from app.models.client import Client

        client = Client.query.get(int(locked_client_id))
        if client and getattr(client, "status", None) == "active":
            try:
                from flask import g

                g._locked_client = client
            except Exception as e:
                logger.debug("Could not set g._locked_client: %s", e)
            return client
        try:
            from flask import g

            g._locked_client = None
        except Exception as e:
            logger.debug("Could not clear g._locked_client: %s", e)
        return None
    except Exception as e:
        logger.debug("Could not load locked client: %s", e)
        return None


def enforce_locked_client_id(submitted_client_id: Optional[int]) -> Optional[int]:
    """Return locked client id if configured, else the submitted one."""
    locked_client_id = get_locked_client_id()
    return locked_client_id if locked_client_id else submitted_client_id
