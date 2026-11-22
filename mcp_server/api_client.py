"""HTTP client for TimeTracker /api/v1."""

from __future__ import annotations

import os
import re
import uuid
from contextvars import ContextVar
from typing import Any, Optional

import httpx

_token_var: ContextVar[Optional[str]] = ContextVar("timetracker_api_token", default=None)
_tool_var: ContextVar[Optional[str]] = ContextVar("mcp_tool_name", default=None)

_FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', re.IGNORECASE)


def set_api_token(token: Optional[str]) -> None:
    _token_var.set(token)


def get_api_token() -> str:
    token = _token_var.get() or os.environ.get("TIMETRACKER_API_TOKEN") or ""
    if not token:
        raise RuntimeError("No API token: set TIMETRACKER_API_TOKEN or pass Authorization bearer")
    return token


def set_tool_name(name: Optional[str]) -> None:
    _tool_var.set(name)


def base_url() -> str:
    return (os.environ.get("TIMETRACKER_BASE_URL") or "http://localhost:8080").rstrip("/")


class TimeTrackerClient:
    """Thin wrapper around /api/v1 with MCP audit headers."""

    def __init__(self, token: Optional[str] = None, timeout: float = 60.0):
        self._token = token
        self._timeout = timeout

    def _headers(self, idempotency_key: Optional[str] = None, *, accept: str = "application/json") -> dict[str, str]:
        token = self._token or get_api_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "User-Agent": "TimeTracker-MCP/1.0",
        }
        if accept == "application/json":
            headers["Content-Type"] = "application/json"
        tool = _tool_var.get()
        if tool:
            headers["X-MCP-Tool"] = tool
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        url = f"{base_url()}{path if path.startswith('/') else '/' + path}"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.request(
                method,
                url,
                headers=self._headers(idempotency_key),
                json=json,
                params=params,
            )
        try:
            body: Any = resp.json()
        except Exception:
            body = {"raw": resp.text}
        if resp.status_code >= 400:
            message = body.get("message") if isinstance(body, dict) else None
            error = body.get("error") if isinstance(body, dict) else None
            raise RuntimeError(f"API {method} {path} failed ({resp.status_code}): {message or error or body}")
        return body if isinstance(body, dict) else {"data": body}

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        clean = {k: v for k, v in params.items() if v is not None}
        return self.request("GET", path, params=clean or None)

    def get_bytes(
        self,
        path: str,
        *,
        params: Optional[dict] = None,
        accept: str = "application/pdf,*/*",
    ) -> tuple[bytes, str, Optional[str]]:
        """Fetch a binary response. Returns (content, content_type, filename)."""
        url = f"{base_url()}{path if path.startswith('/') else '/' + path}"
        clean = {k: v for k, v in (params or {}).items() if v is not None} or None
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.request(
                "GET",
                url,
                headers=self._headers(accept=accept),
                params=clean,
            )
        if resp.status_code >= 400:
            try:
                body: Any = resp.json()
            except Exception:
                body = {"raw": resp.text}
            message = body.get("message") if isinstance(body, dict) else None
            error = body.get("error") if isinstance(body, dict) else None
            raise RuntimeError(f"API GET {path} failed ({resp.status_code}): {message or error or body}")
        content_type = (resp.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
        filename: Optional[str] = None
        disposition = resp.headers.get("content-disposition") or ""
        match = _FILENAME_RE.search(disposition)
        if match:
            filename = match.group(1).strip()
        return resp.content, content_type, filename

    def post(
        self,
        path: str,
        json: Any = None,
        *,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        return self.request("POST", path, json=json, idempotency_key=idempotency_key)

    def put(self, path: str, json: Any = None) -> dict[str, Any]:
        return self.request("PUT", path, json=json)

    def patch(self, path: str, json: Any = None) -> dict[str, Any]:
        return self.request("PATCH", path, json=json)

    def delete(self, path: str, json: Any = None) -> dict[str, Any]:
        return self.request("DELETE", path, json=json)


def new_idempotency_key(prefix: str = "mcp") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def whoami(client: Optional[TimeTrackerClient] = None) -> dict[str, Any]:
    c = client or TimeTrackerClient()
    return c.get("/api/v1/users/me")


def has_write_scope(scopes: list[str]) -> bool:
    if not scopes:
        return True  # unknown — allow and let API enforce
    if "admin:all" in scopes or "*" in scopes or "write:*" in scopes:
        return True
    return any(s.startswith("write:") for s in scopes)


def token_has_scope(scopes: list[str], required: str) -> bool:
    if not scopes:
        return True
    if "admin:all" in scopes or "*" in scopes:
        return True
    if required in scopes:
        return True
    action, _, resource = required.partition(":")
    if resource and f"{action}:*" in scopes:
        return True
    return False
