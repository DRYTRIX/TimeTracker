"""Tests for audit logging utility"""

import pytest
from datetime import datetime
from app.models import AuditLog, Project, User
from app import db
from app.utils.audit import should_track_model, should_track_field, serialize_value, get_entity_name, get_entity_type


class TestAuditLoggingUtility:
    """Tests for audit logging utility functions"""

    def test_should_track_model(self, app, test_project):
        """Test model tracking detection"""
        with app.app_context():
            assert should_track_model(test_project) == True

            # Test with non-tracked model (if any)
            from app.models import Settings

            settings = Settings()
            assert should_track_model(settings) == True  # Settings is in TRACKED_MODELS

    def test_should_track_field(self):
        """Test field tracking exclusion"""
        assert should_track_field("name") == True
        assert should_track_field("description") == True
        assert should_track_field("id") == False  # Excluded
        assert should_track_field("created_at") == False  # Excluded
        assert should_track_field("updated_at") == False  # Excluded
        assert should_track_field("password") == False  # Excluded
        assert should_track_field("password_hash") == False  # Excluded

    def test_serialize_value(self):
        """Test value serialization"""
        # Test None
        assert serialize_value(None) is None

        # Test datetime
        dt = datetime(2024, 1, 1, 12, 0, 0)
        assert serialize_value(dt) == dt.isoformat()

        # Test Decimal
        from decimal import Decimal

        dec = Decimal("123.45")
        assert serialize_value(dec) == "123.45"

        # Test boolean
        assert serialize_value(True) == True
        assert serialize_value(False) == False

        # Test string
        assert serialize_value("test") == "test"

        # Test list
        assert serialize_value([1, 2, 3]) == "[1, 2, 3]" or serialize_value([1, 2, 3]) == str([1, 2, 3])

    def test_get_entity_name(self, app, test_project, test_user):
        """Test entity name extraction"""
        with app.app_context():
            # Test with project (has 'name' field)
            assert get_entity_name(test_project) == test_project.name

            # Test with user (has 'username' field)
            assert get_entity_name(test_user) == test_user.username

    def test_get_entity_type(self, app, test_project):
        """Test entity type extraction"""
        with app.app_context():
            assert get_entity_type(test_project) == "Project"


class TestAuditLoggingIntegration:
    """Integration tests for audit logging"""

    def test_audit_logging_on_create(self, app, test_user, test_client):
        """Test that audit logs are created when entities are created"""
        with app.app_context():
            project = Project(name="Test Project", client_id=test_client.id)
            db.session.add(project)
            db.session.flush()

            audit_logs = AuditLog.query.filter_by(entity_type="Project", entity_id=project.id, action="created").all()
            assert len(audit_logs) >= 1, "At least one audit log should be created for entity create"
            assert audit_logs[0].action == "created"
            assert audit_logs[0].entity_type == "Project"

    def test_audit_logging_on_update(self, app, test_user, test_project):
        """Test that audit logs are created when entities are updated"""
        with app.app_context():
            project_id = test_project.id
            merged = db.session.merge(test_project)
            merged.name = "Updated Project Name"
            db.session.flush()

            audit_logs = AuditLog.query.filter_by(
                entity_type="Project", entity_id=project_id, action="updated"
            ).all()
            assert len(audit_logs) >= 1, "At least one audit log should be created for entity update"
            assert audit_logs[0].action == "updated"
            assert audit_logs[0].entity_type == "Project"

    def test_audit_logging_on_delete(self, app, test_user, test_project):
        """Test that audit logs are created when entities are deleted"""
        with app.app_context():
            project_id = test_project.id
            merged = db.session.merge(test_project)
            db.session.delete(merged)
            db.session.flush()

            audit_logs = AuditLog.query.filter_by(entity_type="Project", entity_id=project_id, action="deleted").all()
            assert len(audit_logs) >= 1, "At least one audit log should be created for entity delete"
            assert audit_logs[0].action == "deleted"
            assert audit_logs[0].entity_type == "Project"
