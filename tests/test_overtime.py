"""
Tests for overtime calculation functionality
"""

import pytest
from datetime import datetime, timedelta, date
from app import db
from app.models import User, TimeEntry, Project, Client
from factories import UserFactory, ClientFactory, ProjectFactory, TimeEntryFactory
from app.utils.overtime import (
    calculate_daily_overtime,
    calculate_period_overtime,
    get_daily_breakdown,
    get_weekly_overtime_summary,
    get_overtime_statistics,
)


class TestOvertimeCalculations:
    """Test suite for overtime calculation utilities"""

    def test_calculate_daily_overtime_no_overtime(self):
        """Test that no overtime is calculated when hours are below standard"""
        result = calculate_daily_overtime(6.0, 8.0)
        assert result == 0.0

    def test_calculate_daily_overtime_exact_standard(self):
        """Test that no overtime is calculated when hours equal standard"""
        result = calculate_daily_overtime(8.0, 8.0)
        assert result == 0.0

    def test_calculate_daily_overtime_with_overtime(self):
        """Test overtime calculation when hours exceed standard"""
        result = calculate_daily_overtime(10.0, 8.0)
        assert result == 2.0

    def test_calculate_daily_overtime_large_overtime(self):
        """Test overtime calculation with significant overtime"""
        result = calculate_daily_overtime(14.5, 8.0)
        assert result == 6.5


class TestPeriodOvertime:
    """Test suite for period-based overtime calculations"""

    @pytest.fixture
    def test_user(self, app):
        """Create a test user with 8 hour standard day"""
        user = UserFactory()
        user.standard_hours_per_day = 8.0
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def test_client_obj(self, app):
        """Create a test client"""
        test_client = ClientFactory(name="Test Client OT")
        db.session.commit()
        return test_client

    @pytest.fixture
    def test_project(self, app, test_client_obj):
        """Create a test project"""
        project = ProjectFactory(client_id=test_client_obj.id, name="Test Project OT")
        db.session.commit()
        return project

    def test_period_overtime_no_entries(self, app, test_user):
        """Test period overtime calculation with no time entries"""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = calculate_period_overtime(test_user, start_date, end_date)

        assert result["regular_hours"] == 0.0
        assert result["overtime_hours"] == 0.0
        assert result["total_hours"] == 0.0
        assert result["days_with_overtime"] == 0

    def test_period_overtime_all_regular(self, app, test_user, test_project):
        """Test period with all regular hours (no overtime)"""
        start_date = date.today() - timedelta(days=2)

        # Create entries for 2 days with 7 hours each (below standard 8)
        for i in range(2):
            entry_date = start_date + timedelta(days=i)
            entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9))
            entry_end = entry_start + timedelta(hours=7)

            TimeEntryFactory(
                user_id=test_user.id,
                project_id=test_project.id,
                start_time=entry_start,
                end_time=entry_end,
                notes="Regular work",
            )

        db.session.commit()

        result = calculate_period_overtime(test_user, start_date, date.today())

        assert result["regular_hours"] == 14.0
        assert result["overtime_hours"] == 0.0
        assert result["total_hours"] == 14.0
        assert result["days_with_overtime"] == 0

    def test_period_overtime_with_overtime(self, app, test_user, test_project):
        """Test period with overtime hours"""
        start_date = date.today() - timedelta(days=2)

        # Day 1: 10 hours (2 hours overtime)
        entry_date = start_date
        entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9))
        entry_end = entry_start + timedelta(hours=10)

        TimeEntryFactory(
            user_id=test_user.id,
            project_id=test_project.id,
            start_time=entry_start,
            end_time=entry_end,
            notes="Long day",
        )

        # Day 2: 6 hours (no overtime)
        entry_date2 = start_date + timedelta(days=1)
        entry_start2 = datetime.combine(entry_date2, datetime.min.time().replace(hour=9))
        entry_end2 = entry_start2 + timedelta(hours=6)

        TimeEntryFactory(
            user_id=test_user.id,
            project_id=test_project.id,
            start_time=entry_start2,
            end_time=entry_end2,
            notes="Short day",
        )

        db.session.commit()

        result = calculate_period_overtime(test_user, start_date, date.today())

        assert result["regular_hours"] == 14.0  # 8 + 6
        assert result["overtime_hours"] == 2.0
        assert result["total_hours"] == 16.0
        assert result["days_with_overtime"] == 1

    def test_period_overtime_multiple_entries_same_day(self, app, test_user, test_project):
        """Test overtime calculation with multiple entries on the same day"""
        entry_date = date.today()

        # Create 3 entries totaling 10 hours (2 hours overtime)
        for i, hours in enumerate([4, 3, 3]):
            entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9 + i * 3))
            entry_end = entry_start + timedelta(hours=hours)

            TimeEntryFactory(
                user_id=test_user.id,
                project_id=test_project.id,
                start_time=entry_start,
                end_time=entry_end,
                notes=f"Entry {i+1}",
            )

        db.session.commit()

        result = calculate_period_overtime(test_user, entry_date, entry_date)

        assert result["regular_hours"] == 8.0
        assert result["overtime_hours"] == 2.0
        assert result["total_hours"] == 10.0
        assert result["days_with_overtime"] == 1


