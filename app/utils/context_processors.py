from flask import g, request, current_app
from flask_babel import get_locale
from flask_login import current_user
from app.models import Settings
from app.utils.timezone import get_timezone_offset_for_timezone

def register_context_processors(app):
    """Register context processors for the application"""
    
    # Register permission helpers for templates
    from app.utils.permissions import init_permission_helpers
    init_permission_helpers(app)
    
    @app.context_processor
    def inject_settings():
        """Inject settings into all templates"""
        try:
            from app import db
            # Check if we have an active database session
            if db.session.is_active:
                settings = Settings.get_settings()
                return {
                    'settings': settings,
                    'currency': settings.currency,
                    'timezone': settings.timezone
                }
        except Exception as e:
            # Log the error but continue with defaults
            print(f"Warning: Could not inject settings: {e}")
            # Rollback the failed transaction
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
            pass
        
        # Return defaults if settings not available
        return {
            'settings': None,
            'currency': 'EUR',
            'timezone': 'Europe/Rome'
        }
    
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates"""
        try:
            from app import db
            # Check if we have an active database session
            if db.session.is_active:
                settings = Settings.get_settings()
                timezone_name = settings.timezone if settings else 'Europe/Rome'
            else:
                timezone_name = 'Europe/Rome'
        except Exception as e:
            # Log the error but continue with defaults
            print(f"Warning: Could not inject globals: {e}")
            # Rollback the failed transaction
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
            timezone_name = 'Europe/Rome'

        # Resolve user-specific timezone, falling back to application timezone
        user_timezone = timezone_name
        try:
            if current_user and getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'timezone', None):
                user_timezone = current_user.timezone
        except Exception:
            pass

        # Determine app version from environment or config
        try:
            import os
            from app.config import Config
            env_version = os.getenv('APP_VERSION')
            # If running in GitHub Actions build, prefer tag-like versions
            version_value = env_version or getattr(Config, 'APP_VERSION', None) or 'dev-0'
            # Strip any leading 'v' prefix to avoid double 'v' in template (e.g., vv3.5.0)
            if version_value and version_value.startswith('v'):
                version_value = version_value[1:]
        except Exception:
            version_value = 'dev-0'
        
        # Current locale code (e.g., 'en', 'de')
        try:
            current_locale = str(get_locale())
        except Exception:
            current_locale = 'en'
        # Normalize to short code for comparisons (e.g., 'en' from 'en_US')
        short_locale = (current_locale.split('_', 1)[0] if current_locale else 'en')
        
        # Reverse-map normalized locale codes back to config keys for label lookup
        # 'nb' (used by Flask-Babel) should map back to 'no' (used in LANGUAGES config)
        display_locale = short_locale
        if short_locale == 'nb':
            display_locale = 'no'
        
        available_languages = current_app.config.get('LANGUAGES', {}) or {}
        current_language_label = available_languages.get(display_locale, short_locale.upper())
        
        # Check if current language is RTL
        rtl_languages = current_app.config.get('RTL_LANGUAGES', set())
        is_rtl = short_locale in rtl_languages

        return {
            'app_name': 'Time Tracker',
            'app_version': version_value,
            'timezone': timezone_name,
            'timezone_offset': get_timezone_offset_for_timezone(timezone_name),
            'user_timezone': user_timezone,
            'current_locale': current_locale,
            'current_language_code': display_locale,  # Use display locale (e.g., 'no' not 'nb')
            'current_language_label': current_language_label,
            'is_rtl': is_rtl,
            'available_languages': available_languages,
            'config': current_app.config
        }
    
    @app.before_request
    def before_request():
        """Set up request-specific data"""
        g.request_start_time = request.start_time if hasattr(request, 'start_time') else None
