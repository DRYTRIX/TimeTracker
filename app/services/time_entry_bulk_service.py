"""Bulk time entry actions shared by legacy session API and API v1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app import db
from app.models import TimeEntry
from app.models.time_entry import local_now
from app.utils.db import safe_commit


def apply_bulk_time_entry_actions(
    entry_ids: List[int],
    action: str,
    value: Any,
    *,
    user_id: int,
    is_admin: bool,
) -> Dict[str, Any]:
    """
    Apply bulk action to time entries. Same rules as legacy /api/entries/bulk.

    Returns dict with keys: success (bool), affected (int), error (optional str),
    http_status (int).
    """
    if not entry_ids:
        return {"success": False, "error": "entry_ids must be a non-empty list", "http_status": 400}
    if action not in {"delete", "set_billable", "set_paid", "add_tag", "remove_tag"}:
        return {"success": False, "error": "Unsupported action", "http_status": 400}

    q = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids))
    entries = q.all()
    if not entries:
        return {"success": False, "error": "No entries found", "http_status": 404}

    if not is_admin:
        for e in entries:
            if e.user_id != user_id:
                return {"success": False, "error": "Access denied for one or more entries", "http_status": 403}

    affected = 0
    if action == "delete":
        for e in entries:
            if e.is_active:
                continue
            db.session.delete(e)
            affected += 1
    elif action == "set_billable":
        flag = bool(value)
        for e in entries:
            if e.is_active:
                continue
            e.billable = flag
            e.updated_at = local_now()
            affected += 1
    elif action == "set_paid":
        flag = bool(value)
        for e in entries:
            if e.is_active:
                continue
            e.set_paid(flag, commit=False)
            affected += 1
    elif action in {"add_tag", "remove_tag"}:
        tag = (value or "").strip() if value is not None else ""
        if not tag:
            return {"success": False, "error": "Tag value is required", "http_status": 400}
        for e in entries:
            if e.is_active:
                continue
            tags = set(e.tag_list)
            if action == "add_tag":
                tags.add(tag)
            else:
                tags.discard(tag)
            e.tags = ", ".join(sorted(tags)) if tags else None
            e.updated_at = local_now()
            affected += 1

    if affected > 0:
        if not safe_commit("bulk_time_entries", {"action": action, "count": affected}):
            return {"success": False, "error": "Database error during bulk operation", "http_status": 500}
    else:
        db.session.rollback()
        if entries:
            return {
                "success": False,
                "error": "No entries were updated; active (running) time entries cannot be changed with this bulk action",
                "http_status": 400,
                "affected": 0,
            }

    return {"success": True, "affected": affected, "http_status": 200}
