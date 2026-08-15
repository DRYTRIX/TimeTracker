"""Unit tests for time rounding functionality"""

from datetime import datetime, timedelta

import pytest
from app.utils.time_rounding import (
    round_time_duration,
    apply_user_rounding,
    format_rounding_interval,
    get_available_rounding_intervals,
    get_available_rounding_methods,
    get_user_rounding_settings,
)


class TestRoundTimeDuration:
    """Test the core time rounding function"""

    def test_no_rounding_when_interval_is_one(self):
        """Test that rounding_minutes=1 returns exact duration"""
        assert round_time_duration(3720, 1, "nearest") == 3720
        assert round_time_duration(3722, 1, "up") == 3722
        assert round_time_duration(3718, 1, "down") == 3718

    def test_round_to_nearest_5_minutes(self):
        """Test rounding to nearest 5 minute interval"""
        # 62 minutes should round to 60 minutes (nearest 5-min interval)
        assert round_time_duration(3720, 5, "nearest") == 3600
        # 63 minutes should round to 65 minutes
        assert round_time_duration(3780, 5, "nearest") == 3900
        # 2 minutes should round to 0
        assert round_time_duration(120, 5, "nearest") == 0
        # 3 minutes should round to 5
        assert round_time_duration(180, 5, "nearest") == 300

    def test_round_to_nearest_15_minutes(self):
        """Test rounding to nearest 15 minute interval"""
        # 62 minutes should round to 60 minutes
        assert round_time_duration(3720, 15, "nearest") == 3600
        # 68 minutes should round to 75 minutes
        assert round_time_duration(4080, 15, "nearest") == 4500
        # 7 minutes should round to 0
        assert round_time_duration(420, 15, "nearest") == 0
        # 8 minutes should round to 15
        assert round_time_duration(480, 15, "nearest") == 900

    def test_round_up(self):
        """Test always rounding up (ceiling)"""
        # 62 minutes with 15-min interval rounds up to 75
        assert round_time_duration(3720, 15, "up") == 4500
        # 60 minutes with 15-min interval stays 60 (exact match)
        assert round_time_duration(3600, 15, "up") == 3600
        # 61 minutes with 15-min interval rounds up to 75
        assert round_time_duration(3660, 15, "up") == 4500
        # 1 minute with 5-min interval rounds up to 5
        assert round_time_duration(60, 5, "up") == 300

    def test_round_down(self):
        """Test always rounding down (floor)"""
        # 62 minutes with 15-min interval rounds down to 60
        assert round_time_duration(3720, 15, "down") == 3600
        # 74 minutes with 15-min interval rounds down to 60
        assert round_time_duration(4440, 15, "down") == 3600
        # 75 minutes with 15-min interval stays 75 (exact match)
        assert round_time_duration(4500, 15, "down") == 4500

    def test_round_to_hour(self):
        """Test rounding to 1 hour intervals"""
        # 62 minutes rounds to 60 minutes (nearest hour)
        assert round_time_duration(3720, 60, "nearest") == 3600
        # 90 minutes rounds to 120 minutes (nearest hour)
        assert round_time_duration(5400, 60, "nearest") == 7200
        # 89 minutes rounds to 60 minutes (nearest hour)
        assert round_time_duration(5340, 60, "nearest") == 3600

    def test_invalid_rounding_method_defaults_to_nearest(self):
        """Test that invalid rounding method falls back to 'nearest'"""
        result = round_time_duration(3720, 15, "invalid")
        expected = round_time_duration(3720, 15, "nearest")
        assert result == expected

    def test_zero_duration(self):
        """Test handling of zero duration"""
        assert round_time_duration(0, 15, "nearest") == 0
        assert round_time_duration(0, 15, "up") == 0
        assert round_time_duration(0, 15, "down") == 0

    def test_very_small_durations(self):
        """Test rounding of very small durations"""
        # 30 seconds with 5-min rounding
        assert round_time_duration(30, 5, "nearest") == 0
        assert round_time_duration(30, 5, "up") == 300  # Rounds up to 5 minutes
        assert round_time_duration(30, 5, "down") == 0

    def test_very_large_durations(self):
        """Test rounding of large durations"""
        # 8 hours 7 minutes (487 minutes) with 15-min rounding
        # 487 / 15 = 32.47 -> rounds to 32 intervals = 480 minutes = 28800 seconds
        assert round_time_duration(29220, 15, "nearest") == 28800  # 480 minutes (8 hours)
        # 8 hours 8 minutes (488 minutes) with 15-min rounding
        # 488 / 15 = 32.53 -> rounds to 33 intervals = 495 minutes = 29700 seconds
        assert round_time_duration(29280, 15, "nearest") == 29700  # 495 minutes (8 hours 15 min)


