"""
Routes for push notification management.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import User
from app.utils.db import safe_commit
import json

push_bp = Blueprint('push', __name__)


@push_bp.route('/api/push/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    """Subscribe user to push notifications."""
    try:
        subscription = request.json
        
        # Store subscription in user model or separate table
        # For now, store in user's settings/preferences
        if not hasattr(current_user, 'push_subscription'):
            # Add push_subscription field to User model if needed
            pass
        
        # Store subscription (could be in a separate PushSubscription model)
        # For simplicity, storing as JSON in user preferences
        user_prefs = getattr(current_user, 'preferences', {}) or {}
        if not isinstance(user_prefs, dict):
            user_prefs = {}
        
        user_prefs['push_subscription'] = subscription
        current_user.preferences = user_prefs
        
        if safe_commit('subscribe_push', {'user_id': current_user.id}):
            return jsonify({'success': True, 'message': 'Subscribed to push notifications'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save subscription'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@push_bp.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def unsubscribe_push():
    """Unsubscribe user from push notifications."""
    try:
        user_prefs = getattr(current_user, 'preferences', {}) or {}
        if isinstance(user_prefs, dict):
            user_prefs.pop('push_subscription', None)
            current_user.preferences = user_prefs
            
            if safe_commit('unsubscribe_push', {'user_id': current_user.id}):
                return jsonify({'success': True, 'message': 'Unsubscribed from push notifications'})
        
        return jsonify({'success': False, 'message': 'No subscription found'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

