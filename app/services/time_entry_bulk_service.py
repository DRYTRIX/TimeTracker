"""Bulk time entry actions shared by legacy session API and API v1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app import db
from app.models import TimeEntry
from app.models.time_entry import local_now
from app.utils.db import safe_commit

# Reasons an entry is left unchanged by a bulk action (keys of ``skipped_reasons``).
SKIP_TIMER_RUNNING = "timer_running"
SKIP_ALREADY_INVOICED = "already_invoiced"


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

    Entries with a running timer are skipped for every action. ``set_billable`` also
    skips entries that are already invoiced (``paid`` is True).

    Returns dict with keys: success (bool), affected (int), affected_ids (list of int),
    skipped (int), skipped_reasons (dict reason -> count, only reasons that occurred),
    error (optional str), http_status (int).
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

    affected_ids: List[int] = []
    skipped_reasons: Dict[str, int] = {}

    def _skip(reason: str) -> None:
        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

    if action in {"add_tag", "remove_tag"}:
        tag = (value or "").strip() if value is not None else ""
        if not tag:
            return {"success": False, "error": "Tag value is required", "http_status": 400}

    for e in entries:
        if e.is_active:
            _skip(SKIP_TIMER_RUNNING)
            continue
        if action == "delete":
            db.session.delete(e)
        elif action == "set_billable":
            if e.paid:
                _skip(SKIP_ALREADY_INVOICED)
                continue
            e.set_billable(bool(value), commit=False)
        elif action == "set_paid":
            e.set_paid(bool(value), commit=False)
        else:
            tags = set(e.tag_list)
            if action == "add_tag":
                tags.add(tag)
            else:
                tags.discard(tag)
            e.tags = ", ".join(sorted(tags)) if tags else None
            e.updated_at = local_now()
        affected_ids.append(e.id)

    affected = len(affected_ids)
    skipped = sum(skipped_reasons.values())
    counts = {
        "affected": affected,
        "affected_ids": affected_ids,
        "skipped": skipped,
        "skipped_reasons": skipped_reasons,
    }

    if affected > 0:
        if not safe_commit("bulk_time_entries", {"action": action, "count": affected}):
            return {"success": False, "error": "Database error during bulk operation", "http_status": 500}
    else:
        db.session.rollback()
        if set(skipped_reasons) == {SKIP_TIMER_RUNNING}:
            error = "No entries were updated; active (running) time entries cannot be changed with this bulk action"
        else:
            error = (
                "No entries were updated; already invoiced entries and active (running) time entries "
                "cannot be changed with this bulk action"
            )
        return {"success": False, "error": error, "http_status": 400, **counts}

    return {"success": True, "http_status": 200, **counts}