class TestApplyUserRounding:
    """Test applying user-specific rounding preferences"""

    def test_with_rounding_disabled(self):
        """Test that rounding is skipped when disabled for user"""

        class MockUser:
            time_rounding_enabled = False
            time_rounding_minutes = 15
            time_rounding_method = "nearest"

        user = MockUser()
        assert apply_user_rounding(3720, user) == 3720

    def test_with_rounding_enabled(self):
        """Test that rounding is applied when enabled"""

        class MockUser:
            time_rounding_enabled = True
            time_rounding_minutes = 15
            time_rounding_method = "nearest"

        user = MockUser()
        # 62 minutes should round to 60 with 15-min interval
        assert apply_user_rounding(3720, user) == 3600

    def test_different_user_preferences(self):
        """Test that different users can have different rounding settings"""

        class MockUser1:
            time_rounding_enabled = True
            time_rounding_minutes = 5
            time_rounding_method = "up"

        class MockUser2:
            time_rounding_enabled = True
            time_rounding_minutes = 15
            time_rounding_method = "down"

        duration = 3720  # 62 minutes

        # User 1: 5-min up -> 65 minutes
        assert apply_user_rounding(duration, MockUser1()) == 3900

        # User 2: 15-min down -> 60 minutes
        assert apply_user_rounding(duration, MockUser2()) == 3600

    def test_get_user_rounding_settings(self):
        """Test retrieving user rounding settings"""

        class MockUser:
            time_rounding_enabled = True
            time_rounding_minutes = 10
            time_rounding_method = "up"

        settings = get_user_rounding_settings(MockUser())
        assert settings["enabled"] is True
        assert settings["minutes"] == 10
        assert settings["method"] == "up"

    def test_get_user_rounding_settings_with_defaults(self):
        """Test default values when attributes don't exist"""

        class MockUser:
            pass

        settings = get_user_rounding_settings(MockUser())
        assert settings["enabled"] is True
        assert settings["minutes"] == 1
        assert settings["method"] == "nearest"


class TestFormattingFunctions:
    """Test formatting and helper functions"""

    def test_format_rounding_interval(self):
        """Test formatting of rounding intervals"""
        assert format_rounding_interval(1) == "No rounding (exact time)"
        assert format_rounding_interval(5) == "5 minutes"
        assert format_rounding_interval(15) == "15 minutes"
        assert format_rounding_interval(30) == "30 minutes"
        assert format_rounding_interval(60) == "1 hour"
        assert format_rounding_interval(120) == "2 hours"

    def test_get_available_rounding_intervals(self):
        """Test getting available rounding intervals"""
        intervals = get_available_rounding_intervals()
        assert len(intervals) == 6
        assert intervals[0][0] == 1
        assert (5, "5 minutes") in intervals
        assert (60, "1 hour") in intervals

    def test_get_available_rounding_methods(self):
        """Test getting available rounding methods"""
        methods = get_available_rounding_methods()
        assert len(methods) == 4

        method_values = [m[0] for m in methods]
        assert "nearest" in method_values
        assert "up" in method_values
        assert "down" in method_values
        assert "boundary" in method_values


