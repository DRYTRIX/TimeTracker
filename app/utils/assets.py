"""
Hashed asset resolution for bundled frontend files.

`scripts/build-js.mjs` emits content-hashed bundles into ``app/static/dist/`` plus a
``manifest.json`` mapping a stable logical name to the hashed path, e.g.::

    {"core": "dist/core.a1b2c3d4e5f6.min.js"}

Templates reference the stable name via the ``asset_url()`` Jinja global::

    <script src="{{ asset_url('core') }}"></script>

This replaces the ad-hoc ``?v={{ app_version }}-toastfix1`` query-string busting that
was scattered through base.html: the hash changes only when the bundle content
changes, so browsers cache correctly across releases that don't touch the asset.
"""

from __future__ import annotations

import json
import threading
from typing import Dict, Optional

from flask import current_app, url_for

_MANIFEST_LOCK = threading.Lock()
_MANIFEST_CACHE: Optional[Dict[str, str]] = None


def _manifest_path() -> str:
    import os

    return os.path.join(current_app.static_folder, "dist", "manifest.json")


def load_manifest(force: bool = False) -> Dict[str, str]:
    """
    Read (and cache) the build manifest.

    In debug the manifest is re-read on every call so a rebuild is picked up without
    restarting Flask. In production it is read once and cached.
    """
    global _MANIFEST_CACHE

    if not force and _MANIFEST_CACHE is not None and not current_app.debug:
        return _MANIFEST_CACHE

    try:
        with open(_manifest_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            data = {}
    except FileNotFoundError:
        # Assets not built yet (fresh checkout, or running tests without a JS build).
        # Callers fall back to the unbundled source file.
        data = {}
    except (OSError, json.JSONDecodeError) as exc:
        current_app.logger.warning("Could not read asset manifest: %s", exc)
        data = {}

    with _MANIFEST_LOCK:
        _MANIFEST_CACHE = data
    return data


def asset_url(name: str, fallback: Optional[str] = None) -> str:
    """
    Resolve a logical bundle name to its hashed static URL.

    Args:
        name: Logical bundle name from the manifest (e.g. "core").
        fallback: Static path to use when the manifest has no entry — lets the app
            still render if the JS build has not run.

    Returns:
        A URL suitable for a ``src`` attribute.
    """
    manifest = load_manifest()
    path = manifest.get(name)

    if path is None:
        if fallback is None:
            current_app.logger.warning(
                "Asset %r missing from manifest; run `npm run build:js`. "
                "Emitting an unbuilt path so the request 404s visibly.",
                name,
            )
            # Deliberately not "": an empty src makes the browser re-request the current
            # document and try to execute the HTML as JavaScript. A path that 404s is
            # quieter in the console and names the missing bundle in the network tab.
            path = f"dist/{name}.min.js"
        else:
            path = fallback

    return url_for("static", filename=path)


def register_asset_helpers(app) -> None:
    """Expose ``asset_url`` to templates."""
    app.jinja_env.globals["asset_url"] = asset_url
