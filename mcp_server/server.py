"""TimeTracker MCP server — stdio and Streamable HTTP."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import get_api_token, has_write_scope, set_api_token, set_http_mode, whoami
from mcp_server.tools_admin import register_admin_tools
from mcp_server.tools_user import register_user_tools

logger = logging.getLogger("timetracker.mcp")

# Simple in-process cache: sha256(token) -> (expires_monotonic, whoami_payload)
_WHOAMI_CACHE: dict[str, tuple[float, dict]] = {}
_WHOAMI_TTL_SECONDS = 60.0


def _resolve_toolset(me: dict, *, http_mode: bool = False) -> tuple[str, bool]:
    """Return (toolset, allow_writes) from whoami payload and env overrides."""
    override = (os.environ.get("MCP_TOOLSET") or "auto").strip().lower()
    scopes = me.get("token_scopes") or []
    allow_writes = has_write_scope(scopes)

    is_admin = bool(me.get("is_admin"))
    role_names = [r.lower() for r in (me.get("role_names") or [])]
    user = me.get("user") or {}
    if not is_admin and (user.get("role") or "").lower() in ("admin", "super_admin"):
        is_admin = True
    if not is_admin and any(r in ("admin", "super_admin") for r in role_names):
        is_admin = True

    if override in ("user", "admin", "admin_readonly", "admin-readonly", "readonly"):
        if override in ("admin_readonly", "admin-readonly", "readonly"):
            # Narrowing only — never widen a non-admin to admin tools
            return ("admin" if is_admin else "user"), False
        if override == "admin":
            if http_mode and not is_admin:
                # HTTP mode: MCP_TOOLSET must not elevate a non-admin token
                return "user", allow_writes
            return "admin", allow_writes
        return "user", allow_writes

    if is_admin:
        return "admin", allow_writes
    return "user", allow_writes


def _whoami_cached(token: str) -> dict[str, Any]:
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.monotonic()
    cached = _WHOAMI_CACHE.get(key)
    if cached and cached[0] > now:
        return cached[1]
    set_api_token(token)
    me = whoami()
    _WHOAMI_CACHE[key] = (now + _WHOAMI_TTL_SECONDS, me)
    # Bound cache size
    if len(_WHOAMI_CACHE) > 256:
        expired = [k for k, (exp, _) in _WHOAMI_CACHE.items() if exp <= now]
        for k in expired:
            _WHOAMI_CACHE.pop(k, None)
    return me


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


class TimeTrackerMCP(FastMCP):
    """FastMCP subclass that binds each HTTP call to the caller's Bearer token."""

    def __init__(self, *args, http_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._http_mode = http_mode
        self._admin_tool_names: set[str] = set()
        self._user_tool_names: set[str] = set()

    def remember_toolsets(self, *, user_names: set[str], admin_names: set[str]) -> None:
        self._user_tool_names = set(user_names)
        self._admin_tool_names = set(admin_names)

    async def list_tools(self):  # type: ignore[override]
        tools = await super().list_tools()
        if not self._http_mode:
            return tools
        me = self._current_me()
        if me is None:
            return []
        toolset, _ = _resolve_toolset(me, http_mode=True)
        allowed = set(self._user_tool_names)
        if toolset == "admin":
            allowed |= self._admin_tool_names
        return [t for t in tools if getattr(t, "name", None) in allowed]

    async def call_tool(self, name: str, arguments: dict):  # type: ignore[override]
        if self._http_mode:
            me = self._current_me()
            if me is None:
                raise RuntimeError("Unauthorized: Bearer token required")
            toolset, _ = _resolve_toolset(me, http_mode=True)
            allowed = set(self._user_tool_names)
            if toolset == "admin":
                allowed |= self._admin_tool_names
            if name not in allowed:
                raise RuntimeError(f"Unknown tool: {name}")
        return await super().call_tool(name, arguments)

    def _current_me(self) -> Optional[dict]:
        try:
            token = get_api_token()
        except RuntimeError:
            return None
        try:
            return _whoami_cached(token)
        except Exception as exc:
            logger.warning("whoami failed for request token: %s", exc)
            return None


def create_mcp(*, http_mode: bool = False) -> FastMCP:
    if http_mode:
        set_http_mode(True)
        # Shared env token must not authenticate every caller in HTTP mode
        if os.environ.get("TIMETRACKER_API_TOKEN"):
            logger.warning(
                "TIMETRACKER_API_TOKEN is set but ignored in HTTP mode; "
                "each MCP request must send its own Authorization Bearer token"
            )
        # Do not seed ContextVar from env in HTTP mode
        set_api_token(None)
    else:
        set_http_mode(False)
        token = os.environ.get("TIMETRACKER_API_TOKEN")
        if token:
            set_api_token(token)

    instructions = (
        "TimeTracker MCP server. Time-tracking tools never take user_id for regular users. "
        "Destructive and log_time writes require confirm=true. "
        "No tools send email, Peppol, SDI, or charge payments."
    )
    mcp = TimeTrackerMCP(
        name="TimeTracker",
        instructions=instructions,
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8090")),
        streamable_http_path="/mcp",
        stateless_http=True,
        http_mode=http_mode,
    )

    # Register both toolsets; HTTP mode filters per request. Stdio keeps prior behaviour.
    before_user = {t.name for t in getattr(mcp, "_tool_manager", None).list_tools()} if False else set()
    register_user_tools(mcp, allow_writes=True)
    user_names = set()
    admin_names = set()
    try:
        # FastMCP stores tools on _tool_manager
        tm = getattr(mcp, "_tool_manager", None)
        if tm is not None:
            user_names = {t.name for t in tm.list_tools()}
    except Exception:
        pass

    register_admin_tools(mcp, allow_writes=True)
    try:
        tm = getattr(mcp, "_tool_manager", None)
        if tm is not None:
            all_names = {t.name for t in tm.list_tools()}
            admin_names = all_names - user_names
            if not user_names:
                user_names = all_names - admin_names
    except Exception:
        pass

    mcp.remember_toolsets(user_names=user_names or before_user, admin_names=admin_names)

    if not http_mode:
        me: dict = {}
        try:
            me = whoami()
        except Exception as exc:
            logger.warning("Could not resolve whoami at startup (%s); registering user toolset only", exc)
            return mcp

        toolset, allow_writes = _resolve_toolset(me, http_mode=False)
        logger.info(
            "MCP toolset=%s allow_writes=%s user=%s",
            toolset,
            allow_writes,
            (me.get("user") or {}).get("username"),
        )
        # Stdio already registered both; re-create with correct allow_writes if needed
        # Keep both registered — call filtering isn't applied in stdio beyond startup choice.
        # For stdio we historically only registered the chosen set; rebuild for parity.
        mcp = TimeTrackerMCP(
            name="TimeTracker",
            instructions=instructions,
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_PORT", "8090")),
            streamable_http_path="/mcp",
            stateless_http=True,
            http_mode=False,
        )
        register_user_tools(mcp, allow_writes=allow_writes)
        if toolset == "admin":
            register_admin_tools(mcp, allow_writes=allow_writes)
        return mcp

    return mcp


def _install_http_auth_middleware(mcp: FastMCP) -> None:
    """Require Authorization Bearer on every HTTP request and bind it to ContextVar."""
    try:
        app = mcp.streamable_http_app()
    except Exception as exc:
        logger.warning("Could not attach MCP HTTP auth middleware: %s", exc)
        return

    @app.middleware("http")
    async def mcp_bearer_auth(request, call_next):  # type: ignore[no-untyped-def]
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        token = _extract_bearer(auth)
        if not token:
            from starlette.responses import JSONResponse

            issuer = (os.environ.get("TIMETRACKER_BASE_URL") or "http://localhost:8080").rstrip("/")
            return JSONResponse(
                {"error": "unauthorized", "message": "Bearer token required"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="TimeTracker MCP", resource_metadata="{issuer}/.well-known/oauth-protected-resource"'},
            )
        try:
            _whoami_cached(token)
        except Exception:
            from starlette.responses import JSONResponse

            return JSONResponse(
                {"error": "unauthorized", "message": "Invalid or expired token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        set_api_token(token)
        try:
            return await call_next(request)
        finally:
            set_api_token(None)

    logger.info("MCP HTTP Bearer auth middleware installed")


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

    http_mode = args.transport in ("streamable-http", "http")
    if not http_mode and not os.environ.get("TIMETRACKER_API_TOKEN"):
        logger.error("TIMETRACKER_API_TOKEN is required for stdio transport")
        sys.exit(1)

    mcp = create_mcp(http_mode=http_mode)
    if http_mode:
        _install_http_auth_middleware(mcp)

    transport = "stdio" if args.transport == "stdio" else "streamable-http"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
