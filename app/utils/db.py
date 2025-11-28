from typing import Optional, Dict, Any
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db


def safe_commit(action: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
    """Commit the current database session with robust error handling.

    - Rolls back the session on failure
    - Logs the exception with context
    - Returns True on success, False on failure
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        try:
            db.session.rollback()
        finally:
            pass
        try:
            if action:
                if context:
                    current_app.logger.exception(
                        "Database commit failed during %s | context=%s | error=%s",
                        action,
                        context,
                        e,
                    )
                else:
                    current_app.logger.exception("Database commit failed during %s | error=%s", action, e)
            else:
                current_app.logger.exception("Database commit failed: %s", e)
        except Exception:
            # As a last resort, avoid crashing the request due to logging errors
            pass
        return False
    except Exception as e:
        # Catch-all for unexpected errors
        try:
            db.session.rollback()
        finally:
            pass
        try:
            current_app.logger.exception("Unexpected database error on commit: %s", e)
        except Exception:
            pass
        return False
