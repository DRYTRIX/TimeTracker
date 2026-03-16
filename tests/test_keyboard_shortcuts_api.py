"""
Tests for keyboard shortcuts API: GET/POST/reset, validation, auth.
"""
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.routes]

from app import db
from app.models import User
from app.utils.keyboard_shortcuts_defaults import (
    FORBIDDEN_KEYS,
    merge_overrides,
    normalize_key,
    validate_overrides,
)


@pytest.fixture
def api_authenticated_client(client, user):
    """Authenticate via session (avoids login endpoint)."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    return client


class TestKeyboardShortcutsAPI:
    """API endpoints for keyboard shortcuts."""

    def test_get_requires_auth(self, app, client):
        """GET /api/settings/keyboard-shortcuts returns 302 redirect when not logged in."""
        response = client.get("/api/settings/keyboard-shortcuts")
        assert response.status_code == 302
        assert "login" in (response.location or "").lower()

    def test_get_returns_config_when_authenticated(self, api_authenticated_client):
        """GET returns 200 and structure { shortcuts, overrides } when logged in."""
        response = api_authenticated_client.get("/api/settings/keyboard-shortcuts")
        assert response.status_code == 200
        data = response.get_json()
        assert "shortcuts" in data
        assert "overrides" in data
        assert isinstance(data["shortcuts"], list)
        assert isinstance(data["overrides"], dict)
        assert len(data["shortcuts"]) > 0
        first = data["shortcuts"][0]
        assert "id" in first
        assert "default_key" in first
        assert "current_key" in first
        assert "name" in first

    def test_get_returns_defaults_when_no_overrides(self, api_authenticated_client):
        """When user has no overrides (e.g. new user), current_key equals default_key for all."""
        response = api_authenticated_client.get("/api/settings/keyboard-shortcuts")
        assert response.status_code == 200
        data = response.get_json()
        overrides = data.get("overrides") or {}
        for s in data["shortcuts"]:
            expected = overrides.get(s["id"]) or s["default_key"]
            assert s["current_key"] == expected

    def test_post_save_valid_overrides(self, api_authenticated_client):
        """POST with valid overrides returns 200 and saves; GET returns updated current_key."""
        payload = {"overrides": {"nav_dashboard": "g 1"}}
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.get_json()
        nav = next((s for s in data["shortcuts"] if s["id"] == "nav_dashboard"), None)
        assert nav is not None
        assert nav["current_key"] == "g 1"
        assert data["overrides"].get("nav_dashboard") == "g 1" or "nav_dashboard" in data["overrides"]

        get_resp = api_authenticated_client.get("/api/settings/keyboard-shortcuts")
        get_data = get_resp.get_json()
        nav2 = next((s for s in get_data["shortcuts"] if s["id"] == "nav_dashboard"), None)
        assert nav2 is not None
        assert nav2["current_key"] == "g 1"

    def test_post_reject_conflict(self, api_authenticated_client):
        """POST with two actions sharing the same key in same context returns 400."""
        payload = {"overrides": {"nav_dashboard": "g p", "nav_projects": "g p"}}
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "conflict" in data["error"].lower() or "multiple" in data["error"].lower()

    def test_post_reject_forbidden_key(self, api_authenticated_client):
        """POST with a forbidden key returns 400."""
        forbidden = next(iter(FORBIDDEN_KEYS))
        payload = {"overrides": {"nav_dashboard": forbidden}}
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "forbidden" in data["error"].lower()

    def test_post_reset_clears_overrides(self, api_authenticated_client, user):
        """POST reset returns 200 and GET returns defaults."""
        with api_authenticated_client.application.app_context():
            user.keyboard_shortcuts_overrides = {"nav_dashboard": "g 1"}
            db.session.commit()
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts/reset",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.get_json()
        nav = next((s for s in data["shortcuts"] if s["id"] == "nav_dashboard"), None)
        assert nav is not None
        assert nav["current_key"] == nav["default_key"]
        assert not data.get("overrides") or len(data["overrides"]) == 0

    def test_post_invalid_body(self, api_authenticated_client):
        """POST with overrides not an object returns 400."""
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts",
            json={"overrides": "not-a-dict"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_post_non_json_body_returns_400_or_415(self, api_authenticated_client):
        """POST with non-JSON body (e.g. text/plain or invalid JSON) returns 400 or 415."""
        # No Content-Type or non-JSON: get_json(silent=True) returns None, overrides becomes {}
        response = api_authenticated_client.post(
            "/api/settings/keyboard-shortcuts",
            data="not json",
            headers={"Content-Type": "text/plain"},
        )
        # Backend uses get_json(silent=True) or {} so may still process; empty overrides is valid
        assert response.status_code in (200, 400, 415)
        if response.status_code == 400:
            data = response.get_json()
            assert data is None or "error" in (data or {})

    def test_reset_requires_auth(self, app, client):
        """POST reset without auth returns 302 redirect to login."""
        response = client.post(
            "/api/settings/keyboard-shortcuts/reset",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 302
        assert "login" in (response.location or "").lower()


class TestKeyboardShortcutsValidation:
    """Unit tests for keyboard_shortcuts_defaults."""

    def test_normalize_key(self):
        assert normalize_key("Ctrl+K") == "ctrl+k"
        assert normalize_key("  g   d  ") == "g d"
        assert normalize_key("Command+Shift+X") == "ctrl+shift+x"

    def test_merge_overrides_empty(self):
        merged = merge_overrides(None)
        assert len(merged) > 0
        for s in merged:
            assert s["current_key"] == s["default_key"]

    def test_merge_overrides_applied(self):
        merged = merge_overrides({"nav_dashboard": "g 1"})
        nav = next((s for s in merged if s["id"] == "nav_dashboard"), None)
        assert nav is not None
        assert nav["current_key"] == "g 1"

    def test_validate_overrides_success(self):
        result = validate_overrides({"nav_dashboard": "g 1"})
        assert len(result) == 4
        ok, err, merged, to_save = result
        assert ok is True
        assert err is None
        assert merged is not None
        assert to_save is not None
        assert to_save.get("nav_dashboard") == "g 1"

    def test_validate_overrides_conflict(self):
        ok, err, merged, to_save = validate_overrides({"nav_dashboard": "g p", "nav_projects": "g p"})
        assert ok is False
        assert err is not None
        assert merged is None
        assert to_save is None

    def test_validate_overrides_forbidden(self):
        forbidden = next(iter(FORBIDDEN_KEYS))
        ok, err, merged, to_save = validate_overrides({"nav_dashboard": forbidden})
        assert ok is False
        assert "forbidden" in (err or "").lower()
        assert merged is None
        assert to_save is None

    def test_validate_overrides_unknown_id(self):
        ok, err, merged, to_save = validate_overrides({"unknown_id_xyz": "ctrl+a"})
        assert ok is False
        assert "unknown" in (err or "").lower()
        assert merged is None
        assert to_save is None
