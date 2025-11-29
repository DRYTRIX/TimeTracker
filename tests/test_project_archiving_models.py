"""Model tests for project archiving functionality"""

import pytest
from datetime import datetime, timedelta
from app.models import Project


@pytest.mark.models
class TestProjectArchivingFields:
    """Test project archiving model fields"""

    def test_archived_at_field_exists(self, app, project):
        """Test that archived_at field exists and can be set"""
        from app import db

        now = datetime.utcnow()
        project.archived_at = now
        db.session.commit()

        db.session.refresh(project)
        assert project.archived_at is not None
        assert abs((project.archived_at - now).total_seconds()) < 1

    def test_archived_by_field_exists(self, app, project, admin_user):
        """Test that archived_by field exists and references users"""
        from app import db

        project.archived_by = admin_user.id
        db.session.commit()

        db.session.refresh(project)
        assert project.archived_by == admin_user.id

    def test_archived_reason_field_exists(self, app, project):
        """Test that archived_reason field exists and stores text"""
        from app import db

        long_reason = "This is a very long reason for archiving the project. " * 10
        project.archived_reason = long_reason
        db.session.commit()

        db.session.refresh(project)
        assert project.archived_reason == long_reason

    def test_archived_at_is_nullable(self, app, test_client):
        """Test that archived_at can be null for non-archived projects"""
        from app import db

        project = Project(name="Test Project", client_id=test_client.id)
        db.session.add(project)
        db.session.commit()

        assert project.archived_at is None

    def test_archived_by_is_nullable(self, app, test_client):
        """Test that archived_by can be null"""
        from app import db

        project = Project(name="Test Project", client_id=test_client.id)
        db.session.add(project)
        db.session.commit()

        assert project.archived_by is None

    def test_archived_reason_is_nullable(self, app, test_client):
        """Test that archived_reason can be null"""
        from app import db

        project = Project(name="Test Project", client_id=test_client.id)
        db.session.add(project)
        db.session.commit()

        assert project.archived_reason is None


@pytest.mark.models
class TestProjectArchiveMethod:
    """Test project archive() method"""

    def test_archive_sets_status(self, app, project):
        """Test that archive() sets status to 'archived'"""
        from app import db

        project.archive()
        db.session.commit()

        assert project.status == "archived"

    def test_archive_sets_timestamp(self, app, project):
        """Test that archive() sets archived_at timestamp"""
        from app import db

        before = datetime.utcnow()
        project.archive()
        db.session.commit()
        after = datetime.utcnow()

        assert project.archived_at is not None
        assert before <= project.archived_at <= after

    def test_archive_with_user_id(self, app, project, admin_user):
        """Test that archive() accepts and stores user_id"""
        from app import db

        project.archive(user_id=admin_user.id)
        db.session.commit()

        assert project.archived_by == admin_user.id

    def test_archive_with_reason(self, app, project):
        """Test that archive() accepts and stores reason"""
        from app import db

        reason = "Test archiving reason"
        project.archive(reason=reason)
        db.session.commit()

        assert project.archived_reason == reason

    def test_archive_with_all_parameters(self, app, project, admin_user):
        """Test that archive() works with all parameters"""
        from app import db

        reason = "Comprehensive test"
        project.archive(user_id=admin_user.id, reason=reason)
        db.session.commit()

        assert project.status == "archived"
        assert project.archived_at is not None
        assert project.archived_by == admin_user.id
        assert project.archived_reason == reason

    def test_archive_without_parameters(self, app, project):
        """Test that archive() works without parameters"""
        from app import db

        project.archive()
        db.session.commit()

        assert project.status == "archived"
        assert project.archived_at is not None
        assert project.archived_by is None
        assert project.archived_reason is None

    def test_archive_updates_updated_at(self, app, project):
        """Test that archive() updates the updated_at timestamp"""
        from app import db

        original_updated_at = project.updated_at
        # Wait a tiny bit to ensure timestamp difference
        import time

        time.sleep(0.01)

        project.archive()
        db.session.commit()

        assert project.updated_at > original_updated_at

    def test_archive_can_be_called_multiple_times(self, app, project, admin_user):
        """Test that archive() can be called multiple times (re-archiving)"""
        from app import db

        # First archive
        project.archive(user_id=admin_user.id, reason="First time")
        db.session.commit()
        first_archived_at = project.archived_at

        import time

        time.sleep(0.01)

        # Second archive with different reason
        project.archive(user_id=admin_user.id, reason="Second time")
        db.session.commit()

        assert project.status == "archived"
        assert project.archived_at > first_archived_at
        assert project.archived_reason == "Second time"


