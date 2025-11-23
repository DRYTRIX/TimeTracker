"""
Unit tests for TimeTrackingService.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.time_tracking_service import TimeTrackingService
from app.repositories import TimeEntryRepository, ProjectRepository
from app.models import TimeEntry, Project, Task
from app.constants import TimeEntrySource


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
    """Sample project for testing"""
    project = Mock(spec=Project)
    project.id = 1
    project.status = 'active'
    project.name = "Test Project"
    return project


class TestStartTimer:
    """Tests for start_timer method"""
    
    def test_start_timer_success(self, service, mock_time_entry_repo, mock_project_repo, sample_project):
        """Test successful timer start"""
        # Setup mocks
        mock_time_entry_repo.get_active_timer.return_value = None
        mock_project_repo.get_by_id.return_value = sample_project
        mock_timer = Mock(spec=TimeEntry)
        mock_timer.id = 1
        mock_time_entry_repo.create_timer.return_value = mock_timer
        
        # Mock safe_commit
        with patch('app.services.time_tracking_service.safe_commit', return_value=True):
            result = service.start_timer(
                user_id=1,
                project_id=1,
                task_id=None,
                notes="Test notes"
            )
        
        # Assertions
        assert result['success'] is True
        assert 'timer' in result
        mock_time_entry_repo.get_active_timer.assert_called_once_with(1)
        mock_project_repo.get_by_id.assert_called_once_with(1)
        mock_time_entry_repo.create_timer.assert_called_once()
    
    def test_start_timer_already_running(self, service, mock_time_entry_repo):
        """Test starting timer when one is already running"""
        # Setup mocks
        active_timer = Mock(spec=TimeEntry)
        mock_time_entry_repo.get_active_timer.return_value = active_timer
        
        # Execute
        result = service.start_timer(user_id=1, project_id=1)
        
        # Assertions
        assert result['success'] is False
        assert result['error'] == 'timer_already_running'
        assert 'already have an active timer' in result['message'].lower()
    
    def test_start_timer_invalid_project(self, service, mock_time_entry_repo, mock_project_repo):
        """Test starting timer with invalid project"""
        # Setup mocks
        mock_time_entry_repo.get_active_timer.return_value = None
        mock_project_repo.get_by_id.return_value = None
        
        # Execute
        result = service.start_timer(user_id=1, project_id=999)
        
        # Assertions
        assert result['success'] is False
        assert result['error'] == 'invalid_project'
    
    def test_start_timer_archived_project(self, service, mock_time_entry_repo, mock_project_repo):
        """Test starting timer for archived project"""
        # Setup mocks
        mock_time_entry_repo.get_active_timer.return_value = None
        archived_project = Mock(spec=Project)
        archived_project.id = 1
        archived_project.status = 'archived'
        mock_project_repo.get_by_id.return_value = archived_project
        
        # Execute
        result = service.start_timer(user_id=1, project_id=1)
        
        # Assertions
        assert result['success'] is False
        assert result['error'] == 'project_archived'


class TestStopTimer:
    """Tests for stop_timer method"""
    
    def test_stop_timer_success(self, service, mock_time_entry_repo):
        """Test successful timer stop"""
        # Setup mocks
        active_timer = Mock(spec=TimeEntry)
        active_timer.id = 1
        active_timer.user_id = 1
        active_timer.end_time = None
        active_timer.calculate_duration = Mock()
        mock_time_entry_repo.get_active_timer.return_value = active_timer
        
        # Mock safe_commit
        with patch('app.services.time_tracking_service.safe_commit', return_value=True):
            with patch('app.services.time_tracking_service.local_now', return_value=datetime.now()):
                result = service.stop_timer(user_id=1)
        
        # Assertions
        assert result['success'] is True
        assert active_timer.end_time is not None
        active_timer.calculate_duration.assert_called_once()
    
    def test_stop_timer_no_active_timer(self, service, mock_time_entry_repo):
        """Test stopping timer when none is active"""
        # Setup mocks
        mock_time_entry_repo.get_active_timer.return_value = None
        
        # Execute
        result = service.stop_timer(user_id=1)
        
        # Assertions
        assert result['success'] is False
        assert result['error'] == 'no_active_timer'


class TestCreateManualEntry:
    """Tests for create_manual_entry method"""
    
    def test_create_manual_entry_success(self, service, mock_time_entry_repo, mock_project_repo, sample_project):
        """Test successful manual entry creation"""
        # Setup mocks
        mock_project_repo.get_by_id.return_value = sample_project
        mock_entry = Mock(spec=TimeEntry)
        mock_entry.id = 1
        mock_time_entry_repo.create_manual_entry.return_value = mock_entry
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        
        # Mock safe_commit
        with patch('app.services.time_tracking_service.safe_commit', return_value=True):
            result = service.create_manual_entry(
                user_id=1,
                project_id=1,
                start_time=start_time,
                end_time=end_time,
                notes="Test entry"
            )
        
        # Assertions
        assert result['success'] is True
        assert 'entry' in result
        mock_time_entry_repo.create_manual_entry.assert_called_once()
    
    def test_create_manual_entry_invalid_time_range(self, service, mock_project_repo, sample_project):
        """Test creating entry with invalid time range"""
        # Setup mocks
        mock_project_repo.get_by_id.return_value = sample_project
        
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)  # End before start
        
        # Execute
        result = service.create_manual_entry(
            user_id=1,
            project_id=1,
            start_time=start_time,
            end_time=end_time
        )
        
        # Assertions
        assert result['success'] is False
        assert result['error'] == 'invalid_time_range'

