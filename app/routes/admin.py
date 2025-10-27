from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, send_file, jsonify, render_template_string
from flask_babel import gettext as _
from flask_login import login_required, current_user
import app as app_module
from app import db, limiter
from app.models import User, Project, TimeEntry, Settings, Invoice
from datetime import datetime
from sqlalchemy import text
import os
from werkzeug.utils import secure_filename
import uuid
from app.utils.db import safe_commit
from app.utils.backup import create_backup, restore_backup
from app.utils.installation import get_installation_config
from app.utils.telemetry import get_telemetry_fingerprint, is_telemetry_enabled
from app.utils.permissions import admin_or_permission_required
import threading
import time
import shutil

admin_bp = Blueprint('admin', __name__)

# In-memory restore progress tracking (simple, per-process)
RESTORE_PROGRESS = {}

# Allowed file extensions for logos
# Avoid SVG due to XSS risk unless sanitized server-side
ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def admin_required(f):
    """Decorator to require admin access
    
    DEPRECATED: Use @admin_or_permission_required() with specific permissions instead.
    This decorator is kept for backward compatibility.
    """
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_('Administrator access required'), 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_logo_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS

def get_upload_folder():
    """Get the upload folder path for logos"""
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    from app.config import Config
    
    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status='active').count()
    total_entries = TimeEntry.query.filter(TimeEntry.end_time.isnot(None)).count()
    active_timers = TimeEntry.query.filter_by(end_time=None).count()
    
    # Get recent activity
    recent_entries = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None)
    ).order_by(
        TimeEntry.created_at.desc()
    ).limit(10).all()
    
    # Get OIDC status
    auth_method = (getattr(Config, 'AUTH_METHOD', 'local') or 'local').strip().lower()
    oidc_enabled = auth_method in ('oidc', 'both')
    oidc_issuer = getattr(Config, 'OIDC_ISSUER', None)
    oidc_configured = oidc_enabled and oidc_issuer and getattr(Config, 'OIDC_CLIENT_ID', None) and getattr(Config, 'OIDC_CLIENT_SECRET', None)
    
    # Count OIDC users
    oidc_users_count = 0
    try:
        oidc_users_count = User.query.filter(
            User.oidc_issuer.isnot(None),
            User.oidc_sub.isnot(None)
        ).count()
    except Exception:
        pass
    
    # Build stats object expected by the template
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_entries': total_entries,
        'total_hours': TimeEntry.get_total_hours_for_period(),
        'billable_hours': TimeEntry.get_total_hours_for_period(billable_only=True),
        'last_backup': None
    }
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        active_timers=active_timers,
        recent_entries=recent_entries,
        oidc_enabled=oidc_enabled,
        oidc_configured=oidc_configured,
        oidc_auth_method=auth_method,
        oidc_users_count=oidc_users_count
    )

# Compatibility alias for code/templates that might reference 'admin.dashboard'
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard_alias():
    """Alias endpoint so url_for('admin.dashboard') remains valid.

    Some older references may use the endpoint name 'admin.dashboard'.
    Redirect to the canonical admin dashboard endpoint.
    """
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/users')
@login_required
@admin_or_permission_required('view_users')
def list_users():
    """List all users"""
    users = User.query.order_by(User.username).all()
    
    # Build stats for users page
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'admin_users': User.query.filter_by(role='admin').count(),
        'total_hours': TimeEntry.get_total_hours_for_period()
    }
    
    return render_template('admin/users.html', users=users, stats=stats)

