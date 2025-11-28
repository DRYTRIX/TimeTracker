"""Common decorators for route handlers"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from flask_babel import gettext as _


def admin_required(f):
    """Decorator to require admin access

    DEPRECATED: Use @admin_or_permission_required() with specific permissions instead.
    This decorator is kept for backward compatibility.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_("Administrator access required"), "error")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)

    return decorated_function

