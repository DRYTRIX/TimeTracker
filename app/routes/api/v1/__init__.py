"""
API v1 Routes

This module contains the v1 API endpoints.
v1 is the current stable API version.

API Versioning Policy:
- v1: Current stable API (backward compatible)
- Breaking changes require new version (v2, v3, etc.)
- Each version maintains backward compatibility
- Deprecated endpoints are marked but not removed
"""

from flask import Blueprint

# Create v1 blueprint
api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import all v1 endpoints
# Note: The actual endpoints are in api_v1.py for now
# This structure allows for future reorganization

__all__ = ['api_v1_bp']

