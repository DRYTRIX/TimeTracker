"""Utility for migrating users from legacy role field to new role system"""

from app import db
from app.models import User, Role
from typing import Dict, Optional


def migrate_user_roles(dry_run: bool = False) -> Dict[str, any]:
    """
    Migrate users from legacy role field to new role system.
    
    Args:
        dry_run: If True, don't make changes, just report what would be done
        
    Returns:
        Dictionary with migration statistics
    """
    stats = {
        "total_users": 0,
        "users_with_roles": 0,
        "users_needing_migration": 0,
        "migrated": 0,
        "failed": 0,
        "errors": []
    }
    
    # Get all users
    users = User.query.all()
    stats["total_users"] = len(users)
    
    # Map of legacy role names to new role names
    role_mapping = {
        "admin": "admin",
        "user": "user",
        "manager": "manager",
        "viewer": "viewer",
    }
    
    for user in users:
        # Skip if user already has roles assigned
        if user.roles:
            stats["users_with_roles"] += 1
            continue
        
        # Skip if user has no legacy role or role is not in mapping
        if not user.role or user.role not in role_mapping:
            continue
        
        stats["users_needing_migration"] += 1
        
        # Get the target role
        target_role_name = role_mapping[user.role]
        target_role = Role.query.filter_by(name=target_role_name).first()
        
        if not target_role:
            error_msg = f"User {user.username}: Role '{target_role_name}' not found in database"
            stats["errors"].append(error_msg)
            stats["failed"] += 1
            continue
        
        if not dry_run:
            try:
                # Assign the role
                user.roles.append(target_role)
                db.session.commit()
                stats["migrated"] += 1
            except Exception as e:
                db.session.rollback()
                error_msg = f"User {user.username}: Failed to assign role - {str(e)}"
                stats["errors"].append(error_msg)
                stats["failed"] += 1
        else:
            # Dry run - just count what would be migrated
            stats["migrated"] += 1
    
    return stats


def migrate_single_user(user_id: int, role_name: Optional[str] = None) -> bool:
    """
    Migrate a single user to the new role system.
    
    Args:
        user_id: ID of the user to migrate
        role_name: Optional role name to assign. If None, uses legacy role field.
        
    Returns:
        True if successful, False otherwise
    """
    user = User.query.get(user_id)
    if not user:
        return False
    
    # If user already has roles, skip
    if user.roles:
        return True
    
    # Determine target role
    if role_name:
        target_role_name = role_name
    elif user.role:
        role_mapping = {
            "admin": "admin",
            "user": "user",
            "manager": "manager",
            "viewer": "viewer",
        }
        target_role_name = role_mapping.get(user.role)
    else:
        # Default to "user" role
        target_role_name = "user"
    
    if not target_role_name:
        return False
    
    # Get the role
    target_role = Role.query.filter_by(name=target_role_name).first()
    if not target_role:
        return False
    
    try:
        user.roles.append(target_role)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
