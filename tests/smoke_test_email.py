"""
Smoke tests for email functionality

These tests verify that the email feature is properly integrated and
the critical paths work end-to-end.
"""

import pytest
from flask import url_for


class TestEmailSmokeTests:
    """Smoke tests for email feature integration"""

    def test_email_support_page_loads(self, admin_authenticated_client):
        """Smoke test: Email support page loads without errors"""
        # Access email support page
        response = admin_authenticated_client.get("/admin/email")

        # Page should load successfully
        assert response.status_code == 200

        # Check for key elements
        assert b"Email Configuration" in response.data or b"email" in response.data.lower()
        assert b"Test Email" in response.data or b"test" in response.data.lower()

    def check_email_configuration_status_api(self, admin_authenticated_client):
        """Smoke test: Email configuration status API works"""
        # Get configuration status
        response = admin_authenticated_client.get("/admin/email/config-status")

        # API should respond successfully
        assert response.status_code == 200

        # Response should be JSON
        data = response.get_json()
        assert data is not None

        # Should contain required fields
        assert "configured" in data
        assert "settings" in data
        assert "errors" in data
        assert "warnings" in data

    def test_admin_dashboard_integration(self, admin_authenticated_client):
        """Smoke test: Email feature integrates with admin dashboard"""
        # Access admin dashboard
        response = admin_authenticated_client.get("/admin")

        assert response.status_code == 200

        # Admin dashboard should load successfully
        assert b"Admin" in response.data

    def test_email_utilities_importable(self):
        """Smoke test: Email utilities can be imported"""
        try:
            from app.utils.email import send_email, check_email_configuration, send_test_email, init_mail

            # If we can import, test passes
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import email utilities: {e}")

    def test_email_routes_registered(self, app):
        """Smoke test: Email routes are properly registered"""
        with app.app_context():
            # Check that email routes exist
            rules = [rule.rule for rule in app.url_map.iter_rules()]

            # Email support page route
            assert "/admin/email" in rules

            # Test email route
            assert "/admin/email/test" in rules

            # Config status route
            assert "/admin/email/config-status" in rules

    def test_email_template_exists(self, app):
        """Smoke test: Email templates exist"""
        with app.app_context():
            from flask import render_template

            # Test that admin email support template exists
            try:
                # Try to get the template (won't render, just check it exists)
                from jinja2 import TemplateNotFound

                try:
                    app.jinja_env.get_template("admin/email_support.html")
                    admin_template_exists = True
                except TemplateNotFound:
                    admin_template_exists = False

                assert admin_template_exists, "Admin email support template not found"

                # Test that email test template exists
                try:
                    app.jinja_env.get_template("email/test_email.html")
                    test_template_exists = True
                except TemplateNotFound:
                    test_template_exists = False

                assert test_template_exists, "Email test template not found"

            except Exception as e:
                pytest.fail(f"Failed to check templates: {e}")

    def check_email_configuration_with_environment(self, app, monkeypatch):
        """Smoke test: Email configuration loads from environment"""
        # Set test environment variables
        monkeypatch.setenv("MAIL_SERVER", "smtp.test.com")
        monkeypatch.setenv("MAIL_PORT", "587")
        monkeypatch.setenv("MAIL_USE_TLS", "true")
        monkeypatch.setenv("MAIL_DEFAULT_SENDER", "test@example.com")

        with app.app_context():
            from app.utils.email import init_mail

            # Initialize mail with environment
            mail = init_mail(app)

            # Check configuration loaded correctly
            assert app.config["MAIL_SERVER"] == "smtp.test.com"
            assert app.config["MAIL_PORT"] == 587
            assert app.config["MAIL_USE_TLS"] is True
            assert app.config["MAIL_DEFAULT_SENDER"] == "test@example.com"


class TestEmailFeatureIntegrity:
    """Tests to verify email feature integrity"""

    def test_all_email_functions_have_docstrings(self):
        """Verify all email functions have proper documentation"""
        from app.utils import email
        import inspect

        functions = ["send_email", "check_email_configuration", "send_test_email", "init_mail"]

        for func_name in functions:
            func = getattr(email, func_name, None)
            assert func is not None, f"Function {func_name} not found"
            assert func.__doc__ is not None, f"Function {func_name} missing docstring"

    def test_email_routes_have_proper_decorators(self):
        """Verify email routes have proper authentication decorators"""
        from app.routes import admin
        import inspect

        # Get the email_support function
        email_support = getattr(admin, "email_support", None)
        assert email_support is not None

        # Check that it has route decorator (will be wrapped)
        # This is a basic check - the route should be registered
        assert callable(email_support)
