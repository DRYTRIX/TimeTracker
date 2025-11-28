"""
Smoke tests for user settings feature.
Quick validation tests to ensure the feature is working at a basic level.
"""

import pytest
from flask import url_for
from app.models import User
from app import db


class TestUserSettingsSmokeTests:
    """Smoke tests for user settings functionality"""

    def test_settings_page_accessible(self, client, user):
        """Smoke test: Settings page loads without errors"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        assert response.status_code == 200, "Settings page should load successfully"

    def test_can_update_basic_profile(self, client, user):
        """Smoke test: Can update basic profile information"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings", data={"full_name": "Smoke Test User", "email": "smoke@test.com"}, follow_redirects=True
        )

        assert response.status_code == 200, "Settings update should succeed"
        assert b"Settings saved successfully" in response.data or b"saved" in response.data.lower()

        # Verify changes
        db.session.refresh(user)
        assert user.full_name == "Smoke Test User"
        assert user.email == "smoke@test.com"

    def test_can_toggle_notifications(self, client, user):
        """Smoke test: Can toggle email notifications on/off"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Enable notifications
        response = client.post("/settings", data={"email_notifications": "on"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.email_notifications is True, "Should enable notifications"

        # Disable notifications
        response = client.post(
            "/settings",
            data={
                # No email_notifications key = unchecked
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.email_notifications is False, "Should disable notifications"

    def test_can_change_theme(self, client, user):
        """Smoke test: Can change theme preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Set to dark theme
        response = client.post("/settings", data={"theme_preference": "dark"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.theme_preference == "dark"

    def test_can_change_timezone(self, client, user):
        """Smoke test: Can change timezone"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"timezone": "America/New_York"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.timezone == "America/New_York"

    def test_can_change_date_format(self, client, user):
        """Smoke test: Can change date format"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"date_format": "DD/MM/YYYY"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.date_format == "DD/MM/YYYY"

    def test_can_enable_time_rounding(self, client, user):
        """Smoke test: Can enable and configure time rounding"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={"time_rounding_enabled": "on", "time_rounding_minutes": "15", "time_rounding_method": "nearest"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.time_rounding_enabled is True
        assert user.time_rounding_minutes == 15
        assert user.time_rounding_method == "nearest"

    def test_can_set_standard_hours(self, client, user):
        """Smoke test: Can set standard hours per day"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"standard_hours_per_day": "7.5"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.standard_hours_per_day == 7.5

    def test_theme_api_works(self, client, user):
        """Smoke test: Theme API endpoint works"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/api/theme", json={"theme": "dark"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        db.session.refresh(user)
        assert user.theme_preference == "dark"

    def test_preferences_api_works(self, client, user):
        """Smoke test: Preferences API endpoint works"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.patch("/api/preferences", json={"email_notifications": False})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        db.session.refresh(user)
        assert user.email_notifications is False

    def test_settings_page_has_required_forms(self, client, user):
        """Smoke test: Settings page contains all required form elements"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        data = response.data.decode("utf-8")

        # Check for form fields
        assert "full_name" in data
        assert "email" in data
        assert "theme_preference" in data
        assert "timezone" in data
        assert "date_format" in data
        assert "time_format" in data
        assert "email_notifications" in data
        assert "time_rounding_enabled" in data
        assert "standard_hours_per_day" in data

    def test_invalid_timezone_rejected(self, client, user):
        """Smoke test: Invalid timezone is properly rejected"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"timezone": "NotAValidTimezone"}, follow_redirects=True)

        assert response.status_code == 200
        # Should show error message
        assert b"Invalid timezone" in response.data or b"error" in response.data.lower()

    def test_invalid_hours_rejected(self, client, user):
        """Smoke test: Invalid standard hours value is rejected"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings", data={"standard_hours_per_day": "100"}, follow_redirects=True  # Way too high
        )

        assert response.status_code == 200
        # Should show validation error
        assert b"between 0.5 and 24" in response.data or b"error" in response.data.lower()

    def test_settings_persist_after_save(self, client, user):
        """Smoke test: Settings persist after saving"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Save settings
        client.post(
            "/settings",
            data={"full_name": "Persistent User", "theme_preference": "dark", "timezone": "Europe/London"},
            follow_redirects=True,
        )

        # Reload page
        response = client.get("/settings")
        data = response.data.decode("utf-8")

        # Verify values are still there
        assert "Persistent User" in data
        assert "Europe/London" in data
