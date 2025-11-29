"""Smoke tests for audit trail feature"""

import pytest
from datetime import datetime
from app.models import AuditLog, Project, User, Task
from app import db


@pytest.mark.smoke
class TestAuditTrailSmoke:
    """Smoke tests to verify audit trail feature works end-to-end"""

    def test_audit_log_creation_smoke(self, app, test_user, test_project):
        """Smoke test: Create an audit log entry"""
        with app.app_context():
            audit_log = AuditLog.log_change(
                user_id=test_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
                change_description="Smoke test audit log",
            )

            # Verify log was created
            logs = AuditLog.query.filter_by(entity_type="Project", entity_id=test_project.id).all()

            assert len(logs) > 0
            assert logs[0].action == "created"
            assert logs[0].user_id == test_user.id

    def test_audit_log_field_change_tracking_smoke(self, app, test_user, test_project):
        """Smoke test: Track field-level changes"""
        with app.app_context():
            # Log a field change
            AuditLog.log_change(
                user_id=test_user.id,
                action="updated",
                entity_type="Project",
                entity_id=test_project.id,
                field_name="name",
                old_value="Old Project Name",
                new_value="New Project Name",
                entity_name=test_project.name,
            )

            # Verify field change was logged
            logs = AuditLog.query.filter_by(entity_type="Project", entity_id=test_project.id, field_name="name").all()

            assert len(logs) > 0
            log = logs[0]
            assert log.field_name == "name"
            assert log.get_old_value() == "Old Project Name"
            assert log.get_new_value() == "New Project Name"

    def test_audit_log_entity_history_smoke(self, app, test_user, test_project):
        """Smoke test: Retrieve entity history"""
        with app.app_context():
            # Create multiple audit logs for the same entity
            for i in range(3):
                AuditLog.log_change(
                    user_id=test_user.id,
                    action="updated",
                    entity_type="Project",
                    entity_id=test_project.id,
                    field_name=f"field_{i}",
                    old_value=f"old_{i}",
                    new_value=f"new_{i}",
                    entity_name=test_project.name,
                )

            # Retrieve entity history
            history = AuditLog.get_for_entity("Project", test_project.id, limit=10)

            assert len(history) == 3
            assert all(log.entity_type == "Project" for log in history)
            assert all(log.entity_id == test_project.id for log in history)

    def test_audit_log_user_activity_smoke(self, app, test_user, test_project):
        """Smoke test: Retrieve user activity history"""
        with app.app_context():
            # Create multiple audit logs by the same user
            for i in range(3):
                AuditLog.log_change(
                    user_id=test_user.id,
                    action="updated",
                    entity_type="Project",
                    entity_id=test_project.id,
                    field_name=f"field_{i}",
                    old_value=f"old_{i}",
                    new_value=f"new_{i}",
                    entity_name=test_project.name,
                )

            # Retrieve user activity
            user_logs = AuditLog.get_for_user(test_user.id, limit=10)

            assert len(user_logs) >= 3
            assert all(log.user_id == test_user.id for log in user_logs)

    def test_audit_log_filtering_smoke(self, app, test_user, test_project):
        """Smoke test: Filter audit logs by various criteria"""
        with app.app_context():
            # Create audit logs with different actions
            AuditLog.log_change(
                user_id=test_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )
            AuditLog.log_change(
                user_id=test_user.id,
                action="updated",
                entity_type="Project",
                entity_id=test_project.id,
                field_name="name",
                old_value="Old",
                new_value="New",
                entity_name=test_project.name,
            )
            AuditLog.log_change(
                user_id=test_user.id,
                action="deleted",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )

            # Filter by action
            created_logs = AuditLog.get_recent(action="created", limit=10)
            assert len(created_logs) == 1
            assert created_logs[0].action == "created"

            # Filter by entity type
            project_logs = AuditLog.get_recent(entity_type="Project", limit=10)
            assert len(project_logs) >= 3

            # Filter by user
            user_logs = AuditLog.get_recent(user_id=test_user.id, limit=10)
            assert len(user_logs) >= 3

    def test_audit_log_value_serialization_smoke(self, app, test_user, test_project):
        """Smoke test: Verify value serialization works correctly"""
        with app.app_context():
            # Test with various value types
            test_cases = [
                ("string", "Old Value", "New Value"),
                ("number", 123, 456),
                ("boolean", True, False),
                ("datetime", datetime(2024, 1, 1), datetime(2024, 1, 2)),
            ]

            for field_type, old_val, new_val in test_cases:
                AuditLog.log_change(
                    user_id=test_user.id,
                    action="updated",
                    entity_type="Project",
                    entity_id=test_project.id,
                    field_name=f"test_{field_type}",
                    old_value=old_val,
                    new_value=new_val,
                    entity_name=test_project.name,
                )

            # Verify all logs were created
            logs = AuditLog.query.filter_by(entity_type="Project", entity_id=test_project.id).all()

            assert len(logs) >= len(test_cases)

            # Verify values can be retrieved
            for log in logs:
                if log.field_name and log.field_name.startswith("test_"):
                    old_val = log.get_old_value()
                    new_val = log.get_new_value()
                    assert old_val is not None or log.old_value is None
                    assert new_val is not None or log.new_value is None
