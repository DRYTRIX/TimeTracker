import pytest
from flask import url_for

from app.models import Settings, User
from app import db


class TestSystemUiFlags:
    def test_calendar_hidden_when_system_disabled(self, client, user):
        """If calendar is disabled system-wide, it should not appear in nav or user settings."""
        # Disable calendar system-wide
        settings = Settings.get_settings()
        settings.ui_allow_calendar = False
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Settings page should not contain the calendar checkbox
        resp = client.get("/settings")
        data = resp.data.decode("utf-8")
        assert "ui_show_calendar" not in data

        # Sidebar nav should not show Calendar section label
        resp = client.get(url_for("main.dashboard"))
        nav = resp.data.decode("utf-8")
        assert "Calendar" not in nav



