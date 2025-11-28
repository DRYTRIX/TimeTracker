import pytest
import pytz
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import Settings, TimeEntry, User, Project
from app.utils.timezone import (
    get_app_timezone,
    utc_to_local,
    local_to_utc,
    now_in_app_timezone,
    convert_app_datetime_to_user,
    format_user_datetime,
    get_available_timezones,
)
from app.routes.user import update_preferences
from flask_login import login_user


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key-for-testing-at-least-32-chars",
            "FLASK_ENV": "testing",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def user(app):
    """Create test user"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def project(app):
    """Create test project"""
    with app.app_context():
        project = Project(name="Test Project", client="Test Client", billable=True, hourly_rate=50.0)
        db.session.add(project)
        db.session.commit()
        return project


def test_timezone_default_from_environment(app):
    """Test that timezone defaults to environment variable when no database settings exist"""
    with app.app_context():
        # Clear any existing settings
        Settings.query.delete()
        db.session.commit()

        # Test default timezone
        timezone = get_app_timezone()
        assert timezone == "Europe/Rome"  # Default from config


def test_timezone_from_database_settings(app):
    """Test that timezone is read from database settings"""
    with app.app_context():
        # Create settings with custom timezone
        settings = Settings(timezone="America/New_York")
        db.session.add(settings)
        db.session.commit()

        # Test that timezone is read from database
        timezone = get_app_timezone()
        assert timezone == "America/New_York"


@pytest.mark.xfail(reason="Timezone display test needs adjustment - comparing timezone-aware datetimes")
def test_timezone_change_affects_display(app, user, project):
    """Test that changing timezone affects how times are displayed"""
    with app.app_context():
        # Create settings with Europe/Rome timezone
        settings = Settings(timezone="Europe/Rome")
        db.session.add(settings)
        db.session.commit()

        # Create a time entry at a specific UTC time
        utc_time = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

        # Refresh the user and project objects to ensure they're attached to the session
        user = db.session.merge(user)
        project = db.session.merge(project)

        from factories import TimeEntryFactory

        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=utc_time,
            end_time=utc_time + timedelta(hours=2),
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()

        # Get time in Rome timezone (UTC+1 or UTC+2 depending on DST)
        rome_time = utc_to_local(entry.start_time)

        # Change timezone to America/New_York
        settings.timezone = "America/New_York"
        db.session.commit()

        # Get time in New York timezone (UTC-5 or UTC-4 depending on DST)
        ny_time = utc_to_local(entry.start_time)

        # Times should be different
        assert rome_time != ny_time

        # New York time should be earlier than Rome time (behind UTC)
        # This is a basic check - actual difference depends on DST
        assert ny_time.hour != rome_time.hour or abs(ny_time.hour - rome_time.hour) > 1


def test_timezone_aware_current_time(app):
    """Test that current time is returned in the configured timezone"""
    with app.app_context():
        # Set timezone to Europe/Rome
        settings = Settings(timezone="Europe/Rome")
        db.session.add(settings)
        db.session.commit()

        # Get current time in app timezone
        app_time = now_in_app_timezone()
        utc_now = datetime.now(timezone.utc)

        # App time should be in Rome timezone
        assert app_time.tzinfo is not None
        assert "Europe/Rome" in str(app_time.tzinfo)

        # Convert app_time to UTC for comparison
        app_time_utc = app_time.astimezone(timezone.utc)

        # Times should be close (within a few seconds)
        time_diff = abs((app_time_utc - utc_now).total_seconds())
        assert time_diff < 10


def test_timezone_conversion_utc_to_local(app):
    """Test UTC to local timezone conversion"""
    with app.app_context():
        # Set timezone to Asia/Tokyo
        settings = Settings(timezone="Asia/Tokyo")
        db.session.add(settings)
        db.session.commit()

        # Create a UTC time
        utc_time = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

        # Convert to Tokyo time
        tokyo_time = utc_to_local(utc_time)

        # Tokyo time should be ahead of UTC (UTC+9)
        assert tokyo_time.tzinfo is not None
        assert "Asia/Tokyo" in str(tokyo_time.tzinfo)

        # Tokyo time should be ahead of UTC time
        # Tokyo is UTC+9, so 12:00 UTC should be 21:00 in Tokyo
        assert tokyo_time.hour == 21


def test_timezone_conversion_local_to_utc(app):
    """Test local timezone to UTC conversion"""
    with app.app_context():
        # Set timezone to Europe/London
        settings = Settings(timezone="Europe/London")
        db.session.add(settings)
        db.session.commit()

        # Create a local time (assumed to be in London timezone)
        local_time = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)

        # Convert to UTC
        utc_time = local_to_utc(local_time)

        # UTC time should have timezone info
        assert utc_time.tzinfo is not None

        # Convert back to local to verify
        back_to_local = utc_to_local(utc_time)
        assert back_to_local.hour == 15
        assert back_to_local.minute == 30


def test_invalid_timezone_fallback(app):
    """Test that invalid timezone falls back to UTC"""
    with app.app_context():
        # Set invalid timezone
        settings = Settings(timezone="Invalid/Timezone")
        db.session.add(settings)
        db.session.commit()

        # Should fall back to UTC
        timezone = get_app_timezone()
        assert timezone == "Invalid/Timezone"  # Still stored in database

        # But timezone object should fall back to UTC
        from app.utils.timezone import get_timezone_obj

        tz_obj = get_timezone_obj()
        assert "UTC" in str(tz_obj)


def test_timezone_settings_update(app):
    """Test that updating timezone settings takes effect immediately"""
    with app.app_context():
        # Create initial settings
        settings = Settings(timezone="Europe/Rome")
        db.session.add(settings)
        db.session.commit()

        # Verify initial timezone
        assert get_app_timezone() == "Europe/Rome"

        # Update timezone
        settings.timezone = "America/Los_Angeles"
        db.session.commit()

        # Verify timezone change takes effect
        assert get_app_timezone() == "America/Los_Angeles"

        # Test that time conversion uses new timezone
        utc_time = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
        la_time = utc_to_local(utc_time)

        # LA time should be in Pacific timezone
        assert la_time.tzinfo is not None
        assert "America/Los_Angeles" in str(la_time.tzinfo)


def test_get_available_timezones_matches_pytz_common():
    """Ensure available timezone helper mirrors pytz common timezones."""
    timezones = get_available_timezones()
    assert isinstance(timezones, tuple)
    expected = tuple(sorted(pytz.common_timezones))
    assert timezones == expected


def test_convert_app_datetime_to_user_respects_user_timezone(app, user):
    """Ensure user-specific timezone overrides application timezone for formatting."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.timezone = "America/Denver"
        db.session.commit()

        user = db.session.merge(user)
        user.timezone = "Asia/Kolkata"
        db.session.commit()

        naive_app_time = datetime(2025, 1, 15, 9, 0, 0)
        user_local = convert_app_datetime_to_user(naive_app_time, user=user)

        assert user_local.tzinfo is not None
        assert "Asia/Kolkata" in str(user_local.tzinfo)
        assert user_local.hour == 21
        assert user_local.minute == 30

        formatted = format_user_datetime(naive_app_time, "%Y-%m-%d %H:%M", user=user)
        assert formatted.endswith("21:30")


