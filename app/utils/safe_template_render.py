"""Sandboxed Jinja2 for database-stored templates (PDF HTML, ReportLab strings, invoice email HTML)."""

from __future__ import annotations

from typing import Any

from jinja2.sandbox import SandboxedEnvironment, SecurityError


def render_sandboxed_string(source: str, *, autoescape: bool = True, **context: Any) -> str:
    """Render ``source`` with only ``context`` keys visible (no Flask ``config`` / ``request``).

    ``autoescape=True`` for HTML/CSS (WeasyPrint, browsers). ``autoescape=False`` for ReportLab
    text so markup is not HTML-entity-encoded.

    Raises ``jinja2.sandbox.SecurityError`` on blocked attribute access typical of SSTI.
    """
    if not source:
        return ""
    env = SandboxedEnvironment(autoescape=autoescape)
    return env.from_string(source).render(**context)


__all__ = ["SecurityError", "render_sandboxed_string"]
