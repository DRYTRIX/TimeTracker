"""
Regression guards for reconnect-on-resume (#702 / #703 / #746).

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
    # Delayed probes on resume sweep errors from background fetches (#703 / #746)
    assert "setTimeout" in content
    assert "1500" in content
    assert "5000" in content
    assert content.count("checkOnlineStatus({ quiet: true, onResume: true })") >= 3


def test_idle_background_fetches_are_quiet():
    """Background idle polls must not toast on transient resume failures (#703)."""
    content = (STATIC / "idle.js").read_text(encoding="utf-8")
    assert "fetch('/api/timer/status', { __ttQuiet: true })" in content
    assert "__ttQuiet: true" in content
    assert "/api/timer/heartbeat" in content
    assert "/api/notifications" in content
    # Heartbeat and notifications fetches must both carry the quiet flag
    assert content.count("__ttQuiet: true") >= 3


def test_dashboard_background_polls_are_quiet():
    """Dashboard live polls must not toast while the tab is backgrounded (#703)."""
    content = (STATIC / "dashboard-enhancements.js").read_text(encoding="utf-8")
    assert "__ttQuiet: true" in content
    assert "document.hidden" in content
    assert content.count("__ttQuiet: true") >= 4


def test_smart_notifications_poll_is_quiet():
    content = (STATIC / "smart-notifications.js").read_text(encoding="utf-8")
    assert "/api/notifications" in content
    assert "__ttQuiet: true" in content
    assert "document.hidden" in content


def test_service_worker_does_not_synthesize_api_offline():
    """SW must not intercept /api/ or invent 503 Offline bodies (#746)."""
    content = (STATIC / "js" / "sw.js").read_text(encoding="utf-8")
    assert "networkFirstApi" not in content
    assert "new Response('Offline'" not in content
    assert "path.startsWith('/api/')" in content
    assert "path === '/_health'" in content
    # cacheFirst uses Response.error() instead of a fake 503
    assert "Response.error()" in content


def test_error_handler_no_invalid_status_zero_and_visible_retry_buttons():
    """#746: Response status 0 is invalid; retry buttons must not be white-on-white."""
    content = (STATIC / "error-handling-enhanced.js").read_text(encoding="utf-8")
    assert "status: 0" not in content
    assert "X-TT-Network-Error" in content
    # Retry/recovery buttons on toasts use inherit + slate, not white-on-white
    assert ".error-retry-btn" in content
    assert "color: inherit" in content
    assert "rgba(148, 163, 184" in content
    assert "color: white;\n                border: 1px solid rgba(255, 255, 255" not in content
    # Burst toast dedup in showErrorWithRetry
    assert "Duplicate error suppressed" in content


def test_remaining_background_polls_are_quiet():
    """Chat widget, activity feed, and kanban polls must be quiet + hidden-gated (#746)."""
    chat = (TEMPLATES / "components" / "persistent_chat_widget.html").read_text(encoding="utf-8")
    assert "__ttQuiet: true" in chat
    assert "document.hidden" in chat
    assert "response.ok" in chat

    activity = (TEMPLATES / "components" / "activity_feed_widget.html").read_text(encoding="utf-8")
    assert "__ttQuiet: true" in activity
    assert "document.hidden" in activity

    kanban = (TEMPLATES / "tasks" / "_kanban.html").read_text(encoding="utf-8")
    assert "__ttQuiet: true" in kanban
    assert "document.hidden" in kanban


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
