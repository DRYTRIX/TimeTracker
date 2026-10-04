"""
Unit tests for TimeTrackingService.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.repositories import ProjectRepository, TimeEntryRepository
from app.services.time_tracking_service import TimeTrackingService


@pytest.fixture
def mock_time_entry_repo():
    """Mock time entry repository"""
    return Mock(spec=TimeEntryRepository)


@pytest.fixture
def mock_project_repo():
    """Mock project repository"""
    return Mock(spec=ProjectRepository)


@pytest.fixture
def service(mock_time_entry_repo, mock_project_repo):
    """Create service with mocked repositories"""
    service = TimeTrackingService()
    service.time_entry_repo = mock_time_entry_repo
    service.project_repo = mock_project_repo
    return service


@pytest.fixture
def sample_project():
    """Sample project for testing (plain Mock — avoid SQLAlchemy model spec)."""
    project = Mock()
    project.id = 1
    project.status = "active"
    project.name = "Test Project"
    project.touch_last_used = Mock()
    return project


class TestStartTimer:
    """Tests for start_timer method"""

    def test_start_timer_success(self, service, mock_time_entry_repo, mock_project_repo, sample_project):
        """Test successful timer start"""
        mock_time_entry_repo.get_active_timer.return_value = None
        mock_project_repo.get_by_id.return_value = sample_project
        mock_timer = Mock()
        mock_timer.id = 1
        mock_time_entry_repo.create_timer.return_value = mock_timer

        with patch.object(service, "_is_locked_period", return_value=False):
            with patch("app.services.time_tracking_service.safe_commit", return_value=True):
                with patch("app.services.time_tracking_service.validate_time_entry_requirements", return_value=None):
                    with patch("app.services.time_tracking_service.Settings") as mock_settings:
                        mock_settings.get_settings.return_value = Mock()
                        with patch("app.services.time_tracking_service.emit_event"):
                            result = service.start_timer(user_id=1, project_id=1, task_id=None, notes="Test notes")

        assert result["success"] is True
        assert "timer" in result
        mock_time_entry_repo.get_active_timer.assert_called_with(1)
        mock_project_repo.get_by_id.assert_called_once_with(1)
        mock_time_entry_repo.create_timer.assert_called_once()

    def test_start_timer_already_running(self, service, mock_time_entry_repo):
        """Test starting timer when one is already running"""
        active_timer = Mock()
        mock_time_entry_repo.get_active_timer.return_value = active_timer

        with patch.object(service, "_is_locked_period", return_value=False):
            result = service.start_timer(user_id=1, project_id=1)

        assert result["success"] is False
        assert result["error"] == "timer_already_running"
        assert "already have an active timer" in result["message"].lower()

    def test_start_timer_invalid_project(self, service, mock_time_entry_repo, mock_project_repo):
        """Test starting timer with invalid project"""
        mock_time_entry_repo.get_active_timer.return_value = None
        mock_project_repo.get_by_id.return_value = None

        with patch.object(service, "_is_locked_period", return_value=False):
            result = service.start_timer(user_id=1, project_id=999)

        assert result["success"] is False
        assert result["error"] == "invalid_project"

    def test_start_timer_archived_project(self, service, mock_time_entry_repo, mock_project_repo):
        """Test starting timer for archived project"""
        mock_time_entry_repo.get_active_timer.return_value = None
        archived_project = Mock()
        archived_project.id = 1
        archived_project.status = "archived"
        mock_project_repo.get_by_id.return_value = archived_project

        with patch.object(service, "_is_locked_period", return_value=False):
            result = service.start_timer(user_id=1, project_id=1)

        assert result["success"] is False
        assert result["error"] == "project_archived"


class TestStopTimer:
    """Tests for stop_timer method"""

    def test_stop_timer_success(self, service, mock_time_entry_repo):
        """Test successful timer stop"""
        active_timer = Mock()
        active_timer.id = 1
        active_timer.user_id = 1
        active_timer.end_time = None
        active_timer.start_time = datetime.now() - timedelta(hours=1)
        active_timer.calculate_duration = Mock()
        mock_time_entry_repo.get_active_timer.return_value = active_timer

        with patch("app.services.time_tracking_service.safe_commit", return_value=True):
            with patch("app.services.time_tracking_service.local_now", return_value=datetime.now()):
                with patch("app.utils.workflow_bridge.fire_time_logged_workflow"):
                    result = service.stop_timer(user_id=1)

        assert result["success"] is True
        assert active_timer.end_time is not None
        active_timer.calculate_duration.assert_called_once()

    def test_stop_timer_no_active_timer(self, service, mock_time_entry_repo):
        """Test stopping timer when none is active"""
        mock_time_entry_repo.get_active_timer.return_value = None

        result = service.stop_timer(user_id=1)

        assert result["success"] is False
        assert result["error"] == "no_active_timer"


class TestCreateManualEntry:
    """Tests for create_manual_entry method"""

    def test_create_manual_entry_success(self, service, mock_time_entry_repo, mock_project_repo, sample_project):
        """Test successful manual entry creation"""
        mock_project_repo.get_by_id.return_value = sample_project
        mock_entry = Mock()
        mock_entry.id = 1
        mock_time_entry_repo.create_manual_entry.return_value = mock_entry

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        with patch.object(service, "_is_locked_period", return_value=False):
            with patch("app.services.time_tracking_service.safe_commit", return_value=True):
                with patch("app.services.time_tracking_service.emit_event"):
                    result = service.create_manual_entry(
                        user_id=1,
                        project_id=1,
                        start_time=start_time,
                        end_time=end_time,
                        notes="Test entry",
                        skip_entry_requirements=True,
                    )

        assert result["success"] is True
        assert "entry" in result
        mock_time_entry_repo.create_manual_entry.assert_called_once()

    def test_create_manual_entry_invalid_time_range(self, service, mock_project_repo, sample_project):
        """Test creating entry with invalid time range"""
        mock_project_repo.get_by_id.return_value = sample_project

        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)  # End before start

        with patch.object(service, "_is_locked_period", return_value=False):
            result = service.create_manual_entry(user_id=1, project_id=1, start_time=start_time, end_time=end_time)

        assert result["success"] is False
        assert result["error"] == "invalid_time_range"
