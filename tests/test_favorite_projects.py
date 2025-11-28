"""
Comprehensive tests for Favorite Projects functionality.

This module tests:
- UserFavoriteProject model creation and validation
- Relationships between User and Project models
- Favorite/unfavorite routes and API endpoints
- Filtering projects by favorites
- User permissions and access control
"""

import pytest
from datetime import datetime
from decimal import Decimal
from app import create_app, db
from app.models import User, Project, Client, UserFavoriteProject


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key-do-not-use-in-production",
            "SERVER_NAME": "localhost:5000",
            "APPLICATION_ROOT": "/",
            "PREFERRED_URL_SCHEME": "http",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client_fixture(app):
    """Create a test Flask client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def test_admin(app):
    """Create a test admin user."""
    with app.app_context():
        admin = User(username="admin", role="admin")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def test_client(app):
    """Create a test client."""
    with app.app_context():
        client = Client(name="Test Client", description="A test client")
        db.session.add(client)
        db.session.commit()
        return client.id


@pytest.fixture
def test_project(app, test_client):
    """Create a test project."""
    with app.app_context():
        project = Project(
            name="Test Project",
            client_id=test_client,
            description="A test project",
            billable=True,
            hourly_rate=Decimal("100.00"),
        )
        db.session.add(project)
        db.session.commit()
        return project.id


@pytest.fixture
def test_project_2(app, test_client):
    """Create a second test project."""
    with app.app_context():
        project = Project(
            name="Test Project 2",
            client_id=test_client,
            description="Another test project",
            billable=True,
            hourly_rate=Decimal("150.00"),
        )
        db.session.add(project)
        db.session.commit()
        return project.id


# Model Tests


class TestUserFavoriteProjectModel:
    """Test UserFavoriteProject model creation, validation, and basic operations."""

    def test_create_favorite(self, app, test_user, test_project):
        """Test creating a favorite project entry."""
        with app.app_context():
            favorite = UserFavoriteProject()
            favorite.user_id = test_user
            favorite.project_id = test_project

            db.session.add(favorite)
            db.session.commit()

            assert favorite.id is not None
            assert favorite.user_id == test_user
            assert favorite.project_id == test_project
            assert favorite.created_at is not None
            assert isinstance(favorite.created_at, datetime)

    def test_favorite_unique_constraint(self, app, test_user, test_project):
        """Test that a user cannot favorite the same project twice."""
        with app.app_context():
            # Create first favorite
            favorite1 = UserFavoriteProject()
            favorite1.user_id = test_user
            favorite1.project_id = test_project
            db.session.add(favorite1)
            db.session.commit()

            # Try to create duplicate
            favorite2 = UserFavoriteProject()
            favorite2.user_id = test_user
            favorite2.project_id = test_project
            db.session.add(favorite2)

            # Should raise IntegrityError
            with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
                db.session.commit()

    def test_favorite_to_dict(self, app, test_user, test_project):
        """Test favorite project to_dict method."""
        with app.app_context():
            favorite = UserFavoriteProject()
            favorite.user_id = test_user
            favorite.project_id = test_project
            db.session.add(favorite)
            db.session.commit()

            data = favorite.to_dict()
            assert "id" in data
            assert "user_id" in data
            assert "project_id" in data
            assert "created_at" in data
            assert data["user_id"] == test_user
            assert data["project_id"] == test_project


class TestUserFavoriteProjectMethods:
    """Test User model methods for managing favorite projects."""

    def test_add_favorite_project(self, app, test_user, test_project):
        """Test adding a project to user's favorites."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add to favorites
            user.add_favorite_project(project)

            # Verify it was added
            assert user.is_project_favorite(project)
            assert project in user.favorite_projects.all()

    def test_add_favorite_project_idempotent(self, app, test_user, test_project):
        """Test that adding a favorite twice doesn't cause errors."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add twice
            user.add_favorite_project(project)
            user.add_favorite_project(project)

            # Should still only have one favorite entry
            favorites = UserFavoriteProject.query.filter_by(user_id=test_user, project_id=test_project).all()
            assert len(favorites) == 1

    def test_remove_favorite_project(self, app, test_user, test_project):
        """Test removing a project from user's favorites."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add then remove
            user.add_favorite_project(project)
            assert user.is_project_favorite(project)

            user.remove_favorite_project(project)
            assert not user.is_project_favorite(project)

    def test_is_project_favorite_with_id(self, app, test_user, test_project):
        """Test checking if project is favorite using project ID."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Not a favorite yet
            assert not user.is_project_favorite(test_project)

            # Add to favorites
            user.add_favorite_project(project)

            # Check with ID
            assert user.is_project_favorite(test_project)

    def test_get_favorite_projects(self, app, test_user, test_project, test_project_2):
        """Test getting user's favorite projects."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project1 = db.session.get(Project, test_project)
            project2 = db.session.get(Project, test_project_2)

            # Add both to favorites
            user.add_favorite_project(project1)
            user.add_favorite_project(project2)

            # Get favorites
            favorites = user.get_favorite_projects()
            assert len(favorites) == 2
            assert project1 in favorites
            assert project2 in favorites

    def test_get_favorite_projects_filtered_by_status(self, app, test_user, test_project, test_project_2):
        """Test getting favorite projects filtered by status."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project1 = db.session.get(Project, test_project)
            project2 = db.session.get(Project, test_project_2)

            # Set different statuses
            project1.status = "active"
            project2.status = "archived"
            db.session.commit()

            # Add both to favorites
            user.add_favorite_project(project1)
            user.add_favorite_project(project2)

            # Get only active favorites
            active_favorites = user.get_favorite_projects(status="active")
            assert len(active_favorites) == 1
            assert project1 in active_favorites
            assert project2 not in active_favorites


class TestProjectFavoriteMethods:
    """Test Project model methods for favorite functionality."""

    def test_is_favorited_by_user(self, app, test_user, test_project):
        """Test checking if project is favorited by a specific user."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Not favorited yet
            assert not project.is_favorited_by(user)

            # Add to favorites
            user.add_favorite_project(project)

            # Now should be favorited
            assert project.is_favorited_by(user)

    def test_is_favorited_by_user_id(self, app, test_user, test_project):
        """Test checking if project is favorited using user ID."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add to favorites
            user.add_favorite_project(project)

            # Check with user ID
            assert project.is_favorited_by(test_user)

    def test_project_to_dict_with_favorite_status(self, app, test_user, test_project):
        """Test project to_dict includes favorite status when user provided."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Without user, no is_favorite field
            data = project.to_dict()
            assert "is_favorite" not in data

            # With user, includes is_favorite
            data_with_user = project.to_dict(user=user)
            assert "is_favorite" in data_with_user
            assert data_with_user["is_favorite"] is False

            # Add to favorites
            user.add_favorite_project(project)

            # Now should be True
            data_favorited = project.to_dict(user=user)
            assert data_favorited["is_favorite"] is True


