"""Tests for enhanced project archiving functionality"""

import pytest
from datetime import datetime
from app.models import Project, TimeEntry, Activity


class TestProjectArchivingModel:
    """Test project archiving model functionality"""

    @pytest.mark.models
    def test_project_archive_with_metadata(self, app, project, admin_user):
        """Test archiving a project with metadata"""
        from app import db

        reason = "Project completed successfully"
        project.archive(user_id=admin_user.id, reason=reason)
        db.session.commit()

        assert project.status == "archived"
        assert project.is_archived is True
        assert project.archived_at is not None
        assert project.archived_by == admin_user.id
        assert project.archived_reason == reason

    @pytest.mark.models
    def test_project_archive_without_reason(self, app, project, admin_user):
        """Test archiving a project without a reason"""
        from app import db

        project.archive(user_id=admin_user.id, reason=None)
        db.session.commit()

        assert project.status == "archived"
        assert project.is_archived is True
        assert project.archived_at is not None
        assert project.archived_by == admin_user.id
        assert project.archived_reason is None

    @pytest.mark.models
    def test_project_unarchive_clears_metadata(self, app, project, admin_user):
        """Test unarchiving a project clears archiving metadata"""
        from app import db

        # Archive first
        project.archive(user_id=admin_user.id, reason="Test reason")
        db.session.commit()
        assert project.is_archived is True

        # Then unarchive
        project.unarchive()
        db.session.commit()

        assert project.status == "active"
        assert project.is_archived is False
        assert project.archived_at is None
        assert project.archived_by is None
        assert project.archived_reason is None

    @pytest.mark.models
    def test_project_archived_by_user_property(self, app, project, admin_user):
        """Test archived_by_user property returns correct user"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        archived_by_user = project.archived_by_user
        assert archived_by_user is not None
        assert archived_by_user.id == admin_user.id
        assert archived_by_user.username == admin_user.username

    @pytest.mark.models
    def test_project_to_dict_includes_archive_metadata(self, app, project, admin_user):
        """Test to_dict includes archiving metadata"""
        from app import db

        reason = "Project completed"
        project.archive(user_id=admin_user.id, reason=reason)
        db.session.commit()

        project_dict = project.to_dict()

        assert project_dict["is_archived"] is True
        assert project_dict["archived_at"] is not None
        assert project_dict["archived_by"] == admin_user.id
        assert project_dict["archived_reason"] == reason

    @pytest.mark.models
    def test_archived_at_timestamp_accuracy(self, app, project, admin_user):
        """Test that archived_at timestamp is accurate"""
        from app import db

        before_archive = datetime.utcnow()
        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        after_archive = datetime.utcnow()

        assert project.archived_at is not None
        assert before_archive <= project.archived_at <= after_archive


class TestProjectArchivingRoutes:
    """Test project archiving routes"""

    @pytest.mark.routes
    def test_archive_project_route_get(self, admin_authenticated_client, app, project):
        """Test GET archive route shows form"""
        project_id = project.id

        response = admin_authenticated_client.get(f"/projects/{project_id}/archive")

        assert response.status_code == 200
        assert b"Archive Project" in response.data
        assert b"Reason for Archiving" in response.data
        assert b"Quick Select" in response.data

    @pytest.mark.routes
    def test_archive_project_route_post_with_reason(self, admin_authenticated_client, app, project):
        """Test POST archive route with reason"""
        from app import db

        project_id = project.id
        reason = "Project completed successfully"

        response = admin_authenticated_client.post(
            f"/projects/{project_id}/archive", data={"reason": reason}, follow_redirects=True
        )

        assert response.status_code == 200

        db.session.refresh(project)
        assert project.status == "archived"
        assert project.archived_reason == reason
        assert project.archived_by is not None

    @pytest.mark.routes
    def test_archive_project_route_post_without_reason(self, admin_authenticated_client, app, project):
        """Test POST archive route without reason"""
        from app import db

        project_id = project.id

        response = admin_authenticated_client.post(f"/projects/{project_id}/archive", data={}, follow_redirects=True)

        assert response.status_code == 200

        db.session.refresh(project)
        assert project.status == "archived"
        assert project.archived_reason is None

    @pytest.mark.routes
    def test_unarchive_project_clears_metadata(self, admin_authenticated_client, app, project, admin_user):
        """Test unarchive route clears metadata"""
        from app import db

        # Archive first
        project.archive(user_id=admin_user.id, reason="Test reason")
        db.session.commit()
        project_id = project.id

        # Unarchive
        response = admin_authenticated_client.post(f"/projects/{project_id}/unarchive", follow_redirects=True)

        assert response.status_code == 200

        db.session.refresh(project)
        assert project.status == "active"
        assert project.archived_at is None
        assert project.archived_by is None
        assert project.archived_reason is None

    @pytest.mark.routes
    def test_bulk_archive_with_reason(self, admin_authenticated_client, app, test_client):
        """Test bulk archiving multiple projects with reason"""
        from app import db

        # Create multiple projects
        project1 = Project(name="Project 1", client_id=test_client.id)
        project2 = Project(name="Project 2", client_id=test_client.id)
        db.session.add_all([project1, project2])
        db.session.commit()

        reason = "Bulk archive - projects completed"

        response = admin_authenticated_client.post(
            "/projects/bulk-status-change",
            data={"project_ids[]": [project1.id, project2.id], "new_status": "archived", "archive_reason": reason},
            follow_redirects=True,
        )

        assert response.status_code == 200

        db.session.refresh(project1)
        db.session.refresh(project2)

        assert project1.status == "archived"
        assert project1.archived_reason == reason
        assert project2.status == "archived"
        assert project2.archived_reason == reason

    @pytest.mark.routes
    def test_filter_archived_projects(self, admin_authenticated_client, app, test_client, admin_user):
        """Test filtering projects by archived status"""
        from app import db

        # Create projects with different statuses
        active_project = Project(name="Active Project", client_id=test_client.id)
        archived_project = Project(name="Archived Project", client_id=test_client.id)

        db.session.add_all([active_project, archived_project])
        db.session.commit()

        archived_project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        # Test filter for archived projects
        response = admin_authenticated_client.get("/projects?status=archived")
        assert response.status_code == 200
        assert b"Archived Project" in response.data
        assert b"Active Project" not in response.data

    @pytest.mark.routes
    def test_non_admin_cannot_archive(self, authenticated_client, app, project):
        """Test that non-admin users cannot archive projects"""
        project_id = project.id

        response = authenticated_client.post(
            f"/projects/{project_id}/archive", data={"reason": "Test"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"You do not have permission to archive projects" in response.data


class TestArchivedProjectValidation:
    """Test validation for archived projects"""

    @pytest.mark.routes
    def test_cannot_start_timer_on_archived_project(self, authenticated_client, app, project, admin_user):
        """Test that users cannot start timers on archived projects"""
        from app import db

        # Archive the project
        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        project_id = project.id

        # Try to start a timer
        response = authenticated_client.post("/timer/start", data={"project_id": project_id}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Cannot start timer for an archived project" in response.data

    @pytest.mark.routes
    def test_cannot_create_manual_entry_on_archived_project(self, authenticated_client, app, project, admin_user):
        """Test that users cannot create manual entries on archived projects"""
        from app import db

        # Archive the project
        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        project_id = project.id

        # Try to create a manual entry
        response = authenticated_client.post(
            "/timer/manual",
            data={
                "project_id": project_id,
                "start_date": "2025-01-01",
                "start_time": "09:00",
                "end_date": "2025-01-01",
                "end_time": "17:00",
                "notes": "Test",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Cannot create time entries for an archived project" in response.data

    @pytest.mark.routes
    def test_cannot_create_bulk_entry_on_archived_project(self, authenticated_client, app, project, admin_user):
        """Test that users cannot create bulk entries on archived projects"""
        from app import db

        # Archive the project
        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        project_id = project.id

        # Try to create bulk entries
        response = authenticated_client.post(
            "/timer/bulk",
            data={
                "project_id": project_id,
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "start_time": "09:00",
                "end_time": "17:00",
                "skip_weekends": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Cannot create time entries for an archived project" in response.data

    @pytest.mark.routes
    def test_archived_projects_not_in_active_list(self, authenticated_client, app, test_client, admin_user):
        """Test that archived projects don't appear in timer dropdown"""
        from app import db

        # Create and archive a project
        archived_project = Project(name="Archived Project", client_id=test_client.id)
        active_project = Project(name="Active Project", client_id=test_client.id)

        db.session.add_all([archived_project, active_project])
        db.session.commit()

        archived_project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        # Check dashboard
        response = authenticated_client.get("/")
        assert response.status_code == 200

        # Active project should be in select options
        assert b"Active Project" in response.data
        # Archived project should not be in select options for starting timer
        # (This is a basic check - more sophisticated checks could verify the select element)


