"""
Configuration module for TimeTracker.

This module contains:
- Flask application configuration (Config, ProductionConfig, etc.)
- Analytics configuration for telemetry
"""

# Import Flask configuration classes from parent config.py
# We need to import from the parent app module to avoid circular imports
import sys
import os

# Import analytics configuration
from app.config.analytics_defaults import get_analytics_config, has_analytics_configured

# Import Flask Config classes from the config.py file in parent directory
# The config.py was shadowed when we created this config/ package
# So we need to import it properly
try:
    # Try to import from a renamed file if it exists
    from app.flask_config import Config, ProductionConfig, DevelopmentConfig, TestingConfig
except ImportError:
    # If the file wasn't renamed, we need to import it differently
    # Add parent to path temporarily to import the shadowed config.py
    import importlib.util

    config_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    if os.path.exists(config_py_path):
        spec = importlib.util.spec_from_file_location("flask_config_module", config_py_path)
        flask_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flask_config)
        Config = flask_config.Config
        ProductionConfig = flask_config.ProductionConfig
        DevelopmentConfig = flask_config.DevelopmentConfig
        TestingConfig = flask_config.TestingConfig
    else:
        # Fallback - create minimal config
        class Config:
            pass

        ProductionConfig = Config
        DevelopmentConfig = Config
        TestingConfig = Config

__all__ = [
    "get_analytics_config",
    "has_analytics_configured",
    "Config",
    "ProductionConfig",
    "DevelopmentConfig",
    "TestingConfig",
]
