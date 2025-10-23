"""User profile and settings routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Activity
from app.utils.db import safe_commit
from flask_babel import gettext as _
import pytz

user_bp = Blueprint('user', __name__)


@user_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user statistics
    total_hours = current_user.total_hours
    active_timer = current_user.active_timer
    recent_entries = current_user.get_recent_entries(limit=10)
    
    # Get recent activities
    recent_activities = Activity.get_recent(user_id=current_user.id, limit=20)
    
    return render_template('user/profile.html',
                         user=current_user,
                         total_hours=total_hours,
                         active_timer=active_timer,
                         recent_entries=recent_entries,
                         recent_activities=recent_activities)


@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings and preferences page"""
    if request.method == 'POST':
        try:
            # Notification preferences
            current_user.email_notifications = 'email_notifications' in request.form
            current_user.notification_overdue_invoices = 'notification_overdue_invoices' in request.form
            current_user.notification_task_assigned = 'notification_task_assigned' in request.form
            current_user.notification_task_comments = 'notification_task_comments' in request.form
            current_user.notification_weekly_summary = 'notification_weekly_summary' in request.form
            
            # Profile information
            full_name = request.form.get('full_name', '').strip()
            if full_name:
                current_user.full_name = full_name
            
            email = request.form.get('email', '').strip()
            if email:
                current_user.email = email
            
            # Display preferences
            theme_preference = request.form.get('theme_preference')
            if theme_preference in ['light', 'dark', None, '']:
                current_user.theme_preference = theme_preference if theme_preference else None
            
            # Regional settings
            timezone = request.form.get('timezone')
            if timezone:
                try:
                    # Validate timezone
                    pytz.timezone(timezone)
                    current_user.timezone = timezone
                except pytz.exceptions.UnknownTimeZoneError:
                    flash(_('Invalid timezone selected'), 'error')
                    return redirect(url_for('user.settings'))
            
            date_format = request.form.get('date_format')
            if date_format:
                current_user.date_format = date_format
            
            time_format = request.form.get('time_format')
            if time_format in ['12h', '24h']:
                current_user.time_format = time_format
            
            week_start_day = request.form.get('week_start_day', type=int)
            if week_start_day is not None and 0 <= week_start_day <= 6:
                current_user.week_start_day = week_start_day
            
            # Language preference
            preferred_language = request.form.get('preferred_language')
            if preferred_language:
                current_user.preferred_language = preferred_language
            
            # Save changes
            if safe_commit(db.session):
                # Log activity
                Activity.log(
                    user_id=current_user.id,
                    action='updated',
                    entity_type='user',
                    entity_id=current_user.id,
                    entity_name=current_user.username,
                    description='Updated user settings'
                )
                
                flash(_('Settings saved successfully'), 'success')
            else:
                flash(_('Error saving settings'), 'error')
                
        except Exception as e:
            flash(_('Error saving settings: %(error)s', error=str(e)), 'error')
            db.session.rollback()
        
        return redirect(url_for('user.settings'))
    
    # Get all available timezones
    timezones = sorted(pytz.common_timezones)
    
    # Get available languages from config
    from flask import current_app
    languages = current_app.config.get('LANGUAGES', {
        'en': 'English',
        'nl': 'Nederlands',
        'de': 'Deutsch',
        'fr': 'Français',
        'it': 'Italiano',
        'fi': 'Suomi'
    })
    
    return render_template('user/settings.html',
                         user=current_user,
                         timezones=timezones,
                         languages=languages)


@user_bp.route('/api/preferences', methods=['PATCH'])
@login_required
def update_preferences():
    """API endpoint to update user preferences (for AJAX calls)"""
    try:
        data = request.get_json()
        
        if 'theme_preference' in data:
            theme = data['theme_preference']
            if theme in ['light', 'dark', 'system', None, '']:
                current_user.theme_preference = theme if theme and theme != 'system' else None
        
        if 'email_notifications' in data:
            current_user.email_notifications = bool(data['email_notifications'])
        
        if 'timezone' in data:
            try:
                pytz.timezone(data['timezone'])
                current_user.timezone = data['timezone']
            except pytz.exceptions.UnknownTimeZoneError:
                return jsonify({'error': 'Invalid timezone'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': _('Preferences updated')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@user_bp.route('/api/theme', methods=['POST'])
@login_required
def set_theme():
    """Quick API endpoint to set theme (for theme switcher)"""
    try:
        data = request.get_json()
        theme = data.get('theme')
        
        if theme in ['light', 'dark', None, '']:
            current_user.theme_preference = theme if theme else None
            db.session.commit()
            
            return jsonify({
                'success': True,
                'theme': current_user.theme_preference or 'system'
            })
        
        return jsonify({'error': 'Invalid theme'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

