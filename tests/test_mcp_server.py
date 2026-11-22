"""Unit tests for mcp_server toolset selection and log_time confirm/approval flow."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


def test_resolve_toolset_user_and_admin_readonly():
    from mcp_server.server import _resolve_toolset

    toolset, writes = _resolve_toolset({"is_admin": False, "token_scopes": ["read:time_entries", "write:time_entries"]})
    assert toolset == "user"
    assert writes is True

    toolset, writes = _resolve_toolset({"is_admin": True, "token_scopes": ["read:reports", "read:projects"]})
    assert toolset == "admin"
    assert writes is False

    with patch.dict(os.environ, {"MCP_TOOLSET": "admin_readonly"}):
        toolset, writes = _resolve_toolset({"is_admin": True, "token_scopes": ["write:invoices"]})
        assert toolset == "admin"
        assert writes is False


def test_create_mcp_registers_user_tools_only(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "user")

    fake_me = {
        "user": {"username": "alice", "role": "user"},
        "is_admin": False,
        "role_names": ["user"],
        "token_scopes": ["read:users", "read:projects", "read:time_entries", "write:time_entries"],
        "standard_hours_per_day": 8.0,
    }

    with patch("mcp_server.server.whoami", return_value=fake_me):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        # FastMCP stores tools in _tool_manager
        tools = mcp._tool_manager.list_tools()
        names = {t.name for t in tools}
        assert "whoami" in names
        assert "log_time" in names
        assert "report_unbilled" not in names
        assert "list_users" not in names


def test_create_mcp_admin_readonly_hides_writes(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "admin_readonly")

    fake_me = {
        "user": {"username": "admin", "role": "admin"},
        "is_admin": True,
        "role_names": ["admin"],
        "token_scopes": ["read:reports", "read:invoices"],
    }

    with patch("mcp_server.server.whoami", return_value=fake_me):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        names = {t.name for t in mcp._tool_manager.list_tools()}
        assert "report_unbilled" in names
        assert "whoami" in names
        assert "log_time" not in names
        assert "create_invoice" not in names
        # Read-only billing tools remain available without write scope (#937)
        assert "get_invoice_pdf" in names
        assert "get_invoice_pdf_url" in names
        assert "get_time_entry_admin" in names
        assert "report_missing_hours" in names
        assert "report_expenses" in names
        assert "list_expense_categories" in names
        assert "update_time_entry_admin" not in names
        assert "delete_time_entry_admin" not in names
        assert "bulk_update_time_entries" not in names
        assert "delete_invoice" not in names


def test_create_mcp_admin_registers_billing_writes(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "admin")

    fake_me = {
        "user": {"username": "admin", "role": "admin"},
        "is_admin": True,
        "role_names": ["admin"],
        "token_scopes": ["admin:all", "write:time_entries", "write:invoices"],
    }

    with patch("mcp_server.server.whoami", return_value=fake_me):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        names = {t.name for t in mcp._tool_manager.list_tools()}
        for expected in (
            "update_time_entry_admin",
            "delete_time_entry_admin",
            "bulk_update_time_entries",
            "update_invoice",
            "delete_invoice",
            "list_invoice_time_entries",
            "get_invoice_pdf",
            "update_task",
            "delete_task",
            "approve_expense",
            "reject_expense",
            "create_project_cost",
            "report_budget",
        ):
            assert expected in names


def test_update_time_entry_admin_requires_confirm(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "admin")

    fake_me = {
        "user": {"username": "admin", "role": "admin"},
        "is_admin": True,
        "role_names": ["admin"],
        "token_scopes": ["admin:all"],
    }
    client = MagicMock()
    client.patch.return_value = {"time_entry": {"id": 9, "billable": False}}

    with patch("mcp_server.server.whoami", return_value=fake_me), patch(
        "mcp_server.tools_admin.TimeTrackerClient", return_value=client
    ):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        fn = mcp._tool_manager._tools["update_time_entry_admin"].fn
        preview = json.loads(fn(entry_id=9, fields={"billable": False}, confirm=False))
        assert preview["preview"] is True
        client.patch.assert_not_called()
        applied = json.loads(fn(entry_id=9, fields={"billable": False}, confirm=True))
        assert applied["time_entry"]["id"] == 9
        client.patch.assert_called_once()


def test_delete_time_entry_admin_refuses_invoiced(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "admin")

    fake_me = {
        "user": {"username": "admin", "role": "admin"},
        "is_admin": True,
        "role_names": ["admin"],
        "token_scopes": ["admin:all"],
    }
    client = MagicMock()
    client.get.return_value = {"time_entry": {"id": 5, "paid": True}}

    with patch("mcp_server.server.whoami", return_value=fake_me), patch(
        "mcp_server.tools_admin.TimeTrackerClient", return_value=client
    ):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        fn = mcp._tool_manager._tools["delete_time_entry_admin"].fn
        out = json.loads(fn(entry_id=5, confirm=True))
        assert out["error"] == "refused"
        client.delete.assert_not_called()


def test_delete_invoice_refuses_non_draft(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "admin")

    fake_me = {
        "user": {"username": "admin", "role": "admin"},
        "is_admin": True,
        "role_names": ["admin"],
        "token_scopes": ["admin:all"],
    }
    client = MagicMock()
    client.get.return_value = {"invoice": {"id": 3, "status": "sent"}}

    with patch("mcp_server.server.whoami", return_value=fake_me), patch(
        "mcp_server.tools_admin.TimeTrackerClient", return_value=client
    ):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        fn = mcp._tool_manager._tools["delete_invoice"].fn
        out = json.loads(fn(invoice_id=3, confirm=True))
        assert out["error"] == "refused"
        client.delete.assert_not_called()


def test_log_time_preview_then_confirm_and_unconfirmed_approval(monkeypatch):
    monkeypatch.setenv("TIMETRACKER_API_TOKEN", "tt_test")
    monkeypatch.setenv("MCP_TOOLSET", "user")

    fake_me = {
        "user": {"username": "alice", "role": "user"},
        "is_admin": False,
        "role_names": ["user"],
        "token_scopes": ["write:time_entries", "read:time_entries", "write:time_approvals"],
    }

    preview_body = {
        "preview": True,
        "would_write": {"start_time": "2026-01-01T09:00:00", "duration_seconds": 2400},
        "checks": {"ok": True},
    }
    created_body = {"message": "ok", "time_entry": {"id": 42, "source": "agent"}}
    approval_body = {"success": True, "approval": {"id": 7}}

    client = MagicMock()
    client.post.side_effect = [preview_body, created_body, approval_body]

    with patch("mcp_server.server.whoami", return_value=fake_me), patch(
        "mcp_server.tools_user.TimeTrackerClient", return_value=client
    ):
        from mcp_server.server import create_mcp

        mcp = create_mcp()
        log_time = next(t for t in mcp._tool_manager.list_tools() if t.name == "log_time")
        # Call underlying function via tool manager
        fn = mcp._tool_manager._tools["log_time"].fn

        out = json.loads(fn(project_id=1, date="2026-01-01", duration_seconds=2400, confirm=False))
        assert out.get("preview") is True or out.get("hint")

        out2 = json.loads(
            fn(
                project_id=1,
                date="2026-01-01",
                duration_seconds=2400,
                confirm=True,
                unconfirmed=True,
                idempotency_key="k1",
            )
        )
        assert out2["created"]["time_entry"]["id"] == 42
        assert out2["approval"]["success"] is True
        assert client.post.call_count == 3
