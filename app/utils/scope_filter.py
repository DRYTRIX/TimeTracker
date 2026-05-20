"""Scope filtering: restrict data to assigned clients/projects (subcontractors, client portal users)."""

from typing import Set, Tuple

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


def apply_project_scope(Project, query, user=None):
    """Apply project scope to a Project query. Returns query with scope filter applied if restricted."""
    scope = apply_project_scope_to_model(Project, user)
    if scope is None:
        return query
    return query.filter(scope)


def apply_client_scope_to_model(Client, user=None):
    """Return filter expression for Client query (Client.id.in_(...) or None for no filter)."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u or u.is_admin:
        return None
    allowed = u.get_allowed_client_ids()
    if allowed is None:
        return None
    if not allowed:
        return Client.id.in_([])  # never match
    return Client.id.in_(allowed)


def apply_project_scope_to_model(Project, user=None):
    """Return filter expression for Project query (Project.id.in_(...) or None for no filter)."""
    u = user or (current_user if current_user.is_authenticated else None)
    if not u or u.is_admin:
        return None
    allowed_projects = u.get_allowed_project_ids()
    if allowed_projects is None:
        return None
    if not allowed_projects:
        return Project.id.in_([])  # never match
    return Project.id.in_(allowed_projects)


def user_can_access_client(user, client_id):
    """Return True if user may access this client (for direct ID checks / 403)."""
    if not user:
        return False
    if user.is_admin:
        return True
    allowed = user.get_allowed_client_ids()
    if allowed is None:
        return True
    return client_id in allowed


def user_can_access_project(user, project_id):
    """Return True if user may access this project (for direct ID checks / 403)."""
    if not user:
        return False
    if user.is_admin:
        return True
    allowed = user.get_allowed_project_ids()
    if allowed is None:
        return True
    return project_id in allowed


def get_active_clients_for_user(user, *, status="active"):
    """Return clients visible to user (respects scope)."""
    from app.models import Client

    query = Client.query.filter_by(status=status).order_by(Client.name)
    scope = apply_client_scope_to_model(Client, user)
    if scope is not None:
        query = query.filter(scope)
    return query.all()


def get_active_projects_for_user(user, *, status="active"):
    """Return projects visible to user (respects scope)."""
    from app.models import Project

    query = Project.query.filter_by(status=status).order_by(Project.name)
    scope = apply_project_scope_to_model(Project, user)
    if scope is not None:
        query = query.filter(scope)
    return query.all()


def get_accessible_project_and_client_ids_for_user(user_id: int) -> Tuple[Set[int], Set[int]]:
    """
    Return (accessible_project_ids, accessible_client_ids) for issue-style access:
    projects the user has time entries for or is assigned to tasks on, and clients of those projects.
    Used to filter issues for non-admin users without view_all_issues permission.
    """
    from app.models import Project, Task
    from app.repositories import TimeEntryRepository

    time_entry_repo = TimeEntryRepository()
    user_project_ids = set(time_entry_repo.get_distinct_project_ids_for_user(user_id))
    task_project_rows = (
        Task.query.with_entities(Task.project_id)
        .filter_by(assigned_to=user_id)
        .filter(Task.project_id.isnot(None))
        .distinct()
        .all()
    )
    task_project_ids = {r[0] for r in task_project_rows}
    all_accessible_project_ids = user_project_ids | task_project_ids
    if not all_accessible_project_ids:
        return set(), set()
    client_rows = (
        Project.query.with_entities(Project.client_id)
        .filter(Project.id.in_(all_accessible_project_ids), Project.client_id.isnot(None))
        .distinct()
        .all()
    )
    accessible_client_ids = {r[0] for r in client_rows}
    return all_accessible_project_ids, accessible_client_ids
