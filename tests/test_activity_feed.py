"""Tests for Activity Feed functionality"""

import pytest
from datetime import datetime, timedelta
from app.models import Activity, User, Project, Task, TimeEntry, Client
from app import db


class TestActivityModel:
    """Tests for the Activity model"""
    
    def test_activity_creation(self, app, test_user, test_project):
        """Test creating an activity log entry"""
        with app.app_context():
            activity = Activity(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description=f'Created project "{test_project.name}"'
            )
            db.session.add(activity)
            db.session.commit()
            
            assert activity.id is not None
            assert activity.user_id == test_user.id
            assert activity.action == 'created'
            assert activity.entity_type == 'project'
            assert activity.entity_id == test_project.id
            assert activity.created_at is not None
    
    def test_activity_log_method(self, app, test_user, test_project):
        """Test the Activity.log() class method"""
        with app.app_context():
            Activity.log(
                user_id=test_user.id,
                action='updated',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description=f'Updated project "{test_project.name}"',
                extra_data={'field': 'name'}
            )
            
            activity = Activity.query.filter_by(
                user_id=test_user.id,
                entity_type='project',
                entity_id=test_project.id
            ).first()
            
            assert activity is not None
            assert activity.action == 'updated'
            assert activity.extra_data == {'field': 'name'}
    
    def test_activity_get_recent(self, app, test_user, test_project):
        """Test getting recent activities"""
        with app.app_context():
            # Create multiple activities
            for i in range(5):
                Activity.log(
                    user_id=test_user.id,
                    action='updated',
                    entity_type='project',
                    entity_id=test_project.id,
                    entity_name=test_project.name,
                    description=f'Action {i}'
                )
            
            # Get recent activities
            activities = Activity.get_recent(user_id=test_user.id, limit=3)
            
            assert len(activities) == 3
            assert activities[0].description == 'Action 4'  # Most recent first
    
    def test_activity_filter_by_entity_type(self, app, test_user, test_project, test_task):
        """Test filtering activities by entity type"""
        with app.app_context():
            # Create activities for different entity types
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Project created'
            )
            
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='task',
                entity_id=test_task.id,
                entity_name=test_task.name,
                description='Task created'
            )
            
            # Filter by entity type
            project_activities = Activity.get_recent(
                user_id=test_user.id,
                entity_type='project'
            )
            
            task_activities = Activity.get_recent(
                user_id=test_user.id,
                entity_type='task'
            )
            
            assert len(project_activities) == 1
            assert project_activities[0].entity_type == 'project'
            assert len(task_activities) == 1
            assert task_activities[0].entity_type == 'task'
    
    def test_activity_to_dict(self, app, test_user, test_project):
        """Test converting activity to dictionary"""
        with app.app_context():
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Test activity'
            )
            
            activity = Activity.query.filter_by(user_id=test_user.id).first()
            activity_dict = activity.to_dict()
            
            assert activity_dict['id'] == activity.id
            assert activity_dict['user_id'] == test_user.id
            assert activity_dict['action'] == 'created'
            assert activity_dict['entity_type'] == 'project'
            assert activity_dict['entity_id'] == test_project.id
            assert activity_dict['description'] == 'Test activity'
            assert 'created_at' in activity_dict
    
    def test_activity_get_icon(self, app, test_user, test_project):
        """Test getting icon for different activity types"""
        with app.app_context():
            actions = ['created', 'updated', 'deleted', 'started', 'stopped']
            
            for action in actions:
                Activity.log(
                    user_id=test_user.id,
                    action=action,
                    entity_type='project',
                    entity_id=test_project.id,
                    entity_name=test_project.name,
                    description=f'{action} project'
                )
                
                activity = Activity.query.filter_by(action=action).first()
                icon = activity.get_icon()
                
                assert icon is not None
                assert 'fas fa-' in icon


