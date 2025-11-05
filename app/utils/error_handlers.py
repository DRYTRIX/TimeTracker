from flask import render_template, request, jsonify
from werkzeug.exceptions import HTTPException
import traceback

def get_user_friendly_message(status_code, error_description=None):
    """Get user-friendly error messages"""
    messages = {
        400: {
            'title': 'Invalid Request',
            'message': 'The request was invalid. Please check your input and try again.',
            'recovery': ['Go to Dashboard', 'Go Back']
        },
        401: {
            'title': 'Authentication Required',
            'message': 'You need to log in to access this feature.',
            'recovery': ['Go to Login']
        },
        403: {
            'title': 'Access Denied',
            'message': 'You don\'t have permission to perform this action.',
            'recovery': ['Go to Dashboard', 'Go Back']
        },
        404: {
            'title': 'Page Not Found',
            'message': 'The page or resource you\'re looking for doesn\'t exist.',
            'recovery': ['Go to Dashboard', 'Go Back']
        },
        409: {
            'title': 'Conflict',
            'message': 'This action conflicts with existing data. Please refresh and try again.',
            'recovery': ['Refresh Page', 'Go Back']
        },
        422: {
            'title': 'Validation Error',
            'message': 'Please check your input and try again.',
            'recovery': ['Go Back']
        },
        429: {
            'title': 'Too Many Requests',
            'message': 'You\'ve made too many requests. Please wait a moment and try again.',
            'recovery': ['Refresh Page']
        },
        500: {
            'title': 'Server Error',
            'message': 'A server error occurred. Our team has been notified. Please try again later.',
            'recovery': ['Refresh Page', 'Go to Dashboard']
        },
        502: {
            'title': 'Service Unavailable',
            'message': 'The server is temporarily unavailable. Please try again later.',
            'recovery': ['Refresh Page']
        },
        503: {
            'title': 'Service Unavailable',
            'message': 'Service temporarily unavailable. Please try again in a few moments.',
            'recovery': ['Refresh Page']
        },
        504: {
            'title': 'Request Timeout',
            'message': 'The request took too long. Please try again.',
            'recovery': ['Refresh Page', 'Go Back']
        }
    }
    
    if status_code in messages:
        msg = messages[status_code].copy()
        if error_description:
            msg['message'] = f"{msg['message']} ({error_description})"
        return msg
    
    return {
        'title': 'Error',
        'message': error_description or 'An error occurred. Please try again.',
        'recovery': ['Go to Dashboard', 'Go Back']
    }

def register_error_handlers(app):
    """Register error handlers for the application"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(404)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), 404
        error_info = get_user_friendly_message(404)
        return render_template('errors/404.html', error_info=error_info), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(500)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), 500
        error_info = get_user_friendly_message(500)
        return render_template('errors/500.html', error_info=error_info), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(403)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), 403
        error_info = get_user_friendly_message(403)
        return render_template('errors/403.html', error_info=error_info), 403
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(400)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), 400
        error_info = get_user_friendly_message(400)
        return render_template('errors/400.html', error_info=error_info), 400
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(error.code, error.description)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), error.code
        error_info = get_user_friendly_message(error.code, error.description)
        return render_template('errors/generic.html', error=error, error_info=error_info), error.code
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Log the error
        app.logger.error(f'Unhandled exception: {error}')
        app.logger.error(traceback.format_exc())
        
        if request.path.startswith('/api/'):
            error_info = get_user_friendly_message(500)
            return jsonify({
                'error': error_info['message'],
                'title': error_info['title'],
                'recovery': error_info['recovery']
            }), 500
        error_info = get_user_friendly_message(500)
        return render_template('errors/500.html', error_info=error_info), 500
