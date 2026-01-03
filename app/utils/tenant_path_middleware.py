"""
WSGI middleware to support path-based multi-tenancy.

Incoming requests:
  /t/<tenant_slug>/anything...

Are rewritten for Flask routing as:
  /anything...

While SCRIPT_NAME is extended so url generation (url_for) automatically includes:
  /t/<tenant_slug>
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional


class TenantPathMiddleware:
    def __init__(
        self,
        app: Callable,
        *,
        enabled: bool = True,
        path_prefix: str = "/t",
        environ_key: str = "tt.tenant_slug",
    ) -> None:
        self.app = app
        self.enabled = bool(enabled)
        self.path_prefix = (path_prefix or "/t").rstrip("/") or "/t"
        self.environ_key = environ_key

    def __call__(self, environ, start_response) -> Iterable[bytes]:
        if not self.enabled:
            return self.app(environ, start_response)

        try:
            path_info = environ.get("PATH_INFO") or "/"
            prefix = self.path_prefix

            # Only handle /t/<slug>/... or /t/<slug>
            if not path_info.startswith(prefix + "/"):
                return self.app(environ, start_response)

            # Remove prefix and parse slug
            remainder = path_info[len(prefix) + 1 :]  # skip "/t/"
            if not remainder:
                return self.app(environ, start_response)

            parts = remainder.split("/", 1)
            slug = (parts[0] or "").strip().lower()
            if not slug:
                return self.app(environ, start_response)

            rest = "/" + parts[1] if len(parts) > 1 and parts[1] else "/"

            # Store tenant slug for later resolution
            environ[self.environ_key] = slug

            # Make url_for include /t/<slug> automatically by extending SCRIPT_NAME
            script_name = (environ.get("SCRIPT_NAME") or "").rstrip("/")
            environ["SCRIPT_NAME"] = f"{script_name}{prefix}/{slug}"

            # Rewrite PATH_INFO for Flask routing
            environ["PATH_INFO"] = rest
        except Exception:
            # Never block the request on middleware edge cases
            pass

        return self.app(environ, start_response)

