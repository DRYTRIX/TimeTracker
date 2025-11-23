"""
Service for user business logic.
"""

from typing import Optional, Dict, Any, List
from app import db
from app.repositories import UserRepository
from app.models import User
from app.constants import UserRole
from app.utils.db import safe_commit


class UserService:
    """Service for user operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def create_user(
        self,
        username: str,
        role: str = UserRole.USER.value,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: bool = True,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Returns:
            dict with 'success', 'message', and 'user' keys
        """
        # Check for duplicate username
        existing = self.user_repo.get_by_username(username)
        if existing:
            return {
                'success': False,
                'message': 'Username already exists',
                'error': 'duplicate_username'
            }
        
        # Validate role
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            return {
                'success': False,
                'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}',
                'error': 'invalid_role'
            }
        
        # Create user
        user = self.user_repo.create(
            username=username,
            role=role,
            email=email,
            full_name=full_name,
            is_active=is_active
        )
        
        if not safe_commit('create_user', {'username': username, 'created_by': created_by}):
            return {
                'success': False,
                'message': 'Could not create user due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'User created successfully',
            'user': user
        }
    
    def update_user(
        self,
        user_id: int,
        updated_by: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a user.
        
        Returns:
            dict with 'success', 'message', and 'user' keys
        """
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'message': 'User not found',
                'error': 'not_found'
            }
        
        # Validate role if being updated
        if 'role' in kwargs:
            valid_roles = [r.value for r in UserRole]
            if kwargs['role'] not in valid_roles:
                return {
                    'success': False,
                    'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}',
                    'error': 'invalid_role'
                }
        
        # Update fields
        self.user_repo.update(user, **kwargs)
        
        if not safe_commit('update_user', {'user_id': user_id, 'updated_by': updated_by}):
            return {
                'success': False,
                'message': 'Could not update user due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'User updated successfully',
            'user': user
        }
    
    def deactivate_user(
        self,
        user_id: int,
        deactivated_by: int
    ) -> Dict[str, Any]:
        """
        Deactivate a user.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'message': 'User not found',
                'error': 'not_found'
            }
        
        user.is_active = False
        
        if not safe_commit('deactivate_user', {'user_id': user_id, 'deactivated_by': deactivated_by}):
            return {
                'success': False,
                'message': 'Could not deactivate user due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'User deactivated successfully'
        }
    
    def get_active_users(self) -> List[User]:
        """Get all active users"""
        return self.user_repo.get_active_users()
    
    def get_by_role(self, role: str) -> List[User]:
        """Get users by role"""
        return self.user_repo.get_by_role(role)

