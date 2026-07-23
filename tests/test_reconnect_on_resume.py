"""
Regression guards for reconnect-on-resume (#702 / #703).

After the UI is backgrounded (tray-hide or inactive tab), a transient network
failure must not stick the client in an unavailable state. These tests assert
the client-side recovery hooks exist in source.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
DESKTOP = ROOT / "desktop" / "src"

pytestmark = [pytest.mark.unit]


def test_error_handler_quiet_health_and_visibility_reconnect():
    content = (STATIC / "error-handling-enhanced.js").read_text(encoding="utf-8")
    assert "isQuietHealthUrl" in content
    assert "quietFetch" in content
    assert "dismissConnectivityErrors" in content
    assert "visibilitychange" in content
    assert "startHealthProbeInterval" in content
    assert "/api/health" in content
    assert "if (quiet)" in content


def test_service_worker_bypasses_health_probe():
    content = (STATIC / "js" / "sw.js").read_text(encoding="utf-8")
    assert "path === '/api/health'" in content
    assert "path === '/_health'" in content


def test_base_template_reconnects_socket_on_visible():
    content = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "visibilitychange" in content
    assert "socket.disconnected" in content
    assert "socket.connect()" in content


def test_desktop_renderer_revalidates_session_on_resume():
    main_jsx = (DESKTOP / "renderer-react" / "src" / "main.jsx").read_text(encoding="utf-8")
    main_js = (DESKTOP / "main" / "main.js").read_text(encoding="utf-8")
    preload = (DESKTOP / "main" / "preload.js").read_text(encoding="utf-8")

    assert "revalidateSession" in main_jsx
    assert "revalidateOnResume" in main_jsx
    assert "onAppResume" in main_jsx
    assert "visibilitychange" in main_jsx

    assert "powerMonitor" in main_js
    assert "notifyAppResume" in main_js
    assert "app:resume" in main_js
    assert "mainWindow.on('show'" in main_js

    assert "onAppResume" in preload
    assert "app:resume" in preload