class TestCalculateDurationTransientUser:
    """calculate_duration must apply per-user rounding on transient TimeEntry instances."""

    def test_rounding_applies_when_user_relationship_unavailable(self, app, user, project):
        """When self.user cannot be loaded, fall back to user_id lookup and still round."""
        from unittest.mock import PropertyMock, patch

        from app import db
        from app.models import TimeEntry, User
        from app.utils.time_rounding import apply_user_rounding

        with app.app_context():
            user_id = user.id
            project_id = project.id

            # Persist rounding prefs via bulk update to avoid audit-listener lock flakes
            db.session.query(User).filter_by(id=user_id).update(
                {
                    "time_rounding_enabled": True,
                    "time_rounding_minutes": 15,
                    "time_rounding_method": "nearest",
                },
                synchronize_session=False,
            )
            db.session.commit()

            rounding_user = db.session.get(User, user_id)
            expected = apply_user_rounding(62 * 60, rounding_user)
            assert expected == 3600

            start = datetime(2025, 6, 1, 9, 0, 0)
            # 62 minutes raw → nearest 15 min = 60 minutes = 3600 seconds
            end = start + timedelta(minutes=62)
            entry = TimeEntry(
                user_id=user_id,
                project_id=project_id,
                start_time=start,
                end_time=end,
                source="manual",
                billable=True,
            )
            # Intentionally not added to the session (transient)
            assert entry not in db.session

            # Simulate the transient-instance relationship failure that #725 fixes
            with patch.object(
                TimeEntry,
                "user",
                new_callable=PropertyMock,
                side_effect=Exception("transient: user relationship unavailable"),
            ):
                entry.calculate_duration()

            assert entry.duration_seconds == expected
            assert entry.duration_seconds == 3600