@pytest.mark.models
class TestProjectUnarchiveMethod:
    """Test project unarchive() method"""

    def test_unarchive_sets_status_to_active(self, app, project, admin_user):
        """Test that unarchive() sets status to 'active'"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        project.unarchive()
        db.session.commit()

        assert project.status == "active"

    def test_unarchive_clears_archived_at(self, app, project, admin_user):
        """Test that unarchive() clears archived_at"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        assert project.archived_at is not None

        project.unarchive()
        db.session.commit()

        assert project.archived_at is None

    def test_unarchive_clears_archived_by(self, app, project, admin_user):
        """Test that unarchive() clears archived_by"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        assert project.archived_by is not None

        project.unarchive()
        db.session.commit()

        assert project.archived_by is None

    def test_unarchive_clears_archived_reason(self, app, project, admin_user):
        """Test that unarchive() clears archived_reason"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test reason")
        db.session.commit()
        assert project.archived_reason is not None

        project.unarchive()
        db.session.commit()

        assert project.archived_reason is None

    def test_unarchive_updates_updated_at(self, app, project, admin_user):
        """Test that unarchive() updates the updated_at timestamp"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()
        original_updated_at = project.updated_at

        import time

        time.sleep(0.01)

        project.unarchive()
        db.session.commit()

        assert project.updated_at > original_updated_at


@pytest.mark.models
class TestProjectArchiveProperties:
    """Test project archiving properties"""

    def test_is_archived_property_when_archived(self, app, project, admin_user):
        """Test that is_archived property returns True for archived projects"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        assert project.is_archived is True

    def test_is_archived_property_when_active(self, app, project):
        """Test that is_archived property returns False for active projects"""
        assert project.is_archived is False

    def test_is_archived_property_when_inactive(self, app, project):
        """Test that is_archived property returns False for inactive projects"""
        from app import db

        project.deactivate()
        db.session.commit()

        assert project.is_archived is False

    def test_archived_by_user_property_returns_user(self, app, project, admin_user):
        """Test that archived_by_user property returns the correct user"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        archived_by = project.archived_by_user
        assert archived_by is not None
        assert archived_by.id == admin_user.id
        assert archived_by.username == admin_user.username

    def test_archived_by_user_property_returns_none_when_not_archived(self, app, project):
        """Test that archived_by_user property returns None for non-archived projects"""
        assert project.archived_by_user is None

    def test_archived_by_user_property_returns_none_when_user_deleted(self, app, project, test_client):
        """Test archived_by_user handles deleted users gracefully"""
        from app import db
        from app.models import User

        # Create a temporary user
        temp_user = User(username="tempuser", email="temp@test.com")
        temp_user.is_active = True  # Set after creation
        db.session.add(temp_user)
        db.session.commit()
        temp_user_id = temp_user.id

        # Archive with temp user
        project.archive(user_id=temp_user_id, reason="Test")
        db.session.commit()

        # Delete the user
        db.session.delete(temp_user)
        db.session.commit()

        # archived_by should still be set but user query returns None
        assert project.archived_by == temp_user_id
        assert project.archived_by_user is None


@pytest.mark.models
class TestProjectToDictArchiveFields:
    """Test project to_dict() method with archive fields"""

    def test_to_dict_includes_is_archived(self, app, project):
        """Test that to_dict includes is_archived field"""
        project_dict = project.to_dict()

        assert "is_archived" in project_dict
        assert project_dict["is_archived"] is False

    def test_to_dict_includes_archived_at(self, app, project, admin_user):
        """Test that to_dict includes archived_at field"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        project_dict = project.to_dict()

        assert "archived_at" in project_dict
        assert project_dict["archived_at"] is not None
        # Check that it's in ISO format
        assert "T" in project_dict["archived_at"]

    def test_to_dict_includes_archived_by(self, app, project, admin_user):
        """Test that to_dict includes archived_by field"""
        from app import db

        project.archive(user_id=admin_user.id, reason="Test")
        db.session.commit()

        project_dict = project.to_dict()

        assert "archived_by" in project_dict
        assert project_dict["archived_by"] == admin_user.id

    def test_to_dict_includes_archived_reason(self, app, project, admin_user):
        """Test that to_dict includes archived_reason field"""
        from app import db

        reason = "Test archiving"
        project.archive(user_id=admin_user.id, reason=reason)
        db.session.commit()

        project_dict = project.to_dict()

        assert "archived_reason" in project_dict
        assert project_dict["archived_reason"] == reason

    def test_to_dict_archive_fields_null_when_not_archived(self, app, project):
        """Test that archive fields are null for non-archived projects"""
        project_dict = project.to_dict()

        assert project_dict["is_archived"] is False
        assert project_dict["archived_at"] is None
        assert project_dict["archived_by"] is None
        assert project_dict["archived_reason"] is None


@pytest.mark.models
class TestProjectArchiveEdgeCases:
    """Test edge cases for project archiving"""

    def test_archive_with_empty_string_reason(self, app, project):
        """Test archiving with empty string reason treats it as None"""
        from app import db

        project.archive(reason="")
        db.session.commit()

        # Empty string should be stored as-is (route layer handles conversion to None)
        assert project.archived_reason == ""

    def test_archive_with_very_long_reason(self, app, project):
        """Test archiving with very long reason"""
        from app import db

        # Create a 10000 character reason
        long_reason = "x" * 10000
        project.archive(reason=long_reason)
        db.session.commit()

        db.session.refresh(project)
        assert len(project.archived_reason) == 10000

    def test_archive_with_special_characters_in_reason(self, app, project):
        """Test archiving with special characters in reason"""
        from app import db

        special_reason = "Test with 特殊字符 émojis 🎉 and symbols: @#$%^&*()"
        project.archive(reason=special_reason)
        db.session.commit()

        db.session.refresh(project)
        assert project.archived_reason == special_reason

    def test_archive_with_invalid_user_id(self, app, project):
        """Test that archiving with non-existent user_id still works"""
        from app import db

        # Use a user ID that doesn't exist
        project.archive(user_id=999999, reason="Test")
        db.session.commit()

        assert project.status == "archived"
        assert project.archived_by == 999999
        # archived_by_user should return None for invalid ID
        assert project.archived_by_user is None