class TestArchivingActivityLogs:
    """Test that archiving creates activity logs"""

    @pytest.mark.routes
    def test_archive_creates_activity_log(self, admin_authenticated_client, app, project):
        """Test that archiving a project creates an activity log"""
        from app import db

        project_id = project.id
        reason = "Project completed"

        response = admin_authenticated_client.post(
            f"/projects/{project_id}/archive", data={"reason": reason}, follow_redirects=True
        )

        assert response.status_code == 200

        # Check that activity was logged
        activity = Activity.query.filter_by(entity_type="project", entity_id=project_id, action="archived").first()

        assert activity is not None
        assert reason in activity.description

    @pytest.mark.routes
    def test_unarchive_creates_activity_log(self, admin_authenticated_client, app, project, admin_user):
        """Test that unarchiving a project creates an activity log"""
        from app import db

        # Archive first
        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        project_id = project.id

        # Unarchive
        response = admin_authenticated_client.post(f"/projects/{project_id}/unarchive", follow_redirects=True)

        assert response.status_code == 200

        # Check that activity was logged
        activity = Activity.query.filter_by(entity_type="project", entity_id=project_id, action="unarchived").first()

        assert activity is not None


class TestArchivingUI:
    """Test archiving UI elements"""

    @pytest.mark.routes
    def test_project_view_shows_archive_metadata(self, admin_authenticated_client, app, project, admin_user):
        """Test that project view shows archiving metadata"""
        from app import db

        # Archive the project
        reason = "Project completed successfully"
        project.archive(user_id=admin_user.id, reason=reason)
        db.session.commit()
        project_id = project.id

        # View the project
        response = admin_authenticated_client.get(f"/projects/{project_id}")
        assert response.status_code == 200

        # Check for archive information
        assert b"Archive Information" in response.data
        assert b"Archived on:" in response.data
        assert b"Archived by:" in response.data
        assert b"Reason:" in response.data
        assert reason.encode() in response.data

    @pytest.mark.routes
    def test_project_list_shows_archived_status_badge(self, admin_authenticated_client, app, test_client, admin_user):
        """Test that project list shows archived status badge"""
        from app import db

        # Create and archive a project
        archived_project = Project(name="Archived Test Project", client_id=test_client.id)
        db.session.add(archived_project)
        db.session.commit()

        archived_project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        # View projects list with archived filter
        response = admin_authenticated_client.get("/projects?status=archived")
        assert response.status_code == 200

        assert b"Archived Test Project" in response.data
        assert b"Archived" in response.data  # Status badge

    @pytest.mark.routes
    def test_archive_form_has_quick_select_buttons(self, admin_authenticated_client, app, project):
        """Test that archive form has quick select buttons"""
        project_id = project.id

        response = admin_authenticated_client.get(f"/projects/{project_id}/archive")
        assert response.status_code == 200

        # Check for quick select buttons
        assert b"Project Completed" in response.data
        assert b"Contract Ended" in response.data
        assert b"Cancelled" in response.data
        assert b"On Hold" in response.data
        assert b"Maintenance Ended" in response.data


