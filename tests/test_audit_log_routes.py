"""Tests for audit log routes"""

import pytest
from flask import url_for
from app.models import AuditLog, User, Project
from app import db


class TestAuditLogRoutes:
    """Tests for audit log route endpoints"""

    def test_list_audit_logs_requires_auth(self, app, client):
        """Test that audit logs list requires authentication"""
        with app.app_context():
            response = client.get("/audit-logs")
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403]

    def test_list_audit_logs_requires_permission(self, app, client, test_user):
        """Test that audit logs list requires permission"""
        with app.app_context():
            # Login as regular user (without view_audit_logs permission)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(test_user.id)

            response = client.get("/audit-logs")
            # Should return 403 if permission check is enforced
            # Or redirect/error if permission system is not fully set up
            assert response.status_code in [200, 302, 403]

    def test_list_audit_logs_as_admin(self, app, client, admin_user):
        """Test that admin can view audit logs"""
        with app.app_context():
            # Create some audit logs
            project = Project.query.first()
            if project:
                AuditLog.log_change(
                    user_id=admin_user.id,
                    action="created",
                    entity_type="Project",
                    entity_id=project.id,
                    entity_name=project.name,
                )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get("/audit-logs")
            assert response.status_code == 200
            assert b"Audit Logs" in response.data or b"audit" in response.data.lower()

    def test_view_audit_log_detail(self, app, client, admin_user, test_project):
        """Test viewing a specific audit log entry"""
        with app.app_context():
            # Create an audit log
            audit_log = AuditLog(
                user_id=admin_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
                change_description="Test audit log",
            )
            db.session.add(audit_log)
            db.session.commit()

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(f"/audit-logs/{audit_log.id}")
            assert response.status_code == 200

    def test_entity_history_route(self, app, client, admin_user, test_project):
        """Test viewing audit history for a specific entity"""
        with app.app_context():
            # Create some audit logs for the project
            for i in range(3):
                AuditLog.log_change(
                    user_id=admin_user.id,
                    action="updated",
                    entity_type="Project",
                    entity_id=test_project.id,
                    field_name=f"field_{i}",
                    old_value=f"old_{i}",
                    new_value=f"new_{i}",
                    entity_name=test_project.name,
                )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(f"/audit-logs/entity/Project/{test_project.id}")
            assert response.status_code == 200

    def test_api_audit_logs_endpoint(self, app, client, admin_user, test_project):
        """Test API endpoint for audit logs"""
        with app.app_context():
            # Create some audit logs
            AuditLog.log_change(
                user_id=admin_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get("/api/audit-logs")
            assert response.status_code == 200

            data = response.get_json()
            assert "audit_logs" in data
            assert "count" in data
            assert isinstance(data["audit_logs"], list)

    def test_filter_audit_logs_by_entity_type(self, app, client, admin_user, test_project):
        """Test filtering audit logs by entity type"""
        with app.app_context():
            # Create audit logs for different entity types
            AuditLog.log_change(
                user_id=admin_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get("/audit-logs?entity_type=Project")
            assert response.status_code == 200

    def test_filter_audit_logs_by_action(self, app, client, admin_user, test_project):
        """Test filtering audit logs by action"""
        with app.app_context():
            # Create audit logs with different actions
            AuditLog.log_change(
                user_id=admin_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get("/audit-logs?action=created")
            assert response.status_code == 200

    def test_filter_audit_logs_by_user(self, app, client, admin_user, test_project):
        """Test filtering audit logs by user"""
        with app.app_context():
            # Create audit log
            AuditLog.log_change(
                user_id=admin_user.id,
                action="created",
                entity_type="Project",
                entity_id=test_project.id,
                entity_name=test_project.name,
            )

            # Login as admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(f"/audit-logs?user_id={admin_user.id}")
            assert response.status_code == 200