class TestBoundaryRounding:
    """Issue #725: round start down / end up to interval boundaries."""

    def test_round_entry_boundaries_5_minutes(self):
        from app.utils.time_rounding import round_entry_boundaries

        start = datetime(2026, 8, 12, 9, 46, 0)
        end = datetime(2026, 8, 12, 9, 54, 0)
        rounded_start, rounded_end = round_entry_boundaries(start, end, 5)
        assert rounded_start == datetime(2026, 8, 12, 9, 45, 0)
        assert rounded_end == datetime(2026, 8, 12, 9, 55, 0)
        assert int((rounded_end - rounded_start).total_seconds()) == 600

    def test_boundary_already_on_marker(self):
        from app.utils.time_rounding import round_entry_boundaries

        start = datetime(2026, 8, 12, 9, 45, 0)
        end = datetime(2026, 8, 12, 9, 55, 0)
        rounded_start, rounded_end = round_entry_boundaries(start, end, 5)
        assert rounded_start == start
        assert rounded_end == end

    def test_calculate_duration_persists_boundaries(self, app, user, project):
        from app import db
        from app.models import TimeEntry, User

        with app.app_context():
            user_id = user.id
            project_id = project.id
            db.session.query(User).filter_by(id=user_id).update(
                {
                    "time_rounding_enabled": True,
                    "time_rounding_minutes": 5,
                    "time_rounding_method": "boundary",
                    "time_rounding_minimum_minutes": 0,
                },
                synchronize_session=False,
            )
            db.session.commit()

            entry = TimeEntry(
                user_id=user_id,
                project_id=project_id,
                start_time=datetime(2026, 8, 12, 9, 46, 0),
                end_time=datetime(2026, 8, 12, 9, 54, 0),
                source="manual",
                billable=True,
            )
            db.session.add(entry)
            db.session.flush()
            entry.calculate_duration()
            db.session.commit()

            assert entry.start_time == datetime(2026, 8, 12, 9, 45, 0)
            assert entry.end_time == datetime(2026, 8, 12, 9, 55, 0)
            assert entry.duration_seconds == 600

    def test_duration_seconds_override_adjusts_boundaries(self, app, user, project):
        """Creating with duration_seconds override under boundary method still adjusts start/end."""
        from app import db
        from app.models import TimeEntry, User

        with app.app_context():
            user_id = user.id
            project_id = project.id
            db.session.query(User).filter_by(id=user_id).update(
                {
                    "time_rounding_enabled": True,
                    "time_rounding_minutes": 5,
                    "time_rounding_method": "boundary",
                    "time_rounding_minimum_minutes": 0,
                },
                synchronize_session=False,
            )
            db.session.commit()

            # Explicit duration matches raw span (8 min); without the fix, start/end
            # would stay at 09:46–09:54 while duration stayed 480.
            entry = TimeEntry(
                user_id=user_id,
                project_id=project_id,
                start_time=datetime(2026, 8, 12, 9, 46, 0),
                end_time=datetime(2026, 8, 12, 9, 54, 0),
                duration_seconds=480,
                source="manual",
                billable=True,
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.start_time == datetime(2026, 8, 12, 9, 45, 0)
            assert entry.end_time == datetime(2026, 8, 12, 9, 55, 0)
            assert entry.duration_seconds == 600

    def test_create_manual_entry_duration_override_boundary(self, app, user, project):
        """Service/repo path with duration override under boundary adjusts timestamps."""
        from app import db
        from app.models import User
        from app.services.time_tracking_service import TimeTrackingService

        with app.app_context():
            user_id = user.id
            project_id = project.id
            db.session.query(User).filter_by(id=user_id).update(
                {
                    "time_rounding_enabled": True,
                    "time_rounding_minutes": 5,
                    "time_rounding_method": "boundary",
                    "time_rounding_minimum_minutes": 0,
                },
                synchronize_session=False,
            )
            db.session.commit()

            result = TimeTrackingService().create_manual_entry(
                user_id=user_id,
                project_id=project_id,
                start_time=datetime(2026, 8, 12, 9, 46, 0),
                end_time=datetime(2026, 8, 12, 9, 54, 0),
                duration_seconds=480,
                billable=True,
            )
            assert result["success"] is True
            entry = result["entry"]
            assert entry.start_time == datetime(2026, 8, 12, 9, 45, 0)
            assert entry.end_time == datetime(2026, 8, 12, 9, 55, 0)
            assert entry.duration_seconds == 600


class TestMinimumDuration:
    """Issue #725: minimum billable duration floor."""

    def test_apply_minimum_duration(self):
        from app.utils.time_rounding import apply_minimum_duration

        assert apply_minimum_duration(60, 5) == 300
        assert apply_minimum_duration(600, 5) == 600
        assert apply_minimum_duration(60, 0) == 60

    def test_apply_user_rounding_with_minimum(self):
        class MockUser:
            time_rounding_enabled = True
            time_rounding_minutes = 5
            time_rounding_method = "nearest"
            time_rounding_minimum_minutes = 5

        # 1 min raw → nearest 5 = 0, then minimum raises to 5 min
        assert apply_user_rounding(60, MockUser()) == 300

    def test_boundary_in_available_methods(self):
        methods = [m[0] for m in get_available_rounding_methods()]
        assert "boundary" in methods


class TestGlobalRoundingPolicy:
    """Issue #725 follow-up: admin global policy and enforce-all-users."""

    def test_enforced_policy_overrides_customised_user(self, monkeypatch):
        monkeypatch.setattr(
            "app.utils.time_rounding.get_global_rounding_policy",
            lambda: {
                "enabled": True,
                "minutes": 5,
                "method": "boundary",
                "minimum_minutes": 10,
                "enforced": True,
            },
        )

        class MockUser:
            time_rounding_enabled = False
            time_rounding_minutes = 15
            time_rounding_method = "up"
            time_rounding_minimum_minutes = 30

        settings = get_user_rounding_settings(MockUser())
        assert settings["enabled"] is True
        assert settings["minutes"] == 5
        assert settings["method"] == "boundary"
        assert settings["minimum_minutes"] == 10

    def test_none_user_returns_global_policy(self, monkeypatch):
        monkeypatch.setattr(
            "app.utils.time_rounding.get_global_rounding_policy",
            lambda: {
                "enabled": True,
                "minutes": 15,
                "method": "up",
                "minimum_minutes": 5,
                "enforced": False,
            },
        )
        settings = get_user_rounding_settings(None)
        assert settings["minutes"] == 15
        assert settings["method"] == "up"
        assert settings["minimum_minutes"] == 5

    def test_per_field_fallback_when_not_enforced(self, monkeypatch):
        monkeypatch.setattr(
            "app.utils.time_rounding.get_global_rounding_policy",
            lambda: {
                "enabled": True,
                "minutes": 10,
                "method": "up",
                "minimum_minutes": 15,
                "enforced": False,
            },
        )

        class DefaultUser:
            time_rounding_enabled = True
            time_rounding_minutes = 1
            time_rounding_method = "nearest"
            time_rounding_minimum_minutes = 0

        inherited = get_user_rounding_settings(DefaultUser())
        assert inherited["minutes"] == 10
        assert inherited["method"] == "up"
        assert inherited["minimum_minutes"] == 15

        class CustomUser:
            time_rounding_enabled = True
            time_rounding_minutes = 30
            time_rounding_method = "down"
            time_rounding_minimum_minutes = 5

        custom = get_user_rounding_settings(CustomUser())
        assert custom["minutes"] == 30
        assert custom["method"] == "down"
        assert custom["minimum_minutes"] == 5

    def test_calculate_duration_uses_enforced_global_boundary(self, app, user, project):
        from app import db
        from app.models import Settings, TimeEntry, User

        with app.app_context():
            settings_obj = Settings.get_settings()
            settings_obj.rounding_minutes = 5
            settings_obj.rounding_method = "boundary"
            settings_obj.rounding_minimum_minutes = 0
            settings_obj.rounding_enforce_global = True
            db.session.commit()

            user_id = user.id
            project_id = project.id
            db.session.query(User).filter_by(id=user_id).update(
                {
                    "time_rounding_enabled": True,
                    "time_rounding_minutes": 15,
                    "time_rounding_method": "nearest",
                    "time_rounding_minimum_minutes": 0,
                },
                synchronize_session=False,
            )
            db.session.commit()

            entry = TimeEntry(
                user_id=user_id,
                project_id=project_id,
                start_time=datetime(2026, 8, 12, 9, 46, 0),
                end_time=datetime(2026, 8, 12, 9, 54, 0),
                source="manual",
                billable=True,
            )
            db.session.add(entry)
            db.session.flush()
            entry.calculate_duration()
            db.session.commit()

            assert entry.start_time == datetime(2026, 8, 12, 9, 45, 0)
            assert entry.end_time == datetime(2026, 8, 12, 9, 55, 0)
            assert entry.duration_seconds == 600

    def test_calculate_duration_applies_global_minimum_without_user(self, app, project):
        from app import db
        from app.models import Settings, TimeEntry

        with app.app_context():
            settings_obj = Settings.get_settings()
            settings_obj.rounding_minutes = 5
            settings_obj.rounding_method = "nearest"
            settings_obj.rounding_minimum_minutes = 15
            settings_obj.rounding_enforce_global = False
            db.session.commit()

            entry = TimeEntry(
                user_id=0,
                project_id=project.id,
                start_time=datetime(2026, 8, 12, 9, 0, 0),
                end_time=datetime(2026, 8, 12, 9, 1, 0),
                source="manual",
                billable=True,
            )
            # user_id 0 does not resolve a User, so calculate_duration uses the global policy
            entry.calculate_duration()
            # 1 min nearest 5 → 0, then minimum 15 → 900
            assert entry.duration_seconds == 900
