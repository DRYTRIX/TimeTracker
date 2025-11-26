"""
Service for permission and role management.
"""

from typing import List, Dict, Any, Optional
from app import db
from app.models import Permission, Role, User
from app.repositories import UserRepository
from app.utils.db import safe_commit


class PermissionService:
    """Service for permission operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def check_permission(
        self,
        user_id: int,
        permission_name: str
    ) -> bool:
        """
        Check if a user has a specific permission.
        
        Returns:
            True if user has permission, False otherwise
        """
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            return False
        
        # Admins have all permissions
        if user.role == 'admin':
            return True
        
        # Check role permissions
        role = Role.query.filter_by(name=user.role).first()
        if role:
            permission = Permission.query.filter_by(
                name=permission_name,
                role_id=role.id
            ).first()
            if permission and permission.granted:
                return True
        
        return False
    
    def grant_permission(
        self,
        role_name: str,
        permission_name: str
    ) -> Dict[str, Any]:
        """
        Grant a permission to a role.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return {
                'success': False,
                'message': 'Role not found',
                'error': 'invalid_role'
            }
        
        # Check if permission already exists
        permission = Permission.query.filter_by(
            name=permission_name,
            role_id=role.id
        ).first()
        
        if permission:
            permission.granted = True
        else:
            permission = Permission(
                name=permission_name,
                role_id=role.id,
                granted=True
            )
            db.session.add(permission)
        
        if not safe_commit('grant_permission', {'role': role_name, 'permission': permission_name}):
            return {
                'success': False,
                'message': 'Could not grant permission due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Permission granted successfully'
        }
    
    def revoke_permission(
        self,
        role_name: str,
        permission_name: str
    ) -> Dict[str, Any]:
        """
        Revoke a permission from a role.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return {
                'success': False,
                'message': 'Role not found',
                'error': 'invalid_role'
            }
        
        permission = Permission.query.filter_by(
            name=permission_name,
            role_id=role.id
        ).first()
        
        if permission:
            permission.granted = False
            
            if not safe_commit('revoke_permission', {'role': role_name, 'permission': permission_name}):
                return {
                    'success': False,
                    'message': 'Could not revoke permission due to a database error',
                    'error': 'database_error'
                }
        
        return {
            'success': True,
            'message': 'Permission revoked successfully'
        }
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """
        Get all permissions for a user.
        
        Returns:
            List of permission names
        """
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            return []
        
        # Admins have all permissions
        if user.role == 'admin':
            return ['admin:all']
        
        # Get role permissions
        role = Role.query.filter_by(name=user.role).first()
        if not role:
            return []
        
        permissions = Permission.query.filter_by(
            role_id=role.id,
            granted=True
        ).all()
        
        return [p.name for p in permissions]

