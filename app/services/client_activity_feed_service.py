"""
Client Activity Feed Service

Builds a unified, client-visible activity feed from Activity and Comment models.
Only includes events for the client's projects and excludes internal-only comments.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import Activity, Comment, Project, TimeEntry


def get_client_activity_feed(
    client_id: int,
    limit: int = 50,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Return a unified feed of client-visible events for the given client.
    Includes: Activity (project and time_entry for client's projects), Comment (non-internal).
    Each feed item is a dict: feed_type, created_at, description, action, project_name,
    project_id, link_url, user_display_name, entity_type, entity_id, extra.
    """
    project_ids = [
        p.id for p in Project.query.filter_by(client_id=client_id).with_entities(Project.id).all()
    ]
    if not project_ids:
        return []

    feed_items: List[Dict[str, Any]] = []

    # Activity: project-scoped
    project_activities = (
        Activity.query.filter(
            Activity.entity_type == "project",
            Activity.entity_id.in_(project_ids),
        )
        .order_by(Activity.created_at.desc())
        .limit(limit * 2)
        .all()
    )

    # Activity: time_entry for client's projects
    time_entry_ids = [
        row[0]
        for row in TimeEntry.query.filter(
            TimeEntry.project_id.in_(project_ids),
        ).with_entities(TimeEntry.id).all()
    ]
    time_entry_activities = []
    if time_entry_ids:
        time_entry_activities = (
            Activity.query.filter(
                Activity.entity_type == "time_entry",
                Activity.entity_id.in_(time_entry_ids),
            )
            .order_by(Activity.created_at.desc())
            .limit(limit * 2)
            .all()
        )

    # Map project_id -> name for display
    projects = {p.id: p.name for p in Project.query.filter(Project.id.in_(project_ids)).all()}

    for act in project_activities:
        feed_items.append(_activity_to_feed_item(act, projects.get(act.entity_id), "/client-portal/projects"))

    for act in time_entry_activities:
        te = TimeEntry.query.get(act.entity_id)
        project_name = None
        if te and te.project_id:
            project_name = projects.get(te.project_id) or (te.project.name if te.project else None)
        feed_items.append(
            _activity_to_feed_item(act, project_name, "/client-portal/time-entries")
        )

    # Comments: client-visible only (is_internal == False)
    comments = (
        Comment.query.filter(
            Comment.project_id.in_(project_ids),
            Comment.is_internal == False,
        )
        .order_by(Comment.created_at.desc())
        .limit(limit * 2)
        .all()
    )

    for c in comments:
        author_name = None
        if c.author:
            author_name = getattr(c.author, "display_name", None) or getattr(c.author, "username", None)
        elif c.client_contact:
            author_name = f"{c.client_contact.first_name or ''} {c.client_contact.last_name or ''}".strip() or c.client_contact.email
        feed_items.append({
            "feed_type": "comment",
            "created_at": c.created_at,
            "description": (c.content[:200] + "…") if c.content and len(c.content) > 200 else (c.content or ""),
            "action": "commented",
            "project_name": projects.get(c.project_id) if c.project_id else None,
            "project_id": c.project_id,
            "link_url": f"/client-portal/projects/{c.project_id}/comments" if c.project_id else "/client-portal/projects",
            "user_display_name": author_name,
            "entity_type": "comment",
            "entity_id": c.id,
        })

    if since:
        feed_items = [i for i in feed_items if i["created_at"] and i["created_at"] >= since]

    feed_items.sort(key=lambda x: x["created_at"] or datetime.min, reverse=True)
    return feed_items[:limit]


def _activity_to_feed_item(
    act: Activity,
    project_name: Optional[str],
    default_link: str,
) -> Dict[str, Any]:
    user_display = None
    if act.user:
        user_display = getattr(act.user, "display_name", None) or getattr(act.user, "username", None)
    link = default_link
    if act.entity_type == "project" and act.entity_id:
        link = f"/client-portal/projects"
    return {
        "feed_type": "activity",
        "created_at": act.created_at,
        "description": act.description or f"{act.action} {act.entity_type}",
        "action": act.action,
        "project_name": project_name,
        "project_id": act.entity_id if act.entity_type == "project" else None,
        "link_url": link,
        "user_display_name": user_display,
        "entity_type": act.entity_type,
        "entity_id": act.entity_id,
    }