class TestDailyBreakdown:
    """Test suite for daily overtime breakdown"""

    @pytest.fixture
    def test_user_daily(self, app):
        """Create a test user"""
        user = UserFactory()
        user.standard_hours_per_day = 8.0
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def test_project_daily(self, app, test_client_obj):
        """Create a test project"""
        project = ProjectFactory(client_id=test_client_obj.id, name="Test Project Daily")
        db.session.commit()
        return project

    @pytest.fixture
    def test_client_obj(self, app):
        """Create a test client"""
        test_client = ClientFactory(name="Test Client Daily")
        db.session.commit()
        return test_client

    def test_daily_breakdown_empty(self, app, test_user_daily):
        """Test daily breakdown with no entries"""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = get_daily_breakdown(test_user_daily, start_date, end_date)

        assert len(result) == 0

    def test_daily_breakdown_with_entries(self, app, test_user_daily, test_project_daily):
        """Test daily breakdown with various entries"""
        start_date = date.today() - timedelta(days=2)

        # Day 1: 9 hours (1 hour overtime)
        entry1_start = datetime.combine(start_date, datetime.min.time().replace(hour=9))
        entry1_end = entry1_start + timedelta(hours=9)
        TimeEntryFactory(
            user_id=test_user_daily.id, project_id=test_project_daily.id, start_time=entry1_start, end_time=entry1_end
        )

        # Day 2: 6 hours (no overtime)
        entry2_start = datetime.combine(start_date + timedelta(days=1), datetime.min.time().replace(hour=9))
        entry2_end = entry2_start + timedelta(hours=6)
        TimeEntryFactory(
            user_id=test_user_daily.id, project_id=test_project_daily.id, start_time=entry2_start, end_time=entry2_end
        )

        db.session.commit()

        result = get_daily_breakdown(test_user_daily, start_date, date.today())

        assert len(result) == 2

        # Check day 1
        day1 = result[0]
        assert day1["total_hours"] == 9.0
        assert day1["regular_hours"] == 8.0
        assert day1["overtime_hours"] == 1.0
        assert day1["is_overtime"] is True

        # Check day 2
        day2 = result[1]
        assert day2["total_hours"] == 6.0
        assert day2["regular_hours"] == 6.0
        assert day2["overtime_hours"] == 0.0
        assert day2["is_overtime"] is False


class TestOvertimeStatistics:
    """Test suite for comprehensive overtime statistics"""

    @pytest.fixture
    def test_user_stats(self, app):
        """Create a test user"""
        user = UserFactory()
        user.standard_hours_per_day = 8.0
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def test_project_stats(self, app, test_client_obj):
        """Create a test project"""
        project = ProjectFactory(client_id=test_client_obj.id, name="Test Project Stats")
        db.session.commit()
        return project

    @pytest.fixture
    def test_client_obj(self, app):
        """Create a test client"""
        test_client = ClientFactory(name="Test Client Stats")
        db.session.commit()
        return test_client

    def test_overtime_statistics_comprehensive(self, app, test_user_stats, test_project_stats):
        """Test comprehensive overtime statistics"""
        start_date = date.today() - timedelta(days=4)

        # Create entries for multiple days with varying hours
        hours_per_day = [10, 7, 9, 6, 11]  # 5 days

        for i, hours in enumerate(hours_per_day):
            entry_date = start_date + timedelta(days=i)
            entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9))
            entry_end = entry_start + timedelta(hours=hours)

            TimeEntryFactory(
                user_id=test_user_stats.id, project_id=test_project_stats.id, start_time=entry_start, end_time=entry_end
            )

        db.session.commit()

        result = get_overtime_statistics(test_user_stats, start_date, date.today())

        # Verify structure
        assert "period" in result
        assert "hours" in result
        assert "days_statistics" in result
        assert "averages" in result
        assert "max_overtime" in result

        # Verify calculations
        # Total hours: 10 + 7 + 9 + 6 + 11 = 43
        # Days with overtime: 10 (2 OT), 9 (1 OT), 11 (3 OT) = 3 days
        # Total overtime: 2 + 1 + 3 = 6 hours
        # Regular: 43 - 6 = 37 hours

        assert result["hours"]["total_hours"] == 43.0
        assert result["hours"]["overtime_hours"] == 6.0
        assert result["hours"]["regular_hours"] == 37.0
        assert result["days_statistics"]["days_worked"] == 5
        assert result["days_statistics"]["days_with_overtime"] == 3

        # Max overtime should be 3 hours (from the 11-hour day)
        assert result["max_overtime"]["hours"] == 3.0


