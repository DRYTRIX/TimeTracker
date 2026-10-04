"""Regression: IntegrityError handler rolls back so the session stays usable."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User

pytestmark = [pytest.mark.unit, pytest.mark.database]


def test_integrity_error_handler_rolls_back_session(app, client, user):
    """After an IntegrityError in a request, db.session can still query."""

    @app.route("/__test_integrity_error")
    def _trigger_integrity_error():
        # Poison the session with a failed flush, then raise so the
        # registered IntegrityError handler runs _rollback_session().
        other = User(username=user.username, role="user", email="dup@example.com")
        db.session.add(other)
        try:
            db.session.flush()
        except IntegrityError:
            # Re-raise so Flask's errorhandler (not this except) owns rollback
            raise
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed: users.username"))

    resp = client.get("/__test_integrity_error")
    assert resp.status_code in (302, 409)

    # Session must be usable after the handler rolled back
    found = User.query.filter_by(username=user.username).first()
    assert found is not None
    assert found.id == user.id
    assert User.query.count() >= 1
