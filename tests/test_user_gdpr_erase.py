"""Tests for GDPR user anonymization."""

import pytest

from app import db
from app.models import AuditLog, User
from app.services.user_gdpr_service import UserGdprService

pytestmark = [pytest.mark.unit]


@pytest.mark.unit
def test_anonymize_user_clears_pii_and_reserves_username(app, user):
    with app.app_context():
        original_username = user.username
        user.email = "erase-me@example.com"
        user.full_name = "Erase Me"
        db.session.commit()

        result = UserGdprService().anonymize_user(user_id=user.id, actor_id=user.id, reason="test")
        assert result["success"] is True

        db.session.expire_all()
        refreshed = db.session.get(User, user.id)
        assert refreshed.anonymized_at is not None
        assert refreshed.email is None
        assert refreshed.username.startswith("deleted_user_")
        assert refreshed.is_active is False
        assert refreshed.full_name.startswith("Anonymized User")

        from app.models.deleted_username import DeletedUsername

        reserved = DeletedUsername.query.filter_by(username=original_username.lower()).first()
        assert reserved is not None

        audit = AuditLog.query.filter_by(entity_type="user", entity_id=user.id, action="anonymized").first()
        assert audit is not None


@pytest.mark.unit
def test_anonymize_user_idempotent(app, user):
    with app.app_context():
        UserGdprService().anonymize_user(user_id=user.id, actor_id=user.id)
        again = UserGdprService().anonymize_user(user_id=user.id, actor_id=user.id)
        assert again["success"] is False
        assert again["error"] == "already_anonymized"
