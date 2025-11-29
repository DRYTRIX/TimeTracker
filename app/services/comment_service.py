"""
Service for comment business logic.
"""

from typing import Optional, Dict, Any, List
from app import db
from app.repositories import CommentRepository, ProjectRepository, TaskRepository
from app.models import Comment, Project, Task
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event


class CommentService:
    """Service for comment operations"""

    def __init__(self):
        self.comment_repo = CommentRepository()
        self.project_repo = ProjectRepository()
        self.task_repo = TaskRepository()

    def create_comment(
        self,
        content: str,
        user_id: int,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        quote_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        is_internal: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new comment.

        Returns:
            dict with 'success', 'message', and 'comment' keys
        """
        # Validate content
        if not content or not content.strip():
            return {"success": False, "message": "Comment content cannot be empty", "error": "empty_content"}

        # Validate target
        targets = [x for x in [project_id, task_id, quote_id] if x is not None]
        if len(targets) == 0:
            return {
                "success": False,
                "message": "Comment must be associated with a project, task, or quote",
                "error": "no_target",
            }

        if len(targets) > 1:
            return {
                "success": False,
                "message": "Comment cannot be associated with multiple targets",
                "error": "multiple_targets",
            }

        # Validate target exists
        if project_id:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return {"success": False, "message": "Project not found", "error": "invalid_project"}
        elif task_id:
            task = self.task_repo.get_by_id(task_id)
            if not task:
                return {"success": False, "message": "Task not found", "error": "invalid_task"}

        # Validate parent comment if reply
        if parent_id:
            parent = self.comment_repo.get_by_id(parent_id)
            if not parent:
                return {"success": False, "message": "Parent comment not found", "error": "invalid_parent"}
            # Verify parent is for same target
            if (
                (project_id and parent.project_id != project_id)
                or (task_id and parent.task_id != task_id)
                or (quote_id and parent.quote_id != quote_id)
            ):
                return {"success": False, "message": "Invalid parent comment", "error": "invalid_parent_target"}

        # Create comment
        comment = self.comment_repo.create(
            content=content.strip(),
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            quote_id=quote_id,
            parent_id=parent_id,
            is_internal=is_internal,
        )

        if not safe_commit("create_comment", {"user_id": user_id}):
            return {
                "success": False,
                "message": "Could not create comment due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(
            "comment.created",
            {
                "comment_id": comment.id,
                "user_id": user_id,
                "project_id": project_id,
                "task_id": task_id,
                "quote_id": quote_id,
            },
        )

        return {"success": True, "message": "Comment created successfully", "comment": comment}

    def get_project_comments(self, project_id: int, include_replies: bool = True) -> List[Comment]:
        """Get comments for a project"""
        return self.comment_repo.get_by_project(
            project_id=project_id, include_replies=include_replies, include_relations=True
        )

    def get_task_comments(self, task_id: int, include_replies: bool = True) -> List[Comment]:
        """Get comments for a task"""
        return self.comment_repo.get_by_task(task_id=task_id, include_replies=include_replies, include_relations=True)

    def delete_comment(self, comment_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete a comment.

        Returns:
            dict with 'success' and 'message' keys
        """
        comment = self.comment_repo.get_by_id(comment_id)

        if not comment:
            return {"success": False, "message": "Comment not found", "error": "not_found"}

        # Check permissions (user can only delete their own comments unless admin)
        from flask_login import current_user

        if comment.user_id != user_id and not (hasattr(current_user, "is_admin") and current_user.is_admin):
            return {
                "success": False,
                "message": "You do not have permission to delete this comment",
                "error": "unauthorized",
            }

        if self.comment_repo.delete(comment):
            if safe_commit("delete_comment", {"comment_id": comment_id, "user_id": user_id}):
                return {"success": True, "message": "Comment deleted successfully"}

        return {"success": False, "message": "Could not delete comment", "error": "database_error"}
