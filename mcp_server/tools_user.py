"""User time-tracking MCP tools (no user_id args — always token owner)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_server.api_client import TimeTrackerClient, new_idempotency_key, set_tool_name


def _json(data: Any) -> str:
    return json.dumps(data, default=str, indent=2)


def _client() -> TimeTrackerClient:
    return TimeTrackerClient()


def register_user_tools(mcp: FastMCP, *, allow_writes: bool = True) -> None:
    @mcp.tool(
        name="whoami",
        description="Current user, timezone, standard hours per day, roles, and enabled modules.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def whoami() -> str:
        set_tool_name("whoami")
        return _json(_client().get("/api/v1/users/me"))

    @mcp.tool(
        name="list_my_projects",
        description="Projects the current user may log time to (favorites first when available), with tasks.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_my_projects() -> str:
        set_tool_name("list_my_projects")
        c = _client()
        projects = c.get("/api/v1/projects", per_page=100)
        favorites: list[Any] = []
        try:
            fav = c.get("/api/v1/users/me/favorites/projects")
            favorites = fav.get("projects") or fav.get("favorites") or []
        except Exception:
            favorites = []
        fav_ids = {p.get("id") for p in favorites if isinstance(p, dict)}
        items = projects.get("projects") or []
        items_sorted = sorted(
            items,
            key=lambda p: (0 if p.get("id") in fav_ids else 1, (p.get("name") or "").lower()),
        )
        # Attach tasks for each project (best-effort)
        enriched = []
        for p in items_sorted[:50]:
            row = dict(p)
            try:
                tasks = c.get(f"/api/v1/projects/{p['id']}/tasks", per_page=100)
                row["tasks"] = tasks.get("tasks") or []
            except Exception:
                row["tasks"] = []
            enriched.append(row)
        return _json({"projects": enriched, "favorite_ids": list(fav_ids)})

    @mcp.tool(
        name="find_project",
        description="Find a project (and optional task) by name substring.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def find_project(query: str, task_query: Optional[str] = None) -> str:
        set_tool_name("find_project")
        c = _client()
        projects = c.get("/api/v1/projects", per_page=100, search=query)
        items = projects.get("projects") or []
        q = query.lower()
        matches = [p for p in items if q in (p.get("name") or "").lower()]
        if not matches:
            matches = items
        result = []
        for p in matches[:20]:
            row = {"project": p, "tasks": []}
            try:
                tasks = c.get(f"/api/v1/projects/{p['id']}/tasks", per_page=100)
                tlist = tasks.get("tasks") or []
                if task_query:
                    tq = task_query.lower()
                    tlist = [t for t in tlist if tq in (t.get("name") or "").lower()]
                row["tasks"] = tlist
            except Exception:
                pass
            result.append(row)
        return _json({"matches": result})

    @mcp.tool(
        name="list_my_time_entries",
        description="List the current user's time entries for a period (ISO dates).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_my_time_entries(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_id: Optional[int] = None,
        source: Optional[str] = None,
    ) -> str:
        set_tool_name("list_my_time_entries")
        return _json(
            _client().get(
                "/api/v1/time-entries",
                start_date=start_date,
                end_date=end_date,
                project_id=project_id,
                source=source,
                per_page=100,
            )
        )

    @mcp.tool(
        name="my_week",
        description="Hours per day for the current week against standard hours; highlights empty days.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def my_week(week_start: Optional[str] = None) -> str:
        set_tool_name("my_week")
        c = _client()
        me = c.get("/api/v1/users/me")
        std = float(me.get("standard_hours_per_day") or 8.0)
        if week_start:
            start = date.fromisoformat(week_start[:10])
        else:
            today = date.today()
            start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        entries = c.get(
            "/api/v1/time-entries",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            per_page=200,
        )
        by_day = {(start + timedelta(days=i)).isoformat(): 0.0 for i in range(7)}
        for e in entries.get("time_entries") or []:
            st = e.get("start_time") or ""
            day = st[:10]
            if day in by_day:
                by_day[day] += float(e.get("duration_hours") or 0)
        days = []
        for d, hours in by_day.items():
            days.append(
                {
                    "date": d,
                    "hours": round(hours, 2),
                    "standard_hours": std,
                    "empty": hours <= 0,
                    "shortfall": round(max(0.0, std - hours), 2),
                }
            )
        return _json(
            {
                "week_start": start.isoformat(),
                "week_end": end.isoformat(),
                "standard_hours_per_day": std,
                "days": days,
                "total_hours": round(sum(by_day.values()), 2),
            }
        )

    @mcp.tool(
        name="timer_status",
        description="Current timer status for the authenticated user.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def timer_status() -> str:
        set_tool_name("timer_status")
        return _json(_client().get("/api/v1/timer/status"))

    if not allow_writes:
        return

    @mcp.tool(
        name="log_time",
        description=(
            "Log a time entry. Without confirm=true returns a preview only. "
            "Use date+duration_seconds for duration-only (placed after last entry that day), "
            "or start_time/end_time. Set unconfirmed=true to request approval after write. "
            "Always pass an idempotency_key for retries."
        ),
        annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
    )
    def log_time(
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        task_id: Optional[int] = None,
        date: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        billable: bool = True,
        confirm: bool = False,
        unconfirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> str:
        set_tool_name("log_time")
        c = _client()
        body: dict[str, Any] = {
            "project_id": project_id,
            "client_id": client_id,
            "task_id": task_id,
            "notes": notes,
            "tags": tags,
            "billable": billable,
            "source": "agent",
        }
        if date and duration_seconds is not None:
            body["date"] = date
            body["duration_seconds"] = duration_seconds
        if start_time:
            body["start_time"] = start_time
        if end_time:
            body["end_time"] = end_time
        body = {k: v for k, v in body.items() if v is not None}

        if not confirm:
            preview = c.post("/api/v1/time-entries/preview", body)
            preview["hint"] = "Call again with confirm=true to write this entry."
            return _json(preview)

        key = idempotency_key or new_idempotency_key("log_time")
        created = c.post("/api/v1/time-entries", body, idempotency_key=key)
        result: dict[str, Any] = {"created": created, "idempotency_key": key}

        if unconfirmed:
            entry = created.get("time_entry") or {}
            entry_id = entry.get("id")
            if entry_id:
                try:
                    approval = c.post(
                        f"/api/v1/time-entries/{entry_id}/request-approval",
                        {"comment": "Logged by MCP agent (unconfirmed)"},
                    )
                    result["approval"] = approval
                except Exception as exc:
                    result["approval_warning"] = str(exc)
        return _json(result)

    @mcp.tool(
        name="log_time_batch",
        description="Log multiple time entries. Each item follows log_time fields. Requires confirm=true to write.",
        annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
    )
    def log_time_batch(entries: list[dict[str, Any]], confirm: bool = False) -> str:
        set_tool_name("log_time_batch")
        if not confirm:
            previews = []
            c = _client()
            for item in entries:
                body = {**item, "source": "agent"}
                body.pop("confirm", None)
                body.pop("unconfirmed", None)
                body.pop("idempotency_key", None)
                previews.append(c.post("/api/v1/time-entries/preview", body))
            return _json({"preview": True, "entries": previews, "hint": "Call with confirm=true to write."})

        results = []
        for item in entries:
            # Reuse log_time logic via nested call pattern
            results.append(
                json.loads(
                    log_time(
                        project_id=item.get("project_id"),
                        client_id=item.get("client_id"),
                        task_id=item.get("task_id"),
                        date=item.get("date"),
                        duration_seconds=item.get("duration_seconds"),
                        start_time=item.get("start_time"),
                        end_time=item.get("end_time"),
                        notes=item.get("notes"),
                        tags=item.get("tags"),
                        billable=item.get("billable", True),
                        confirm=True,
                        unconfirmed=bool(item.get("unconfirmed")),
                        idempotency_key=item.get("idempotency_key"),
                    )
                )
            )
        return _json({"results": results})

    @mcp.tool(
        name="start_timer",
        description="Start a timer on a project or client.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def start_timer(
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        set_tool_name("start_timer")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "would_start": {"project_id": project_id, "client_id": client_id, "task_id": task_id},
                    "hint": "Pass confirm=true to start.",
                }
            )
        body = {
            k: v
            for k, v in {"project_id": project_id, "client_id": client_id, "task_id": task_id, "notes": notes}.items()
            if v is not None
        }
        return _json(_client().post("/api/v1/timer/start", body))

    @mcp.tool(
        name="stop_timer",
        description="Stop the active timer.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def stop_timer(confirm: bool = False) -> str:
        set_tool_name("stop_timer")
        if not confirm:
            return _json({"preview": True, "hint": "Pass confirm=true to stop the timer."})
        return _json(_client().post("/api/v1/timer/stop", {}))

    @mcp.tool(
        name="restart_timer",
        description="Restart/resume timer from a previous entry id when supported by the API.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def restart_timer(entry_id: Optional[int] = None, confirm: bool = False) -> str:
        set_tool_name("restart_timer")
        if not confirm:
            return _json({"preview": True, "entry_id": entry_id, "hint": "Pass confirm=true to restart."})
        c = _client()
        # Prefer resume; fall back to start from status context
        try:
            if entry_id:
                return _json(c.post(f"/api/v1/timer/resume", {"entry_id": entry_id}))
            return _json(c.post("/api/v1/timer/resume", {}))
        except Exception:
            return _json(c.post("/api/v1/timer/start", {}))

    @mcp.tool(
        name="update_my_time_entry",
        description="Update one of the current user's time entries (not invoiced / not locked). Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_my_time_entry(entry_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_my_time_entry")
        if not confirm:
            return _json(
                {"preview": True, "entry_id": entry_id, "fields": fields, "hint": "Pass confirm=true to apply."}
            )
        return _json(_client().patch(f"/api/v1/time-entries/{entry_id}", fields))

    @mcp.tool(
        name="delete_my_time_entry",
        description="Delete one of the current user's time entries. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def delete_my_time_entry(entry_id: int, confirm: bool = False) -> str:
        set_tool_name("delete_my_time_entry")
        if not confirm:
            return _json({"preview": True, "entry_id": entry_id, "hint": "Pass confirm=true to delete."})
        return _json(_client().delete(f"/api/v1/time-entries/{entry_id}"))
