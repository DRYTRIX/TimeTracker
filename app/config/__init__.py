"""
Configuration module for TimeTracker.

This module contains:
- Flask application configuration (Config, ProductionConfig, etc.)
- Analytics configuration for telemetry
"""

import os

# Import Flask configuration classes from parent config.py
# We need to import from the parent app module to avoid circular imports
import sys

# Import analytics configuration
from app.config.analytics_defaults import get_analytics_config, has_analytics_configured

# Import Flask Config classes from the config.py file in parent directory
# The config.py was shadowed when we created this config/ package
# So we need to import it properly
try:
    # Try to import from a renamed file if it exists
    from app.flask_config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, normalize_database_url
except ImportError:
    # If the file wasn't renamed, we need to import it differently
    # Add parent to path temporarily to import the shadowed config.py
    import importlib.util

    config_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    if os.path.exists(config_py_path):
        spec = importlib.util.spec_from_file_location("flask_config_module", config_py_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec for {config_py_path}")
        flask_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flask_config)
        Config = flask_config.Config
        ProductionConfig = flask_config.ProductionConfig
        DevelopmentConfig = flask_config.DevelopmentConfig
        TestingConfig = flask_config.TestingConfig
        normalize_database_url = flask_config.normalize_database_url
    else:
        # Fallback - create minimal config
        class Config:  # type: ignore[no-redef]
            pass

        ProductionConfig = Config
        DevelopmentConfig = Config
        TestingConfig = Config

        def normalize_database_url(url):  # type: ignore[misc]
            return url


__all__ = [
    "get_analytics_config",
    "has_analytics_configured",
    "Config",
    "ProductionConfig",
    "DevelopmentConfig",
    "TestingConfig",
    "normalize_database_url",
]
