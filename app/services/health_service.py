"""
Service for health check and system status.
"""

from typing import Dict, Any
from flask import current_app
from app import db
from sqlalchemy import text
from datetime import datetime


class HealthService:
    """Service for health check operations"""

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get system health status.

        Returns:
            dict with health information
        """
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": current_app.config.get("APP_VERSION", "unknown"),
            "checks": {},
        }

        # Database check
        try:
            db.session.execute(text("SELECT 1"))
            status["checks"]["database"] = "healthy"
        except Exception as e:
            status["checks"]["database"] = f"unhealthy: {str(e)}"
            status["status"] = "unhealthy"

        # Disk space check (if possible)
        try:
            import shutil

            total, used, free = shutil.disk_usage("/")
            status["checks"]["disk"] = {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "free_percent": round((free / total) * 100, 2),
            }
        except Exception:
            status["checks"]["disk"] = "unavailable"

        return status

    def get_readiness_status(self) -> Dict[str, Any]:
        """
        Get system readiness status (for Kubernetes readiness probe).

        Returns:
            dict with readiness information
        """
        try:
            # Check database connectivity
            db.session.execute(text("SELECT 1"))

            return {"ready": True, "timestamp": datetime.now().isoformat()}
        except Exception:
            return {"ready": False, "timestamp": datetime.now().isoformat(), "error": "Database not available"}
