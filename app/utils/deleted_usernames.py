from datetime import datetime

from app import db
from app.models.deleted_username import DeletedUsername


def _normalize_username(username):
    return (username or "").strip().lower()


def is_username_reserved(username):
    """Return True if username was reserved when a user account was deleted."""
    normalized = _normalize_username(username)
    if not normalized:
        return False
    return DeletedUsername.query.filter_by(username=normalized).first() is not None


def reserve_deleted_username(username, deleted_by_user_id=None):
    """Record a username as reserved after admin deletion."""
    normalized = _normalize_username(username)
    if not normalized:
        return

    existing = DeletedUsername.query.filter_by(username=normalized).first()
    if existing:
        existing.deleted_at = datetime.utcnow()
        if deleted_by_user_id is not None:
            existing.deleted_by_user_id = deleted_by_user_id
        return

    db.session.add(
        DeletedUsername(
            username=normalized,
            deleted_at=datetime.utcnow(),
            deleted_by_user_id=deleted_by_user_id,
        )
    )
