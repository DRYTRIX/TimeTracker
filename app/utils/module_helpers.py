"""
Module Helper Utilities

Provides decorators and helper functions for checking module availability
and protecting routes based on module flags.
"""
from functools import wraps
from flask import abort, redirect, url_for, flash, current_app
from flask_login import current_user
from flask_babel import gettext as _
from app.models import Settings
from app.utils.module_registry import ModuleRegistry


def module_enabled(module_id: str, redirect_to: str = None):
    """
    Decorator to require a module to be enabled for a route.
    
    Args:
        module_id: The module ID to check
        redirect_to: Optional route name to redirect to if module is disabled
    
    Usage:
        @module_enabled("calendar")
        def view_calendar():
            return render_template("calendar/view.html")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if redirect_to:
                    return redirect(url_for(redirect_to))
                abort(403)
            
            settings = Settings.get_settings()
            if not ModuleRegistry.is_enabled(module_id, settings, current_user):
                if current_user.is_admin:
                    module = ModuleRegistry.get(module_id)
                    module_name = module.name if module else module_id
                    flash(
                        _("Module '%(module)s' is disabled. Enable it in Settings.", module=module_name),
                        "warning"
                    )
                    if redirect_to:
                        return redirect(url_for(redirect_to))
                    return redirect(url_for('admin.settings'))
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_module_enabled(module_id: str) -> bool:
    """
    Check if a module is enabled for the current user.
    
    Args:
        module_id: The module ID to check
    
    Returns:
        True if module is enabled, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    try:
        settings = Settings.get_settings()
        return ModuleRegistry.is_enabled(module_id, settings, current_user)
    except Exception:
        # If we can't check, default to False for safety
        return False


def get_enabled_modules(category=None):
    """
    Get all enabled modules, optionally filtered by category.
    
    Args:
        category: Optional ModuleCategory to filter by
    
    Returns:
        List of enabled ModuleDefinition objects
    """
    if not current_user.is_authenticated:
        return []
    
    try:
        settings = Settings.get_settings()
        modules = ModuleRegistry.get_enabled_modules(settings, current_user)
        
        if category:
            from app.utils.module_registry import ModuleCategory
            if isinstance(category, str):
                try:
                    category = ModuleCategory(category)
                except ValueError:
                    return []
            modules = [m for m in modules if m.category == category]
        
        return modules
    except Exception:
        return []


def init_module_helpers(app):
    """
    Initialize module helper functions for use in templates and routes.
    
    This should be called during app initialization.
    """
    # Initialize module registry
    ModuleRegistry.initialize_defaults()
    
    @app.context_processor
    def inject_module_helpers():
        """Make module helpers available in templates"""
        from app.utils.module_registry import ModuleCategory
        return {
            "is_module_enabled": is_module_enabled,
            "get_enabled_modules": get_enabled_modules,
            "get_modules_by_category": lambda cat: ModuleRegistry.get_by_category(cat),
            "ModuleCategory": ModuleCategory,
        }
    
    # Also make it available as a global function
    app.jinja_env.globals['is_module_enabled'] = is_module_enabled
    app.jinja_env.globals['get_enabled_modules'] = get_enabled_modules

