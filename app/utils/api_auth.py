"""API Token Authentication utilities for REST API"""
from functools import wraps
from flask import request, jsonify, g, current_app
from app.models import ApiToken, User
from app import db


def extract_token_from_request():
    """Extract API token from request headers
    
    Supports multiple formats:
    - Authorization: Bearer <token>
    - Authorization: Token <token>
    - X-API-Key: <token>
    
    Returns:
        str or None: The token if found
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2:
            scheme = parts[0].lower()
            if scheme in ('bearer', 'token'):
                return parts[1]
    
    # Check X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    return None


def authenticate_token(token_string):
    """Authenticate an API token and return the associated user
    
    Args:
        token_string: The plain token string
    
    Returns:
        tuple: (User, ApiToken) if valid, (None, None) otherwise
    """
    if not token_string or not token_string.startswith('tt_'):
        return None, None
    
    # Get token hash
    token_hash = ApiToken.hash_token(token_string)
    
    # Find token in database
    api_token = ApiToken.query.filter_by(token_hash=token_hash).first()
    
    if not api_token:
        return None, None
    
    # Check if token is valid
    if not api_token.is_valid():
        return None, None
    
    # Get associated user
    user = User.query.get(api_token.user_id)
    if not user or not user.is_active:
        return None, None
    
    # Record usage
    try:
        api_token.record_usage(request.remote_addr)
    except Exception as e:
        current_app.logger.warning(f"Failed to record API token usage: {e}")
    
    return user, api_token


def require_api_token(required_scope=None):
    """Decorator to require API token authentication
    
    Args:
        required_scope: Optional scope required for this endpoint (e.g., 'read:projects')
    
    Usage:
        @require_api_token('read:projects')
        def get_projects():
            # Access authenticated user via g.api_user
            # Access token via g.api_token
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract token from request
            token_string = extract_token_from_request()
            
            if not token_string:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'API token must be provided in Authorization header or X-API-Key header'
                }), 401
            
            # Authenticate token
            user, api_token = authenticate_token(token_string)
            
            if not user or not api_token:
                return jsonify({
                    'error': 'Invalid token',
                    'message': 'The provided API token is invalid or expired'
                }), 401
            
            # Check scope if required
            if required_scope and not api_token.has_scope(required_scope):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires the "{required_scope}" scope',
                    'required_scope': required_scope,
                    'available_scopes': api_token.scopes.split(',') if api_token.scopes else []
                }), 403
            
            # Store in request context
            g.api_user = user
            g.api_token = api_token
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def optional_api_token():
    """Decorator that allows both session-based and token-based authentication
    
    Useful for endpoints that can be accessed via web UI or API
    
    Usage:
        @optional_api_token()
        @login_required  # Will be satisfied by API token if present
        def get_data():
            # Access user via current_user (session) or g.api_user (token)
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Try to extract and authenticate token
            token_string = extract_token_from_request()
            
            if token_string:
                user, api_token = authenticate_token(token_string)
                if user and api_token:
                    g.api_user = user
                    g.api_token = api_token
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

