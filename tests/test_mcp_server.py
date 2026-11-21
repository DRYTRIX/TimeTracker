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
