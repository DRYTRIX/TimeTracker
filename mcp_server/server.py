"""TimeTracker MCP server — stdio and Streamable HTTP."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import has_write_scope, set_api_token, whoami
from mcp_server.tools_admin import register_admin_tools
from mcp_server.tools_user import register_user_tools

logger = logging.getLogger("timetracker.mcp")


def _resolve_toolset(me: dict) -> tuple[str, bool]:
    """Return (toolset, allow_writes) from whoami payload and env overrides."""
    override = (os.environ.get("MCP_TOOLSET") or "auto").strip().lower()
    scopes = me.get("token_scopes") or []
    allow_writes = has_write_scope(scopes)
    if override in ("user", "admin", "admin_readonly", "admin-readonly", "readonly"):
        if override in ("admin_readonly", "admin-readonly", "readonly"):
            return "admin", False
        if override == "admin":
            return "admin", allow_writes
        return "user", allow_writes

    is_admin = bool(me.get("is_admin"))
    role_names = [r.lower() for r in (me.get("role_names") or [])]
    user = me.get("user") or {}
    if not is_admin and (user.get("role") or "").lower() in ("admin", "super_admin"):
        is_admin = True
    if not is_admin and any(r in ("admin", "super_admin") for r in role_names):
        is_admin = True

    if is_admin:
        return "admin", allow_writes
    return "user", allow_writes


def create_mcp() -> FastMCP:
    token = os.environ.get("TIMETRACKER_API_TOKEN")
    if token:
        set_api_token(token)

    instructions = (
        "TimeTracker MCP server. Time-tracking tools never take user_id for regular users. "
        "Destructive and log_time writes require confirm=true. "
        "No tools send email, Peppol, SDI, or charge payments."
    )
    mcp = FastMCP(
        name="TimeTracker",
        instructions=instructions,
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8090")),
        streamable_http_path="/mcp",
        stateless_http=True,
    )

    me: dict = {}
    try:
        me = whoami()
    except Exception as exc:
        logger.warning("Could not resolve whoami at startup (%s); registering user toolset only", exc)
        register_user_tools(mcp, allow_writes=True)
        return mcp

    toolset, allow_writes = _resolve_toolset(me)
    logger.info(
        "MCP toolset=%s allow_writes=%s user=%s",
        toolset,
        allow_writes,
        (me.get("user") or {}).get("username"),
    )

    # Everyone gets the personal time-tracking toolset
    register_user_tools(mcp, allow_writes=allow_writes)
    if toolset == "admin":
        register_admin_tools(mcp, allow_writes=allow_writes)
    return mcp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="TimeTracker MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "http"),
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="stdio for local assistants; streamable-http for remote /mcp",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=os.environ.get("MCP_LOG_LEVEL", "INFO"))
    if not os.environ.get("TIMETRACKER_BASE_URL"):
        logger.warning("TIMETRACKER_BASE_URL not set; defaulting to http://localhost:8080")
    if not os.environ.get("TIMETRACKER_API_TOKEN") and args.transport == "stdio":
        logger.error("TIMETRACKER_API_TOKEN is required for stdio transport")
        sys.exit(1)

    mcp = create_mcp()
    transport = "stdio" if args.transport == "stdio" else "streamable-http"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
