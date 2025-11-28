"""
Route helper utilities for standardizing error handling and responses.
"""

from functools import wraps
from typing import Callable, Any, Optional
from flask import request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.api_responses import (
    error_response,
    success_response,
    not_found_response,
    unauthorized_response,
    forbidden_response,
)


def handle_service_result(
    result: dict,
    success_redirect: Optional[str] = None,
    success_message: Optional[str] = None,
    error_redirect: Optional[str] = None,
    json_response: bool = False,
):
    """
    Handle service layer result and return appropriate response.

    Args:
        result: Service result dict with 'success', 'message', etc.
        success_redirect: URL to redirect to on success (for HTML forms)
        success_message: Custom success message (overrides service message)
        error_redirect: URL to redirect to on error (for HTML forms)
        json_response: If True, return JSON response; if False, use flash messages

    Returns:
        Flask response (redirect or JSON)
    """
    if result.get("success"):
        message = success_message or result.get("message", "Operation successful")

        if json_response:
            return success_response(
                data=result.get("data") or result.get("invoice") or result.get("project") or result.get("task"),
                message=message,
            )
        else:
            flash(message, "success")
            if success_redirect:
                return redirect(success_redirect)
            return redirect(url_for("main.dashboard"))
    else:
        message = result.get("message", "An error occurred")
        error_code = result.get("error", "error")

        if json_response:
            status_code = 400
            if error_code == "not_found":
                status_code = 404
            elif error_code == "permission_denied":
                status_code = 403

            return error_response(message=message, error_code=error_code, status_code=status_code)
        else:
            flash(message, "error")
            if error_redirect:
                return redirect(error_redirect)
            return redirect(request.referrer or url_for("main.dashboard"))


def json_api(f: Callable) -> Callable:
    """
    Decorator to ensure route returns JSON API responses.
    Automatically handles service results and converts to JSON.

    Usage:
        @json_api
        @route('/api/projects', methods=['POST'])
        def create_project():
            service = ProjectService()
            result = service.create_project(...)
            return handle_service_result(result, json_response=True)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Set JSON response flag
        request.is_json_api = True
        return f(*args, **kwargs)

    return decorated_function


def require_admin_or_owner(owner_id_getter: Callable[[Any], int]):
    """
    Decorator to require admin or ownership of resource.

    Args:
        owner_id_getter: Function that extracts owner ID from route args/kwargs

    Usage:
        @require_admin_or_owner(lambda **kwargs: kwargs['project_id'])
        def view_project(project_id):
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json or request.path.startswith("/api/"):
                    return unauthorized_response()
                flash("Please log in to access this page", "error")
                return redirect(url_for("auth.login"))

            owner_id = owner_id_getter(*args, **kwargs)

            if not current_user.is_admin and current_user.id != owner_id:
                if request.is_json or request.path.startswith("/api/"):
                    return forbidden_response("You do not have permission to access this resource")
                flash("You do not have permission to access this resource", "error")
                return redirect(url_for("main.dashboard"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator
