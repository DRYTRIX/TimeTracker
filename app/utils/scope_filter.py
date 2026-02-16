"""Scope filtering for subcontractor role: restrict data to assigned clients/projects."""

from flask_login import current_user


def get_allowed_client_ids(user=None):
    """Return allowed client IDs for user, or None for full access. Uses current_user if user is None."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u:
        return []
    return u.get_allowed_client_ids()


def get_allowed_project_ids(user=None):
    """Return allowed project IDs for user, or None for full access. Uses current_user if user is None."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u:
        return []
    return u.get_allowed_project_ids()


def apply_client_scope(Client, query, user=None):
    """Apply client scope to a Client query. Returns query with scope filter applied if restricted."""
    scope = apply_client_scope_to_model(Client, user)
    if scope is None:
        return query
    return query.filter(scope)


def apply_client_scope_to_model(Client, user=None):
    """Return filter expression for Client query (Client.id.in_(...) or None for no filter)."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u or not u.is_scope_restricted:
        return None
    allowed = u.get_allowed_client_ids()
    if allowed is None:
        return None
    if not allowed:
        return Client.id.in_([])  # never match
    return Client.id.in_(allowed)


def apply_project_scope_to_model(Project, user=None):
    """Return filter expression for Project query (Project.client_id.in_(...) or Project.id.in_(...))."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u or not u.is_scope_restricted:
        return None
    allowed_clients = u.get_allowed_client_ids()
    if allowed_clients is None:
        return None
    if not allowed_clients:
        return Project.id.in_([])  # never match
    return Project.client_id.in_(allowed_clients)


def user_can_access_client(user, client_id):
    """Return True if user may access this client (for direct ID checks / 403)."""
    if not user:
        return False
    if user.is_admin or not user.is_scope_restricted:
        return True
    allowed = user.get_allowed_client_ids()
    return allowed is not None and client_id in allowed


def user_can_access_project(user, project_id):
    """Return True if user may access this project (for direct ID checks / 403)."""
    if not user:
        return False
    if user.is_admin or not user.is_scope_restricted:
        return True
    allowed = user.get_allowed_project_ids()
    return allowed is not None and project_id in allowed
