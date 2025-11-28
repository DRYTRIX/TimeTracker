"""
Tests for onboarding system
"""

import pytest
from app import db
from app.models import User


@pytest.mark.unit
@pytest.mark.onboarding
def test_onboarding_manager_exists():
    """Test that onboarding manager exists in the frontend"""
    # This is a frontend test, but we can verify the file exists
    import os

    onboarding_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "static", "onboarding-enhanced.js"
    )
    assert os.path.exists(onboarding_file), "Onboarding enhanced file should exist"


@pytest.mark.unit
@pytest.mark.onboarding
def test_onboarding_js_loaded(authenticated_client):
    """Test that onboarding JavaScript is loaded in base template"""
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    # Check that onboarding-enhanced.js is included
    assert b"onboarding-enhanced.js" in response.data


@pytest.mark.unit
@pytest.mark.onboarding
def test_contextual_help_system():
    """Test that contextual help system is implemented"""
    import os

    onboarding_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "static", "onboarding-enhanced.js"
    )
    if os.path.exists(onboarding_file):
        with open(onboarding_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "initContextualHelp" in content, "Contextual help should be implemented"
            assert "addHelpButton" in content, "Help button functionality should exist"


@pytest.mark.unit
@pytest.mark.onboarding
def test_tooltip_system():
    """Test that tooltip system is implemented"""
    import os

    onboarding_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "static", "onboarding-enhanced.js"
    )
    if os.path.exists(onboarding_file):
        with open(onboarding_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "initTooltips" in content, "Tooltip system should be implemented"
            assert "attachTooltips" in content, "Tooltip attachment should exist"


@pytest.mark.unit
@pytest.mark.onboarding
def test_feature_discovery():
    """Test that feature discovery is implemented"""
    import os

    onboarding_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "static", "onboarding-enhanced.js"
    )
    if os.path.exists(onboarding_file):
        with open(onboarding_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "initFeatureDiscovery" in content, "Feature discovery should be implemented"
            assert "addFeatureBadge" in content, "Feature badge functionality should exist"


@pytest.mark.unit
@pytest.mark.onboarding
def test_enhanced_tour_steps():
    """Test that enhanced tour steps are defined"""
    import os

    onboarding_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "static", "onboarding-enhanced.js"
    )
    if os.path.exists(onboarding_file):
        with open(onboarding_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "getEnhancedTourSteps" in content, "Enhanced tour steps should be defined"
            assert "Welcome to TimeTracker" in content, "Welcome message should exist"


@pytest.mark.smoke
@pytest.mark.onboarding
def test_onboarding_files_exist():
    """Smoke test: Verify onboarding files exist"""
    import os

    base_dir = os.path.dirname(os.path.dirname(__file__))

    files = ["app/static/onboarding.js", "app/static/onboarding-enhanced.js"]

    for file_path in files:
        full_path = os.path.join(base_dir, file_path)
        assert os.path.exists(full_path), f"File {file_path} should exist"


@pytest.mark.unit
@pytest.mark.onboarding
def test_onboarding_base_template_integration(authenticated_client):
    """Test that onboarding scripts are included in base template"""
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Check for onboarding scripts
    assert "onboarding.js" in html or "onboarding-enhanced.js" in html
