"""
Smoke tests for overtime feature
Quick tests to verify basic overtime functionality is working
"""

import pytest
from datetime import datetime, timedelta, date
from app import db
from app.models import User, TimeEntry, Project, Client
from factories import UserFactory, ClientFactory, ProjectFactory, TimeEntryFactory
from app.utils.overtime import calculate_daily_overtime, calculate_period_overtime


class TestOvertimeSmoke:
    """Smoke tests for overtime feature"""

    def test_overtime_utils_import(self):
        """Smoke test: verify overtime utilities can be imported"""
        from app.utils import overtime

        assert hasattr(overtime, "calculate_daily_overtime")
        assert hasattr(overtime, "calculate_period_overtime")
        assert hasattr(overtime, "get_daily_breakdown")
        assert hasattr(overtime, "get_weekly_overtime_summary")
        assert hasattr(overtime, "get_overtime_statistics")

    def test_user_model_has_standard_hours(self, app):
        """Smoke test: verify User model has standard_hours_per_day field"""
        user = UserFactory(username="smoke_test_user")
        assert hasattr(user, "standard_hours_per_day")
        assert user.standard_hours_per_day == 8.0  # Default value

    def test_basic_overtime_calculation(self):
        """Smoke test: verify basic overtime calculation works"""
        # 10 hours worked with 8 hour standard = 2 hours overtime
        overtime = calculate_daily_overtime(10.0, 8.0)
        assert overtime == 2.0

    def test_no_overtime_calculation(self):
        """Smoke test: verify no overtime when under standard hours"""
        overtime = calculate_daily_overtime(6.0, 8.0)
        assert overtime == 0.0

    def test_period_overtime_basic(self, app):
        """Smoke test: verify period overtime calculation doesn't crash"""
        # Create a test user
        user = UserFactory(username="smoke_period_user")
        user.standard_hours_per_day = 8.0
        db.session.add(user)
        db.session.commit()

        # Calculate overtime for a period with no entries
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = calculate_period_overtime(user, start_date, end_date)

        # Should return valid structure even with no data
        assert "regular_hours" in result
        assert "overtime_hours" in result
        assert "total_hours" in result
        assert "days_with_overtime" in result
        assert result["overtime_hours"] == 0.0

    def test_settings_route_accessible(self, app):
        """Smoke test: verify settings page is accessible"""
        from app.routes.user import settings

        # Just verify the route exists and is importable
        assert settings is not None

    def test_user_report_route_exists(self, app):
        """Smoke test: verify user report route exists"""
        from app.routes.reports import user_report

        assert user_report is not None

    def test_analytics_overtime_route_exists(self, app):
        """Smoke test: verify analytics overtime route exists"""
        from app.routes.analytics import overtime_analytics

        assert overtime_analytics is not None

    def test_overtime_calculation_with_real_entry(self, app):
        """Smoke test: verify overtime calculation with a real time entry"""
        # Create test data
        user = UserFactory(username="smoke_entry_user")
        user.standard_hours_per_day = 8.0
        db.session.add(user)

        client_obj = ClientFactory(name="Smoke Test Client")
        db.session.commit()

        project = ProjectFactory(name="Smoke Test Project", client_id=client_obj.id)
        db.session.commit()

        # Create a 10-hour time entry (should result in 2 hours overtime)
        entry_date = date.today()
        entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9))
        entry_end = entry_start + timedelta(hours=10)

        TimeEntryFactory(
            user_id=user.id, project_id=project.id, start_time=entry_start, end_time=entry_end, notes="Smoke test entry"
        )
        db.session.commit()

        # Calculate overtime
        result = calculate_period_overtime(user, entry_date, entry_date)

        assert result["total_hours"] == 10.0
        assert result["regular_hours"] == 8.0
        assert result["overtime_hours"] == 2.0
        assert result["days_with_overtime"] == 1

    def test_migration_file_exists(self):
        """Smoke test: verify migration file exists"""
        import os

        migration_path = "migrations/versions/031_add_standard_hours_per_day.py"
        assert os.path.exists(migration_path), f"Migration file not found: {migration_path}"

    def test_overtime_template_fields(self, app):
        """Smoke test: verify settings template has overtime field"""
        import os

        template_path = "app/templates/user/settings.html"
        assert os.path.exists(template_path)

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "standard_hours_per_day" in content, "Settings template missing overtime field"
            assert "Overtime Settings" in content, "Settings template missing overtime section"