# Route Tests


class TestFavoriteProjectRoutes:
    """Test favorite project routes and endpoints."""

    def test_favorite_project_route(self, app, client_fixture, test_user, test_project):
        """Test favoriting a project via POST route."""
        with app.app_context():
            # Login as test user
            with client_fixture.session_transaction() as sess:
                sess["_user_id"] = str(test_user)

            # Favorite the project
            response = client_fixture.post(
                f"/projects/{test_project}/favorite", headers={"X-Requested-With": "XMLHttpRequest"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify in database
            user = db.session.get(User, test_user)
            assert user.is_project_favorite(test_project)

    def test_unfavorite_project_route(self, app, client_fixture, test_user, test_project):
        """Test unfavoriting a project via POST route."""
        with app.app_context():
            # Setup: Add to favorites first
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)
            user.add_favorite_project(project)

            # Login
            with client_fixture.session_transaction() as sess:
                sess["_user_id"] = str(test_user)

            # Unfavorite the project
            response = client_fixture.post(
                f"/projects/{test_project}/unfavorite", headers={"X-Requested-With": "XMLHttpRequest"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify in database
            user = db.session.get(User, test_user)
            assert not user.is_project_favorite(test_project)

    def test_favorite_nonexistent_project(self, app, client_fixture, test_user):
        """Test favoriting a non-existent project returns 404."""
        with app.app_context():
            with client_fixture.session_transaction() as sess:
                sess["_user_id"] = str(test_user)

            response = client_fixture.post("/projects/99999/favorite")
            assert response.status_code == 404

    def test_favorite_project_requires_login(self, app, client_fixture, test_project):
        """Test that favoriting requires authentication."""
        with app.app_context():
            response = client_fixture.post(f"/projects/{test_project}/favorite")
            # Should redirect to login
            assert response.status_code in [302, 401]


class TestFavoriteProjectFiltering:
    """Test filtering projects by favorites."""

    def test_list_projects_with_favorites_filter(self, app, client_fixture, test_user, test_project, test_project_2):
        """Test listing only favorite projects."""
        with app.app_context():
            # Setup: Favorite only one project
            user = db.session.get(User, test_user)
            project1 = db.session.get(Project, test_project)
            user.add_favorite_project(project1)

            # Login
            with client_fixture.session_transaction() as sess:
                sess["_user_id"] = str(test_user)

            # Request favorites only
            response = client_fixture.get("/projects?favorites=true")

            assert response.status_code == 200
            # Check that the response contains the favorite project
            assert b"Test Project" in response.data

    def test_list_all_projects_without_filter(self, app, client_fixture, test_user, test_project, test_project_2):
        """Test listing all projects without favorites filter."""
        with app.app_context():
            # Setup: Favorite only one project
            user = db.session.get(User, test_user)
            project1 = db.session.get(Project, test_project)
            user.add_favorite_project(project1)

            # Login
            with client_fixture.session_transaction() as sess:
                sess["_user_id"] = str(test_user)

            # Request all projects
            response = client_fixture.get("/projects")

            assert response.status_code == 200
            # Both projects should be in response
            assert b"Test Project" in response.data


# Relationship Tests


class TestFavoriteProjectRelationships:
    """Test database relationships and cascade behavior."""

    def test_delete_user_cascades_favorites(self, app, test_user, test_project):
        """Test that deleting a user removes their favorite entries."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add to favorites
            user.add_favorite_project(project)

            # Verify favorite exists
            favorite_count = UserFavoriteProject.query.filter_by(user_id=test_user).count()
            assert favorite_count == 1

            # Delete user
            db.session.delete(user)
            db.session.commit()

            # Favorite should be deleted
            favorite_count = UserFavoriteProject.query.filter_by(user_id=test_user).count()
            assert favorite_count == 0

    def test_delete_project_cascades_favorites(self, app, test_user, test_project):
        """Test that deleting a project removes related favorite entries."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Add to favorites
            user.add_favorite_project(project)

            # Verify favorite exists
            favorite_count = UserFavoriteProject.query.filter_by(project_id=test_project).count()
            assert favorite_count == 1

            # Delete project
            db.session.delete(project)
            db.session.commit()

            # Favorite should be deleted
            favorite_count = UserFavoriteProject.query.filter_by(project_id=test_project).count()
            assert favorite_count == 0

    def test_multiple_users_favorite_same_project(self, app, test_user, test_admin, test_project):
        """Test that multiple users can favorite the same project."""
        with app.app_context():
            user = db.session.get(User, test_user)
            admin = db.session.get(User, test_admin)
            project = db.session.get(Project, test_project)

            # Both favorite the same project
            user.add_favorite_project(project)
            admin.add_favorite_project(project)

            # Verify both have it as favorite
            assert user.is_project_favorite(project)
            assert admin.is_project_favorite(project)

            # Verify database has 2 entries
            favorite_count = UserFavoriteProject.query.filter_by(project_id=test_project).count()
            assert favorite_count == 2


# Smoke Tests


class TestFavoriteProjectsSmoke:
    """Smoke tests to verify basic favorite projects functionality."""

    def test_complete_favorite_workflow(self, app, test_user, test_project):
        """Test complete workflow: add favorite, check status, remove favorite."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Initially not favorited
            assert not user.is_project_favorite(project)

            # Add to favorites
            user.add_favorite_project(project)
            assert user.is_project_favorite(project)

            # Get favorites list
            favorites = user.get_favorite_projects()
            assert len(favorites) == 1
            assert project in favorites

            # Remove from favorites
            user.remove_favorite_project(project)
            assert not user.is_project_favorite(project)

            # Favorites list should be empty
            favorites = user.get_favorite_projects()
            assert len(favorites) == 0

    def test_favorite_with_archived_projects(self, app, test_user, test_project):
        """Test that favoriting works with archived projects."""
        with app.app_context():
            user = db.session.get(User, test_user)
            project = db.session.get(Project, test_project)

            # Favorite an active project
            user.add_favorite_project(project)

            # Archive the project
            project.status = "archived"
            db.session.commit()

            # Should still be favorited
            assert user.is_project_favorite(project)

            # But won't appear in active favorites
            active_favorites = user.get_favorite_projects(status="active")
            assert len(active_favorites) == 0

            # Will appear in archived favorites
            archived_favorites = user.get_favorite_projects(status="archived")
            assert len(archived_favorites) == 1
