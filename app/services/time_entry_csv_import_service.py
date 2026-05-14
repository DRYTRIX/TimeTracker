"""CSV import for time entries (API v1)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Tuple

from app.services import TimeTrackingService
from app.utils.scope_filter import user_can_access_project


def _parse_dt(val: Any):
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return True
    return str(val).strip().lower() in {"1", "true", "yes", "y"}


def import_time_entries_from_csv_text(
    csv_text: str,
    *,
    user_id: int,
    is_admin: bool,
) -> Tuple[Dict[str, Any], int]:
    """
    Parse CSV and create time entries for the given user.

    Required columns: start_time, end_time, project_id
    Optional: task_id, notes, tags, billable

    Returns (result_dict, http_status).
    """
    if not csv_text or not csv_text.strip():
        return {"success": False, "error": "Empty CSV"}, 400

    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        return {"success": False, "error": "CSV must include a header row"}, 400

    fields_lower = {h.lower().strip(): h for h in reader.fieldnames if h}

    def col(name: str) -> str:
        for key, orig in fields_lower.items():
            if key.replace(" ", "_") == name.lower().replace(" ", "_"):
                return orig
        return name

    svc = TimeTrackingService()
    created = 0
    failed: List[Dict[str, Any]] = []
    row_num = 1

    for row in reader:
        row_num += 1
        try:
            pid_raw = row.get(col("project_id")) or row.get(col("project id"))
            if pid_raw is None or str(pid_raw).strip() == "":
                failed.append({"row": row_num, "error": "project_id is required"})
                continue
            project_id = int(str(pid_raw).strip())

            if not user_can_access_project_by_id(user_id, project_id, is_admin):
                failed.append({"row": row_num, "error": "no access to project"})
                continue

            st = _parse_dt(row.get(col("start_time")) or row.get(col("start")))
            et = _parse_dt(row.get(col("end_time")) or row.get(col("end")))
            if not st or not et:
                failed.append({"row": row_num, "error": "start_time and end_time required (ISO 8601)"})
                continue

            task_id = None
            tr = row.get(col("task_id")) or row.get(col("task id"))
            if tr is not None and str(tr).strip() != "":
                task_id = int(str(tr).strip())

            notes = (row.get(col("notes")) or row.get(col("description")) or "").strip() or None
            tags = (row.get(col("tags")) or "").strip() or None
            billable = _parse_bool(row.get(col("billable")))

            res = svc.create_manual_entry(
                user_id=user_id,
                project_id=project_id,
                client_id=None,
                start_time=st,
                end_time=et,
                task_id=task_id,
                notes=notes,
                tags=tags,
                billable=billable,
                paid=False,
                skip_entry_requirements=is_admin,
            )
            if res.get("success"):
                created += 1
            else:
                failed.append({"row": row_num, "error": res.get("message", "create failed")})
        except Exception as e:
            failed.append({"row": row_num, "error": str(e)})

    return (
        {
            "success": True,
            "created": created,
            "failed": len(failed),
            "errors": failed[:50],
        },
        200,
    )


def user_can_access_project_by_id(user_id: int, project_id: int, is_admin: bool) -> bool:
    from app.models import User

    u = User.query.get(user_id)
    if not u:
        return False
    return user_can_access_project(u, project_id)
