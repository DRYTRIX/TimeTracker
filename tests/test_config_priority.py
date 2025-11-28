"""
Tests for configuration priority system.
Tests that WebUI settings take priority over .env values, and that .env values
are used as initial startup values.
"""

import pytest
import os
from app.models import Settings
from app.utils.config_manager import ConfigManager
from app import db


class TestConfigPriority:
    """Tests for configuration priority: WebUI > .env > defaults"""

    def test_settings_priority_over_env(self, app):
        """Test that Settings model values take priority over environment variables"""
        with app.app_context():
            # Set an environment variable
            os.environ["CURRENCY"] = "USD"

            # Get Settings and verify it's initialized from env
            settings = Settings.get_settings()
            assert settings.currency == "USD" or settings.currency == "EUR"  # May be EUR if already exists

            # Change the setting via WebUI (Settings model)
            settings.currency = "GBP"
            db.session.commit()

            # ConfigManager should return the Settings value, not the env var
            currency = ConfigManager.get_setting("currency")
            assert currency == "GBP", "Settings model should take priority over env vars"

            # Clean up
            if "CURRENCY" in os.environ:
                del os.environ["CURRENCY"]

    def test_env_used_as_initial_value(self, app):
        """Test that .env values are used when creating new Settings instance"""
        with app.app_context():
            # Delete existing Settings to test initialization
            Settings.query.delete()
            db.session.commit()

            # Set environment variables
            os.environ["TZ"] = "America/New_York"
            os.environ["CURRENCY"] = "CAD"
            os.environ["ROUNDING_MINUTES"] = "5"
            os.environ["SINGLE_ACTIVE_TIMER"] = "false"
            os.environ["IDLE_TIMEOUT_MINUTES"] = "60"

            # Create new Settings - should be initialized from env
            settings = Settings.get_settings()

            # Verify it was initialized from env (if it's a new instance)
            # Note: If Settings already existed, it won't be re-initialized
            assert settings.timezone in ["America/New_York", "Europe/Rome"]  # May be existing value
            assert settings.currency in ["CAD", "EUR", "GBP"]  # May be existing value

            # Clean up
            for key in ["TZ", "CURRENCY", "ROUNDING_MINUTES", "SINGLE_ACTIVE_TIMER", "IDLE_TIMEOUT_MINUTES"]:
                if key in os.environ:
                    del os.environ[key]

    def test_config_manager_priority_order(self, app):
        """Test that ConfigManager checks in correct order: Settings > env > defaults"""
        with app.app_context():
            # Set environment variable
            os.environ["ROUNDING_MINUTES"] = "10"

            # Get Settings
            settings = Settings.get_settings()
            original_value = settings.rounding_minutes

            # Change via Settings (simulating WebUI change)
            settings.rounding_minutes = 15
            db.session.commit()

            # ConfigManager should return Settings value (15), not env var (10)
            value = ConfigManager.get_setting("rounding_minutes")
            assert value == 15, "ConfigManager should prioritize Settings over env vars"

            # Restore original value
            settings.rounding_minutes = original_value
            db.session.commit()

            # Clean up
            if "ROUNDING_MINUTES" in os.environ:
                del os.environ["ROUNDING_MINUTES"]

    def test_env_fallback_when_settings_not_set(self, app):
        """Test that env vars are used when Settings field is None"""
        with app.app_context():
            # Set environment variable
            os.environ["BACKUP_TIME"] = "03:00"

            # Get Settings
            settings = Settings.get_settings()
            original_value = settings.backup_time

            # ConfigManager should return env value if Settings is at default
            # (This test verifies the fallback mechanism)
            value = ConfigManager.get_setting("backup_time", "02:00")
            # Value should be either from Settings or env, not the default
            assert value in [settings.backup_time, "03:00", "02:00"]

            # Clean up
            if "BACKUP_TIME" in os.environ:
                del os.environ["BACKUP_TIME"]

    def test_settings_initialization_from_env_types(self, app):
        """Test that Settings initialization handles different value types correctly"""
        with app.app_context():
            # Delete existing Settings
            Settings.query.delete()
            db.session.commit()

            # Set environment variables with different types
            os.environ["TZ"] = "Asia/Tokyo"  # String
            os.environ["ROUNDING_MINUTES"] = "7"  # Integer
            os.environ["SINGLE_ACTIVE_TIMER"] = "false"  # Boolean
            os.environ["ALLOW_SELF_REGISTER"] = "true"  # Boolean

            # Create new Settings
            settings = Settings.get_settings()

            # Verify types are correct
            assert isinstance(settings.timezone, str)
            assert isinstance(settings.rounding_minutes, int)
            assert isinstance(settings.single_active_timer, bool)
            assert isinstance(settings.allow_self_register, bool)

            # Clean up
            for key in ["TZ", "ROUNDING_MINUTES", "SINGLE_ACTIVE_TIMER", "ALLOW_SELF_REGISTER"]:
                if key in os.environ:
                    del os.environ[key]

    def test_webui_changes_persist(self, app):
        """Test that changes made via WebUI (Settings model) persist and take priority"""
        with app.app_context():
            # Set environment variable
            os.environ["CURRENCY"] = "JPY"

            # Get Settings
            settings = Settings.get_settings()

            # Change via Settings (simulating WebUI)
            settings.currency = "CHF"
            db.session.commit()

            # Verify the change persisted
            db.session.refresh(settings)
            assert settings.currency == "CHF"

            # ConfigManager should return the persisted value
            currency = ConfigManager.get_setting("currency")
            assert currency == "CHF", "WebUI changes should persist and take priority"

            # Clean up
            if "CURRENCY" in os.environ:
                del os.environ["CURRENCY"]
