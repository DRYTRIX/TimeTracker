"""
Repository for user data access operations.
"""

from typing import List, Optional
from app import db
from app.models import User
from app.repositories.base_repository import BaseRepository
from app.constants import UserRole


class UserRepository(BaseRepository[User]):
    """Repository for user operations"""

    def __init__(self):
        super().__init__(User)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.model.query.filter_by(username=username).first()

    def get_by_role(self, role: str) -> List[User]:
        """Get users by role"""
        return self.model.query.filter_by(role=role).all()

    def get_active_users(self) -> List[User]:
        """Get all active users"""
        return self.model.query.filter_by(is_active=True).all()

    def get_admins(self) -> List[User]:
        """Get all admin users"""
        return self.model.query.filter_by(role=UserRole.ADMIN.value, is_active=True).all()