@pytest.mark.smoke
class TestArchivingSmokeTests:
    """Smoke tests for complete archiving workflow"""

    def test_complete_archive_unarchive_workflow(self, admin_authenticated_client, app, project, admin_user):
        """Test complete workflow: create, archive, view, unarchive"""
        from app import db

        project_id = project.id
        project_name = project.name

        # 1. Verify project is active
        response = admin_authenticated_client.get("/projects")
        assert response.status_code == 200
        assert project_name.encode() in response.data

        # 2. Archive the project with reason
        reason = "Complete smoke test"
        response = admin_authenticated_client.post(
            f"/projects/{project_id}/archive", data={"reason": reason}, follow_redirects=True
        )
        assert response.status_code == 200

        # 3. Verify it's archived
        db.session.refresh(project)
        assert project.status == "archived"
        assert project.archived_reason == reason

        # 4. View archived project
        response = admin_authenticated_client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        assert b"Archive Information" in response.data
        assert reason.encode() in response.data

        # 5. Verify it appears in archived filter
        response = admin_authenticated_client.get("/projects?status=archived")
        assert response.status_code == 200
        assert project_name.encode() in response.data

        # 6. Unarchive the project
        response = admin_authenticated_client.post(f"/projects/{project_id}/unarchive", follow_redirects=True)
        assert response.status_code == 200

        # 7. Verify it's active again
        db.session.refresh(project)
        assert project.status == "active"
        assert project.archived_at is None

        # 8. Verify it appears in active projects
        response = admin_authenticated_client.get("/projects?status=active")
        assert response.status_code == 200
        assert project_name.encode() in response.data
