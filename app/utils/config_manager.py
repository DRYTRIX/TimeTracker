"""
Configuration management utilities.
"""

from typing import Any, Dict, Optional
from flask import current_app
import os
from app.models import Settings


class ConfigManager:
    """Utility for managing application configuration"""

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Checks in order:
        1. Settings model (WebUI changes have highest priority)
        2. Environment variable (.env file - used as initial values)
        3. App config
        4. Default value

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        # Check Settings model first (WebUI changes have highest priority)
        try:
            settings = Settings.get_settings()
            if settings and hasattr(settings, key):
                value = getattr(settings, key)
                if value is not None:
                    return value
        except Exception:
            pass

        # Check environment variable second (.env file - used as initial values)
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return env_value

        # Check app config
        if current_app:
            value = current_app.config.get(key, default)
            if value is not None:
                return value

        return default

    @staticmethod
    def set_setting(key: str, value: Any) -> bool:
        """
        Set a setting value in the Settings model.

        Args:
            key: Setting key
            value: Setting value

        Returns:
            True if successful
        """
        try:
            settings = Settings.get_settings()
            if settings and hasattr(settings, key):
                setattr(settings, key, value)
                from app import db

                db.session.commit()
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def validate_config() -> Dict[str, Any]:
        """
        Validate application configuration.

        Returns:
            dict with validation results
        """
        errors = []
        warnings = []

        # Check required settings
        required_settings = ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
        for setting in required_settings:
            value = ConfigManager.get_setting(setting)
            if not value:
                errors.append(f"Missing required setting: {setting}")

        # Check secret key strength
        secret_key = ConfigManager.get_setting("SECRET_KEY")
        if secret_key and len(secret_key) < 32:
            warnings.append("SECRET_KEY is too short (should be at least 32 characters)")

        # Check database URL
        db_url = ConfigManager.get_setting("SQLALCHEMY_DATABASE_URI")
        if db_url and "dev-secret-key" in str(db_url):
            warnings.append("Using default database configuration")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