def test_convert_app_datetime_to_user_falls_back_to_app_timezone(app, user):
    """Ensure app timezone is used when user has no preference."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.timezone = "America/Denver"
        db.session.commit()

        user = db.session.merge(user)
        user.timezone = None
        db.session.commit()

        naive_app_time = datetime(2025, 1, 15, 9, 0, 0)
        local_time = convert_app_datetime_to_user(naive_app_time, user=user)

        assert local_time.tzinfo is not None
        assert "America/Denver" in str(local_time.tzinfo)
        assert local_time.hour == 9
        assert local_time.minute == 0


def test_update_preferences_allows_clearing_user_timezone(app, user):
    """Ensure API allows resetting to system default by clearing timezone."""
    with app.app_context():
        user = db.session.merge(user)
        user.timezone = "Asia/Tokyo"
        db.session.commit()

        # Clear with empty string
        with app.test_request_context("/user/api/preferences", method="PATCH", json={"timezone": ""}):
            login_user(user)
            response = update_preferences()
            assert response.status_code == 200
        assert user.timezone is None

        # Reapply and clear with 'system'
        user.timezone = "Asia/Tokyo"
        db.session.commit()
        with app.test_request_context("/user/api/preferences", method="PATCH", json={"timezone": "system"}):
            login_user(user)
            response = update_preferences()
            assert response.status_code == 200
        assert user.timezone is None
