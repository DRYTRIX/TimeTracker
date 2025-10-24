"""Model tests for time rounding preferences integration"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Project, TimeEntry
from app.utils.time_rounding import apply_user_rounding


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user with default rounding preferences"""
    with app.app_context():
        # Check if user already exists (for PostgreSQL tests)
        user = User.query.filter_by(username='roundinguser').first()
        if not user:
            user = User(username='roundinguser', role='user')
            user.is_active = True  # Set after creation
            user.time_rounding_enabled = True
            user.time_rounding_minutes = 15
            user.time_rounding_method = 'nearest'
            db.session.add(user)
            db.session.commit()
        
        # Return the user ID instead of the object
        user_id = user.id
        db.session.expunge_all()
        
    # Re-query the user in a new session
    with app.app_context():
        return User.query.get(user_id)


@pytest.fixture
def test_project(app, test_user):
    """Create a test project"""
    with app.app_context():
        user = User.query.get(test_user.id)
        project = Project(
            name='Test Project',
            client='Test Client'
        )
        project.status = 'active'  # Set after creation
        db.session.add(project)
        db.session.commit()
        
        project_id = project.id
        db.session.expunge_all()
    
    with app.app_context():
        return Project.query.get(project_id)


class TestUserRoundingPreferences:
    """Test User model rounding preference fields"""
    
    def test_user_has_rounding_fields(self, app, test_user):
        """Test that user model has rounding preference fields"""
        with app.app_context():
            user = User.query.get(test_user.id)
            assert hasattr(user, 'time_rounding_enabled')
            assert hasattr(user, 'time_rounding_minutes')
            assert hasattr(user, 'time_rounding_method')
    
    def test_user_default_rounding_values(self, app):
        """Test default rounding values for new users"""
        with app.app_context():
            user = User(username='newuser', role='user')
            user.is_active = True  # Set after creation
            db.session.add(user)
            db.session.commit()
            
            # Defaults should be: enabled=True, minutes=1, method='nearest'
            assert user.time_rounding_enabled is True
            assert user.time_rounding_minutes == 1
            assert user.time_rounding_method == 'nearest'
    
    def test_update_user_rounding_preferences(self, app, test_user):
        """Test updating user rounding preferences"""
        with app.app_context():
            user = User.query.get(test_user.id)
            
            # Update preferences
            user.time_rounding_enabled = False
            user.time_rounding_minutes = 30
            user.time_rounding_method = 'up'
            db.session.commit()
            
            # Verify changes persisted
            user_id = user.id
            db.session.expunge_all()
            
            user = User.query.get(user_id)
            assert user.time_rounding_enabled is False
            assert user.time_rounding_minutes == 30
            assert user.time_rounding_method == 'up'
    
    def test_multiple_users_different_preferences(self, app):
        """Test that different users can have different rounding preferences"""
        with app.app_context():
            user1 = User(username='user1', role='user')
            user1.time_rounding_enabled = True
            user1.time_rounding_minutes = 5
            user1.time_rounding_method = 'up'
            
            user2 = User(username='user2', role='user')
            user2.time_rounding_enabled = False
            user2.time_rounding_minutes = 15
            user2.time_rounding_method = 'down'
            
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Verify each user has their own settings
            assert user1.time_rounding_minutes == 5
            assert user2.time_rounding_minutes == 15
            assert user1.time_rounding_method == 'up'
            assert user2.time_rounding_method == 'down'


class TestTimeEntryRounding:
    """Test time entry duration calculation with per-user rounding"""
    
    def test_time_entry_uses_user_rounding(self, app, test_user, test_project):
        """Test that time entry uses user's rounding preferences"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            # Create a time entry with 62 minutes duration
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # User has 15-min nearest rounding, so 62 minutes should round to 60
            assert entry.duration_seconds == 3600  # 60 minutes
    
    def test_time_entry_respects_disabled_rounding(self, app, test_user, test_project):
        """Test that rounding is not applied when disabled"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            # Disable rounding for user
            user.time_rounding_enabled = False
            db.session.commit()
            
            # Create a time entry with 62 minutes duration
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62, seconds=30)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # With rounding disabled, should be exact: 62.5 minutes = 3750 seconds
            assert entry.duration_seconds == 3750
    
    def test_time_entry_round_up_method(self, app, test_user, test_project):
        """Test time entry with 'up' rounding method"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            # Set to round up with 15-minute intervals
            user.time_rounding_method = 'up'
            db.session.commit()
            
            # Create entry with 61 minutes (should round up to 75)
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=61)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # 61 minutes rounds up to 75 minutes (next 15-min interval)
            assert entry.duration_seconds == 4500  # 75 minutes
    
    def test_time_entry_round_down_method(self, app, test_user, test_project):
        """Test time entry with 'down' rounding method"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            # Set to round down with 15-minute intervals
            user.time_rounding_method = 'down'
            db.session.commit()
            
            # Create entry with 74 minutes (should round down to 60)
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=74)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # 74 minutes rounds down to 60 minutes
            assert entry.duration_seconds == 3600  # 60 minutes
    
    def test_time_entry_different_intervals(self, app, test_user, test_project):
        """Test time entries with different rounding intervals"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            # Test 5-minute rounding
            user.time_rounding_minutes = 5
            db.session.commit()
            
            entry1 = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(entry1)
            db.session.flush()
            
            # 62 minutes rounds to 60 with 5-min intervals
            assert entry1.duration_seconds == 3600
            
            # Test 30-minute rounding
            user.time_rounding_minutes = 30
            db.session.commit()
            
            entry2 = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(entry2)
            db.session.flush()
            
            # 62 minutes rounds to 60 with 30-min intervals
            assert entry2.duration_seconds == 3600
    
    def test_stop_timer_applies_rounding(self, app, test_user, test_project):
        """Test that stopping a timer applies user's rounding preferences"""
        with app.app_context():
            user = User.query.get(test_user.id)
            project = Project.query.get(test_project.id)
            
            # Create an active timer
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=None
            )
            
            db.session.add(entry)
            db.session.commit()
            
            # Stop the timer after 62 minutes
            end_time = start_time + timedelta(minutes=62)
            entry.stop_timer(end_time=end_time)
            
            # Should be rounded to 60 minutes (user has 15-min nearest rounding)
            assert entry.duration_seconds == 3600


class TestBackwardCompatibility:
    """Test backward compatibility with global rounding settings"""
    
    def test_fallback_to_global_rounding_without_user_preferences(self, app, test_project):
        """Test that system falls back to global rounding if user prefs don't exist"""
        with app.app_context():
            # Create a user without setting rounding preferences (simulating default values)
            user = User(username='olduser', role='user')
            user.is_active = True
            # Don't set time_rounding_enabled, time_rounding_minutes, or time_rounding_method
            # This simulates a user with default/null values for rounding preferences
            db.session.add(user)
            db.session.commit()
            
            project = Project.query.get(test_project.id)
            
            # Create a time entry - should fall back to global rounding
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # Should use global rounding (Config.ROUNDING_MINUTES, default is 1)
            # With global rounding = 1, duration should be exact
            assert entry.duration_seconds == 3720  # 62 minutes exactly

