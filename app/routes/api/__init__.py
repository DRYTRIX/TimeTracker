"""
API Routes Package

This package contains versioned API routes.
Current structure:
- v1: Current stable API (migrated from api_v1.py)
- Future: v2, v3, etc. for breaking changes

Note: The legacy api_bp is imported from the api.py module file
to maintain backward compatibility.
"""

import importlib.util
import os

# Import versioned blueprints
from app.routes.api.v1 import api_v1_bp

# Import legacy api_bp from the api.py module file
# We need to load it directly since Python prioritizes packages over modules
api_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api.py")

try:
    spec = importlib.util.spec_from_file_location("app.routes.api_legacy", api_module_path)
    if spec and spec.loader:
        api_legacy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_legacy_module)
        api_bp = api_legacy_module.api_bp
        _get_client_id_from_session = api_legacy_module._get_client_id_from_session
    else:
        raise ImportError("Could not load api.py module")
except Exception:
    import logging

    logger = logging.getLogger(__name__)
    logger.exception("Could not import legacy api_bp from app.routes.api.py")
    if os.getenv("ALLOW_DUMMY_LEGACY_API_BLUEPRINT", "").strip().lower() in ("1", "true", "yes"):
        from flask import Blueprint

        api_bp = Blueprint("api", __name__)
        logger.warning("ALLOW_DUMMY_LEGACY_API_BLUEPRINT is set; legacy /api routes are disabled.")
    else:
        raise

__all__ = ["api_v1_bp", "api_bp", "_get_client_id_from_session"]
