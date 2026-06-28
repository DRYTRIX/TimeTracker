"""Tests for deleted username blocklist (issue #677)."""

import pytest
from flask import url_for

from app import db
from app.models import DeletedUsername, Settings, User
from app.utils.deleted_usernames import is_username_reserved, reserve_deleted_username

pytestmark = [pytest.mark.integration]


class TestDeletedUsernameHelpers:
    def test_reserve_and_check_username(self, app):
        with app.app_context():
            reserve_deleted_username("former_user", deleted_by_user_id=None)
            db.session.commit()
            assert is_username_reserved("former_user") is True
            assert is_username_reserved("Former_User") is True
            assert is_username_reserved("other") is False

    def test_reserve_updates_existing_entry(self, app):
        with app.app_context():
            reserve_deleted_username("repeat_user")
            db.session.commit()
            first = DeletedUsername.query.filter_by(username="repeat_user").first()
            first_deleted_at = first.deleted_at

            reserve_deleted_username("repeat_user")
            db.session.commit()
            second = DeletedUsername.query.filter_by(username="repeat_user").first()
            assert second.deleted_at >= first_deleted_at


class TestDeletedUsernameOnAdminDelete:
    def test_delete_user_reserves_username(self, client, admin_user, app):
        with app.app_context():
            doomed = User(username="deleteme_block", role="user")
            doomed.is_active = True
            db.session.add(doomed)
            db.session.commit()
            user_id = doomed.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)
            response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)
            assert response.status_code == 200

        with app.app_context():
            assert User.query.get(user_id) is None
            assert is_username_reserved("deleteme_block") is True


class TestDeletedUsernameBlocksSelfRegistration:
    def test_deleted_username_not_recreated_on_login(self, client, admin_user, app):
        with app.app_context():
            settings = Settings.get_settings()
            settings.allow_self_register = True
            db.session.commit()

            doomed = User(username="blocked_login", role="user")
            doomed.is_active = True
            db.session.add(doomed)
            db.session.commit()
            user_id = doomed.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)
            client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

            resp = client.post(
                "/login",
                data={"username": "blocked_login", "password": "newpassword123"},
                follow_redirects=True,
            )
            assert resp.status_code == 200

        with app.app_context():
            assert User.query.filter_by(username="blocked_login").first() is None
            assert is_username_reserved("blocked_login") is True
