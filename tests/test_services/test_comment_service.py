"""
Tests for CommentService.
"""

import pytest
from app.services import CommentService
from app.repositories import CommentRepository, ProjectRepository
from app.models import Comment, Project


class TestCommentService:
    """Test cases for CommentService"""

    def test_create_comment_success(self, db_session, sample_project, sample_user):
        """Test successful comment creation"""
        service = CommentService()

        result = service.create_comment(
            content="This is a test comment", user_id=sample_user.id, project_id=sample_project.id, is_internal=True
        )

        assert result["success"] is True
        assert result["comment"] is not None
        assert result["comment"].content == "This is a test comment"
        assert result["comment"].project_id == sample_project.id

    def test_create_comment_empty_content(self, db_session, sample_project, sample_user):
        """Test comment creation with empty content"""
        service = CommentService()

        result = service.create_comment(content="", user_id=sample_user.id, project_id=sample_project.id)

        assert result["success"] is False
        assert result["error"] == "empty_content"

    def test_create_comment_no_target(self, db_session, sample_user):
        """Test comment creation without target"""
        service = CommentService()

        result = service.create_comment(content="Test comment", user_id=sample_user.id)

        assert result["success"] is False
        assert result["error"] == "no_target"

    def test_create_comment_invalid_project(self, db_session, sample_user):
        """Test comment creation with invalid project"""
        service = CommentService()

        result = service.create_comment(content="Test comment", user_id=sample_user.id, project_id=99999)

        assert result["success"] is False
        assert result["error"] == "invalid_project"

    def test_get_project_comments(self, db_session, sample_project, sample_user):
        """Test getting comments for a project"""
        service = CommentService()

        # Create comments
        service.create_comment(content="First comment", user_id=sample_user.id, project_id=sample_project.id)

        service.create_comment(content="Second comment", user_id=sample_user.id, project_id=sample_project.id)

        comments = service.get_project_comments(sample_project.id)

        assert len(comments) == 2
        assert comments[0].content in ["First comment", "Second comment"]

    def test_delete_comment_success(self, db_session, sample_project, sample_user):
        """Test successful comment deletion"""
        service = CommentService()

        # Create comment
        result = service.create_comment(
            content="Comment to delete", user_id=sample_user.id, project_id=sample_project.id
        )

        comment_id = result["comment"].id

        # Delete comment
        delete_result = service.delete_comment(comment_id, sample_user.id)

        assert delete_result["success"] is True
