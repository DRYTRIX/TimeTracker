"""Socket.IO origin check runs without a Flask app context (issue #848)."""

import threading

import pytest
from flask import has_app_context

from app.utils.cors import socketio_cors_allowed_origin

pytestmark = [pytest.mark.unit, pytest.mark.security]


def _call_like_engineio(origin, environ):
    """Call the callable the way Engine.IO does: from WSGI, with no app context.

    The ``app`` fixture keeps an app context pushed in the test thread, so run
    the call in a fresh thread, which starts without one.
    """
    result = {}

    def run():
        result["had_app_context"] = has_app_context()
        try:
            result["allowed"] = socketio_cors_allowed_origin(origin, environ)
        except Exception as exc:  # pragma: no cover - the regression itself
            result["error"] = exc

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    return result


def _environ(app):
    # Flask-SocketIO's middleware puts the app into the WSGI environ.
    return {"flask.app": app, "wsgi.url_scheme": "http", "HTTP_HOST": "localhost:8080"}


def test_allowed_origin_accepted_without_app_context(app):
    app.config["APP_BASE_URL"] = "https://tt.example.com"

    result = _call_like_engineio("https://tt.example.com", _environ(app))

    assert result["had_app_context"] is False
    assert "error" not in result
    assert result["allowed"] is True


def test_foreign_origin_rejected_without_app_context(app):
    app.config["APP_BASE_URL"] = "https://tt.example.com"

    result = _call_like_engineio("https://evil.example.com", _environ(app))

    assert "error" not in result
    assert result["allowed"] is False


def test_same_host_origin_accepted_without_app_context(app):
    app.config["APP_BASE_URL"] = ""

    result = _call_like_engineio("http://localhost:8080", _environ(app))

    assert "error" not in result
    assert result["allowed"] is True
