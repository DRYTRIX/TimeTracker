"""
API Routes Package

This package contains versioned API routes.
Current structure:
- v1: Current stable API (migrated from api_v1.py)
- Future: v2, v3, etc. for breaking changes

Note: The legacy api_bp is imported from the api.py module file
to maintain backward compatibility.
"""

import os
import importlib.util

# Import versioned blueprints
from app.routes.api.v1 import api_v1_bp

# Import legacy api_bp from the api.py module file
# We need to load it directly since Python prioritizes packages over modules
api_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api.py')

try:
    spec = importlib.util.spec_from_file_location("app.routes.api_legacy", api_module_path)
    if spec and spec.loader:
        api_legacy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_legacy_module)
        api_bp = api_legacy_module.api_bp
    else:
        raise ImportError("Could not load api.py module")
except Exception as e:
    # Last resort: create a dummy blueprint to prevent import errors
    from flask import Blueprint
    api_bp = Blueprint('api', __name__)
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import api_bp from api.py: {e}. Using dummy blueprint.")

__all__ = ['api_v1_bp', 'api_bp']

