"""Utilities for permission checking and decorators"""

from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import current_user


def permission_required(*permissions, require_all=False):
    """
    Decorator to require one or more permissions.

    Args:
        *permissions: Permission name(s) required
        require_all: If True, user must have ALL permissions. If False, user needs ANY permission.

    Example:
        @permission_required('edit_projects')
        def edit_project():
            ...

        @permission_required('view_reports', 'export_reports', require_all=True)
        def export_report():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash(_("Please log in to access this page"), "error")
                return redirect(url_for("auth.login"))

            # Check if user has required permissions
            if require_all:
                has_access = current_user.has_all_permissions(*permissions)
            else:
                has_access = current_user.has_any_permission(*permissions)

            if not has_access:
                flash(_("You do not have permission to access this page"), "error")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_or_permission_required(*permissions):
    """
    Decorator that allows access if user is an admin OR has any of the specified permissions.
    This is useful for gradual migration from admin-only to permission-based access.

    Example:
        @admin_or_permission_required('delete_projects')
        def delete_project():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash(_("Please log in to access this page"), "error")
                return redirect(url_for("auth.login"))

            # Allow access if user is admin or has any of the required permissions
            if current_user.is_admin or current_user.has_any_permission(*permissions):
                return f(*args, **kwargs)

            flash(_("You do not have permission to access this page"), "error")
            abort(403)

        return decorated_function

    return decorator


def user_has_view_all_projects(user):
    """True if user may view all projects (including legacy NULL owners)."""
    if not user or not getattr(user, "is_authenticated", True):
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("view_all_projects", "view_projects")


def user_has_view_all_clients(user):
    """True if user may view all clients (including legacy NULL owners)."""
    if not user or not getattr(user, "is_authenticated", True):
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("view_all_clients", "view_clients")


def user_has_view_own_projects_only(user):
    if not user or user.is_admin:
        return False
    return user.has_permission("view_own_projects") and not user_has_view_all_projects(user)


def user_has_view_own_clients_only(user):
    if not user or user.is_admin:
        return False
    return user.has_permission("view_own_clients") and not user_has_view_all_clients(user)


def user_can_edit_project(user, project):
    if not user or not project:
        return False
    if user.is_admin:
        return True
    if user.has_any_permission("edit_all_projects", "edit_projects"):
        return True
    if user.has_permission("edit_own_projects") and project.created_by == user.id:
        return True
    return False


def user_can_delete_project(user, project):
    if not user or not project:
        return False
    if user.is_admin:
        return True
    if user.has_any_permission("delete_all_projects", "delete_projects"):
        return True
    if user.has_permission("delete_own_projects") and project.created_by == user.id:
        return True
    return False


def user_can_edit_client(user, client):
    if not user or not client:
        return False
    if user.is_admin:
        return True
    if user.has_any_permission("edit_all_clients", "edit_clients"):
        return True
    if user.has_permission("edit_own_clients") and client.created_by == user.id:
        return True
    return False


def user_can_delete_client(user, client):
    if not user or not client:
        return False
    if user.is_admin:
        return True
    if user.has_any_permission("delete_all_clients", "delete_clients"):
        return True
    if user.has_permission("delete_own_clients") and client.created_by == user.id:
        return True
    return False


def user_has_any_project_edit_permission(user):
    if not user:
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("edit_projects", "edit_all_projects", "edit_own_projects")


def user_has_any_project_delete_permission(user):
    if not user:
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("delete_projects", "delete_all_projects", "delete_own_projects")


def user_has_any_client_edit_permission(user):
    if not user:
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("edit_clients", "edit_all_clients", "edit_own_clients")


def user_has_any_client_delete_permission(user):
    if not user:
        return False
    if user.is_admin:
        return True
    return user.has_any_permission("delete_clients", "delete_all_clients", "delete_own_clients")


def check_permission(user, permission_name):
    """
    Check if a user has a specific permission.

    Args:
        user: User object
        permission_name: Name of the permission to check

    Returns:
        bool: True if user has the permission, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    return user.has_permission(permission_name)


def check_any_permission(user, *permission_names):
    """
    Check if a user has any of the specified permissions.

    Args:
        user: User object
        *permission_names: Names of permissions to check

    Returns:
        bool: True if user has any of the permissions, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    return user.has_any_permission(*permission_names)


def check_all_permissions(user, *permission_names):
    """
    Check if a user has all of the specified permissions.

    Args:
        user: User object
        *permission_names: Names of permissions to check

    Returns:
        bool: True if user has all of the permissions, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    return user.has_all_permissions(*permission_names)


def get_user_permissions(user):
    """
    Get all permissions for a user.

    Args:
        user: User object

    Returns:
        list: List of Permission objects
    """
    if not user:
        return []

    return user.get_all_permissions()


def get_user_permission_names(user):
    """
    Get all permission names for a user.

    Args:
        user: User object

    Returns:
        list: List of permission name strings
    """
    if not user:
        return []

    permissions = user.get_all_permissions()
    return [p.name for p in permissions]


# Template helper functions (register these in app context)
def init_permission_helpers(app):
    """
    Initialize permission helper functions for use in templates.

    Usage in templates:
        {% if has_permission('edit_projects') %}
            <button>Edit Project</button>
        {% endif %}
    """

    @app.context_processor
    def inject_permission_helpers():
        return {
            "has_permission": lambda perm: check_permission(current_user, perm),
            "has_any_permission": lambda *perms: check_any_permission(current_user, *perms),
            "has_all_permissions": lambda *perms: check_all_permissions(current_user, *perms),
            "get_user_permissions": lambda: (
                get_user_permission_names(current_user) if current_user.is_authenticated else []
            ),
        }
