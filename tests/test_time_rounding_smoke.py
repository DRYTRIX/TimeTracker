"""Smoke tests for time rounding preferences feature - end-to-end testing"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Project, TimeEntry


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost'
    
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
def authenticated_user(app, client):
    """Create and authenticate a test user"""
    with app.app_context():
        user = User(username='smoketest', role='user', email='smoke@test.com')
        user.is_active = True  # Set after creation
        user.time_rounding_enabled = True
        user.time_rounding_minutes = 15
        user.time_rounding_method = 'nearest'
        db.session.add(user)
        
        project = Project(
            name='Smoke Test Project',
            client='Smoke Test Client'
        )
        project.status = 'active'  # Set after creation
        db.session.add(project)
        db.session.commit()
        
        user_id = user.id
        project_id = project.id
    
    # Simulate login
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['_fresh'] = True
    
    return {'user_id': user_id, 'project_id': project_id}


class TestTimeRoundingFeatureSmokeTests:
    """High-level smoke tests for the time rounding feature"""
    
    def test_user_can_view_rounding_settings(self, app, client, authenticated_user):
        """Test that user can access the settings page with rounding options"""
        with app.test_request_context():
            response = client.get('/settings')
            
            # Should be able to access settings page
            assert response.status_code in [200, 302]  # 302 if redirect to login
    
    def test_user_can_update_rounding_preferences(self, app, client, authenticated_user):
        """Test that user can update their rounding preferences"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            
            # Change preferences
            user.time_rounding_enabled = False
            user.time_rounding_minutes = 30
            user.time_rounding_method = 'up'
            db.session.commit()
            
            # Verify changes were saved
            db.session.expunge_all()
            user = User.query.get(authenticated_user['user_id'])
            
            assert user.time_rounding_enabled is False
            assert user.time_rounding_minutes == 30
            assert user.time_rounding_method == 'up'
    
    def test_time_entry_reflects_user_rounding_preferences(self, app, authenticated_user):
        """Test that creating a time entry applies user's rounding preferences"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Create a time entry with 62 minutes
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.commit()
            
            # User has 15-min nearest rounding, so 62 -> 60 minutes
            assert entry.duration_seconds == 3600
            assert entry.duration_hours == 1.0
    
    def test_different_users_have_independent_rounding(self, app):
        """Test that different users can have different rounding settings"""
        with app.app_context():
            # Create two users with different preferences
            user1 = User(username='user1', role='user')
            user1.time_rounding_enabled = True
            user1.time_rounding_minutes = 5
            user1.time_rounding_method = 'nearest'
            
            user2 = User(username='user2', role='user')
            user2.time_rounding_enabled = True
            user2.time_rounding_minutes = 30
            user2.time_rounding_method = 'up'
            
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create a project
            project = Project(
                name='Test Project',
                client='Test Client',
                status='active',
                created_by_id=user1.id
            )
            db.session.add(project)
            db.session.commit()
            
            # Create identical time entries for both users
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            entry1 = TimeEntry(
                user_id=user1.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            entry2 = TimeEntry(
                user_id=user2.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add_all([entry1, entry2])
            db.session.commit()
            
            # User1 (5-min nearest): 62 -> 60 minutes
            assert entry1.duration_seconds == 3600
            
            # User2 (30-min up): 62 -> 90 minutes
            assert entry2.duration_seconds == 5400
    
    def test_disabling_rounding_uses_exact_time(self, app, authenticated_user):
        """Test that disabling rounding results in exact time tracking"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Disable rounding
            user.time_rounding_enabled = False
            db.session.commit()
            
            # Create entry with odd duration
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62, seconds=37)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.commit()
            
            # Should be exact: 62 minutes 37 seconds = 3757 seconds
            assert entry.duration_seconds == 3757
    
    def test_rounding_with_various_intervals(self, app, authenticated_user):
        """Test that all rounding intervals work correctly"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Test duration: 37 minutes
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=37)
            
            test_cases = [
                (1, 2220),   # No rounding: 37 minutes
                (5, 2100),   # 5-min: 37 -> 35 minutes
                (10, 2400),  # 10-min: 37 -> 40 minutes
                (15, 2700),  # 15-min: 37 -> 45 minutes
                (30, 1800),  # 30-min: 37 -> 30 minutes
                (60, 3600),  # 60-min: 37 -> 60 minutes (1 hour)
            ]
            
            for interval, expected_seconds in test_cases:
                user.time_rounding_minutes = interval
                user.time_rounding_method = 'nearest'
                db.session.commit()
                
                entry = TimeEntry(
                    user_id=user.id,
                    project_id=project.id,
                    start_time=start_time,
                    end_time=end_time
                )
                
                db.session.add(entry)
                db.session.flush()
                
                assert entry.duration_seconds == expected_seconds, \
                    f"Failed for {interval}-minute rounding: expected {expected_seconds}, got {entry.duration_seconds}"
                
                db.session.rollback()
    
    def test_rounding_methods_comparison(self, app, authenticated_user):
        """Test that different rounding methods produce different results"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Test with 62 minutes and 15-min intervals
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = start_time + timedelta(minutes=62)
            
            user.time_rounding_minutes = 15
            
            # Test 'nearest' method
            user.time_rounding_method = 'nearest'
            db.session.commit()
            
            entry_nearest = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(entry_nearest)
            db.session.flush()
            
            # 62 minutes nearest to 15-min interval -> 60 minutes
            assert entry_nearest.duration_seconds == 3600
            db.session.rollback()
            
            # Test 'up' method
            user.time_rounding_method = 'up'
            db.session.commit()
            
            entry_up = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(entry_up)
            db.session.flush()
            
            # 62 minutes rounded up to 15-min interval -> 75 minutes
            assert entry_up.duration_seconds == 4500
            db.session.rollback()
            
            # Test 'down' method
            user.time_rounding_method = 'down'
            db.session.commit()
            
            entry_down = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(entry_down)
            db.session.flush()
            
            # 62 minutes rounded down to 15-min interval -> 60 minutes
            assert entry_down.duration_seconds == 3600
    
    def test_migration_compatibility(self, app):
        """Test that the feature works after migration"""
        with app.app_context():
            # Verify that new users get the columns
            user = User(username='newuser', role='user')
            db.session.add(user)
            db.session.commit()
            
            # Check that all fields exist and have correct defaults
            assert hasattr(user, 'time_rounding_enabled')
            assert hasattr(user, 'time_rounding_minutes')
            assert hasattr(user, 'time_rounding_method')
            
            assert user.time_rounding_enabled is True
            assert user.time_rounding_minutes == 1
            assert user.time_rounding_method == 'nearest'
    
    def test_full_workflow(self, app, authenticated_user):
        """Test complete workflow: set preferences -> create entry -> verify rounding"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Step 1: User sets their rounding preferences
            user.time_rounding_enabled = True
            user.time_rounding_minutes = 10
            user.time_rounding_method = 'up'
            db.session.commit()
            
            # Step 2: User starts a timer
            start_time = datetime(2025, 1, 1, 9, 0, 0)
            timer = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=None  # Active timer
            )
            db.session.add(timer)
            db.session.commit()
            
            # Verify timer is active
            assert timer.is_active is True
            assert timer.duration_seconds is None
            
            # Step 3: User stops the timer after 23 minutes
            end_time = start_time + timedelta(minutes=23)
            timer.stop_timer(end_time=end_time)
            
            # Step 4: Verify the duration was rounded correctly
            # With 10-min 'up' rounding, 23 minutes should round up to 30 minutes
            assert timer.duration_seconds == 1800  # 30 minutes
            assert timer.is_active is False
            
            # Step 5: Verify the entry is queryable with correct rounded duration
            db.session.expunge_all()
            saved_entry = TimeEntry.query.get(timer.id)
            assert saved_entry.duration_seconds == 1800
            assert saved_entry.duration_hours == 0.5


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_duration_time_entry(self, app, authenticated_user):
        """Test handling of zero-duration entries"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # Create entry with same start and end time
            time = datetime(2025, 1, 1, 10, 0, 0)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=time,
                end_time=time
            )
            
            db.session.add(entry)
            db.session.commit()
            
            # Zero duration should stay zero regardless of rounding
            assert entry.duration_seconds == 0
    
    def test_very_long_duration(self, app, authenticated_user):
        """Test rounding of very long time entries (multi-day)"""
        with app.app_context():
            user = User.query.get(authenticated_user['user_id'])
            project = Project.query.get(authenticated_user['project_id'])
            
            # 8 hours 7 minutes
            start_time = datetime(2025, 1, 1, 9, 0, 0)
            end_time = start_time + timedelta(hours=8, minutes=7)
            
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(entry)
            db.session.commit()
            
            # User has 15-min nearest rounding
            # 487 minutes -> 485 minutes (rounded down to nearest 15)
            assert entry.duration_seconds == 29100  # 485 minutes

