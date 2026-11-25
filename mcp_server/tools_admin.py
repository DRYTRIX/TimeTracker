"""Admin MCP tools — CRUD and reports (optional user_id where API allows)."""

from __future__ import annotations

import base64
import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_server.api_client import TimeTrackerClient, new_idempotency_key, set_tool_name


def _json(data: Any) -> str:
    return json.dumps(data, default=str, indent=2)


def _client() -> TimeTrackerClient:
    return TimeTrackerClient()


def _parse_time_entry_ids(raw: Any) -> list[int]:
    """Parse invoice item time_entry_ids (comma-separated string or list)."""
    ids: list[int] = []
    if raw is None:
        return ids
    if isinstance(raw, list):
        parts = raw
    else:
        parts = str(raw).split(",")
    for part in parts:
        try:
            ids.append(int(str(part).strip()))
        except (TypeError, ValueError):
            continue
    return ids


def register_admin_tools(mcp: FastMCP, *, allow_writes: bool = True) -> None:
    @mcp.tool(
        name="list_users",
        description="List users (admin). Read-only.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_users(page: int = 1, per_page: int = 50) -> str:
        set_tool_name("list_users")
        return _json(_client().get("/api/v1/users", page=page, per_page=per_page))

    @mcp.tool(
        name="list_clients",
        description="List clients.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_clients(page: int = 1, per_page: int = 50, search: Optional[str] = None) -> str:
        set_tool_name("list_clients")
        return _json(_client().get("/api/v1/clients", page=page, per_page=per_page, search=search))

    @mcp.tool(
        name="get_client",
        description="Get a client by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_client(client_id: int) -> str:
        set_tool_name("get_client")
        return _json(_client().get(f"/api/v1/clients/{client_id}"))

    @mcp.tool(
        name="list_projects_admin",
        description="List all projects (admin view).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_projects_admin(page: int = 1, per_page: int = 50, client_id: Optional[int] = None) -> str:
        set_tool_name("list_projects_admin")
        return _json(_client().get("/api/v1/projects", page=page, per_page=per_page, client_id=client_id))

    @mcp.tool(
        name="get_project",
        description="Get a project by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_project(project_id: int) -> str:
        set_tool_name("get_project")
        return _json(_client().get(f"/api/v1/projects/{project_id}"))

    @mcp.tool(
        name="list_tasks",
        description="List tasks; optional project_id filter (any project).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_tasks(
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> str:
        set_tool_name("list_tasks")
        return _json(
            _client().get(
                "/api/v1/tasks",
                project_id=project_id,
                status=status,
                page=page,
                per_page=per_page,
            )
        )

    @mcp.tool(
        name="list_time_entries_admin",
        description="List time entries; optional user_id filter (admin).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_time_entries_admin(
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> str:
        set_tool_name("list_time_entries_admin")
        return _json(
            _client().get(
                "/api/v1/time-entries",
                user_id=user_id,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                source=source,
                page=page,
                per_page=per_page,
            )
        )

    @mcp.tool(
        name="get_time_entry_admin",
        description="Get one time entry by id (any user). Read-only.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_time_entry_admin(entry_id: int) -> str:
        set_tool_name("get_time_entry_admin")
        return _json(_client().get(f"/api/v1/time-entries/{entry_id}"))

    @mcp.tool(
        name="report_summary",
        description="Time tracking summary report grouped by project/user.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def report_summary(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> str:
        set_tool_name("report_summary")
        return _json(
            _client().get(
                "/api/v1/reports/summary",
                start_date=start_date,
                end_date=end_date,
                project_id=project_id,
                user_id=user_id,
            )
        )

    @mcp.tool(
        name="report_unbilled",
        description="Unbilled hours and amount per project (matches invoice rate resolution).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def report_unbilled(
        client_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        set_tool_name("report_unbilled")
        return _json(
            _client().get(
                "/api/v1/reports/unbilled",
                client_id=client_id,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

    @mcp.tool(
        name="report_expenses",
        description="Expense totals by project, user, and category for a period.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def report_expenses(
        start_date: str,
        end_date: str,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> str:
        set_tool_name("report_expenses")
        return _json(
            _client().get(
                "/api/v1/reports/expenses",
                start_date=start_date,
                end_date=end_date,
                project_id=project_id,
                user_id=user_id,
                category=category,
                status=status,
            )
        )

    @mcp.tool(
        name="report_budget",
        description="Budget vs actuals: project health, estimates-vs-actuals, and budget alerts.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def report_budget(project_id: Optional[int] = None) -> str:
        set_tool_name("report_budget")
        c = _client()
        result: dict[str, Any] = {
            "estimates_vs_actuals": c.get("/api/v1/reports/estimates-vs-actuals", project_id=project_id),
            "budget_alerts": c.get("/api/v1/budget-alerts", project_id=project_id, page=1, per_page=50),
        }
        if project_id is not None:
            try:
                result["health"] = c.get(f"/api/v1/projects/{project_id}/health")
            except Exception as exc:
                result["health_error"] = str(exc)
        return _json(result)

    @mcp.tool(
        name="report_missing_hours",
        description="Users who logged less than standard hours (weekdays × standard_hours_per_day) in a period.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def report_missing_hours(
        start_date: str,
        end_date: str,
        only_missing: bool = True,
    ) -> str:
        set_tool_name("report_missing_hours")
        return _json(
            _client().get(
                "/api/v1/reports/missing-hours",
                start_date=start_date,
                end_date=end_date,
                only_missing=str(only_missing).lower(),
            )
        )

    @mcp.tool(
        name="list_invoices",
        description="List invoices.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_invoices(page: int = 1, per_page: int = 50, client_id: Optional[int] = None) -> str:
        set_tool_name("list_invoices")
        return _json(_client().get("/api/v1/invoices", page=page, per_page=per_page, client_id=client_id))

    @mcp.tool(
        name="get_invoice",
        description="Get invoice detail by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_invoice(invoice_id: int) -> str:
        set_tool_name("get_invoice")
        return _json(_client().get(f"/api/v1/invoices/{invoice_id}"))

    @mcp.tool(
        name="list_invoice_time_entries",
        description="List time entries included on an invoice (derived from line item time_entry_ids).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_invoice_time_entries(invoice_id: int) -> str:
        set_tool_name("list_invoice_time_entries")
        c = _client()
        detail = c.get(f"/api/v1/invoices/{invoice_id}")
        invoice = detail.get("invoice") or detail
        items = invoice.get("items") or []
        entry_ids: list[int] = []
        for item in items:
            entry_ids.extend(_parse_time_entry_ids(item.get("time_entry_ids")))
        # Preserve order, unique
        seen: set[int] = set()
        unique_ids: list[int] = []
        for eid in entry_ids:
            if eid not in seen:
                seen.add(eid)
                unique_ids.append(eid)
        entries = []
        errors = []
        for eid in unique_ids:
            try:
                entries.append(c.get(f"/api/v1/time-entries/{eid}"))
            except Exception as exc:
                errors.append({"entry_id": eid, "error": str(exc)})
        return _json(
            {
                "invoice_id": invoice_id,
                "time_entry_ids": unique_ids,
                "time_entries": entries,
                "errors": errors,
            }
        )

    @mcp.tool(
        name="get_invoice_pdf_url",
        description="Return the API path to download an invoice PDF (does not email or send Peppol/SDI).",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_invoice_pdf_url(invoice_id: int) -> str:
        set_tool_name("get_invoice_pdf_url")
        return _json(
            {
                "invoice_id": invoice_id,
                "path": f"/api/v1/invoices/{invoice_id}/pdf",
                "note": "Fetch with the same Bearer token. Prefer get_invoice_pdf for embedded content.",
            }
        )

    @mcp.tool(
        name="get_invoice_pdf",
        description="Download an invoice PDF as base64 (embedded). Does not email or send Peppol/SDI.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_invoice_pdf(invoice_id: int, size: str = "A4") -> str:
        set_tool_name("get_invoice_pdf")
        content, content_type, filename = _client().get_bytes(
            f"/api/v1/invoices/{invoice_id}/pdf",
            params={"size": size},
        )
        return _json(
            {
                "invoice_id": invoice_id,
                "filename": filename or f"invoice-{invoice_id}.pdf",
                "mime_type": content_type or "application/pdf",
                "encoding": "base64",
                "content_base64": base64.b64encode(content).decode("ascii"),
                "size_bytes": len(content),
                "path": f"/api/v1/invoices/{invoice_id}/pdf",
                "note": "No outbound send via MCP.",
            }
        )

    @mcp.tool(
        name="list_quotes",
        description="List quotes.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_quotes(page: int = 1, per_page: int = 50) -> str:
        set_tool_name("list_quotes")
        return _json(_client().get("/api/v1/quotes", page=page, per_page=per_page))

    @mcp.tool(
        name="get_quote",
        description="Get a quote by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_quote(quote_id: int) -> str:
        set_tool_name("get_quote")
        return _json(_client().get(f"/api/v1/quotes/{quote_id}"))

    @mcp.tool(
        name="list_expenses",
        description="List expenses.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_expenses(page: int = 1, per_page: int = 50, project_id: Optional[int] = None) -> str:
        set_tool_name("list_expenses")
        return _json(_client().get("/api/v1/expenses", page=page, per_page=per_page, project_id=project_id))

    @mcp.tool(
        name="get_expense",
        description="Get an expense by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_expense(expense_id: int) -> str:
        set_tool_name("get_expense")
        return _json(_client().get(f"/api/v1/expenses/{expense_id}"))

    @mcp.tool(
        name="list_expense_categories",
        description="List expense categories.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_expense_categories(include_inactive: bool = False) -> str:
        set_tool_name("list_expense_categories")
        return _json(
            _client().get(
                "/api/v1/expense-categories",
                include_inactive=str(include_inactive).lower(),
            )
        )

    @mcp.tool(
        name="list_project_costs",
        description="List non-hourly project costs for a project.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_project_costs(
        project_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> str:
        set_tool_name("list_project_costs")
        return _json(
            _client().get(
                f"/api/v1/projects/{project_id}/costs",
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page,
            )
        )

    if not allow_writes:
        return

    @mcp.tool(
        name="create_client",
        description="Create a client. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_client(fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_client")
        if not confirm:
            return _json({"preview": True, "fields": fields, "hint": "Pass confirm=true to create."})
        return _json(_client().post("/api/v1/clients", fields))

    @mcp.tool(
        name="update_client",
        description="Update a client. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_client(client_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_client")
        if not confirm:
            return _json({"preview": True, "client_id": client_id, "fields": fields})
        return _json(_client().patch(f"/api/v1/clients/{client_id}", fields))

    @mcp.tool(
        name="create_project",
        description="Create a project. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_project(fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_project")
        if not confirm:
            return _json({"preview": True, "fields": fields})
        return _json(_client().post("/api/v1/projects", fields))

    @mcp.tool(
        name="update_project",
        description="Update a project. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_project(project_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_project")
        if not confirm:
            return _json({"preview": True, "project_id": project_id, "fields": fields})
        return _json(_client().patch(f"/api/v1/projects/{project_id}", fields))

    @mcp.tool(
        name="create_task",
        description="Create a task on a project. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_task(project_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_task")
        if not confirm:
            return _json({"preview": True, "project_id": project_id, "fields": fields})
        body = {**fields, "project_id": project_id}
        return _json(_client().post("/api/v1/tasks", body))

    @mcp.tool(
        name="update_task",
        description="Update a task. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_task(task_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_task")
        if not confirm:
            return _json({"preview": True, "task_id": task_id, "fields": fields, "hint": "Pass confirm=true to apply."})
        return _json(_client().patch(f"/api/v1/tasks/{task_id}", fields))

    @mcp.tool(
        name="delete_task",
        description="Delete a task. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def delete_task(task_id: int, confirm: bool = False) -> str:
        set_tool_name("delete_task")
        if not confirm:
            return _json({"preview": True, "task_id": task_id, "hint": "Pass confirm=true to delete."})
        return _json(_client().delete(f"/api/v1/tasks/{task_id}"))

    @mcp.tool(
        name="update_time_entry_admin",
        description="Update any user's time entry (notes, project, task, times/duration, billable). Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_time_entry_admin(entry_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_time_entry_admin")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "entry_id": entry_id,
                    "fields": fields,
                    "hint": "Pass confirm=true to apply.",
                }
            )
        return _json(_client().patch(f"/api/v1/time-entries/{entry_id}", fields))

    @mcp.tool(
        name="delete_time_entry_admin",
        description="Delete any user's time entry. Refused for invoiced (paid) entries. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def delete_time_entry_admin(entry_id: int, confirm: bool = False, reason: Optional[str] = None) -> str:
        set_tool_name("delete_time_entry_admin")
        c = _client()
        current = c.get(f"/api/v1/time-entries/{entry_id}")
        entry = current.get("time_entry") or current
        if entry.get("paid"):
            return _json(
                {
                    "error": "refused",
                    "message": "Cannot delete an invoiced (paid) time entry.",
                    "entry_id": entry_id,
                }
            )
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "entry_id": entry_id,
                    "entry": entry,
                    "hint": "Pass confirm=true to delete.",
                }
            )
        body = {"reason": reason} if reason else None
        return _json(c.delete(f"/api/v1/time-entries/{entry_id}", json=body))

    @mcp.tool(
        name="bulk_update_time_entries",
        description=(
            "Bulk-update time entries: billable, project_id, and/or task_id. "
            "Preview unless confirm=true. Skips running and invoiced entries."
        ),
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def bulk_update_time_entries(
        entry_ids: list[int],
        billable: Optional[bool] = None,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        confirm: bool = False,
    ) -> str:
        set_tool_name("bulk_update_time_entries")
        fields: dict[str, Any] = {}
        if billable is not None:
            fields["billable"] = billable
        if project_id is not None:
            fields["project_id"] = project_id
        if task_id is not None:
            fields["task_id"] = task_id
        if not fields:
            return _json({"error": "Provide at least one of billable, project_id, task_id."})
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "entry_ids": entry_ids,
                    "fields": fields,
                    "hint": "Pass confirm=true to apply bulk actions sequentially.",
                }
            )
        c = _client()
        results: list[dict[str, Any]] = []
        if "billable" in fields:
            results.append(
                {
                    "action": "set_billable",
                    "result": c.post(
                        "/api/v1/time-entries/bulk",
                        {"entry_ids": entry_ids, "action": "set_billable", "value": fields["billable"]},
                    ),
                }
            )
        if "project_id" in fields:
            results.append(
                {
                    "action": "set_project",
                    "result": c.post(
                        "/api/v1/time-entries/bulk",
                        {"entry_ids": entry_ids, "action": "set_project", "value": fields["project_id"]},
                    ),
                }
            )
        if "task_id" in fields:
            results.append(
                {
                    "action": "set_task",
                    "result": c.post(
                        "/api/v1/time-entries/bulk",
                        {"entry_ids": entry_ids, "action": "set_task", "value": fields["task_id"]},
                    ),
                }
            )
        return _json({"entry_ids": entry_ids, "results": results})

    @mcp.tool(
        name="log_time_for_user",
        description="Admin: log time for a user_id. Preview unless confirm=true. source=agent.",
        annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True),
    )
    def log_time_for_user(
        user_id: int,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        task_id: Optional[int] = None,
        date: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        notes: Optional[str] = None,
        billable: bool = True,
        confirm: bool = False,
        unconfirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> str:
        set_tool_name("log_time_for_user")
        c = _client()
        body: dict[str, Any] = {
            "user_id": user_id,
            "project_id": project_id,
            "client_id": client_id,
            "task_id": task_id,
            "notes": notes,
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
            return _json(c.post("/api/v1/time-entries/preview", body))
        key = idempotency_key or new_idempotency_key("admin_log_time")
        created = c.post("/api/v1/time-entries", body, idempotency_key=key)
        result: dict[str, Any] = {"created": created, "idempotency_key": key}
        if unconfirmed:
            entry_id = (created.get("time_entry") or {}).get("id")
            if entry_id:
                try:
                    result["approval"] = c.post(
                        f"/api/v1/time-entries/{entry_id}/request-approval",
                        {"comment": "Logged by MCP agent (unconfirmed)"},
                    )
                except Exception as exc:
                    result["approval_warning"] = str(exc)
        return _json(result)

    @mcp.tool(
        name="create_expense",
        description="Create an expense. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_expense(fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_expense")
        if not confirm:
            return _json({"preview": True, "fields": fields})
        return _json(_client().post("/api/v1/expenses", fields))

    @mcp.tool(
        name="update_expense",
        description="Update an expense. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_expense(expense_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_expense")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "expense_id": expense_id,
                    "fields": fields,
                    "hint": "Pass confirm=true to apply.",
                }
            )
        return _json(_client().patch(f"/api/v1/expenses/{expense_id}", fields))

    @mcp.tool(
        name="approve_expense",
        description="Approve a pending expense. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def approve_expense(expense_id: int, notes: Optional[str] = None, confirm: bool = False) -> str:
        set_tool_name("approve_expense")
        body: dict[str, Any] = {}
        if notes:
            body["notes"] = notes
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "expense_id": expense_id,
                    "body": body,
                    "hint": "Pass confirm=true to approve.",
                }
            )
        return _json(_client().post(f"/api/v1/expenses/{expense_id}/approve", body))

    @mcp.tool(
        name="reject_expense",
        description="Reject a pending expense. Requires confirm=true and reason.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def reject_expense(expense_id: int, reason: str, confirm: bool = False) -> str:
        set_tool_name("reject_expense")
        body = {"reason": reason}
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "expense_id": expense_id,
                    "body": body,
                    "hint": "Pass confirm=true to reject.",
                }
            )
        return _json(_client().post(f"/api/v1/expenses/{expense_id}/reject", body))

    @mcp.tool(
        name="create_quote",
        description="Create a quote. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_quote(fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_quote")
        if not confirm:
            return _json({"preview": True, "fields": fields})
        return _json(_client().post("/api/v1/quotes", fields))

    @mcp.tool(
        name="update_quote",
        description="Update a quote. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_quote(quote_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_quote")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "quote_id": quote_id,
                    "fields": fields,
                    "hint": "Pass confirm=true to apply.",
                }
            )
        return _json(_client().patch(f"/api/v1/quotes/{quote_id}", fields))

    @mcp.tool(
        name="create_project_cost",
        description="Create a non-hourly project cost. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_project_cost(project_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_project_cost")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "project_id": project_id,
                    "fields": fields,
                    "hint": "Pass confirm=true to create.",
                }
            )
        return _json(_client().post(f"/api/v1/projects/{project_id}/costs", fields))

    @mcp.tool(
        name="create_invoice",
        description="Create an invoice. Requires confirm=true. Does not send email or e-invoice.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def create_invoice(fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("create_invoice")
        if not confirm:
            return _json({"preview": True, "fields": fields})
        return _json(_client().post("/api/v1/invoices", fields))

    @mcp.tool(
        name="update_invoice",
        description="Update draft invoice header fields (dates, notes, terms, currency, …). Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_invoice(invoice_id: int, fields: dict[str, Any], confirm: bool = False) -> str:
        set_tool_name("update_invoice")
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "invoice_id": invoice_id,
                    "fields": fields,
                    "hint": "Pass confirm=true to apply.",
                }
            )
        return _json(_client().patch(f"/api/v1/invoices/{invoice_id}", fields))

    @mcp.tool(
        name="delete_invoice",
        description="Cancel a draft invoice only (soft-cancel). Requires confirm=true. Does not send.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def delete_invoice(invoice_id: int, confirm: bool = False) -> str:
        set_tool_name("delete_invoice")
        c = _client()
        detail = c.get(f"/api/v1/invoices/{invoice_id}")
        invoice = detail.get("invoice") or detail
        status = (invoice.get("status") or "").lower()
        if status != "draft":
            return _json(
                {
                    "error": "refused",
                    "message": f"Only draft invoices can be deleted via MCP (status={status or 'unknown'}).",
                    "invoice_id": invoice_id,
                    "status": status,
                }
            )
        if not confirm:
            return _json(
                {
                    "preview": True,
                    "invoice_id": invoice_id,
                    "status": status,
                    "hint": "Pass confirm=true to cancel this draft invoice.",
                }
            )
        return _json(c.delete(f"/api/v1/invoices/{invoice_id}"))

    @mcp.tool(
        name="invoice_from_unbilled",
        description="Create a draft invoice from all unbilled time for a client. Requires confirm=true. Does not send.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def invoice_from_unbilled(client_id: int, confirm: bool = False) -> str:
        set_tool_name("invoice_from_unbilled")
        if not confirm:
            preview = _client().get("/api/v1/reports/unbilled", client_id=client_id)
            return _json({"preview": True, "unbilled": preview, "hint": "Pass confirm=true to create draft invoice."})
        return _json(_client().post(f"/api/v1/clients/{client_id}/invoice-unbilled", {}))

    @mcp.tool(
        name="invoice_generate_from_time",
        description="Add time entry IDs to an existing invoice. Requires confirm=true. Does not send.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def invoice_generate_from_time(
        invoice_id: int,
        time_entry_ids: list[int],
        replace_existing: bool = True,
        confirm: bool = False,
    ) -> str:
        set_tool_name("invoice_generate_from_time")
        body = {"time_entry_ids": time_entry_ids, "replace_existing": replace_existing}
        if not confirm:
            return _json({"preview": True, "invoice_id": invoice_id, "body": body})
        return _json(_client().post(f"/api/v1/invoices/{invoice_id}/generate-from-time", body))

    @mcp.tool(
        name="update_invoice_items",
        description="Replace invoice line items on a draft invoice. Requires confirm=true.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def update_invoice_items(invoice_id: int, items: list[dict[str, Any]], confirm: bool = False) -> str:
        set_tool_name("update_invoice_items")
        if not confirm:
            return _json({"preview": True, "invoice_id": invoice_id, "items": items})
        return _json(_client().put(f"/api/v1/invoices/{invoice_id}/items", {"items": items}))