class TestUserModel:
    """Test suite for User model overtime-related functionality"""

    def test_user_has_standard_hours_field(self, app):
        """Test that User model has standard_hours_per_day field"""
        user = User(username="test_user_field", role="user")
        db.session.add(user)
        db.session.commit()

        # Check that field exists and has default value
        assert hasattr(user, "standard_hours_per_day")
        assert user.standard_hours_per_day == 8.0

    def test_user_can_set_custom_standard_hours(self, app):
        """Test that standard hours can be customized"""
        user = User(username="test_user_custom", role="user")
        user.standard_hours_per_day = 7.5
        db.session.add(user)
        db.session.commit()

        # Reload from database
        user_reloaded = User.query.filter_by(username="test_user_custom").first()
        assert user_reloaded.standard_hours_per_day == 7.5

    def test_user_standard_hours_validation_min(self, app):
        """Test that standard hours can be set to minimum value"""
        user = User(username="test_user_min", role="user")
        user.standard_hours_per_day = 0.5
        db.session.add(user)
        db.session.commit()

        assert user.standard_hours_per_day == 0.5

    def test_user_standard_hours_validation_max(self, app):
        """Test that standard hours can be set to maximum value"""
        user = User(username="test_user_max", role="user")
        user.standard_hours_per_day = 24.0
        db.session.add(user)
        db.session.commit()

        assert user.standard_hours_per_day == 24.0


class TestWeeklyOvertimeSummary:
    """Test suite for weekly overtime summaries"""

    @pytest.fixture
    def test_user_weekly(self, app):
        """Create a test user"""
        user = User(username="test_user_weekly", role="user")
        user.standard_hours_per_day = 8.0
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def test_project_weekly(self, app, test_client_obj):
        """Create a test project"""
        project = Project(name="Test Project Weekly", client_id=test_client_obj.id)
        db.session.add(project)
        db.session.commit()
        return project

    @pytest.fixture
    def test_client_obj(self, app):
        """Create a test client"""
        test_client = Client(name="Test Client Weekly")
        db.session.add(test_client)
        db.session.commit()
        return test_client

    def test_weekly_summary_empty(self, app, test_user_weekly):
        """Test weekly summary with no entries"""
        result = get_weekly_overtime_summary(test_user_weekly, weeks=2)
        assert len(result) == 0

    def test_weekly_summary_with_data(self, app, test_user_weekly, test_project_weekly):
        """Test weekly summary with entries across multiple weeks"""
        # Create entries for the past 2 weeks
        for week in range(2):
            for day in range(5):  # 5 working days
                entry_date = date.today() - timedelta(weeks=1 - week, days=day)
                entry_start = datetime.combine(entry_date, datetime.min.time().replace(hour=9))
                entry_end = entry_start + timedelta(hours=9)  # 9 hours per day (1 hour OT)

                entry = TimeEntry(
                    user_id=test_user_weekly.id,
                    project_id=test_project_weekly.id,
                    start_time=entry_start,
                    end_time=entry_end,
                )
                db.session.add(entry)

        db.session.commit()

        result = get_weekly_overtime_summary(test_user_weekly, weeks=2)

        # Should have data for weeks with entries
        assert len(result) > 0

        # Each week should have proper structure
        for week_data in result:
            assert "week_start" in week_data
            assert "week_end" in week_data
            assert "regular_hours" in week_data
            assert "overtime_hours" in week_data
            assert "total_hours" in week_data
            assert "days_worked" in week_data
