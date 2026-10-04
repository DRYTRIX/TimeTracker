"""Postgres advisory-lock leader election for the background scheduler.

Session-level ``pg_try_advisory_lock`` requires the connection that acquired
the lock to remain open for the process lifetime. The connection is stored on
``app.extensions['scheduler_lock_conn']`` so it is never returned to the pool
while this process is the scheduler leader.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Fixed bigint key for TimeTracker scheduler leadership.
SCHEDULER_ADVISORY_LOCK_KEY = 874512039


def try_acquire_scheduler_leadership(app) -> bool:
    """Try to become the single process that runs BackgroundScheduler.

    Returns True if this process should start the scheduler.

    - TESTING: False (create_app already skips the scheduler)
    - SQLite / non-Postgres: True (single-process assumed; no advisory locks)
    - Postgres: True only if ``pg_try_advisory_lock`` succeeds on a dedicated
      connection kept in ``app.extensions['scheduler_lock_conn']``
    """
    if app.config.get("TESTING"):
        return False

    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").lower()
    if "sqlite" in uri:
        return True
    if "postgres" not in uri:
        return True

    if app.extensions.get("scheduler_lock_conn") is not None:
        return True

    conn = None
    try:
        from app import db

        # Hold a dedicated engine connection for the process lifetime.
        # Session-level advisory locks are released when the session ends.
        with app.app_context():
            conn = db.engine.connect()
            result = conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": SCHEDULER_ADVISORY_LOCK_KEY},
            )
            acquired = bool(result.scalar())
            # Commit so the connection is idle; session-level lock remains held.
            conn.commit()

        if acquired:
            app.extensions["scheduler_lock_conn"] = conn
            logger.info(
                "Acquired scheduler leadership lock (key=%s)",
                SCHEDULER_ADVISORY_LOCK_KEY,
            )
            return True

        conn.close()
        logger.info(
            "Scheduler leadership lock held by another process (key=%s); "
            "skipping BackgroundScheduler start",
            SCHEDULER_ADVISORY_LOCK_KEY,
        )
        return False
    except Exception as e:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        logger.warning(
            "Could not acquire scheduler leadership lock: %s; skipping scheduler start",
            e,
            exc_info=True,
        )
        return False
