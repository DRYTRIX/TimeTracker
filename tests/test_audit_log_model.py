"""Tests for AuditLog model"""

import pytest
from datetime import datetime
from app.models import AuditLog, User, Project
from app import db


class TestAuditLogModel:
    """Tests for the AuditLog model"""
    
    def test_audit_log_creation(self, app, test_user, test_project):
        """Test creating an audit log entry"""
        with app.app_context():
            audit_log = AuditLog(
                user_id=test_user.id,
                action='created',
                entity_type='Project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                change_description=f'Created project "{test_project.name}"'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            assert audit_log.id is not None
            assert audit_log.user_id == test_user.id
            assert audit_log.action == 'created'
            assert audit_log.entity_type == 'Project'
            assert audit_log.entity_id == test_project.id
            assert audit_log.created_at is not None
    
    def test_audit_log_log_change_method(self, app, test_user, test_project):
        """Test the AuditLog.log_change() class method"""
        with app.app_context():
            AuditLog.log_change(
                user_id=test_user.id,
                action='updated',
                entity_type='Project',
                entity_id=test_project.id,
                field_name='name',
                old_value='Old Name',
                new_value='New Name',
                entity_name=test_project.name,
                change_description='Updated project name'
            )
            
            audit_log = AuditLog.query.filter_by(
                user_id=test_user.id,
                entity_type='Project',
                entity_id=test_project.id,
                field_name='name'
            ).first()
            
            assert audit_log is not None
            assert audit_log.action == 'updated'
            assert audit_log.field_name == 'name'
            assert audit_log.get_old_value() == 'Old Name'
            assert audit_log.get_new_value() == 'New Name'
    
    def test_audit_log_value_encoding(self, app, test_user, test_project):
        """Test that values are properly encoded/decoded"""
        with app.app_context():
            # Test with datetime
            old_dt = datetime(2024, 1, 1, 12, 0, 0)
            new_dt = datetime(2024, 1, 2, 12, 0, 0)
            
            AuditLog.log_change(
                user_id=test_user.id,
                action='updated',
                entity_type='Project',
                entity_id=test_project.id,
                field_name='updated_at',
                old_value=old_dt,
                new_value=new_dt,
                entity_name=test_project.name
            )
            
            audit_log = AuditLog.query.filter_by(
                entity_type='Project',
                entity_id=test_project.id,
                field_name='updated_at'
            ).first()
            
            assert audit_log is not None
            # Values should be JSON-encoded strings
            assert isinstance(audit_log.old_value, str)
            assert isinstance(audit_log.new_value, str)
            # Decoded values should match
            assert audit_log.get_old_value() == old_dt.isoformat()
            assert audit_log.get_new_value() == new_dt.isoformat()
    
    def test_audit_log_get_for_entity(self, app, test_user, test_project):
        """Test getting audit logs for a specific entity"""
        with app.app_context():
            # Create multiple audit logs for the same entity
            for i in range(5):
                AuditLog.log_change(
                    user_id=test_user.id,
                    action='updated',
                    entity_type='Project',
                    entity_id=test_project.id,
                    field_name=f'field_{i}',
                    old_value=f'old_{i}',
                    new_value=f'new_{i}',
                    entity_name=test_project.name
                )
            
            # Get audit logs for this entity
            logs = AuditLog.get_for_entity('Project', test_project.id, limit=3)
            
            assert len(logs) == 3
            assert all(log.entity_type == 'Project' for log in logs)
            assert all(log.entity_id == test_project.id for log in logs)
    
    def test_audit_log_get_for_user(self, app, test_user, test_project):
        """Test getting audit logs for a specific user"""
        with app.app_context():
            # Create multiple audit logs by the same user
            for i in range(5):
                AuditLog.log_change(
                    user_id=test_user.id,
                    action='updated',
                    entity_type='Project',
                    entity_id=test_project.id,
                    field_name=f'field_{i}',
                    old_value=f'old_{i}',
                    new_value=f'new_{i}',
                    entity_name=test_project.name
                )
            
            # Get audit logs for this user
            logs = AuditLog.get_for_user(test_user.id, limit=3)
            
            assert len(logs) == 3
            assert all(log.user_id == test_user.id for log in logs)
    
    def test_audit_log_get_recent(self, app, test_user, test_project):
        """Test getting recent audit logs with filters"""
        with app.app_context():
            # Create audit logs with different actions
            AuditLog.log_change(
                user_id=test_user.id,
                action='created',
                entity_type='Project',
                entity_id=test_project.id,
                entity_name=test_project.name
            )
            AuditLog.log_change(
                user_id=test_user.id,
                action='updated',
                entity_type='Project',
                entity_id=test_project.id,
                field_name='name',
                old_value='Old',
                new_value='New',
                entity_name=test_project.name
            )
            AuditLog.log_change(
                user_id=test_user.id,
                action='deleted',
                entity_type='Project',
                entity_id=test_project.id,
                entity_name=test_project.name
            )
            
            # Filter by action
            created_logs = AuditLog.get_recent(action='created', limit=10)
            assert len(created_logs) == 1
            assert created_logs[0].action == 'created'
            
            # Filter by entity type
            project_logs = AuditLog.get_recent(entity_type='Project', limit=10)
            assert len(project_logs) == 3
    
    def test_audit_log_to_dict(self, app, test_user, test_project):
        """Test converting audit log to dictionary"""
        with app.app_context():
            audit_log = AuditLog(
                user_id=test_user.id,
                action='created',
                entity_type='Project',
                entity_id=test_project.id,
                entity_name=test_project.name,
                change_description='Test description'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            log_dict = audit_log.to_dict()
            
            assert isinstance(log_dict, dict)
            assert log_dict['id'] == audit_log.id
            assert log_dict['user_id'] == test_user.id
            assert log_dict['action'] == 'created'
            assert log_dict['entity_type'] == 'Project'
            assert log_dict['entity_id'] == test_project.id
            assert log_dict['username'] == test_user.username
            assert log_dict['display_name'] == test_user.display_name
    
    def test_audit_log_icons_and_colors(self, app, test_user, test_project):
        """Test icon and color methods"""
        with app.app_context():
            created_log = AuditLog(
                user_id=test_user.id,
                action='created',
                entity_type='Project',
                entity_id=test_project.id
            )
            assert 'green' in created_log.get_icon()
            assert created_log.get_color() == 'green'
            
            updated_log = AuditLog(
                user_id=test_user.id,
                action='updated',
                entity_type='Project',
                entity_id=test_project.id
            )
            assert 'blue' in updated_log.get_icon()
            assert updated_log.get_color() == 'blue'
            
            deleted_log = AuditLog(
                user_id=test_user.id,
                action='deleted',
                entity_type='Project',
                entity_id=test_project.id
            )
            assert 'red' in deleted_log.get_icon()
            assert deleted_log.get_color() == 'red'

