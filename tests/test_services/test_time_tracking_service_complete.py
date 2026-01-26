"""
Comprehensive tests for TimeTrackingService including update and delete methods.
"""

import pytest
from datetime import datetime, timedelta
from app.services import TimeTrackingService
from app.models import TimeEntry, Project, User


class TestTimeTrackingServiceComplete:
    """Complete tests for TimeTrackingService"""

    def test_update_entry_success(self, app, user, project, time_entry):
        """Test successful time entry update"""
        service = TimeTrackingService()

        result = service.update_entry(
            entry_id=time_entry.id, user_id=user.id, is_admin=False, notes="Updated notes", billable=False
        )

        assert result["success"] is True
        assert result["entry"].notes == "Updated notes"
        assert result["entry"].billable is False

    def test_update_entry_recalculates_duration_when_start_end_edited(self, app, user, project, time_entry):
        """Duration should be recomputed when start_time or end_time is updated (issue #451)."""
        service = TimeTrackingService()
        old_duration = time_entry.duration_seconds

        # Change start/end so the span is exactly 15 minutes
        new_start = time_entry.start_time.replace(minute=0, second=0, microsecond=0)
        new_end = new_start + timedelta(minutes=15)
        expected_seconds = 15 * 60  # 900

        result = service.update_entry(
            entry_id=time_entry.id,
            user_id=user.id,
            is_admin=False,
            start_time=new_start,
            end_time=new_end,
        )

        assert result["success"] is True
        assert result["entry"].start_time == new_start
        assert result["entry"].end_time == new_end
        assert result["entry"].duration_seconds == expected_seconds, (
            f"duration_seconds should be {expected_seconds} after editing start/end, got {result['entry'].duration_seconds} (old was {old_duration})"
        )

    def test_update_entry_not_found(self, app, user):
        """Test update with non-existent entry"""
        service = TimeTrackingService()

        result = service.update_entry(entry_id=99999, user_id=user.id, is_admin=False)

        assert result["success"] is False
        assert result["error"] == "not_found"

    def test_update_entry_access_denied(self, app, user, other_user, time_entry):
        """Test update with access denied"""
        service = TimeTrackingService()

        result = service.update_entry(entry_id=time_entry.id, user_id=other_user.id, is_admin=False)

        assert result["success"] is False
        assert result["error"] == "access_denied"

    def test_delete_entry_success(self, app, user, time_entry):
        """Test successful time entry deletion"""
        # Ensure entry is not active
        time_entry.end_time = datetime.utcnow()
        from app import db

        db.session.commit()

        service = TimeTrackingService()

        result = service.delete_entry(entry_id=time_entry.id, user_id=user.id, is_admin=False)

        assert result["success"] is True

    def test_delete_entry_active_timer(self, app, user, time_entry):
        """Test delete fails for active timer"""
        # Ensure entry is active
        time_entry.end_time = None
        from app import db

        db.session.commit()

        service = TimeTrackingService()

        result = service.delete_entry(entry_id=time_entry.id, user_id=user.id, is_admin=False)

        assert result["success"] is False
        assert result["error"] == "timer_active"