class TestOvertimeIntegration:
    """Integration tests for overtime feature"""

    def test_full_overtime_workflow(self, app):
        """Integration test: full overtime calculation workflow"""
        # 1. Create user with custom standard hours
        user = UserFactory(username="integration_user")
        user.standard_hours_per_day = 7.5  # 7.5 hour workday
        db.session.add(user)

        # 2. Create client and project
        client_obj = ClientFactory(name="Integration Client")
        db.session.commit()

        project = ProjectFactory(name="Integration Project", client_id=client_obj.id)
        db.session.commit()

        # 3. Create time entries over multiple days
        start_date = date.today() - timedelta(days=4)

        # Day 1: 9 hours (1.5 hours overtime)
        entry1_start = datetime.combine(start_date, datetime.min.time().replace(hour=9))
        entry1_end = entry1_start + timedelta(hours=9)
        TimeEntryFactory(user_id=user.id, project_id=project.id, start_time=entry1_start, end_time=entry1_end)

        # Day 2: 7 hours (no overtime)
        entry2_start = datetime.combine(start_date + timedelta(days=1), datetime.min.time().replace(hour=9))
        entry2_end = entry2_start + timedelta(hours=7)
        TimeEntryFactory(user_id=user.id, project_id=project.id, start_time=entry2_start, end_time=entry2_end)

        # Day 3: 10 hours (2.5 hours overtime)
        entry3_start = datetime.combine(start_date + timedelta(days=2), datetime.min.time().replace(hour=9))
        entry3_end = entry3_start + timedelta(hours=10)
        TimeEntryFactory(user_id=user.id, project_id=project.id, start_time=entry3_start, end_time=entry3_end)

        db.session.commit()

        # 4. Calculate period overtime
        result = calculate_period_overtime(user, start_date, date.today())

        # 5. Verify results
        # Total: 9 + 7 + 10 = 26 hours
        # Overtime: 1.5 + 0 + 2.5 = 4 hours
        # Regular: 26 - 4 = 22 hours
        assert result["total_hours"] == 26.0
        assert result["overtime_hours"] == 4.0
        assert result["regular_hours"] == 22.0
        assert result["days_with_overtime"] == 2

        # 6. Verify daily breakdown
        from app.utils.overtime import get_daily_breakdown

        breakdown = get_daily_breakdown(user, start_date, date.today())

        assert len(breakdown) == 3
        assert breakdown[0]["overtime_hours"] == 1.5  # Day 1
        assert breakdown[1]["overtime_hours"] == 0.0  # Day 2
        assert breakdown[2]["overtime_hours"] == 2.5  # Day 3

    def test_different_standard_hours_between_users(self, app):
        """Integration test: different users with different standard hours"""
        # User 1: 8 hour standard
        user1 = UserFactory(username="user_8h")
        user1.standard_hours_per_day = 8.0
        db.session.add(user1)

        # User 2: 6 hour standard (part-time)
        user2 = UserFactory(username="user_6h")
        user2.standard_hours_per_day = 6.0
        db.session.add(user2)

        # Create client and project
        client_obj = ClientFactory(name="Multi User Client")
        db.session.commit()

        project = ProjectFactory(name="Multi User Project", client_id=client_obj.id)
        db.session.commit()

        # Both users work 7 hours today
        today = date.today()
        entry_start = datetime.combine(today, datetime.min.time().replace(hour=9))
        entry_end = entry_start + timedelta(hours=7)

        TimeEntryFactory(user_id=user1.id, project_id=project.id, start_time=entry_start, end_time=entry_end)

        TimeEntryFactory(user_id=user2.id, project_id=project.id, start_time=entry_start, end_time=entry_end)

        db.session.commit()

        # Calculate overtime for both users
        result1 = calculate_period_overtime(user1, today, today)
        result2 = calculate_period_overtime(user2, today, today)

        # User 1: 7 hours, no overtime (under 8)
        assert result1["overtime_hours"] == 0.0
        assert result1["regular_hours"] == 7.0

        # User 2: 7 hours, 1 hour overtime (over 6)
        assert result2["overtime_hours"] == 1.0
        assert result2["regular_hours"] == 6.0
