"""
Search utilities for full-text search across the application.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_
from app.models import Project, TimeEntry, Task, Invoice, Client, Comment


def search_projects(query: str, user_id: Optional[int] = None, status: Optional[str] = None) -> List[Project]:
    """
    Search projects by name and description.

    Args:
        query: Search query
        user_id: Optional user ID filter
        status: Optional status filter

    Returns:
        List of matching projects
    """
    search_term = f"%{query}%"

    search_query = Project.query.filter(or_(Project.name.ilike(search_term), Project.description.ilike(search_term)))

    if status:
        search_query = search_query.filter_by(status=status)

    return search_query.order_by(Project.name).all()


def search_time_entries(query: str, user_id: Optional[int] = None, project_id: Optional[int] = None) -> List[TimeEntry]:
    """
    Search time entries by notes and tags.

    Args:
        query: Search query
        user_id: Optional user ID filter
        project_id: Optional project ID filter

    Returns:
        List of matching time entries
    """
    search_term = f"%{query}%"

    search_query = TimeEntry.query.filter(or_(TimeEntry.notes.ilike(search_term), TimeEntry.tags.ilike(search_term)))

    if user_id:
        search_query = search_query.filter_by(user_id=user_id)

    if project_id:
        search_query = search_query.filter_by(project_id=project_id)

    return search_query.order_by(TimeEntry.start_time.desc()).all()


def search_tasks(query: str, project_id: Optional[int] = None, status: Optional[str] = None) -> List[Task]:
    """
    Search tasks by name and description.

    Args:
        query: Search query
        project_id: Optional project ID filter
        status: Optional status filter

    Returns:
        List of matching tasks
    """
    search_term = f"%{query}%"

    search_query = Task.query.filter(or_(Task.name.ilike(search_term), Task.description.ilike(search_term)))

    if project_id:
        search_query = search_query.filter_by(project_id=project_id)

    if status:
        search_query = search_query.filter_by(status=status)

    return search_query.order_by(Task.priority.desc(), Task.created_at.desc()).all()


def search_invoices(query: str, status: Optional[str] = None) -> List[Invoice]:
    """
    Search invoices by number and client name.

    Args:
        query: Search query
        status: Optional status filter

    Returns:
        List of matching invoices
    """
    search_term = f"%{query}%"

    search_query = Invoice.query.filter(
        or_(Invoice.invoice_number.ilike(search_term), Invoice.client_name.ilike(search_term))
    )

    if status:
        search_query = search_query.filter_by(status=status)

    return search_query.order_by(Invoice.created_at.desc()).all()


def search_clients(query: str) -> List[Client]:
    """
    Search clients by name, email, and company.

    Args:
        query: Search query

    Returns:
        List of matching clients
    """
    search_term = f"%{query}%"

    return (
        Client.query.filter(
            or_(Client.name.ilike(search_term), Client.email.ilike(search_term), Client.company.ilike(search_term))
        )
        .order_by(Client.name)
        .all()
    )


def global_search(query: str, user_id: Optional[int] = None, limit_per_type: int = 10) -> Dict[str, List[Any]]:
    """
    Perform a global search across all entities.

    Args:
        query: Search query
        user_id: Optional user ID filter
        limit_per_type: Maximum results per entity type

    Returns:
        dict with search results by entity type
    """
    results = {
        "projects": search_projects(query, user_id=user_id)[:limit_per_type],
        "time_entries": search_time_entries(query, user_id=user_id)[:limit_per_type],
        "tasks": search_tasks(query)[:limit_per_type],
        "invoices": search_invoices(query)[:limit_per_type],
        "clients": search_clients(query)[:limit_per_type],
    }

    return results
