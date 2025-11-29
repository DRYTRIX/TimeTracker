"""
Comprehensive tests for user settings routes and functionality.
Tests settings page rendering, form validation, preference updates, and API endpoints.
"""

import pytest
from flask import url_for
from app.models import User
from app import db
import pytz


class TestUserSettingsPage:
    """Tests for the user settings page GET endpoint"""

    def test_settings_page_requires_login(self, client):
        """Test that settings page redirects to login if not authenticated"""
        response = client.get("/settings", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_settings_page_loads_for_authenticated_user(self, client, user):
        """Test that settings page loads successfully for authenticated users"""
        # Log in the user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Settings" in response.data
        assert b"Notification Preferences" in response.data
        assert b"Display Preferences" in response.data
        assert b"Regional Settings" in response.data

    def test_settings_page_displays_current_values(self, client, user):
        """Test that settings page displays user's current settings"""
        # Set some specific settings
        user.theme_preference = "dark"
        user.timezone = "America/New_York"
        user.date_format = "MM/DD/YYYY"
        user.email_notifications = True
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        assert response.status_code == 200
        data = response.data.decode("utf-8")

        # Check that current values are selected
        assert 'value="dark" selected' in data or 'value="dark"' in data
        assert "America/New_York" in data
        assert "email_notifications" in data

    def test_settings_page_includes_all_sections(self, client, user):
        """Test that all settings sections are present on the page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        data = response.data.decode("utf-8")

        # Check for all major sections
        assert "Profile Information" in data
        assert "Notification Preferences" in data
        assert "Display Preferences" in data
        assert "Time Rounding Preferences" in data
        assert "Overtime Settings" in data
        assert "UI Customization" in data
        assert "Regional Settings" in data


class TestUserSettingsUpdate:
    """Tests for updating user settings via POST"""

    def test_update_profile_information(self, client, user):
        """Test updating profile information (full name and email)"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings", data={"full_name": "John Doe", "email": "john.doe@example.com"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Settings saved successfully" in response.data

        # Verify changes in database
        db.session.refresh(user)
        assert user.full_name == "John Doe"
        assert user.email == "john.doe@example.com"

    def test_update_notification_preferences(self, client, user):
        """Test updating email notification preferences"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={
                "email_notifications": "on",
                "notification_overdue_invoices": "on",
                "notification_task_assigned": "on",
                "notification_task_comments": "on",
                "notification_weekly_summary": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify changes
        db.session.refresh(user)
        assert user.email_notifications is True
        assert user.notification_overdue_invoices is True
        assert user.notification_task_assigned is True
        assert user.notification_task_comments is True
        assert user.notification_weekly_summary is True

    def test_update_notification_preferences_all_disabled(self, client, user):
        """Test disabling all notification preferences"""
        # First enable them
        user.email_notifications = True
        user.notification_overdue_invoices = True
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # POST without checkbox values (unchecked checkboxes don't send values)
        response = client.post("/settings", data={"full_name": user.full_name or ""}, follow_redirects=True)

        assert response.status_code == 200

        # Verify all notifications are disabled
        db.session.refresh(user)
        assert user.email_notifications is False
        assert user.notification_overdue_invoices is False
        assert user.notification_task_assigned is False
        assert user.notification_task_comments is False
        assert user.notification_weekly_summary is False

    def test_update_theme_preference(self, client, user):
        """Test updating theme preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Test setting dark theme
        response = client.post("/settings", data={"theme_preference": "dark"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.theme_preference == "dark"

        # Test setting light theme
        response = client.post("/settings", data={"theme_preference": "light"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.theme_preference == "light"

        # Test setting system default (empty string)
        response = client.post("/settings", data={"theme_preference": ""}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.theme_preference is None

    def test_update_timezone(self, client, user):
        """Test updating timezone preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"timezone": "America/New_York"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.timezone == "America/New_York"

    def test_update_timezone_with_invalid_value(self, client, user):
        """Test that invalid timezone is rejected"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"timezone": "Invalid/Timezone"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Invalid timezone selected" in response.data

    def test_update_date_format(self, client, user):
        """Test updating date format preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        for date_format in ["YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY", "DD.MM.YYYY"]:
            response = client.post("/settings", data={"date_format": date_format}, follow_redirects=True)

            assert response.status_code == 200
            db.session.refresh(user)
            assert user.date_format == date_format

    def test_update_time_format(self, client, user):
        """Test updating time format preference (12h/24h)"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Test 24-hour format
        response = client.post("/settings", data={"time_format": "24h"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.time_format == "24h"

        # Test 12-hour format
        response = client.post("/settings", data={"time_format": "12h"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.time_format == "12h"

    def test_update_week_start_day(self, client, user):
        """Test updating week start day preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Test Monday (1)
        response = client.post("/settings", data={"week_start_day": "1"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.week_start_day == 1

        # Test Sunday (0)
        response = client.post("/settings", data={"week_start_day": "0"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.week_start_day == 0

    def test_update_time_rounding_preferences(self, client, user):
        """Test updating time rounding preferences"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={"time_rounding_enabled": "on", "time_rounding_minutes": "15", "time_rounding_method": "up"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.time_rounding_enabled is True
        assert user.time_rounding_minutes == 15
        assert user.time_rounding_method == "up"

    def test_update_time_rounding_intervals(self, client, user):
        """Test all valid time rounding intervals"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        valid_intervals = [1, 5, 10, 15, 30, 60]

        for interval in valid_intervals:
            response = client.post(
                "/settings",
                data={"time_rounding_enabled": "on", "time_rounding_minutes": str(interval)},
                follow_redirects=True,
            )

            assert response.status_code == 200
            db.session.refresh(user)
            assert user.time_rounding_minutes == interval

    def test_update_time_rounding_methods(self, client, user):
        """Test all valid time rounding methods"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        valid_methods = ["nearest", "up", "down"]

        for method in valid_methods:
            response = client.post(
                "/settings", data={"time_rounding_enabled": "on", "time_rounding_method": method}, follow_redirects=True
            )

            assert response.status_code == 200
            db.session.refresh(user)
            assert user.time_rounding_method == method

    def test_update_standard_hours_per_day(self, client, user):
        """Test updating standard hours per day for overtime calculation"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"standard_hours_per_day": "7.5"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.standard_hours_per_day == 7.5

    def test_update_standard_hours_validation(self, client, user):
        """Test validation of standard hours per day (must be between 0.5 and 24)"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Test too low
        response = client.post("/settings", data={"standard_hours_per_day": "0.2"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Standard hours per day must be between 0.5 and 24" in response.data

        # Test too high
        response = client.post("/settings", data={"standard_hours_per_day": "25"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Standard hours per day must be between 0.5 and 24" in response.data

    def test_update_language_preference(self, client, user):
        """Test updating language preference"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/settings", data={"preferred_language": "de"}, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(user)
        assert user.preferred_language == "de"

    def test_update_multiple_settings_at_once(self, client, user):
        """Test updating multiple settings in a single request"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={
                "full_name": "Jane Smith",
                "email": "jane@example.com",
                "theme_preference": "dark",
                "timezone": "Europe/London",
                "date_format": "DD/MM/YYYY",
                "time_format": "24h",
                "email_notifications": "on",
                "time_rounding_enabled": "on",
                "time_rounding_minutes": "15",
                "standard_hours_per_day": "8",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Settings saved successfully" in response.data

        # Verify all changes
        db.session.refresh(user)
        assert user.full_name == "Jane Smith"
        assert user.email == "jane@example.com"
        assert user.theme_preference == "dark"
        assert user.timezone == "Europe/London"
        assert user.date_format == "DD/MM/YYYY"
        assert user.time_format == "24h"
        assert user.email_notifications is True
        assert user.time_rounding_enabled is True
        assert user.time_rounding_minutes == 15
        assert user.standard_hours_per_day == 8.0


class TestUserSettingsAPIEndpoints:
    """Tests for API endpoints for updating preferences"""

    def test_update_preferences_api_requires_login(self, client):
        """Test that API endpoint requires authentication"""
        response = client.patch("/api/preferences", json={"theme_preference": "dark"})
        assert response.status_code == 302  # Redirect to login

    def test_update_theme_via_api(self, client, user):
        """Test updating theme via AJAX API"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.patch("/api/preferences", json={"theme_preference": "dark"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        db.session.refresh(user)
        assert user.theme_preference == "dark"

    def test_update_email_notifications_via_api(self, client, user):
        """Test updating email notifications via API"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.patch("/api/preferences", json={"email_notifications": False})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        db.session.refresh(user)
        assert user.email_notifications is False

    def test_update_timezone_via_api(self, client, user):
        """Test updating timezone via API"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.patch("/api/preferences", json={"timezone": "Asia/Tokyo"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        db.session.refresh(user)
        assert user.timezone == "Asia/Tokyo"

    def test_update_invalid_timezone_via_api(self, client, user):
        """Test that API rejects invalid timezone"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.patch("/api/preferences", json={"timezone": "Invalid/Zone"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_update_ui_feature_flags(self, client, user):
        """Test updating UI feature flags"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={
                "ui_show_inventory": "on",
                "ui_show_mileage": "on",
                # ui_show_per_diem and ui_show_kanban_board not checked (should be False)
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Settings saved successfully" in response.data

        # Verify changes
        db.session.refresh(user)
        assert user.ui_show_inventory is True
        assert user.ui_show_mileage is True
        assert user.ui_show_per_diem is False
        assert user.ui_show_kanban_board is False

    def test_ui_feature_flags_default_to_true(self, client, user):
        """Test that UI feature flags default to True for new users"""
        # Create a new user
        new_user = User(username="newuser", email="newuser@example.com")
        new_user.set_password("password")
        db.session.add(new_user)
        db.session.commit()

        # Check defaults
        assert new_user.ui_show_inventory is True
        assert new_user.ui_show_mileage is True
        assert new_user.ui_show_per_diem is True
        assert new_user.ui_show_kanban_board is True

    def test_settings_page_includes_ui_customization_section(self, client, user):
        """Test that settings page includes UI customization section"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        data = response.data.decode("utf-8")

        # Check for UI customization section and key flags
        assert "UI Customization" in data
        assert "ui_show_inventory" in data
        assert "ui_show_mileage" in data
        assert "ui_show_per_diem" in data
        assert "ui_show_kanban_board" in data
        assert "ui_show_calendar" in data
        assert "ui_show_quotes" in data
        assert "ui_show_reports" in data
        assert "ui_show_analytics" in data
        assert "ui_show_tools" in data

    def test_update_ui_feature_flags(self, client, user):
        """Test updating UI feature flags"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post(
            "/settings",
            data={
                "ui_show_inventory": "on",
                "ui_show_mileage": "on",
                "ui_show_calendar": "on",
                "ui_show_quotes": "on",
                # Other flags not checked (should be False)
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Settings saved successfully" in response.data

        # Verify changes
        db.session.refresh(user)
        assert user.ui_show_inventory is True
        assert user.ui_show_mileage is True
        assert user.ui_show_calendar is True
        assert user.ui_show_quotes is True
        assert user.ui_show_per_diem is False
        assert user.ui_show_kanban_board is False
        assert user.ui_show_reports is False

    def test_ui_feature_flags_default_to_true(self, client, user):
        """Test that UI feature flags default to True for new users"""
        # Create a new user
        new_user = User(username="newuser", email="newuser@example.com")
        new_user.set_password("password")
        db.session.add(new_user)
        db.session.commit()

        # Check defaults - all should be True
        assert new_user.ui_show_inventory is True
        assert new_user.ui_show_mileage is True
        assert new_user.ui_show_per_diem is True
        assert new_user.ui_show_kanban_board is True
        assert new_user.ui_show_calendar is True
        assert new_user.ui_show_project_templates is True
        assert new_user.ui_show_gantt_chart is True
        assert new_user.ui_show_weekly_goals is True
        assert new_user.ui_show_quotes is True
        assert new_user.ui_show_reports is True
        assert new_user.ui_show_analytics is True
        assert new_user.ui_show_tools is True

    def test_settings_page_includes_ui_customization_section(self, client, user):
        """Test that settings page includes UI customization section"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/settings")
        data = response.data.decode("utf-8")

        # Check for UI customization section and key flags
        assert "UI Customization" in data
        assert "ui_show_inventory" in data
        assert "ui_show_mileage" in data
        assert "ui_show_per_diem" in data
        assert "ui_show_kanban_board" in data
        assert "ui_show_calendar" in data
        assert "ui_show_quotes" in data
        assert "ui_show_reports" in data
        assert "ui_show_analytics" in data
        assert "ui_show_tools" in data

    def test_set_theme_api_endpoint(self, client, user):
        """Test the dedicated theme switcher API endpoint"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Test setting dark theme
        response = client.post("/api/theme", json={"theme": "dark"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["theme"] == "dark"

        db.session.refresh(user)
        assert user.theme_preference == "dark"

        # Test setting system default
        response = client.post("/api/theme", json={"theme": ""})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["theme"] == "system"

        db.session.refresh(user)
        assert user.theme_preference is None

    def test_set_invalid_theme_via_api(self, client, user):
        """Test that API rejects invalid theme values"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/api/theme", json={"theme": "invalid"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestUserSettingsIntegration:
    """Integration tests for user settings feature"""

    def test_settings_persist_across_sessions(self, client, user):
        """Test that settings persist after saving and reloading"""
        # Save settings
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        client.post(
            "/settings",
            data={
                "full_name": "Test User",
                "email": "test@example.com",
                "theme_preference": "dark",
                "timezone": "America/Los_Angeles",
                "date_format": "MM/DD/YYYY",
                "email_notifications": "on",
                "time_rounding_enabled": "on",
                "time_rounding_minutes": "15",
                "standard_hours_per_day": "8",
            },
            follow_redirects=True,
        )

        # Reload page and verify settings are still there
        response = client.get("/settings")
        data = response.data.decode("utf-8")

        assert "Test User" in data
        assert "test@example.com" in data
        assert "America/Los_Angeles" in data

    def test_default_settings_for_new_user(self, app):
        """Test that new users get appropriate default settings"""
        with app.app_context():
            new_user = User(username="newuser", role="user")
            db.session.add(new_user)
            db.session.commit()

            # Check defaults
            assert new_user.email_notifications is True
            assert new_user.notification_overdue_invoices is True
            assert new_user.notification_task_assigned is True
            assert new_user.notification_task_comments is True
            assert new_user.notification_weekly_summary is False
            assert new_user.date_format == "YYYY-MM-DD"
            assert new_user.time_format == "24h"
            assert new_user.week_start_day == 1
            assert new_user.time_rounding_enabled is True
            assert new_user.time_rounding_minutes == 1
            assert new_user.time_rounding_method == "nearest"
            assert new_user.standard_hours_per_day == 8.0

    def test_settings_form_csrf_protection(self, app):
        """Test that settings form is protected with CSRF token"""
        # Create app with CSRF enabled
        app.config["WTF_CSRF_ENABLED"] = True
        client = app.test_client()

        # Create a test user
        with app.app_context():
            user = User(username="testuser", role="user")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)

        # Verify CSRF token is present in the form
        response = client.get("/settings")
        assert b"csrf_token" in response.data or b"CSRF" in response.data