@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('create_users')
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        role = request.form.get('role', 'user')
        
        if not username:
            flash('Username is required', 'error')
            return render_template('admin/user_form.html', user=None)
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('User already exists', 'error')
            return render_template('admin/user_form.html', user=None)
        
        # Create user
        user = User(username=username, role=role)
        db.session.add(user)
        if not safe_commit('admin_create_user', {'username': username}):
            flash('Could not create user due to a database error. Please check server logs.', 'error')
            return render_template('admin/user_form.html', user=None)
        
        flash(f'User "{username}" created successfully', 'success')
        return redirect(url_for('admin.list_users'))
    
    return render_template('admin/user_form.html', user=None)

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('edit_users')
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        role = request.form.get('role', 'user')
        is_active = request.form.get('is_active') == 'on'
        
        if not username:
            flash('Username is required', 'error')
            return render_template('admin/user_form.html', user=user)
        
        # Check if username is already taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already exists', 'error')
            return render_template('admin/user_form.html', user=user)
        
        # Update user
        user.username = username
        user.role = role
        user.is_active = is_active
        if not safe_commit('admin_edit_user', {'user_id': user.id}):
            flash('Could not update user due to a database error. Please check server logs.', 'error')
            return render_template('admin/user_form.html', user=user)
        
        flash(f'User "{username}" updated successfully', 'success')
        return redirect(url_for('admin.list_users'))
    
    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_or_permission_required('delete_users')
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Don't allow deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(role='admin', is_active=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last administrator', 'error')
            return redirect(url_for('admin.list_users'))
    
    # Don't allow deleting users with time entries
    if user.time_entries.count() > 0:
        flash('Cannot delete user with existing time entries', 'error')
        return redirect(url_for('admin.list_users'))
    
    username = user.username
    db.session.delete(user)
    if not safe_commit('admin_delete_user', {'user_id': user.id}):
        flash('Could not delete user due to a database error. Please check server logs.', 'error')
        return redirect(url_for('admin.list_users'))
    
    flash(f'User "{username}" deleted successfully', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/admin/telemetry')
@login_required
@admin_or_permission_required('manage_telemetry')
def telemetry_dashboard():
    """Telemetry and analytics dashboard"""
    installation_config = get_installation_config()
    
    # Get telemetry status
    telemetry_data = {
        'enabled': is_telemetry_enabled(),
        'setup_complete': installation_config.is_setup_complete(),
        'installation_id': installation_config.get_installation_id(),
        'telemetry_salt': installation_config.get_installation_salt()[:16] + '...',  # Show partial salt
        'fingerprint': get_telemetry_fingerprint(),
        'config': installation_config.get_all_config()
    }
    
    # Get PostHog status
    posthog_data = {
        'enabled': bool(os.getenv('POSTHOG_API_KEY')),
        'host': os.getenv('POSTHOG_HOST', 'https://app.posthog.com'),
        'api_key_set': bool(os.getenv('POSTHOG_API_KEY'))
    }
    
    # Get Sentry status
    sentry_data = {
        'enabled': bool(os.getenv('SENTRY_DSN')),
        'dsn_set': bool(os.getenv('SENTRY_DSN')),
        'traces_rate': os.getenv('SENTRY_TRACES_RATE', '0.0')
    }
    
    # Log dashboard access
    app_module.log_event("admin.telemetry_dashboard_viewed", user_id=current_user.id)
    app_module.track_event(current_user.id, "admin.telemetry_dashboard_viewed", {})
    
    return render_template('admin/telemetry.html',
                         telemetry=telemetry_data,
                         posthog=posthog_data,
                         sentry=sentry_data)


@admin_bp.route('/admin/telemetry/toggle', methods=['POST'])
@login_required
@admin_or_permission_required('manage_telemetry')
def toggle_telemetry():
    """Toggle telemetry on/off"""
    installation_config = get_installation_config()
    current_state = installation_config.get_telemetry_preference()
    new_state = not current_state
    
    installation_config.set_telemetry_preference(new_state)
    
    # Log the change
    app_module.log_event("admin.telemetry_toggled", user_id=current_user.id, new_state=new_state)
    app_module.track_event(current_user.id, "admin.telemetry_toggled", {"enabled": new_state})
    
    if new_state:
        flash('Telemetry has been enabled. Thank you for helping us improve!', 'success')
    else:
        flash('Telemetry has been disabled.', 'info')
    
    return redirect(url_for('admin.telemetry_dashboard'))


@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('manage_settings')
def settings():
    """Manage system settings"""
    settings_obj = Settings.get_settings()
    installation_config = get_installation_config()
    
    # Sync analytics preference from installation config to database on load
    # (installation config is the source of truth for telemetry)
    if settings_obj.allow_analytics != installation_config.get_telemetry_preference():
        settings_obj.allow_analytics = installation_config.get_telemetry_preference()
        db.session.commit()
    
    if request.method == 'POST':
        # Validate timezone
        timezone = request.form.get('timezone', 'Europe/Rome')
        try:
            import pytz
            pytz.timezone(timezone)  # This will raise an exception if timezone is invalid
        except pytz.exceptions.UnknownTimeZoneError:
            flash(f'Invalid timezone: {timezone}', 'error')
            return render_template('admin/settings.html', settings=settings_obj)
        
        # Update basic settings
        settings_obj.timezone = timezone
        settings_obj.currency = request.form.get('currency', 'EUR')
        settings_obj.rounding_minutes = int(request.form.get('rounding_minutes', 1))
        settings_obj.single_active_timer = request.form.get('single_active_timer') == 'on'
        settings_obj.allow_self_register = request.form.get('allow_self_register') == 'on'
        settings_obj.idle_timeout_minutes = int(request.form.get('idle_timeout_minutes', 30))
        settings_obj.backup_retention_days = int(request.form.get('backup_retention_days', 30))
        settings_obj.backup_time = request.form.get('backup_time', '02:00')
        settings_obj.export_delimiter = request.form.get('export_delimiter', ',')
        
        # Update company branding settings
        settings_obj.company_name = request.form.get('company_name', 'Your Company Name')
        settings_obj.company_address = request.form.get('company_address', 'Your Company Address')
        settings_obj.company_email = request.form.get('company_email', 'info@yourcompany.com')
        settings_obj.company_phone = request.form.get('company_phone', '+1 (555) 123-4567')
        settings_obj.company_website = request.form.get('company_website', 'www.yourcompany.com')
        settings_obj.company_tax_id = request.form.get('company_tax_id', '')
        settings_obj.company_bank_info = request.form.get('company_bank_info', '')
        
        # Update invoice defaults
        settings_obj.invoice_prefix = request.form.get('invoice_prefix', 'INV')
        settings_obj.invoice_start_number = int(request.form.get('invoice_start_number', 1000))
        settings_obj.invoice_terms = request.form.get('invoice_terms', 'Payment is due within 30 days of invoice date.')
        settings_obj.invoice_notes = request.form.get('invoice_notes', 'Thank you for your business!')
        
        # Update privacy and analytics settings
        allow_analytics = request.form.get('allow_analytics') == 'on'
        old_analytics_state = settings_obj.allow_analytics
        settings_obj.allow_analytics = allow_analytics
        
        # Also update the installation config (used by telemetry system)
        # This ensures the telemetry system sees the updated preference
        installation_config.set_telemetry_preference(allow_analytics)
        
        # Log analytics preference change if it changed
        if old_analytics_state != allow_analytics:
            app_module.log_event("admin.analytics_toggled", user_id=current_user.id, new_state=allow_analytics)
            app_module.track_event(current_user.id, "admin.analytics_toggled", {"enabled": allow_analytics})
        
        if not safe_commit('admin_update_settings'):
            flash('Could not update settings due to a database error. Please check server logs.', 'error')
            return render_template('admin/settings.html', settings=settings_obj)
        flash('Settings updated successfully', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', settings=settings_obj)


@admin_bp.route('/admin/pdf-layout', methods=['GET', 'POST'])
@limiter.limit("30 per minute", methods=["POST"])  # editor saves
@login_required
@admin_or_permission_required('manage_settings')
def pdf_layout():
    """Edit PDF invoice layout template (HTML and CSS)."""
    settings_obj = Settings.get_settings()
    if request.method == 'POST':
        html_template = request.form.get('invoice_pdf_template_html', '')
        css_template = request.form.get('invoice_pdf_template_css', '')
        settings_obj.invoice_pdf_template_html = html_template
        settings_obj.invoice_pdf_template_css = css_template
        if not safe_commit('admin_update_pdf_layout'):
            from flask_babel import gettext as _
            flash(_('Could not update PDF layout due to a database error.'), 'error')
        else:
            from flask_babel import gettext as _
            flash(_('PDF layout updated successfully'), 'success')
        return redirect(url_for('admin.pdf_layout'))
    # Provide initial defaults to the template if no custom HTML/CSS saved
    initial_html = settings_obj.invoice_pdf_template_html or ''
    initial_css = settings_obj.invoice_pdf_template_css or ''
    try:
        if not initial_html:
            env = current_app.jinja_env
            html_src, _, _ = env.loader.get_source(env, 'invoices/pdf_default.html')
            # Extract body only for editor
            try:
                import re as _re
                m = _re.search(r'<body[^>]*>([\s\S]*?)</body>', html_src, _re.IGNORECASE)
                initial_html = (m.group(1).strip() if m else html_src)
            except Exception:
                pass
        if not initial_css:
            env = current_app.jinja_env
            css_src, _, _ = env.loader.get_source(env, 'invoices/pdf_styles_default.css')
            initial_css = css_src
    except Exception:
        pass
    return render_template('admin/pdf_layout.html', settings=settings_obj, initial_html=initial_html, initial_css=initial_css)


@admin_bp.route('/admin/pdf-layout/reset', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required('manage_settings')
def pdf_layout_reset():
    """Reset PDF layout to defaults (clear custom templates)."""
    settings_obj = Settings.get_settings()
    settings_obj.invoice_pdf_template_html = ''
    settings_obj.invoice_pdf_template_css = ''
    if not safe_commit('admin_reset_pdf_layout'):
        flash(_('Could not reset PDF layout due to a database error.'), 'error')
    else:
        flash(_('PDF layout reset to defaults'), 'success')
    return redirect(url_for('admin.pdf_layout'))


@admin_bp.route('/admin/pdf-layout/default', methods=['GET'])
@login_required
@admin_or_permission_required('manage_settings')
def pdf_layout_default():
    """Return default HTML and CSS template sources for the PDF layout editor."""
    try:
        env = current_app.jinja_env
        # Get raw template sources, not rendered
        html_src, _, _ = env.loader.get_source(env, 'invoices/pdf_default.html')
        # Extract only the body content for GrapesJS
        try:
            import re as _re
            match = _re.search(r'<body[^>]*>([\s\S]*?)</body>', html_src, _re.IGNORECASE)
            if match:
                html_src = match.group(1).strip()
        except Exception:
            pass
    except Exception:
        html_src = '<div class="wrapper"><h1>{{ _(\'INVOICE\') }} {{ invoice.invoice_number }}</h1></div>'
    try:
        css_src, _, _ = env.loader.get_source(env, 'invoices/pdf_styles_default.css')
    except Exception:
        css_src = ''
    return jsonify({
        'html': html_src,
        'css': css_src,
    })


@admin_bp.route('/admin/pdf-layout/preview', methods=['POST'])
@limiter.limit("60 per minute")
@login_required
@admin_or_permission_required('manage_settings')
def pdf_layout_preview():
    """Render a live preview of the provided HTML/CSS using an invoice context."""
    html = request.form.get('html', '')
    css = request.form.get('css', '')
    invoice_id = request.form.get('invoice_id', type=int)
    invoice = None
    if invoice_id:
        invoice = Invoice.query.get(invoice_id)
    if invoice is None:
        invoice = Invoice.query.order_by(Invoice.id.desc()).first()
    settings_obj = Settings.get_settings()
    
    # Provide a minimal mock invoice if none exists to avoid template errors
    from types import SimpleNamespace
    if invoice is None:
        from datetime import date
        invoice = SimpleNamespace(
            invoice_number='0000',
            issue_date=date.today(),
            due_date=date.today(),
            status='draft',
            client_name='Sample Client',
            client_email='',
            client_address='',
            project=SimpleNamespace(name='Sample Project', description=''),
            items=[],
            subtotal=0.0,
            tax_rate=0.0,
            tax_amount=0.0,
            total_amount=0.0,
            notes='',
            terms='',
        )
    # Ensure at least one sample item to avoid undefined 'item' in templates that reference it outside loops
    sample_item = SimpleNamespace(description='Sample item', quantity=1.0, unit_price=0.0, total_amount=0.0, time_entry_ids='')
    try:
        if not getattr(invoice, 'items', None):
            invoice.items = [sample_item]
    except Exception:
        try:
            invoice.items = [sample_item]
        except Exception:
            pass
    # Helper: sanitize Jinja blocks to fix entities/smart quotes inserted by editor
    def _sanitize_jinja_blocks(raw: str) -> str:
        try:
            import re as _re
            import html as _html
            smart_map = {
                '\u201c': '"', '\u201d': '"',  # “ ” -> "
                '\u2018': "'", '\u2019': "'",  # ‘ ’ -> '
                '\u00a0': ' ',                   # nbsp
                '\u200b': '', '\u200c': '', '\u200d': '',  # zero-width
            }
            def _fix_quotes(s: str) -> str:
                for k, v in smart_map.items():
                    s = s.replace(k, v)
                return s
            def _clean(match):
                open_tag = match.group(1)
                inner = match.group(2)
                # Remove any HTML tags GrapesJS may have inserted inside Jinja braces
                inner = _re.sub(r'</?[^>]+?>', '', inner)
                # Decode HTML entities
                inner = _html.unescape(inner)
                # Fix smart quotes and nbsp
                inner = _fix_quotes(inner)
                # Trim excessive whitespace around pipes and parentheses
                inner = _re.sub(r'\s+\|\s+', ' | ', inner)
                inner = _re.sub(r'\(\s+', '(', inner)
                inner = _re.sub(r'\s+\)', ')', inner)
                # Normalize _("...") -> _('...')
                inner = inner.replace('_("', "_('").replace('")', "')")
                return f"{open_tag}{inner}{' }}' if open_tag == '{{ ' else ' %}'}"
            pattern = _re.compile(r'({{\s|{%\s)([\s\S]*?)(?:}}|%})')
            return _re.sub(pattern, _clean, raw)
        except Exception:
            return raw

    sanitized = _sanitize_jinja_blocks(html)

    # Wrap provided HTML with a minimal page and CSS
    try:
        from pathlib import Path as _Path
        # Provide helpers as callables since templates may use function-style helpers
        try:
            from babel.dates import format_date as _babel_format_date
        except Exception:
            _babel_format_date = None
        def _format_date(value, format='medium'):
            try:
                if _babel_format_date:
                    if format == 'full':
                        return _babel_format_date(value, format='full')
                    if format == 'long':
                        return _babel_format_date(value, format='long')
                    if format == 'short':
                        return _babel_format_date(value, format='short')
                    return _babel_format_date(value, format='medium')
                return value.strftime('%Y-%m-%d')
            except Exception:
                return str(value)
        def _format_money(value):
            try:
                return f"{float(value):,.2f} {settings_obj.currency}"
            except Exception:
                return f"{value} {settings_obj.currency}"
        body_html = render_template_string(
            sanitized,
            invoice=invoice,
            settings=settings_obj,
            Path=_Path,
            format_date=_format_date,
            format_money=_format_money,
            item=sample_item,
        )
    except Exception as e:
        body_html = f"<div style='color:red'>Template error: {str(e)}</div>" + sanitized
    page_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>PDF Preview</title>
        <style>{css}</style>
    </head>
    <body>{body_html}</body>
    </html>
    """
    return page_html

@admin_bp.route('/admin/upload-logo', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required('manage_settings')
def upload_logo():
    """Upload company logo"""
    if 'logo' not in request.files:
        flash('No logo file selected', 'error')
        return redirect(url_for('admin.settings'))
    
    file = request.files['logo']
    if file.filename == '':
        flash('No logo file selected', 'error')
        return redirect(url_for('admin.settings'))
    
    if file and allowed_logo_file(file.filename):
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"company_logo_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Basic server-side validation: verify image type
        try:
            from PIL import Image
            file.stream.seek(0)
            img = Image.open(file.stream)
            img.verify()
            file.stream.seek(0)
        except Exception:
            flash('Invalid image file.', 'error')
            return redirect(url_for('admin.settings'))

        # Save file
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Update settings
        settings_obj = Settings.get_settings()
        
        # Remove old logo if it exists
        if settings_obj.company_logo_filename:
            old_logo_path = os.path.join(upload_folder, settings_obj.company_logo_filename)
            if os.path.exists(old_logo_path):
                try:
                    os.remove(old_logo_path)
                except OSError:
                    pass  # Ignore errors when removing old file
        
        settings_obj.company_logo_filename = unique_filename
        if not safe_commit('admin_upload_logo'):
            flash('Could not save logo due to a database error. Please check server logs.', 'error')
            return redirect(url_for('admin.settings'))
        
        flash('Company logo uploaded successfully', 'success')
    else:
        flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, SVG, WEBP', 'error')
    
    return redirect(url_for('admin.settings'))

@admin_bp.route('/admin/remove-logo', methods=['POST'])
@login_required
@admin_or_permission_required('manage_settings')
def remove_logo():
    """Remove company logo"""
    settings_obj = Settings.get_settings()
    
    if settings_obj.company_logo_filename:
        # Remove file from filesystem
        logo_path = settings_obj.get_logo_path()
        if logo_path and os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except OSError:
                pass  # Ignore errors when removing file
        
        # Clear filename from database
        settings_obj.company_logo_filename = ''
        if not safe_commit('admin_remove_logo'):
            flash('Could not remove logo due to a database error. Please check server logs.', 'error')
            return redirect(url_for('admin.settings'))
        flash('Company logo removed successfully', 'success')
    else:
        flash('No logo to remove', 'info')
    
    return redirect(url_for('admin.settings'))

# Public route to serve uploaded logos from the static uploads directory
@admin_bp.route('/uploads/logos/<path:filename>')
def serve_uploaded_logo(filename):
    """Serve company logo files stored under static/uploads/logos.
    This route is intentionally public so logos render on unauthenticated pages
    like the login screen and in favicons.
    """
    upload_folder = get_upload_folder()
    return send_from_directory(upload_folder, filename)

@admin_bp.route('/admin/backups')
@login_required
@admin_or_permission_required('manage_backups')
def backups_management():
    """Backups management page"""
    # Get list of existing backups
    backups_dir = os.path.join(os.path.abspath(os.path.join(current_app.root_path, '..')), 'backups')
    backups = []
    
    if os.path.exists(backups_dir):
        for filename in os.listdir(backups_dir):
            if filename.endswith('.zip') and not filename.startswith('restore_'):
                filepath = os.path.join(backups_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'size_mb': round(stat.st_size / (1024 * 1024), 2)
                })
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('admin/backups.html', backups=backups)


@admin_bp.route('/admin/backup/create', methods=['POST'])
@login_required
@admin_or_permission_required('manage_backups')
def create_backup_manual():
    """Create manual backup and return the archive for download."""
    try:
        archive_path = create_backup(current_app)
        if not archive_path or not os.path.exists(archive_path):
            flash('Backup failed: archive not created', 'error')
            return redirect(url_for('admin.backups_management'))
        # Stream file to user
        return send_file(archive_path, as_attachment=True)
    except Exception as e:
        flash(f'Backup failed: {e}', 'error')
        return redirect(url_for('admin.backups_management'))


@admin_bp.route('/admin/backup/download/<filename>')
@login_required
@admin_or_permission_required('manage_backups')
def download_backup(filename):
    """Download an existing backup file"""
    # Security: only allow downloading .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith('.zip'):
        flash('Invalid file type', 'error')
        return redirect(url_for('admin.backups_management'))
    
    backups_dir = os.path.join(os.path.abspath(os.path.join(current_app.root_path, '..')), 'backups')
    filepath = os.path.join(backups_dir, filename)
    
    if not os.path.exists(filepath):
        flash('Backup file not found', 'error')
        return redirect(url_for('admin.backups_management'))
    
    return send_file(filepath, as_attachment=True)


@admin_bp.route('/admin/backup/delete/<filename>', methods=['POST'])
@login_required
@admin_or_permission_required('manage_backups')
def delete_backup(filename):
    """Delete a backup file"""
    # Security: only allow deleting .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith('.zip'):
        flash('Invalid file type', 'error')
        return redirect(url_for('admin.backups_management'))
    
    backups_dir = os.path.join(os.path.abspath(os.path.join(current_app.root_path, '..')), 'backups')
    filepath = os.path.join(backups_dir, filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(f'Backup "{filename}" deleted successfully', 'success')
        else:
            flash('Backup file not found', 'error')
    except Exception as e:
        flash(f'Failed to delete backup: {e}', 'error')
    
    return redirect(url_for('admin.backups_management'))

@admin_bp.route('/admin/restore', methods=['GET', 'POST'])
@admin_bp.route('/admin/restore/<filename>', methods=['POST'])
@limiter.limit("3 per minute", methods=["POST"])  # heavy operation
@login_required
@admin_or_permission_required('manage_backups')
def restore(filename=None):
    """Restore from an uploaded backup archive or existing backup file."""
    if request.method == 'POST':
        backups_dir = os.path.join(os.path.abspath(os.path.join(current_app.root_path, '..')), 'backups')
        
        # If restoring from an existing backup file
        if filename:
            filename = secure_filename(filename)
            if not filename.lower().endswith('.zip'):
                flash('Invalid file type. Please select a .zip backup archive.', 'error')
                return redirect(url_for('admin.backups_management'))
            temp_path = os.path.join(backups_dir, filename)
            if not os.path.exists(temp_path):
                flash('Backup file not found.', 'error')
                return redirect(url_for('admin.backups_management'))
            # Copy to temp location for processing
            actual_restore_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{filename}")
            shutil.copy2(temp_path, actual_restore_path)
            temp_path = actual_restore_path
        # If uploading a new backup file
        elif 'backup_file' in request.files and request.files['backup_file'].filename != '':
            file = request.files['backup_file']
            uploaded_filename = secure_filename(file.filename)
            if not uploaded_filename.lower().endswith('.zip'):
                flash('Invalid file type. Please upload a .zip backup archive.', 'error')
                return redirect(url_for('admin.restore'))
            # Save temporarily under project backups
            os.makedirs(backups_dir, exist_ok=True)
            temp_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{uploaded_filename}")
            file.save(temp_path)
        else:
            flash('No backup file provided', 'error')
            return redirect(url_for('admin.restore'))

        # Initialize progress state
        token = uuid.uuid4().hex[:8]
        RESTORE_PROGRESS[token] = {'status': 'starting', 'percent': 0, 'message': 'Queued'}

        def progress_cb(label, percent):
            RESTORE_PROGRESS[token] = {'status': 'running', 'percent': int(percent), 'message': label}

        # Capture the real Flask app object for use in a background thread
        app_obj = current_app._get_current_object()

        def _do_restore():
            try:
                RESTORE_PROGRESS[token] = {'status': 'running', 'percent': 5, 'message': 'Starting restore'}
                success, message = restore_backup(app_obj, temp_path, progress_callback=progress_cb)
                RESTORE_PROGRESS[token] = {
                    'status': 'done' if success else 'error',
                    'percent': 100 if success else RESTORE_PROGRESS[token].get('percent', 0),
                    'message': message
                }
            except Exception as e:
                RESTORE_PROGRESS[token] = {'status': 'error', 'percent': RESTORE_PROGRESS[token].get('percent', 0), 'message': str(e)}
            finally:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        # Run restore in background to keep request responsive
        t = threading.Thread(target=_do_restore, daemon=True)
        t.start()

        flash('Restore started. You can monitor progress on this page.', 'info')
        return redirect(url_for('admin.restore', token=token))
    # GET
    token = request.args.get('token')
    progress = RESTORE_PROGRESS.get(token) if token else None
    return render_template('admin/restore.html', progress=progress, token=token)

@admin_bp.route('/admin/system')
@login_required
@admin_or_permission_required('view_system_info')
def system_info():
    """Show system information"""
    # Get system statistics
    total_users = User.query.count()
    total_projects = Project.query.count()
    total_entries = TimeEntry.query.count()
    active_timers = TimeEntry.query.filter_by(end_time=None).count()
    
    # Get database size
    db_size_bytes = 0
    try:
        engine = db.session.bind
        dialect = engine.dialect.name if engine else ''
        if dialect == 'sqlite':
            db_size_bytes = db.session.execute(
                text('SELECT page_count * page_size AS size FROM pragma_page_count(), pragma_page_size()')
            ).scalar() or 0
        elif dialect in ('postgresql', 'postgres'):
            db_size_bytes = db.session.execute(
                text('SELECT pg_database_size(current_database())')
            ).scalar() or 0
        else:
            db_size_bytes = 0
    except Exception:
        db_size_bytes = 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2) if db_size_bytes else 0
    
    return render_template('admin/system_info.html',
                         total_users=total_users,
                         total_projects=total_projects,
                         total_entries=total_entries,
                         active_timers=active_timers,
                         db_size_mb=db_size_mb)

@admin_bp.route('/admin/oidc/debug')
@login_required
@admin_or_permission_required('manage_oidc')
def oidc_debug():
    """OIDC Configuration Debug Dashboard"""
    from app.config import Config
    from app import oauth
    
    # Gather OIDC configuration
    oidc_config = {
        'enabled': False,
        'auth_method': getattr(Config, 'AUTH_METHOD', 'local'),
        'issuer': getattr(Config, 'OIDC_ISSUER', None),
        'client_id': getattr(Config, 'OIDC_CLIENT_ID', None),
        'client_secret_set': bool(getattr(Config, 'OIDC_CLIENT_SECRET', None)),
        'redirect_uri': getattr(Config, 'OIDC_REDIRECT_URI', None),
        'scopes': getattr(Config, 'OIDC_SCOPES', 'openid profile email'),
        'username_claim': getattr(Config, 'OIDC_USERNAME_CLAIM', 'preferred_username'),
        'email_claim': getattr(Config, 'OIDC_EMAIL_CLAIM', 'email'),
        'full_name_claim': getattr(Config, 'OIDC_FULL_NAME_CLAIM', 'name'),
        'groups_claim': getattr(Config, 'OIDC_GROUPS_CLAIM', 'groups'),
        'admin_group': getattr(Config, 'OIDC_ADMIN_GROUP', None),
        'admin_emails': getattr(Config, 'OIDC_ADMIN_EMAILS', []),
        'post_logout_redirect': getattr(Config, 'OIDC_POST_LOGOUT_REDIRECT_URI', None),
    }
    
    # Check if OIDC is enabled
    auth_method = (oidc_config['auth_method'] or 'local').strip().lower()
    oidc_config['enabled'] = auth_method in ('oidc', 'both')
    
    # Try to get OIDC client metadata
    metadata = None
    metadata_error = None
    well_known_url = None
    
    if oidc_config['enabled'] and oidc_config['issuer']:
        try:
            client = oauth.create_client('oidc')
            if client:
                metadata = client.load_server_metadata()
                well_known_url = f"{oidc_config['issuer'].rstrip('/')}/.well-known/openid-configuration"
        except Exception as e:
            metadata_error = str(e)
            well_known_url = f"{oidc_config['issuer'].rstrip('/')}/.well-known/openid-configuration" if oidc_config['issuer'] else None
    
    # Get OIDC users from database
    oidc_users = []
    try:
        oidc_users = User.query.filter(
            User.oidc_issuer.isnot(None),
            User.oidc_sub.isnot(None)
        ).order_by(User.last_login.desc()).all()
    except Exception:
        pass
    
    return render_template('admin/oidc_debug.html',
                         oidc_config=oidc_config,
                         metadata=metadata,
                         metadata_error=metadata_error,
                         well_known_url=well_known_url,
                         oidc_users=oidc_users)


@admin_bp.route('/admin/oidc/test')
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required('manage_oidc')
def oidc_test():
    """Test OIDC configuration by fetching discovery document"""
    from app.config import Config
    from app import oauth
    import requests
    
    auth_method = (getattr(Config, 'AUTH_METHOD', 'local') or 'local').strip().lower()
    if auth_method not in ('oidc', 'both'):
        flash('OIDC is not enabled. Set AUTH_METHOD to "oidc" or "both".', 'warning')
        return redirect(url_for('admin.oidc_debug'))
    
    issuer = getattr(Config, 'OIDC_ISSUER', None)
    if not issuer:
        flash('OIDC_ISSUER is not configured', 'error')
        return redirect(url_for('admin.oidc_debug'))
    
    # Test 1: Check if discovery document is accessible
    well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    try:
        current_app.logger.info("OIDC Test: Fetching discovery document from %s", well_known_url)
        response = requests.get(well_known_url, timeout=10)
        response.raise_for_status()
        discovery_doc = response.json()
        flash(f'✓ Discovery document fetched successfully from {well_known_url}', 'success')
        current_app.logger.info("OIDC Test: Discovery document retrieved, issuer=%s", discovery_doc.get('issuer'))
    except requests.exceptions.Timeout:
        flash(f'✗ Timeout fetching discovery document from {well_known_url}', 'error')
        current_app.logger.error("OIDC Test: Timeout fetching discovery document")
        return redirect(url_for('admin.oidc_debug'))
    except requests.exceptions.RequestException as e:
        flash(f'✗ Failed to fetch discovery document: {str(e)}', 'error')
        current_app.logger.error("OIDC Test: Failed to fetch discovery document: %s", str(e))
        return redirect(url_for('admin.oidc_debug'))
    except Exception as e:
        flash(f'✗ Unexpected error: {str(e)}', 'error')
        current_app.logger.error("OIDC Test: Unexpected error: %s", str(e))
        return redirect(url_for('admin.oidc_debug'))
    
    # Test 2: Check if OAuth client is registered
    try:
        client = oauth.create_client('oidc')
        if client:
            flash('✓ OAuth client is registered in application', 'success')
            current_app.logger.info("OIDC Test: OAuth client registered")
        else:
            flash('✗ OAuth client is not registered', 'error')
            current_app.logger.error("OIDC Test: OAuth client not registered")
    except Exception as e:
        flash(f'✗ Failed to create OAuth client: {str(e)}', 'error')
        current_app.logger.error("OIDC Test: Failed to create OAuth client: %s", str(e))
    
    # Test 3: Verify required endpoints are present
    required_endpoints = ['authorization_endpoint', 'token_endpoint', 'userinfo_endpoint']
    for endpoint in required_endpoints:
        if endpoint in discovery_doc:
            flash(f'✓ {endpoint}: {discovery_doc[endpoint]}', 'info')
        else:
            flash(f'✗ Missing {endpoint} in discovery document', 'warning')
    
    # Test 4: Check supported scopes
    supported_scopes = discovery_doc.get('scopes_supported', [])
    requested_scopes = getattr(Config, 'OIDC_SCOPES', 'openid profile email').split()
    for scope in requested_scopes:
        if scope in supported_scopes:
            flash(f'✓ Scope "{scope}" is supported by provider', 'info')
        else:
            flash(f'⚠ Scope "{scope}" may not be supported by provider (supported: {", ".join(supported_scopes)})', 'warning')
    
    # Test 5: Check claims
    supported_claims = discovery_doc.get('claims_supported', [])
    if supported_claims:
        flash(f'ℹ Provider supports claims: {", ".join(supported_claims)}', 'info')
        
        # Check if configured claims are supported
        claim_checks = {
            'username': getattr(Config, 'OIDC_USERNAME_CLAIM', 'preferred_username'),
            'email': getattr(Config, 'OIDC_EMAIL_CLAIM', 'email'),
            'full_name': getattr(Config, 'OIDC_FULL_NAME_CLAIM', 'name'),
            'groups': getattr(Config, 'OIDC_GROUPS_CLAIM', 'groups'),
        }
        
        for claim_type, claim_name in claim_checks.items():
            if claim_name in supported_claims:
                flash(f'✓ Configured {claim_type} claim "{claim_name}" is supported', 'info')
            else:
                flash(f'⚠ Configured {claim_type} claim "{claim_name}" not in supported claims list (may still work)', 'warning')
    
    flash('OIDC configuration test completed', 'info')
    return redirect(url_for('admin.oidc_debug'))


@admin_bp.route('/admin/oidc/user/<int:user_id>')
@login_required
@admin_or_permission_required('view_users')
def oidc_user_detail(user_id):
    """View OIDC details for a specific user"""
    user = User.query.get_or_404(user_id)
    
    return render_template('admin/oidc_user_detail.html', user=user)


# ==================== API Token Management ====================

@admin_bp.route('/admin/api-tokens')
@login_required
@admin_required
def api_tokens():
    """API tokens management page"""
    from app.models import ApiToken
    
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    return render_template('admin/api_tokens.html', 
                         tokens=tokens, 
                         users=users,
                         now=datetime.utcnow())


@admin_bp.route('/admin/api-tokens', methods=['POST'])
@login_required
@admin_required
def create_api_token():
    """Create a new API token"""
    from app.models import ApiToken
    
    data = request.get_json() or {}
    
    # Validate input
    if not data.get('name'):
        return jsonify({'error': 'Token name is required'}), 400
    if not data.get('user_id'):
        return jsonify({'error': 'User ID is required'}), 400
    if not data.get('scopes'):
        return jsonify({'error': 'At least one scope is required'}), 400
    
    # Verify user exists
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'Invalid user'}), 400
    
    # Create token
    try:
        api_token, plain_token = ApiToken.create_token(
            user_id=data['user_id'],
            name=data['name'],
            description=data.get('description', ''),
            scopes=data['scopes'],
            expires_days=data.get('expires_days')
        )
        
        db.session.add(api_token)
        db.session.commit()
        
        current_app.logger.info(
            f"API token '{data['name']}' created for user {user.username} by {current_user.username}"
        )
        
        return jsonify({
            'message': 'API token created successfully',
            'token': plain_token,
            'token_id': api_token.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create API token: {e}")
        return jsonify({'error': 'Failed to create token'}), 500


@admin_bp.route('/admin/api-tokens/<int:token_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_api_token(token_id):
    """Toggle API token active status"""
    from app.models import ApiToken
    
    token = ApiToken.query.get_or_404(token_id)
    token.is_active = not token.is_active
    
    try:
        db.session.commit()
        status = 'activated' if token.is_active else 'deactivated'
        current_app.logger.info(
            f"API token '{token.name}' {status} by {current_user.username}"
        )
        return jsonify({'message': f'Token {status} successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to toggle API token: {e}")
        return jsonify({'error': 'Failed to update token'}), 500


@admin_bp.route('/admin/api-tokens/<int:token_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_api_token(token_id):
    """Delete an API token"""
    from app.models import ApiToken
    
    token = ApiToken.query.get_or_404(token_id)
    token_name = token.name
    
    try:
        db.session.delete(token)
        db.session.commit()
        current_app.logger.info(
            f"API token '{token_name}' deleted by {current_user.username}"
        )
        return jsonify({'message': 'Token deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete API token: {e}")
        return jsonify({'error': 'Failed to delete token'}), 500


# ==================== Email Configuration Management ====================

@admin_bp.route('/admin/email')
@login_required
@admin_or_permission_required('manage_settings')
def email_support():
    """Email configuration and testing page"""
    from app.utils.email import test_email_configuration
    
    # Get email configuration status
    email_status = test_email_configuration()
    
    # Log dashboard access
    app_module.log_event("admin.email_support_viewed", user_id=current_user.id)
    app_module.track_event(current_user.id, "admin.email_support_viewed", {})
    
    return render_template('admin/email_support.html',
                         email_status=email_status)


@admin_bp.route('/admin/email/test', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
@admin_or_permission_required('manage_settings')
def test_email():
    """Send a test email"""
    from app.utils.email import send_test_email
    
    data = request.get_json() or {}
    recipient = data.get('recipient')
    
    if not recipient:
        current_app.logger.warning(f"[EMAIL TEST API] No recipient provided by user {current_user.username}")
        return jsonify({'success': False, 'message': 'Recipient email is required'}), 400
    
    current_app.logger.info(f"[EMAIL TEST API] Test email request from user {current_user.username} to {recipient}")
    
    # Send test email
    sender_name = current_user.username or 'TimeTracker Admin'
    success, message = send_test_email(recipient, sender_name)
    
    # Log the test
    current_app.logger.info(f"[EMAIL TEST API] Result: {'SUCCESS' if success else 'FAILED'} - {message}")
    app_module.log_event("admin.email_test_sent", 
                        user_id=current_user.id,
                        recipient=recipient,
                        success=success)
    app_module.track_event(current_user.id, "admin.email_test_sent", {
        'success': success,
        'configured': success
    })
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'message': message}), 500


@admin_bp.route('/admin/email/config-status', methods=['GET'])
@login_required
@admin_or_permission_required('manage_settings')
def email_config_status():
    """Get current email configuration status (for AJAX polling)"""
    from app.utils.email import test_email_configuration
    
    email_status = test_email_configuration()
    return jsonify(email_status), 200


@admin_bp.route('/admin/email/configure', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required('manage_settings')
def save_email_config():
    """Save email configuration to database"""
    from app.utils.email import reload_mail_config
    
    data = request.get_json() or {}
    
    current_app.logger.info(f"[EMAIL CONFIG] Saving email configuration by user {current_user.username}")
    
    # Get settings
    settings = Settings.get_settings()
    
    # Update email configuration
    settings.mail_enabled = data.get('enabled', False)
    settings.mail_server = data.get('server', '').strip()
    settings.mail_port = int(data.get('port', 587))
    settings.mail_use_tls = data.get('use_tls', True)
    settings.mail_use_ssl = data.get('use_ssl', False)
    settings.mail_username = data.get('username', '').strip()
    
    # Only update password if provided (non-empty)
    password = data.get('password', '').strip()
    if password:
        settings.mail_password = password
        current_app.logger.info("[EMAIL CONFIG] Password updated")
    
    settings.mail_default_sender = data.get('default_sender', '').strip()
    
    current_app.logger.info(f"[EMAIL CONFIG] Settings: enabled={settings.mail_enabled}, "
                           f"server={settings.mail_server}:{settings.mail_port}, "
                           f"tls={settings.mail_use_tls}, ssl={settings.mail_use_ssl}")
    
    # Validate
    if settings.mail_enabled and not settings.mail_server:
        current_app.logger.warning("[EMAIL CONFIG] Validation failed: mail server required")
        return jsonify({
            'success': False,
            'message': 'Mail server is required when email is enabled'
        }), 400
    
    if settings.mail_use_tls and settings.mail_use_ssl:
        current_app.logger.warning("[EMAIL CONFIG] Validation failed: both TLS and SSL enabled")
        return jsonify({
            'success': False,
            'message': 'Cannot use both TLS and SSL. Please choose one.'
        }), 400
    
    # Save to database
    if not safe_commit('admin_save_email_config'):
        current_app.logger.error("[EMAIL CONFIG] Failed to save to database")
        return jsonify({
            'success': False,
            'message': 'Failed to save email configuration to database'
        }), 500
    
    current_app.logger.info("[EMAIL CONFIG] ✓ Configuration saved to database")
    
    # Reload mail configuration
    if settings.mail_enabled:
        current_app.logger.info("[EMAIL CONFIG] Reloading mail configuration...")
        reload_result = reload_mail_config(current_app._get_current_object())
        current_app.logger.info(f"[EMAIL CONFIG] Mail config reload: {'SUCCESS' if reload_result else 'FAILED'}")
    
    # Log the change
    app_module.log_event("admin.email_config_saved", 
                        user_id=current_user.id,
                        enabled=settings.mail_enabled)
    app_module.track_event(current_user.id, "admin.email_config_saved", {
        'enabled': settings.mail_enabled,
        'source': 'database'
    })
    
    current_app.logger.info("[EMAIL CONFIG] ✓ Email configuration update complete")
    
    return jsonify({
        'success': True,
        'message': 'Email configuration saved successfully'
    }), 200


@admin_bp.route('/admin/email/get-config', methods=['GET'])
@login_required
@admin_or_permission_required('manage_settings')
def get_email_config():
    """Get current email configuration from database"""
    settings = Settings.get_settings()
    
    return jsonify({
        'enabled': settings.mail_enabled,
        'server': settings.mail_server or '',
        'port': settings.mail_port or 587,
        'use_tls': settings.mail_use_tls if settings.mail_use_tls is not None else True,
        'use_ssl': settings.mail_use_ssl if settings.mail_use_ssl is not None else False,
        'username': settings.mail_username or '',
        'password_set': bool(settings.mail_password),
        'default_sender': settings.mail_default_sender or ''
    }), 200
