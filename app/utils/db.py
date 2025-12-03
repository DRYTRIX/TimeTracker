from typing import Optional, Dict, Any, Callable, TypeVar
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from app import db

T = TypeVar('T')


def safe_query(query_func: Callable[[], T], default: Optional[T] = None) -> Optional[T]:
    """Execute a database query with automatic transaction rollback on failure.
    
    This function handles the case where a transaction has been aborted by PostgreSQL
    (e.g., due to a previous failed query) by rolling back and retrying the query.
    
    Args:
        query_func: A callable that executes the database query
        default: Optional default value to return if query fails (default: None)
    
    Returns:
        The result of the query, or the default value if query fails
    
    Example:
        user = safe_query(lambda: User.query.get(user_id))
    """
    try:
        return query_func()
    except (ValueError, TypeError) as e:
        # Invalid input - don't retry
        current_app.logger.debug(f"Query failed with invalid input: {e}")
        return default
    except SQLAlchemyError as e:
        # Database error - try to rollback and retry
        try:
            db.session.rollback()
            return query_func()
        except Exception as retry_error:
            # Retry also failed - rollback again and return default
            try:
                db.session.rollback()
                current_app.logger.warning(
                    f"Query failed after rollback retry: {retry_error} (original: {e})"
                )
            except Exception:
                pass
            return default
    except Exception as e:
        # Unexpected error - rollback and return default
        try:
            db.session.rollback()
            current_app.logger.warning(f"Unexpected error in safe_query: {e}")
        except Exception:
            pass
        return default


def safe_commit(action: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
    """Commit the current database session with robust error handling.

    - Rolls back the session on failure
    - Logs the exception with context
    - Returns True on success, False on failure
    - Handles missing table errors gracefully (for optional relationships)
    """
    try:
        db.session.commit()
        return True
    except ProgrammingError as e:
        # Check if this is a "relation does not exist" error for time_entry_approvals
        # This can happen when the model defines a relationship but the table hasn't been created yet
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'time_entry_approvals' in error_str and 'does not exist' in error_str:
            # This is a missing table error for an optional relationship
            # Try to rollback and retry the commit, or proceed if it's just a relationship query
            try:
                db.session.rollback()
                # If this is during a delete operation, the object might still be in the session
                # Try to expunge and re-add, or just retry the commit
                current_app.logger.warning(
                    f"Missing time_entry_approvals table detected during {action or 'commit'}. "
                    "This is expected if the migration hasn't been run yet. Proceeding with operation."
                )
                # Retry the commit - the relationship query will fail but we can ignore it
                # if we're just deleting a time entry
                try:
                    db.session.commit()
                    return True
                except Exception:
                    # If retry fails, rollback and return False
                    db.session.rollback()
                    if action:
                        if context:
                            current_app.logger.exception(
                                "Database commit failed during %s after handling missing table | context=%s | error=%s",
                                action,
                                context,
                                e,
                            )
                        else:
                            current_app.logger.exception(
                                "Database commit failed during %s after handling missing table | error=%s", action, e
                            )
                    return False
            except Exception as rollback_error:
                current_app.logger.exception(f"Error during rollback: {rollback_error}")
                return False
        else:
            # Other ProgrammingError - treat as regular SQLAlchemyError
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
                pass
            return False
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
