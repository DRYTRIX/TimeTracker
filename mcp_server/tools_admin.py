"""Admin MCP tools — CRUD and reports (optional user_id where API allows)."""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_server.api_client import TimeTrackerClient, new_idempotency_key, set_tool_name


def _json(data: Any) -> str:
    return json.dumps(data, default=str, indent=2)


def _client() -> TimeTrackerClient:
    return TimeTrackerClient()


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
        name="list_quotes",
        description="List quotes.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_quotes(page: int = 1, per_page: int = 50) -> str:
        set_tool_name("list_quotes")
        return _json(_client().get("/api/v1/quotes", page=page, per_page=per_page))

    @mcp.tool(
        name="list_expenses",
        description="List expenses.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_expenses(page: int = 1, per_page: int = 50, project_id: Optional[int] = None) -> str:
        set_tool_name("list_expenses")
        return _json(_client().get("/api/v1/expenses", page=page, per_page=per_page, project_id=project_id))

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
        name="invoice_from_unbilled",
        description="Create a draft invoice from all unbilled time for a client. Requires confirm=true. Does not send.",
        annotations=ToolAnnotations(destructiveHint=False),
    )
    def invoice_from_unbilled(client_id: int, confirm: bool = False) -> str:
        set_tool_name("invoice_from_unbilled")
        if not confirm:
            # Use unbilled report as preview
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
                "note": "Fetch with the same Bearer token. No outbound send via MCP.",
            }
        )