class TestActivityAPIEndpoints:
    """Tests for Activity Feed API endpoints"""
    
    def test_get_activities(self, client, auth_headers, test_user, test_project):
        """Test GET /api/activities endpoint"""
        # Create some test activities
        with client.application.app_context():
            for i in range(3):
                Activity.log(
                    user_id=test_user.id,
                    action='updated',
                    entity_type='project',
                    entity_id=test_project.id,
                    entity_name=test_project.name,
                    description=f'Activity {i}'
                )
        
        response = client.get('/api/activities', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'activities' in data
        assert len(data['activities']) >= 3
        assert 'total' in data
        assert 'pages' in data
    
    def test_get_activities_with_entity_type_filter(self, client, auth_headers, test_user, test_project, test_task):
        """Test filtering activities by entity type"""
        with client.application.app_context():
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Project activity'
            )
            
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='task',
                entity_id=test_task.id,
                entity_name=test_task.name,
                description='Task activity'
            )
        
        # Filter by project entity type
        response = client.get(
            '/api/activities?entity_type=project',
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert all(
            act['entity_type'] == 'project' 
            for act in data['activities']
        )
    
    def test_get_activities_with_pagination(self, client, auth_headers, test_user, test_project):
        """Test pagination of activities"""
        with client.application.app_context():
            # Create 15 activities
            for i in range(15):
                Activity.log(
                    user_id=test_user.id,
                    action='updated',
                    entity_type='project',
                    entity_id=test_project.id,
                    entity_name=test_project.name,
                    description=f'Activity {i}'
                )
        
        # Get first page
        response = client.get(
            '/api/activities?limit=5&page=1',
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['activities']) == 5
        assert data['has_next'] is True
        
        # Get second page
        response = client.get(
            '/api/activities?limit=5&page=2',
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['activities']) == 5
    
    def test_get_activity_stats(self, client, auth_headers, test_user, test_project, test_task):
        """Test GET /api/activities/stats endpoint"""
        with client.application.app_context():
            # Create varied activities
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Project created'
            )
            
            Activity.log(
                user_id=test_user.id,
                action='updated',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Project updated'
            )
            
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='task',
                entity_id=test_task.id,
                entity_name=test_task.name,
                description='Task created'
            )
        
        response = client.get('/api/activities/stats', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_activities' in data
        assert 'entity_counts' in data
        assert 'action_counts' in data
        assert data['total_activities'] >= 3


class TestActivityIntegration:
    """Tests for activity logging integration in routes"""
    
    def test_project_create_logs_activity(self, client, auth_headers, test_client):
        """Test that creating a project logs an activity"""
        with client.application.app_context():
            # Count activities before
            before_count = Activity.query.count()
        
        response = client.post(
            '/projects/create',
            data={
                'name': 'Test Activity Project',
                'client_id': test_client.id,
                'billable': 'on',
                'description': 'Test project for activity'
            },
            headers=auth_headers,
            follow_redirects=False
        )
        
        with client.application.app_context():
            # Check activity was logged
            after_count = Activity.query.count()
            assert after_count == before_count + 1
            
            activity = Activity.query.order_by(Activity.created_at.desc()).first()
            assert activity.action == 'created'
            assert activity.entity_type == 'project'
            assert 'Test Activity Project' in activity.description
    
    def test_task_create_logs_activity(self, client, auth_headers, test_project):
        """Test that creating a task logs an activity"""
        with client.application.app_context():
            before_count = Activity.query.count()
        
        response = client.post(
            '/tasks/create',
            data={
                'project_id': test_project.id,
                'name': 'Test Activity Task',
                'priority': 'high',
                'description': 'Test task for activity'
            },
            headers=auth_headers,
            follow_redirects=False
        )
        
        with client.application.app_context():
            after_count = Activity.query.count()
            assert after_count == before_count + 1
            
            activity = Activity.query.order_by(Activity.created_at.desc()).first()
            assert activity.action == 'created'
            assert activity.entity_type == 'task'
            assert 'Test Activity Task' in activity.description
    
    def test_timer_start_logs_activity(self, client, auth_headers, test_project):
        """Test that starting a timer logs an activity"""
        with client.application.app_context():
            before_count = Activity.query.count()
        
        response = client.post(
            '/timer/start',
            data={
                'project_id': test_project.id,
                'notes': 'Test timer'
            },
            headers=auth_headers,
            follow_redirects=False
        )
        
        with client.application.app_context():
            after_count = Activity.query.count()
            assert after_count == before_count + 1
            
            activity = Activity.query.order_by(Activity.created_at.desc()).first()
            assert activity.action == 'started'
            assert activity.entity_type == 'time_entry'
            assert test_project.name in activity.description
    
    def test_timer_stop_logs_activity(self, client, auth_headers, test_user, test_project):
        """Test that stopping a timer logs an activity"""
        with client.application.app_context():
            # Create an active timer
            from app.models.time_entry import local_now
            timer = TimeEntry(
                user_id=test_user.id,
                project_id=test_project.id,
                start_time=local_now(),
                source='auto'
            )
            db.session.add(timer)
            db.session.commit()
            
            before_count = Activity.query.count()
        
        response = client.post(
            '/timer/stop',
            headers=auth_headers,
            follow_redirects=False
        )
        
        with client.application.app_context():
            after_count = Activity.query.count()
            assert after_count == before_count + 1
            
            activity = Activity.query.order_by(Activity.created_at.desc()).first()
            assert activity.action == 'stopped'
            assert activity.entity_type == 'time_entry'
            assert test_project.name in activity.description


class TestActivityWidget:
    """Tests for the activity feed widget on dashboard"""
    
    def test_dashboard_includes_activities(self, client, auth_headers, test_user, test_project):
        """Test that the dashboard includes recent activities"""
        with client.application.app_context():
            # Create some activities
            Activity.log(
                user_id=test_user.id,
                action='created',
                entity_type='project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                description='Test activity'
            )
        
        response = client.get('/dashboard', headers=auth_headers)
        assert response.status_code == 200
        assert b'Recent Activity' in response.data
        assert b'Test activity' in response.data

