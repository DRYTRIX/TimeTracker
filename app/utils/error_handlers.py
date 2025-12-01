"""
Enhanced error handling utilities.
Provides consistent error handling across the application.
"""

from typing import Dict, Any, Optional
from flask import jsonify, request, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from app.utils.api_responses import error_response, validation_error_response, handle_validation_error


def register_error_handlers(app):
    """Register error handlers for the Flask app"""

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(
                message=str(error.description) if hasattr(error, "description") else "Bad request",
                error_code="bad_request",
                status_code=400,
            )
        return error, 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(message="Authentication required", error_code="unauthorized", status_code=401)
        return error, 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(message="Insufficient permissions", error_code="forbidden", status_code=403)
        return error, 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(message="Resource not found", error_code="not_found", status_code=404)
        return error, 404

    @app.errorhandler(409)
    def conflict(error):
        """Handle 409 Conflict errors (e.g., duplicate entries)"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(
                message=str(error.description) if hasattr(error, "description") else "Resource conflict",
                error_code="conflict",
                status_code=409,
            )
        return error, 409

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(message="Unprocessable entity", error_code="unprocessable_entity", status_code=422)
        return error, 422

    @app.errorhandler(ValidationError)
    def handle_marshmallow_validation_error(error):
        """Handle Marshmallow validation errors"""
        if request.is_json or request.path.startswith("/api/"):
            return handle_validation_error(error)
        # For HTML forms, flash the error
        from flask import flash

        flash("Validation error: " + str(error.messages), "error")
        return error, 400

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """Handle database integrity errors"""
        current_app.logger.error(f"Integrity error: {error}")

        if request.is_json or request.path.startswith("/api/"):
            # Try to extract meaningful error message
            error_msg = "Database integrity error"
            if "UNIQUE constraint" in str(error.orig):
                error_msg = "Duplicate entry - this record already exists"
            elif "FOREIGN KEY constraint" in str(error.orig):
                error_msg = "Referenced record does not exist"

            return error_response(message=error_msg, error_code="integrity_error", status_code=409)

        from flask import flash

        flash("Database error occurred", "error")
        return error, 409

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        """Handle SQLAlchemy errors"""
        current_app.logger.error(f"SQLAlchemy error: {error}")

        if request.is_json or request.path.startswith("/api/"):
            return error_response(message="Database error occurred", error_code="database_error", status_code=500)

        from flask import flash, render_template

        flash("Database error occurred", "error")
        return (
            render_template(
                "errors/500.html",
                error_info={
                    "title": "Database Error",
                    "message": "A database error occurred. Please contact support if this persists.",
                },
            ),
            500,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions"""
        if request.is_json or request.path.startswith("/api/"):
            return error_response(
                message=error.description or "An error occurred", error_code=error.code, status_code=error.code
            )
        from flask import render_template

        return (
            render_template(
                "errors/generic.html",
                error=error,
                error_info={"title": error.name, "message": error.description or "An error occurred"},
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle all other exceptions"""
        current_app.logger.exception(f"Unhandled exception: {error}")

        if request.is_json or request.path.startswith("/api/"):
            # Don't expose internal error details in production
            if current_app.config.get("FLASK_DEBUG"):
                return error_response(
                    message=str(error),
                    error_code="internal_error",
                    status_code=500,
                    details={"type": type(error).__name__},
                )
            else:
                return error_response(
                    message="An internal error occurred", error_code="internal_error", status_code=500
                )

        from flask import render_template, flash

        flash("An error occurred. Please try again.", "error")
        return (
            render_template(
                "errors/500.html",
                error_info={
                    "title": "Server Error",
                    "message": "Something went wrong on our end. Please try again later.",
                },
            ),
            500,
        )


def create_error_response(
    message: str, error_code: str = "error", status_code: int = 400, details: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response.

    Args:
        message: Error message
        error_code: Error code
        status_code: HTTP status code
        details: Optional additional details

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {"success": False, "error": error_code, "message": message}

    if details:
        response["details"] = details

    return response, status_code
