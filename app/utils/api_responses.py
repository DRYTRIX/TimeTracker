"""
Consistent API response helpers.
Provides standardized response formats for all API endpoints.
"""

from typing import Any, Dict, Optional, List
from flask import jsonify, Response
from marshmallow import ValidationError


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create a successful API response.
    
    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code
        meta: Optional metadata
        
    Returns:
        Flask JSON response
    """
    response = {
        'success': True,
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    if meta:
        response['meta'] = meta
    
    return jsonify(response), status_code


def error_response(
    message: str,
    error_code: Optional[str] = None,
    status_code: int = 400,
    errors: Optional[Dict[str, List[str]]] = None,
    details: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create an error API response.
    
    Args:
        message: Error message
        error_code: Optional error code
        status_code: HTTP status code
        errors: Optional field-specific errors
        details: Optional additional error details
        
    Returns:
        Flask JSON response
    """
    response = {
        'success': False,
        'error': error_code or 'error',
        'message': message
    }
    
    if errors:
        response['errors'] = errors
    
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def validation_error_response(
    errors: Dict[str, List[str]],
    message: str = "Validation failed"
) -> Response:
    """
    Create a validation error response.
    
    Args:
        errors: Field-specific validation errors
        message: Error message
        
    Returns:
        Flask JSON response
    """
    return error_response(
        message=message,
        error_code='validation_error',
        status_code=400,
        errors=errors
    )


def not_found_response(
    resource: str = "Resource",
    resource_id: Optional[Any] = None
) -> Response:
    """
    Create a not found error response.
    
    Args:
        resource: Resource type name
        resource_id: Optional resource ID
        
    Returns:
        Flask JSON response
    """
    message = f"{resource} not found"
    if resource_id is not None:
        message = f"{resource} with ID {resource_id} not found"
    
    return error_response(
        message=message,
        error_code='not_found',
        status_code=404
    )


def unauthorized_response(message: str = "Authentication required") -> Response:
    """
    Create an unauthorized error response.
    
    Args:
        message: Error message
        
    Returns:
        Flask JSON response
    """
    return error_response(
        message=message,
        error_code='unauthorized',
        status_code=401
    )


def forbidden_response(message: str = "Insufficient permissions") -> Response:
    """
    Create a forbidden error response.
    
    Args:
        message: Error message
        
    Returns:
        Flask JSON response
    """
    return error_response(
        message=message,
        error_code='forbidden',
        status_code=403
    )


def paginated_response(
    items: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: Optional[str] = None
) -> Response:
    """
    Create a paginated response.
    
    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total number of items
        message: Optional message
        
    Returns:
        Flask JSON response
    """
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_next': page < pages,
        'has_prev': page > 1,
        'next_page': page + 1 if page < pages else None,
        'prev_page': page - 1 if page > 1 else None
    }
    
    return success_response(
        data=items,
        message=message,
        meta={'pagination': pagination}
    )


def handle_validation_error(error: ValidationError) -> Response:
    """
    Handle Marshmallow validation errors.
    
    Args:
        error: ValidationError instance
        
    Returns:
        Flask JSON response
    """
    errors = {}
    if isinstance(error.messages, dict):
        errors = error.messages
    elif isinstance(error.messages, list):
        errors = {'_general': error.messages}
    
    return validation_error_response(errors=errors)


def created_response(
    data: Any,
    message: Optional[str] = None,
    location: Optional[str] = None
) -> Response:
    """
    Create a 201 Created response.
    
    Args:
        data: Created resource data
        message: Optional success message
        location: Optional resource location URL
        
    Returns:
        Flask JSON response
    """
    response_data = {'data': data}
    if message:
        response_data['message'] = message
    
    response = jsonify(response_data)
    response.status_code = 201
    
    if location:
        response.headers['Location'] = location
    
    return response


def no_content_response() -> Response:
    """
    Create a 204 No Content response.
    
    Returns:
        Flask response
    """
    return '', 204

