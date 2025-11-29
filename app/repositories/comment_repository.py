"""
Repository for comment data access operations.
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload
from app import db
from app.models import Comment
from app.repositories.base_repository import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    """Repository for comment operations"""

    def __init__(self):
        super().__init__(Comment)

    def get_by_project(
        self, project_id: int, include_replies: bool = True, include_relations: bool = False
    ) -> List[Comment]:
        """Get comments for a project"""
        query = self.model.query.filter_by(project_id=project_id)

        if not include_replies:
            query = query.filter_by(parent_id=None)

        if include_relations:
            query = query.options(joinedload(Comment.author), joinedload(Comment.replies) if include_replies else query)

        return query.order_by(Comment.created_at.asc()).all()

    def get_by_task(self, task_id: int, include_replies: bool = True, include_relations: bool = False) -> List[Comment]:
        """Get comments for a task"""
        query = self.model.query.filter_by(task_id=task_id)

        if not include_replies:
            query = query.filter_by(parent_id=None)

        if include_relations:
            query = query.options(joinedload(Comment.author), joinedload(Comment.replies) if include_replies else query)

        return query.order_by(Comment.created_at.asc()).all()

    def get_by_quote(
        self,
        quote_id: int,
        include_replies: bool = True,
        include_internal: bool = True,
        include_relations: bool = False,
    ) -> List[Comment]:
        """Get comments for a quote"""
        query = self.model.query.filter_by(quote_id=quote_id)

        if not include_internal:
            query = query.filter_by(is_internal=False)

        if not include_replies:
            query = query.filter_by(parent_id=None)

        if include_relations:
            query = query.options(joinedload(Comment.author), joinedload(Comment.replies) if include_replies else query)

        return query.order_by(Comment.created_at.asc()).all()

    def get_replies(self, parent_id: int, include_relations: bool = False) -> List[Comment]:
        """Get replies to a comment"""
        query = self.model.query.filter_by(parent_id=parent_id)

        if include_relations:
            query = query.options(joinedload(Comment.author))

        return query.order_by(Comment.created_at.asc()).all()
