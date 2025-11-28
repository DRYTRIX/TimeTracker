"""
Integration tests for TimeEntryRepository.
"""

import pytest
from datetime import datetime, timedelta
from app.repositories import TimeEntryRepository
from app.models import TimeEntry, Project, User
from app import db
from app.constants import TimeEntrySource


@pytest.fixture
def repository():
    """Create repository instance"""
    return TimeEntryRepository()


@pytest.fixture
def sample_user(db_session):
    """Create sample user"""
    user = User(username="testuser", role="user")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_project(db_session, sample_user):
    """Create sample project"""
    from app.models import Client

    client = Client(name="Test Client")
    db_session.add(client)
    db_session.commit()

    project = Project(name="Test Project", client_id=client.id)
    db_session.add(project)
    db_session.commit()
    return project


class TestTimeEntryRepository:
    """Integration tests for TimeEntryRepository"""

    def test_create_timer(self, repository, db_session, sample_user, sample_project):
        """Test creating a timer"""
        timer = repository.create_timer(user_id=sample_user.id, project_id=sample_project.id, notes="Test timer")

        db_session.commit()

        assert timer.id is not None
        assert timer.user_id == sample_user.id
        assert timer.project_id == sample_project.id
        assert timer.end_time is None
        assert timer.source == TimeEntrySource.AUTO.value

    def test_get_active_timer(self, repository, db_session, sample_user, sample_project):
        """Test getting active timer"""
        # Create active timer
        timer = repository.create_timer(user_id=sample_user.id, project_id=sample_project.id)
        db_session.commit()

        # Get active timer
        active = repository.get_active_timer(sample_user.id)

        assert active is not None
        assert active.id == timer.id
        assert active.end_time is None

    def test_stop_timer(self, repository, db_session, sample_user, sample_project):
        """Test stopping a timer"""
        # Create timer
        timer = repository.create_timer(user_id=sample_user.id, project_id=sample_project.id)
        db_session.commit()

        # Stop timer
        end_time = datetime.now()
        stopped = repository.stop_timer(timer.id, end_time)
        db_session.commit()

        assert stopped is not None
        assert stopped.end_time == end_time
        assert stopped.duration_seconds is not None

    def test_get_by_user(self, repository, db_session, sample_user, sample_project):
        """Test getting entries by user"""
        # Create entries
        for i in range(3):
            entry = repository.create_manual_entry(
                user_id=sample_user.id,
                project_id=sample_project.id,
                start_time=datetime.now() - timedelta(hours=i + 1),
                end_time=datetime.now() - timedelta(hours=i),
                notes=f"Entry {i}",
            )
        db_session.commit()

        # Get entries
        entries = repository.get_by_user(sample_user.id, limit=10)

        assert len(entries) == 3
        # Should be ordered by start_time desc
        assert entries[0].start_time > entries[1].start_time

    def test_get_by_date_range(self, repository, db_session, sample_user, sample_project):
        """Test getting entries by date range"""
        # Create entries in different date ranges
        base_date = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        # Entry in range
        entry1 = repository.create_manual_entry(
            user_id=sample_user.id,
            project_id=sample_project.id,
            start_time=base_date - timedelta(days=1),
            end_time=base_date - timedelta(days=1) + timedelta(hours=2),
        )

        # Entry outside range
        entry2 = repository.create_manual_entry(
            user_id=sample_user.id,
            project_id=sample_project.id,
            start_time=base_date - timedelta(days=10),
            end_time=base_date - timedelta(days=10) + timedelta(hours=2),
        )

        db_session.commit()

        # Get entries in range
        start_date = base_date - timedelta(days=2)
        end_date = base_date
        entries = repository.get_by_date_range(start_date=start_date, end_date=end_date, user_id=sample_user.id)

        assert len(entries) == 1
        assert entries[0].id == entry1.id
