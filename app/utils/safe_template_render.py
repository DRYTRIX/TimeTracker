"""Sandboxed Jinja2 for database-stored templates (PDF HTML, ReportLab strings, invoice email HTML)."""

from __future__ import annotations

import pathlib
from typing import Any

from jinja2.sandbox import SandboxedEnvironment, SecurityError

# Types that must never be exposed as template globals (sandbox escape / filesystem).
_BLOCKED_CONTEXT_TYPES = (type(pathlib.Path), type(pathlib.PurePath))
_BLOCKED_CONTEXT_NAMES = frozenset({"Path", "PurePath", "os", "sys", "open", "__builtins__"})


def render_sandboxed_string(source: str, *, autoescape: bool = True, **context: Any) -> str:
    """Render ``source`` with only ``context`` keys visible (no Flask ``config`` / ``request``).

    ``autoescape=True`` for HTML/CSS (WeasyPrint, browsers). ``autoescape=False`` for ReportLab
    text so markup is not HTML-entity-encoded.

    Raises ``jinja2.sandbox.SecurityError`` on blocked attribute access typical of SSTI.

    Admin-authored PDF/email templates are intentionally rendered via Jinja2's
    SandboxedEnvironment (not Flask ``render_template_string``) so attribute
    access typical of SSTI is blocked. Callers must not pass untrusted end-user
    input as ``source``. Filesystem types such as ``pathlib.Path`` are rejected.
    """
    if not source:
        return ""
    for key, value in context.items():
        if key in _BLOCKED_CONTEXT_NAMES:
            raise SecurityError(f"Template context key {key!r} is not allowed")
        if isinstance(value, _BLOCKED_CONTEXT_TYPES) or value in (pathlib.Path, pathlib.PurePath):
            raise SecurityError(f"Template context value for {key!r} must not be a Path type")
    # codeql[py/template-injection]: SandboxedEnvironment for admin-only stored templates
    env = SandboxedEnvironment(autoescape=autoescape)
    template = env.from_string(source)
    return template.render(**context)


__all__ = ["SecurityError", "render_sandboxed_string"]
