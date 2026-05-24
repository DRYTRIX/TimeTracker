"""Shared global search for session /api/search and token /api/v1/search."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Client, Project, Task, TimeEntry, User
from app.utils.scope_filter import apply_client_scope, apply_project_scope


def _parse_search_types(types_filter: str) -> Set[str]:
    allowed = {"project", "task", "client", "entry"}
    raw = (types_filter or "").strip().lower()
    if raw:
        requested = {t.strip() for t in raw.split(",") if t.strip()}
        return requested.intersection(allowed)
    return allowed


def run_global_search(
    user: User,
    query: str,
    *,
    limit: int,
    types_filter: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Run global search for projects, tasks, clients, and finished time entries.

    Returns (results, errors) where errors maps domain key to message if that domain failed.
    Caller handles short-query policy (legacy 200 empty vs v1 400).
    """
    limit = min(max(limit, 1), 50)
    search_types = _parse_search_types(types_filter)
    results: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}
    search_pattern = f"%{query}%"

    if "project" in search_types:
        try:
            projects_query = Project.query.filter(
                Project.status == "active",
                or_(Project.name.ilike(search_pattern), Project.description.ilike(search_pattern)),
            )
            projects_query = apply_project_scope(Project, projects_query, user)
            projects = projects_query.limit(limit).all()

            for project in projects:
                results.append(
                    {
                        "type": "project",
                        "category": "project",
                        "id": project.id,
                        "title": project.name,
                        "description": project.description or "",
                        "url": f"/projects/{project.id}",
                        "badge": "Project",
                    }
                )
        except SQLAlchemyError as e:
            current_app.logger.exception(
                "Error searching projects",
                extra={"event": "api_search_domain_failed", "domain": "projects"},
            )
            errors["projects"] = str(e)

    if "task" in search_types:
        try:
            tasks_query = Task.query.join(Project).filter(
                Project.status == "active",
                or_(Task.name.ilike(search_pattern), Task.description.ilike(search_pattern)),
            )
            tasks_query = apply_project_scope(Project, tasks_query, user)
            if (
                not user.is_admin
                and not user.has_permission("view_all_tasks")
                and not getattr(user, "is_scope_restricted", False)
                and not getattr(user, "is_client_portal_user", False)
            ):
                tasks_query = tasks_query.filter(db.or_(Task.assigned_to == user.id, Task.created_by == user.id))
            tasks = tasks_query.limit(limit).all()

            for task in tasks:
                results.append(
                    {
                        "type": "task",
                        "category": "task",
                        "id": task.id,
                        "title": task.name,
                        "description": f"{task.project.name if task.project else 'No Project'}",
                        "url": f"/tasks/{task.id}",
                        "badge": task.status.replace("_", " ").title() if task.status else "Task",
                    }
                )
        except SQLAlchemyError as e:
            current_app.logger.exception(
                "Error searching tasks",
                extra={"event": "api_search_domain_failed", "domain": "tasks"},
            )
            errors["tasks"] = str(e)

    if "client" in search_types:
        try:
            clients_query = Client.query.filter(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.email.ilike(search_pattern),
                    Client.description.ilike(search_pattern),
                    Client.contact_person.ilike(search_pattern),
                )
            )
            clients_query = apply_client_scope(Client, clients_query, user)
            clients = clients_query.limit(limit).all()

            for client in clients:
                results.append(
                    {
                        "type": "client",
                        "category": "client",
                        "id": client.id,
                        "title": client.name,
                        "description": (client.description or client.contact_person or client.email or ""),
                        "url": f"/clients/{client.id}",
                        "badge": "Client",
                    }
                )
        except SQLAlchemyError as e:
            current_app.logger.exception(
                "Error searching clients",
                extra={"event": "api_search_domain_failed", "domain": "clients"},
            )
            errors["clients"] = str(e)

    if "entry" in search_types:
        try:
            entries_query = TimeEntry.query.filter(
                TimeEntry.end_time.isnot(None),
                or_(TimeEntry.notes.ilike(search_pattern), TimeEntry.tags.ilike(search_pattern)),
            )
            if not user.is_admin:
                entries_query = entries_query.filter(TimeEntry.user_id == user.id)

            entries = entries_query.order_by(TimeEntry.start_time.desc()).limit(limit).all()

            for entry in entries:
                title_parts = []
                if entry.project:
                    title_parts.append(entry.project.name)
                if entry.task:
                    title_parts.append(f"• {entry.task.name}")
                title = " ".join(title_parts) if title_parts else "Time Entry"

                description = entry.notes[:100] if entry.notes else ""
                if entry.tags:
                    description += f" [{entry.tags}]"

                results.append(
                    {
                        "type": "entry",
                        "category": "entry",
                        "id": entry.id,
                        "title": title,
                        "description": description,
                        "url": f"/timer/edit/{entry.id}",
                        "badge": entry.duration_formatted,
                    }
                )
        except SQLAlchemyError as e:
            current_app.logger.exception(
                "Error searching time entries",
                extra={"event": "api_search_domain_failed", "domain": "entries"},
            )
            errors["entries"] = str(e)

    return results, errors
