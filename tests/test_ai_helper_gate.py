"""AI helper feature flag: UI and session API when AI_ENABLED is off."""

import json

import pytest

pytestmark = [pytest.mark.integration]


def test_dashboard_hides_ai_helper_when_disabled(app, authenticated_client):
    """Default test app has AI off; base layout must not include AI drawer or script."""
    app.config["AI_ENABLED"] = False
    response = authenticated_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "aiHelperDrawer" not in html
    assert "ai-helper.js" not in html


def test_dashboard_shows_ai_helper_when_enabled(app, authenticated_client):
    app.config["AI_ENABLED"] = True
    response = authenticated_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "aiHelperDrawer" in html
    assert "ai-helper.js" in html


def test_session_ai_context_preview_503_when_disabled(app, authenticated_client):
    app.config["AI_ENABLED"] = False
    response = authenticated_client.get("/api/ai/context-preview")
    assert response.status_code == 503
    data = json.loads(response.data)
    assert data.get("error_code") == "ai_disabled"


def test_session_ai_context_preview_200_when_enabled(app, authenticated_client):
    app.config["AI_ENABLED"] = True
    response = authenticated_client.get("/api/ai/context-preview")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get("ok") is True
    assert "context" in data
