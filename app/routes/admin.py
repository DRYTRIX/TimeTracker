from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_from_directory,
    send_file,
    jsonify,
    render_template_string,
)
from flask_babel import gettext as _
from flask_login import login_required, current_user
import app as app_module
from app import db, limiter
from app.models import User, Project, TimeEntry, Settings, Invoice, Quote, QuoteItem, Role
from datetime import datetime
from sqlalchemy import text
import os
from werkzeug.utils import secure_filename
import uuid
from app.utils.db import safe_commit
from app.utils.backup import create_backup, restore_backup, get_backup_root_dir
from app.utils.installation import get_installation_config
from app.utils.telemetry import get_telemetry_fingerprint, is_telemetry_enabled
from app.utils.permissions import admin_or_permission_required
from app.utils.timezone import get_available_timezones
import threading
import time
import shutil

admin_bp = Blueprint("admin", __name__)

# In-memory restore progress tracking (simple, per-process)
RESTORE_PROGRESS = {}

# Allowed file extensions for logos
# Avoid SVG due to XSS risk unless sanitized server-side
ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _convert_json_template_to_html_css(template_json, page_size="A4", invoice=None, quote=None, settings=None):
    """
    Convert JSON template to HTML/CSS for preview purposes with full element type support.
    
    Args:
        template_json: Dictionary containing template definition
        page_size: Page size for CSS @page rule
        invoice: Optional invoice object for table data rendering
        quote: Optional quote object for table data rendering
        settings: Optional settings object for company information
        
    Returns:
        tuple: (html_string, css_string)
    """
    from app.utils.pdf_template_schema import get_page_dimensions_points
    import html as html_escape
    import json as json_module
    
    # Get page dimensions
    dims = get_page_dimensions_points(page_size)
    width_pt = dims["width"]
    height_pt = dims["height"]
    
    # Convert points to pixels at 96 DPI for browser (72 DPI * 96/72 = 1.333)
    # But for accuracy, use 1pt = 1.333px conversion for browser
    width_px = int(width_pt * 96 / 72)
    height_px = int(height_pt * 96 / 72)
    
    # Font mapping: ReportLab fonts to web fonts
    font_map = {
        "Helvetica": "Arial, Helvetica, sans-serif",
        "Helvetica-Bold": "Arial, Helvetica, sans-serif",
        "Helvetica-Oblique": "Arial, Helvetica, sans-serif",
        "Helvetica-BoldOblique": "Arial, Helvetica, sans-serif",
        "Times-Roman": "Times New Roman, Times, serif",
        "Times-Bold": "Times New Roman, Times, serif",
        "Times-Italic": "Times New Roman, Times, serif",
        "Times-BoldItalic": "Times New Roman, Times, serif",
        "Courier": "Courier New, Courier, monospace",
        "Courier-Bold": "Courier New, Courier, monospace",
        "Courier-Oblique": "Courier New, Courier, monospace",
        "Courier-BoldOblique": "Courier New, Courier, monospace",
    }
    
    # Get page margins from template
    page_config = template_json.get("page", {})
    margin_top = page_config.get("margin", {}).get("top", 20)
    margin_bottom = page_config.get("margin", {}).get("bottom", 20)
    margin_left = page_config.get("margin", {}).get("left", 20)
    margin_right = page_config.get("margin", {}).get("right", 20)
    
    # Build CSS with @page rule and comprehensive styles
    css = f"""@page {{
    size: {page_size};
    margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm;
}}

* {{
    box-sizing: border-box;
}}

body {{
    width: {width_px}px;
    height: {height_px}px;
    margin: 0;
    padding: 0;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    background: white;
    overflow: hidden;
}}

.invoice-wrapper,
.quote-wrapper {{
    width: {width_px}px;
    height: {height_px}px;
    position: relative;
    background: white;
    margin: 0;
    padding: 0;
}}

.element {{
    position: absolute;
    box-sizing: border-box;
}}

.text-element {{
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    margin: 0;
    padding: 0;
}}

.image-element {{
    object-fit: contain;
    display: block;
}}

.rectangle-element {{
    box-sizing: border-box;
}}

.circle-element {{
    border-radius: 50%;
    box-sizing: border-box;
}}

.line-element {{
    transform-origin: left center;
}}

.table-element {{
    border-collapse: collapse;
    border-spacing: 0;
    table-layout: auto;
    margin: 0;
    box-sizing: border-box;
}}

.table-element th,
.table-element td {{
    padding: 8px 12px;
    border: 1px solid #ddd;
    text-align: left;
    vertical-align: top;
    box-sizing: border-box;
}}

.table-element th {{
    background-color: #f8f9fa;
    font-weight: bold;
    border-bottom: 2px solid #333;
}}

.table-element tbody tr:nth-child(even) {{
    background-color: #f9f9f9;
}}

.table-element tbody tr:hover {{
    background-color: #f0f0f0;
}}
"""
    
    # Helper function to map ReportLab fonts to web fonts
    def get_font_family(font_name):
        if not font_name:
            return "Arial, Helvetica, sans-serif"
        return font_map.get(font_name, font_map.get(font_name.split("-")[0], "Arial, Helvetica, sans-serif"))
    
    # Helper function to get font weight from font name
    def get_font_weight(font_name):
        if not font_name:
            return "normal"
        if "Bold" in font_name:
            return "bold"
        return "normal"
    
    # Helper function to get font style from font name
    def get_font_style(font_name):
        if not font_name:
            return "normal"
        if "Oblique" in font_name or "Italic" in font_name:
            return "italic"
        return "normal"
    
    # Helper function to convert color (supports hex, rgb, named colors)
    def format_color(color):
        if not color:
            return "#000000"
        # If already hex or named color, return as-is
        if color.startswith("#") or color in ["black", "white", "red", "blue", "green", "yellow", "cyan", "magenta"]:
            return color
        # If RGB tuple/list, convert to hex
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            return f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
        return str(color)
    
    # Helper function to render text with Jinja2-like template variables
    def render_text_template(text, data_obj, settings_obj=None):
        """Render text with template variables using actual data"""
        if not text:
            return text
        
        # Simple template variable replacement for preview
        # Replace {{ variable }} patterns with actual values
        import re
        def replace_var(match):
            var_path = match.group(1).strip()
            try:
                # Handle simple attribute access (e.g., "invoice.invoice_number" or "settings.company_name")
                parts = var_path.split(".")
                if parts[0] == "settings" and settings_obj:
                    # Handle settings variables
                    obj = settings_obj
                    for part in parts[1:]:  # Skip "settings" part
                        obj = getattr(obj, part, None)
                        if obj is None:
                            return match.group(0)  # Return original if not found
                    return str(obj) if obj is not None else ""
                elif data_obj:
                    # Handle invoice/quote variables
                    obj = data_obj
                    for part in parts:
                        obj = getattr(obj, part, None)
                        if obj is None:
                            return match.group(0)  # Return original if not found
                    return str(obj) if obj is not None else ""
                else:
                    return match.group(0)  # Return original if no data object
            except Exception:
                return match.group(0)  # Return original on error
        
        return re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_var, text)
    
    # Build HTML from elements
    html_parts = ['<div class="invoice-wrapper">'] if invoice else ['<div class="quote-wrapper">']
    
    elements = template_json.get("elements", [])
    for idx, element in enumerate(elements):
        elem_type = element.get("type", "")
        x = element.get("x", 0)
        y = element.get("y", 0)
        style = element.get("style", {})
        opacity = style.get("opacity", 1.0)
        rotation = element.get("rotation", 0)
        
        # Convert points to pixels at 96 DPI for browser
        x_px = int(x * 96 / 72)
        y_px = int(y * 96 / 72)
        
        # Base style string
        base_style_parts = [
            f"left: {x_px}px",
            f"top: {y_px}px",
            f"opacity: {opacity}",
        ]
        
        if rotation:
            base_style_parts.append(f"transform: rotate({rotation}deg)")
            base_style_parts.append("transform-origin: top left")
        
        style_str_base = "; ".join(base_style_parts)
        
        if elem_type == "text":
            text = element.get("text", "")
            width = element.get("width", 400)
            height = element.get("height", None)
            width_px_elem = int(width * 96 / 72)
            
            font_name = style.get("font", "Helvetica")
            font_size = style.get("size", 10)
            color = format_color(style.get("color", "#000000"))
            align = style.get("align", "left")
            valign = style.get("valign", "top")
            
            # Build complete style string
            style_parts = [style_str_base]
            style_parts.append(f"width: {width_px_elem}px")
            if height:
                style_parts.append(f"height: {int(height * 96 / 72)}px")
            style_parts.append(f"font-family: {get_font_family(font_name)}")
            style_parts.append(f"font-size: {font_size}pt")
            style_parts.append(f"font-weight: {get_font_weight(font_name)}")
            style_parts.append(f"font-style: {get_font_style(font_name)}")
            style_parts.append(f"color: {color}")
            style_parts.append(f"text-align: {align}")
            style_parts.append(f"vertical-align: {valign}")
            
            style_str = "; ".join(style_parts) + ";"
            
            # Render text with actual data if available
            data_obj = invoice if invoice else quote
            rendered_text = render_text_template(text, data_obj, settings) if (data_obj or settings) else text
            
            # Escape HTML but preserve any remaining template syntax
            text_escaped = html_escape.escape(rendered_text)
            # Restore template syntax if any remains (shouldn't after rendering, but just in case)
            text_escaped = text_escaped.replace("&lt;{{", "{{").replace("}}&gt;", "}}")
            
            html_parts.append(f'<div class="element text-element" style="{style_str}">{text_escaped}</div>')
        
        elif elem_type == "image":
            width = element.get("width", 100)
            height = element.get("height", 100)
            width_px_elem = int(width * 96 / 72)
            height_px_elem = int(height * 96 / 72)
            source = element.get("source", "")
            is_decorative = element.get("decorative", False)
            
            # Handle base64 data URLs or file paths
            img_src = ""
            if source.startswith("data:"):
                img_src = source
            elif source.startswith("/uploads/template_images/"):
                # Template image - convert to base64 for PDF generation
                try:
                    from app.utils.template_filters import get_image_base64
                    # Extract filename from URL
                    filename = source.split("/uploads/template_images/")[-1]
                    # Build file path relative to app root (as get_image_base64 expects)
                    relative_path = f"app/static/uploads/template_images/{filename}"
                    # Convert to base64
                    img_src = get_image_base64(relative_path) or source  # Fallback to URL if conversion fails
                except Exception as e:
                    # If conversion fails, use the URL directly
                    current_app.logger.warning(f"Failed to convert template image to base64: {e}")
                    img_src = source
            elif source.startswith("/") or source.startswith("http"):
                img_src = source
            else:
                # Assume it's a relative path or placeholder
                if source:
                    img_src = source
                else:
                    # Placeholder for decorative images without source
                    img_src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23ddd' width='100' height='100'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999'%3EImage%3C/text%3E%3C/svg%3E"
            
            style_parts = [style_str_base]
            style_parts.append(f"width: {width_px_elem}px")
            style_parts.append(f"height: {height_px_elem}px")
            style_str = "; ".join(style_parts) + ";"
            
            if img_src and not img_src.startswith("data:image/svg+xml"):
                html_parts.append(f'<img class="element image-element" src="{img_src}" style="{style_str}" alt="Decorative image">')
            else:
                # Show placeholder for decorative images without source
                html_parts.append(f'<div class="element" style="{style_str}background:#f0f0f0;border:2px dashed #999;display:flex;align-items:center;justify-content:center;color:#666;font-size:12px;">Decorative Image</div>')
        
        elif elem_type == "rectangle":
            width = element.get("width", 100)
            height = element.get("height", 100)
            width_px_elem = int(width * 96 / 72)
            height_px_elem = int(height * 96 / 72)
            fill = format_color(style.get("fill", "#ffffff"))
            stroke = format_color(style.get("stroke", "#000000"))
            stroke_width = style.get("strokeWidth", 1)
            
            style_parts = [style_str_base]
            style_parts.append(f"width: {width_px_elem}px")
            style_parts.append(f"height: {height_px_elem}px")
            style_parts.append(f"background-color: {fill}")
            if stroke_width > 0:
                style_parts.append(f"border: {stroke_width}px solid {stroke}")
            style_str = "; ".join(style_parts) + ";"
            
            html_parts.append(f'<div class="element rectangle-element" style="{style_str}"></div>')
        
        elif elem_type == "circle":
            radius = element.get("radius", 50)
            radius_px = int(radius * 96 / 72)
            fill = format_color(style.get("fill", "#ffffff"))
            stroke = format_color(style.get("stroke", "#000000"))
            stroke_width = style.get("strokeWidth", 1)
            
            style_parts = [style_str_base]
            style_parts.append(f"width: {radius_px * 2}px")
            style_parts.append(f"height: {radius_px * 2}px")
            style_parts.append(f"background-color: {fill}")
            if stroke_width > 0:
                style_parts.append(f"border: {stroke_width}px solid {stroke}")
            style_str = "; ".join(style_parts) + ";"
            
            html_parts.append(f'<div class="element circle-element" style="{style_str}"></div>')
        
        elif elem_type == "line":
            width = element.get("width", 100)
            height = element.get("height", 0)
            # For lines, width is the length, height is the stroke width (thickness)
            width_px_elem = int(width * 96 / 72)
            stroke_width = height if height > 0 else style.get("strokeWidth", 1)
            stroke_width_px = max(1, int(stroke_width * 96 / 72))
            stroke = format_color(style.get("stroke", "#000000"))
            
            style_parts = [style_str_base]
            style_parts.append(f"width: {width_px_elem}px")
            style_parts.append(f"height: {stroke_width_px}px")
            style_parts.append(f"background-color: {stroke}")
            style_str = "; ".join(style_parts) + ";"
            
            html_parts.append(f'<div class="element line-element" style="{style_str}"></div>')
        
        elif elem_type == "table":
            width = element.get("width", 500)
            width_px_elem = int(width * 96 / 72)
            columns = element.get("columns", [])
            row_template = element.get("row_template", {})
            
            # Get table style properties
            table_style = element.get("style", {})
            border_color = format_color(table_style.get("borderColor", "#000000"))
            header_bg = format_color(table_style.get("headerBackground", "#f8f9fa"))
            
            style_parts = [style_str_base]
            style_parts.append(f"width: {width_px_elem}px")
            style_parts.append(f"border: 1px solid {border_color}")
            style_str = "; ".join(style_parts) + ";"
            
            table_html = f'<table class="element table-element" style="{style_str}"><thead><tr>'
            
            # Build header row
            for col in columns:
                header = col.get("header", "")
                align = col.get("align", "left")
                col_width = col.get("width", None)
                width_attr = f' width="{int(col_width * 96 / 72)}px"' if col_width else ""
                table_html += f'<th style="text-align: {align}; background-color: {header_bg};"{width_attr}>{html_escape.escape(header)}</th>'
            table_html += '</tr></thead><tbody>'
            
            # Build data rows with actual invoice/quote data
            data_obj = invoice if invoice else quote
            items = []
            if data_obj and hasattr(data_obj, "items"):
                try:
                    if hasattr(data_obj.items, "all"):
                        items = data_obj.items.all()
                    elif isinstance(data_obj.items, list):
                        items = data_obj.items
                    else:
                        items = list(data_obj.items) if data_obj.items else []
                except Exception:
                    items = []
            
            # If no items available, create sample row from template
            if not items and row_template:
                items = [row_template]  # Use template as sample data
            
            # Render table rows with actual data
            if items:
                for item in items[:10]:  # Limit to 10 rows for preview
                    table_html += '<tr>'
                    for col in columns:
                        field = col.get("field", "")
                        align = col.get("align", "left")
                        # Try to get value from item
                        value = ""
                        try:
                            if hasattr(item, field):
                                value = str(getattr(item, field, ""))
                            elif isinstance(item, dict):
                                value = str(item.get(field, ""))
                            else:
                                value = ""
                        except Exception:
                            value = ""
                        
                        value_escaped = html_escape.escape(str(value))
                        table_html += f'<td style="text-align: {align};">{value_escaped}</td>'
                    table_html += '</tr>'
            else:
                # No data available, show template placeholders
                table_html += '<tr>'
                for col in columns:
                    field = col.get("field", "")
                    align = col.get("align", "left")
                    placeholder = f"{{{{ {field} }}}}"
                    table_html += f'<td style="text-align: {align}; color: #999;">{html_escape.escape(placeholder)}</td>'
                table_html += '</tr>'
            
            table_html += '</tbody></table>'
            html_parts.append(table_html)
    
    html_parts.append('</div>')
    html = '\n'.join(html_parts)
    
    return html, css


def admin_required(f):
    """Decorator to require admin access

    DEPRECATED: Use @admin_or_permission_required() with specific permissions instead.
    This decorator is kept for backward compatibility.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_("Administrator access required"), "error")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def allowed_logo_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


def get_upload_folder():
    """Get the upload folder path for logos"""
    upload_folder = os.path.join(current_app.root_path, "static", "uploads", "logos")
    try:
        os.makedirs(upload_folder, exist_ok=True)
        current_app.logger.info(f"Logo upload folder ensured: {upload_folder}")
    except Exception as e:
        current_app.logger.error(f"Error creating upload folder {upload_folder}: {str(e)}")
        raise
    return upload_folder


@admin_bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    from app.config import Config

    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status="active").count()
    total_entries = TimeEntry.query.filter(TimeEntry.end_time.isnot(None)).count()
    active_timers = TimeEntry.query.filter_by(end_time=None).count()

    # Get recent activity
    recent_entries = (
        TimeEntry.query.filter(TimeEntry.end_time.isnot(None)).order_by(TimeEntry.created_at.desc()).limit(10).all()
    )

    # Get OIDC status
    auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    oidc_enabled = auth_method in ("oidc", "both")
    oidc_issuer = getattr(Config, "OIDC_ISSUER", None)
    oidc_configured = (
        oidc_enabled
        and oidc_issuer
        and getattr(Config, "OIDC_CLIENT_ID", None)
        and getattr(Config, "OIDC_CLIENT_SECRET", None)
    )

    # Count OIDC users
    oidc_users_count = 0
    try:
        oidc_users_count = User.query.filter(User.oidc_issuer.isnot(None), User.oidc_sub.isnot(None)).count()
    except Exception as e:
        # Log error but continue - OIDC user count is not critical for dashboard display
        current_app.logger.warning(f"Failed to count OIDC users: {e}", exc_info=True)

    # Build stats object expected by the template
    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_entries": total_entries,
        "total_hours": TimeEntry.get_total_hours_for_period(),
        "billable_hours": TimeEntry.get_total_hours_for_period(billable_only=True),
        "last_backup": None,
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        active_timers=active_timers,
        recent_entries=recent_entries,
        oidc_enabled=oidc_enabled,
        oidc_configured=oidc_configured,
        oidc_auth_method=auth_method,
        oidc_users_count=oidc_users_count,
    )


# Compatibility alias for code/templates that might reference 'admin.dashboard'
@admin_bp.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard_alias():
    """Alias endpoint so url_for('admin.dashboard') remains valid.

    Some older references may use the endpoint name 'admin.dashboard'.
    Redirect to the canonical admin dashboard endpoint.
    """
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users")
@login_required
@admin_or_permission_required("view_users")
def list_users():
    """List all users"""
    users = User.query.order_by(User.username).all()

    # Build stats for users page
    stats = {
        "total_users": User.query.count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "admin_users": User.query.filter_by(role="admin").count(),
        "total_hours": TimeEntry.get_total_hours_for_period(),
    }

    return render_template("admin/users.html", users=users, stats=stats)


@admin_bp.route("/admin/users/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("create_users")
def create_user():
    """Create a new user"""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        role_name = request.form.get("role", "user")  # This will be a role name from the Role system
        default_password = request.form.get("default_password", "").strip()
        force_password_change = request.form.get("force_password_change") == "on"

        if not username:
            flash(_("Username is required"), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/user_form.html", user=None, all_roles=all_roles)

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash(_("User already exists"), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/user_form.html", user=None, all_roles=all_roles)

        # Get the Role object from the database
        role_obj = Role.query.filter_by(name=role_name).first()
        if not role_obj:
            # Fallback: if role doesn't exist, try to use "user" role
            role_obj = Role.query.filter_by(name="user").first()
            if not role_obj:
                flash(_("Default 'user' role not found. Please run 'flask seed_permissions_cmd' first."), "error")
                all_roles = Role.query.order_by(Role.name).all()
                return render_template("admin/user_form.html", user=None, all_roles=all_roles)

        # Create user with legacy role field for backward compatibility
        user = User(username=username, role=role_name)

        # Assign the role from the new Role system
        user.roles.append(role_obj)

        # Set default password if provided
        if default_password:
            user.set_password(default_password)
            if force_password_change:
                user.password_change_required = True

        db.session.add(user)
        if not safe_commit("admin_create_user", {"username": username}):
            flash(_("Could not create user due to a database error. Please check server logs."), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/user_form.html", user=None, all_roles=all_roles)

        flash(_('User "%(username)s" created successfully', username=username), "success")
        return redirect(url_for("admin.list_users"))

    # GET request - show form with available roles
    all_roles = Role.query.order_by(Role.name).all()
    return render_template("admin/user_form.html", user=None, all_roles=all_roles)


@admin_bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("edit_users")
def edit_user(user_id):
    """Edit an existing user"""
    from app.models import Client

    user = User.query.get_or_404(user_id)
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    all_roles = Role.query.order_by(Role.name).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        role_name = request.form.get("role", "user")  # This will be a role name from the Role system
        is_active = request.form.get("is_active") == "on"
        client_portal_enabled = request.form.get("client_portal_enabled") == "on"
        client_id = request.form.get("client_id", "").strip()

        if not username:
            flash(_("Username is required"), "error")
            return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

        # Check if username is already taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash(_("Username already exists"), "error")
            return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

        # Validate client portal settings
        if client_portal_enabled and not client_id:
            flash(_("Please select a client when enabling client portal access."), "error")
            return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

        # Get the Role object from the database
        role_obj = Role.query.filter_by(name=role_name).first()
        if not role_obj:
            # Fallback: if role doesn't exist, try to use "user" role
            role_obj = Role.query.filter_by(name="user").first()
            if not role_obj:
                flash(_("Default 'user' role not found. Please run 'flask seed_permissions_cmd' first."), "error")
                return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

        # Handle password reset if provided
        new_password = request.form.get("new_password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()
        force_password_change = request.form.get("force_password_change") == "on"

        if new_password:
            # Validate password
            if len(new_password) < 8:
                flash(_("Password must be at least 8 characters long."), "error")
                return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

            if new_password != password_confirm:
                flash(_("Passwords do not match."), "error")
                return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

            # Set the new password
            user.set_password(new_password)
            if force_password_change:
                user.password_change_required = True
            else:
                user.password_change_required = False
            current_app.logger.info("Admin '%s' reset password for user '%s'", current_user.username, user.username)

        # Update user
        user.username = username
        # Update legacy role field for backward compatibility
        user.role = role_name
        
        # Update roles in the new system
        # If user doesn't have the selected role, assign it as the primary role
        # Keep other roles if they exist (multi-role support)
        if role_obj not in user.roles:
            # If user has no roles, assign the selected one
            if not user.roles:
                user.roles.append(role_obj)
            else:
                # If user has roles, replace the first one (primary role) with the selected one
                # This maintains backward compatibility while supporting multi-role
                user.roles[0] = role_obj
        else:
            # If the selected role is already assigned but not first, move it to first position
            if user.roles[0] != role_obj:
                user.roles.remove(role_obj)
                user.roles.insert(0, role_obj)
        
        user.is_active = is_active
        user.client_portal_enabled = client_portal_enabled
        user.client_id = int(client_id) if client_id else None

        if not safe_commit("admin_edit_user", {"user_id": user.id}):
            flash(_("Could not update user due to a database error. Please check server logs."), "error")
            return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)

        if new_password:
            flash(_('Password reset successfully for user "%(username)s"', username=username), "success")
        else:
            flash(_('User "%(username)s" updated successfully', username=username), "success")
        return redirect(url_for("admin.list_users"))

    return render_template("admin/user_form.html", user=user, clients=clients, all_roles=all_roles)


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("delete_users")
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    # Don't allow deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(role="admin", is_active=True).count()
        if admin_count <= 1:
            flash(_("Cannot delete the last administrator"), "error")
            return redirect(url_for("admin.list_users"))

    # Don't allow deleting users with time entries
    if user.time_entries.count() > 0:
        flash(_("Cannot delete user with existing time entries"), "error")
        return redirect(url_for("admin.list_users"))

    username = user.username
    db.session.delete(user)
    if not safe_commit("admin_delete_user", {"user_id": user.id}):
        flash(_("Could not delete user due to a database error. Please check server logs."), "error")
        return redirect(url_for("admin.list_users"))

    flash(_('User "%(username)s" deleted successfully', username=username), "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/admin/telemetry")
@login_required
@admin_or_permission_required("manage_telemetry")
def telemetry_dashboard():
    """Telemetry and analytics dashboard"""
    installation_config = get_installation_config()

    # Get telemetry status
    telemetry_data = {
        "enabled": is_telemetry_enabled(),
        "setup_complete": installation_config.is_setup_complete(),
        "installation_id": installation_config.get_installation_id(),
        "telemetry_salt": installation_config.get_installation_salt()[:16] + "...",  # Show partial salt
        "fingerprint": get_telemetry_fingerprint(),
        "config": installation_config.get_all_config(),
    }

    # Get PostHog status
    posthog_data = {
        "enabled": bool(os.getenv("POSTHOG_API_KEY")),
        "host": os.getenv("POSTHOG_HOST", "https://app.posthog.com"),
        "api_key_set": bool(os.getenv("POSTHOG_API_KEY")),
    }

    # Get Sentry status
    sentry_data = {
        "enabled": bool(os.getenv("SENTRY_DSN")),
        "dsn_set": bool(os.getenv("SENTRY_DSN")),
        "traces_rate": os.getenv("SENTRY_TRACES_RATE", "0.0"),
    }

    # Log dashboard access
    app_module.log_event("admin.telemetry_dashboard_viewed", user_id=current_user.id)
    app_module.track_event(current_user.id, "admin.telemetry_dashboard_viewed", {})

    return render_template("admin/telemetry.html", telemetry=telemetry_data, posthog=posthog_data, sentry=sentry_data)


@admin_bp.route("/admin/telemetry/toggle", methods=["POST"])
@login_required
@admin_or_permission_required("manage_telemetry")
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
        flash(_("Telemetry has been enabled. Thank you for helping us improve!"), "success")
    else:
        flash(_("Telemetry has been disabled."), "info")

    return redirect(url_for("admin.telemetry_dashboard"))


@admin_bp.route("/admin/clear-cache")
@login_required
@admin_or_permission_required("manage_settings")
def clear_cache():
    """Cache clearing utility page"""
    return render_template("admin/clear_cache.html")


@admin_bp.route("/admin/modules", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def manage_modules():
    """Manage module visibility - enable/disable modules system-wide"""
    from app.utils.module_registry import ModuleRegistry, ModuleCategory
    
    # Initialize registry
    ModuleRegistry.initialize_defaults()
    
    # Get settings to access disabled_module_ids
    settings_obj = Settings.get_settings()
    
    # Module visibility: non-CORE modules for admin toggles
    modules_by_category = {}
    for cat in ModuleCategory:
        mods = [m for m in ModuleRegistry.get_by_category(cat) if m.category != ModuleCategory.CORE]
        if mods:
            modules_by_category[cat] = mods
    
    if request.method == "POST":
        # Module visibility: build disabled_module_ids from unchecked module_enabled_* checkboxes
        if hasattr(settings_obj, "disabled_module_ids"):
            disabled = []
            for mods in modules_by_category.values():
                for m in mods:
                    if ("module_enabled_" + m.id) not in request.form:
                        disabled.append(m.id)
            
            # Validate module dependencies before saving
            validation_errors = []
            for module_id in disabled:
                can_disable, affected = ModuleRegistry.validate_module_disable(module_id, disabled)
                if not can_disable and affected:
                    module = ModuleRegistry.get(module_id)
                    module_name = module.name if module else module_id
                    affected_names = [ModuleRegistry.get(aid).name if ModuleRegistry.get(aid) else aid for aid in affected]
                    validation_errors.append(
                        _("Cannot disable '%(module)s' because the following modules depend on it: %(dependents)s",
                          module=module_name, dependents=", ".join(affected_names))
                    )
            
            if validation_errors:
                for error in validation_errors:
                    flash(error, "error")
                return render_template(
                    "admin/modules.html",
                    modules_by_category=modules_by_category,
                    ModuleCategory=ModuleCategory,
                    settings=settings_obj,
                )
            
            settings_obj.disabled_module_ids = disabled
            
            # Ensure settings object is in the session
            if settings_obj not in db.session:
                db.session.add(settings_obj)
            
            if not safe_commit("admin_update_module_visibility"):
                flash(_("Could not update module visibility due to a database error. Please check server logs."), "error")
                return render_template(
                    "admin/modules.html",
                    modules_by_category=modules_by_category,
                    ModuleCategory=ModuleCategory,
                    settings=settings_obj,
                )
            
            flash(_("Module visibility updated successfully"), "success")
            return redirect(url_for("admin.manage_modules"))
    
    return render_template(
        "admin/modules.html",
        modules_by_category=modules_by_category,
        ModuleCategory=ModuleCategory,
        settings=settings_obj,
    )


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def settings():
    """Manage system settings"""
    import os  # Ensure os is available in function scope
    settings_obj = Settings.get_settings()
    installation_config = get_installation_config()
    timezones = get_available_timezones()
    peppol_env_enabled = (os.getenv("PEPPOL_ENABLED", "false") or "").strip().lower() in {"1", "true", "yes", "y", "on"}

    # Sync analytics preference from installation config to database on load
    # (installation config is the source of truth for telemetry)
    if settings_obj.allow_analytics != installation_config.get_telemetry_preference():
        settings_obj.allow_analytics = installation_config.get_telemetry_preference()
        db.session.commit()

    # Prepare kiosk settings with safe defaults (in case migration hasn't run)
    kiosk_settings = {
        "kiosk_mode_enabled": getattr(settings_obj, "kiosk_mode_enabled", False),
        "kiosk_auto_logout_minutes": getattr(settings_obj, "kiosk_auto_logout_minutes", 15),
        "kiosk_allow_camera_scanning": getattr(settings_obj, "kiosk_allow_camera_scanning", True),
        "kiosk_require_reason_for_adjustments": getattr(settings_obj, "kiosk_require_reason_for_adjustments", False),
        "kiosk_default_movement_type": getattr(settings_obj, "kiosk_default_movement_type", "adjustment"),
    }

    if request.method == "POST":
        # Validate timezone
        timezone = request.form.get("timezone") or settings_obj.timezone
        try:
            import pytz

            pytz.timezone(timezone)  # This will raise an exception if timezone is invalid
        except pytz.exceptions.UnknownTimeZoneError:
            flash(_("Invalid timezone: %(timezone)s", timezone=timezone), "error")
            return render_template(
                "admin/settings.html",
                settings=settings_obj,
                timezones=timezones,
                kiosk_settings=kiosk_settings,
                peppol_env_enabled=peppol_env_enabled,
            )

        # Update basic settings
        settings_obj.timezone = timezone
        settings_obj.currency = request.form.get("currency", "EUR")
        settings_obj.rounding_minutes = int(request.form.get("rounding_minutes", 1))
        settings_obj.single_active_timer = request.form.get("single_active_timer") == "on"
        settings_obj.allow_self_register = request.form.get("allow_self_register") == "on"
        settings_obj.idle_timeout_minutes = int(request.form.get("idle_timeout_minutes", 30))
        settings_obj.backup_retention_days = int(request.form.get("backup_retention_days", 30))
        settings_obj.backup_time = request.form.get("backup_time", "02:00")
        settings_obj.export_delimiter = request.form.get("export_delimiter", ",")

        # Update company branding settings
        settings_obj.company_name = request.form.get("company_name", "Your Company Name")
        settings_obj.company_address = request.form.get("company_address", "Your Company Address")
        settings_obj.company_email = request.form.get("company_email", "info@yourcompany.com")
        settings_obj.company_phone = request.form.get("company_phone", "+1 (555) 123-4567")
        settings_obj.company_website = request.form.get("company_website", "www.yourcompany.com")
        settings_obj.company_tax_id = request.form.get("company_tax_id", "")
        settings_obj.company_bank_info = request.form.get("company_bank_info", "")

        # Update invoice defaults
        invoice_prefix_form = request.form.get("invoice_prefix", "INV")
        invoice_start_number_form = request.form.get("invoice_start_number", 1000)
        # #region agent log
        try:
            import json
            log_data = {"location": "admin.py:952", "message": "Saving invoice prefix and start number", "data": {"invoice_prefix_form": str(invoice_prefix_form), "invoice_start_number_form": str(invoice_start_number_form), "settings_obj_id": settings_obj.id if hasattr(settings_obj, "id") else "NO_ID"}, "timestamp": int(datetime.utcnow().timestamp() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "F"}
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data) + "\n")
        except: pass
        # #endregion
        settings_obj.invoice_prefix = invoice_prefix_form
        settings_obj.invoice_start_number = int(invoice_start_number_form)
        settings_obj.invoice_terms = request.form.get("invoice_terms", "Payment is due within 30 days of invoice date.")
        settings_obj.invoice_notes = request.form.get("invoice_notes", "Thank you for your business!")

        # Update Peppol e-invoicing settings (if columns exist)
        try:
            mode = (request.form.get("peppol_enabled_mode") or "env").strip().lower()
            if mode == "true":
                settings_obj.peppol_enabled = True
            elif mode == "false":
                settings_obj.peppol_enabled = False
            else:
                settings_obj.peppol_enabled = None

            settings_obj.peppol_sender_endpoint_id = (request.form.get("peppol_sender_endpoint_id", "") or "").strip()
            settings_obj.peppol_sender_scheme_id = (request.form.get("peppol_sender_scheme_id", "") or "").strip()
            settings_obj.peppol_sender_country = (request.form.get("peppol_sender_country", "") or "").strip()
            settings_obj.peppol_access_point_url = (request.form.get("peppol_access_point_url", "") or "").strip()

            token = (request.form.get("peppol_access_point_token", "") or "").strip()
            if token:
                settings_obj.peppol_access_point_token = token

            try:
                settings_obj.peppol_access_point_timeout = int(request.form.get("peppol_access_point_timeout", 30))
            except Exception:
                settings_obj.peppol_access_point_timeout = 30

            settings_obj.peppol_provider = (request.form.get("peppol_provider", "") or "").strip() or "generic"
            settings_obj.invoices_peppol_compliant = request.form.get("invoices_peppol_compliant") == "on"
        except AttributeError:
            # Peppol columns don't exist yet (migration not run)
            pass

        # Update kiosk mode settings (if columns exist)
        try:
            settings_obj.kiosk_mode_enabled = request.form.get("kiosk_mode_enabled") == "on"
            settings_obj.kiosk_auto_logout_minutes = int(request.form.get("kiosk_auto_logout_minutes", 15))
            settings_obj.kiosk_allow_camera_scanning = request.form.get("kiosk_allow_camera_scanning") == "on"
            settings_obj.kiosk_require_reason_for_adjustments = (
                request.form.get("kiosk_require_reason_for_adjustments") == "on"
            )
            settings_obj.kiosk_default_movement_type = request.form.get("kiosk_default_movement_type", "adjustment")
        except AttributeError:
            # Kiosk columns don't exist yet (migration not run)
            pass

        # Update privacy and analytics settings
        allow_analytics = request.form.get("allow_analytics") == "on"
        old_analytics_state = settings_obj.allow_analytics
        settings_obj.allow_analytics = allow_analytics

        # Also update the installation config (used by telemetry system)
        # This ensures the telemetry system sees the updated preference
        installation_config.set_telemetry_preference(allow_analytics)

        # Log analytics preference change if it changed
        if old_analytics_state != allow_analytics:
            app_module.log_event("admin.analytics_toggled", user_id=current_user.id, new_state=allow_analytics)
            app_module.track_event(current_user.id, "admin.analytics_toggled", {"enabled": allow_analytics})

        # Ensure settings object is in the session (important for new instances)
        if settings_obj not in db.session:
            db.session.add(settings_obj)

        if not safe_commit("admin_update_settings"):
            flash(_("Could not update settings due to a database error. Please check server logs."), "error")
            return render_template(
                "admin/settings.html",
                settings=settings_obj,
                timezones=timezones,
                kiosk_settings=kiosk_settings,
                peppol_env_enabled=peppol_env_enabled,
            )
        # #region agent log
        try:
            import json
            log_data = {"location": "admin.py:1027", "message": "After commit - settings values", "data": {"invoice_prefix": str(settings_obj.invoice_prefix), "invoice_start_number": int(settings_obj.invoice_start_number), "settings_obj_id": settings_obj.id if hasattr(settings_obj, "id") else "NO_ID"}, "timestamp": int(datetime.utcnow().timestamp() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "G"}
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data) + "\n")
        except: pass
        # #endregion
        flash(_("Settings updated successfully"), "success")
        return redirect(url_for("admin.settings"))

    # Update kiosk_settings after potential POST update
    kiosk_settings = {
        "kiosk_mode_enabled": getattr(settings_obj, "kiosk_mode_enabled", False),
        "kiosk_auto_logout_minutes": getattr(settings_obj, "kiosk_auto_logout_minutes", 15),
        "kiosk_allow_camera_scanning": getattr(settings_obj, "kiosk_allow_camera_scanning", True),
        "kiosk_require_reason_for_adjustments": getattr(settings_obj, "kiosk_require_reason_for_adjustments", False),
        "kiosk_default_movement_type": getattr(settings_obj, "kiosk_default_movement_type", "adjustment"),
    }

    return render_template(
        "admin/settings.html",
        settings=settings_obj,
        timezones=timezones,
        kiosk_settings=kiosk_settings,
        peppol_env_enabled=peppol_env_enabled,
    )


@admin_bp.route("/admin/pdf-layout", methods=["GET", "POST"])
@limiter.limit("30 per minute", methods=["POST"])  # editor saves
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout():
    """Edit PDF invoice layout template (HTML and CSS) by page size."""
    from app.models import InvoicePDFTemplate

    # Get page size from query parameter or form, default to A4
    page_size_raw = request.args.get("size", request.form.get("page_size", "A4"))
    current_app.logger.info(f"[PDF_TEMPLATE] Action: template_editor_request, PageSize: '{page_size_raw}', Method: {request.method}, User: {current_user.username}")

    # Ensure valid page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(f"[PDF_TEMPLATE] Invalid page size '{page_size_raw}', defaulting to A4, User: {current_user.username}")
        page_size = "A4"
    else:
        page_size = page_size_raw

    current_app.logger.info(f"[PDF_TEMPLATE] Final validated PageSize: '{page_size}', Method: {request.method}, User: {current_user.username}")

    # Get or create template for this page size (ensures JSON exists)
    current_app.logger.info(f"[PDF_TEMPLATE] Retrieving template from database - PageSize: '{page_size}', User: {current_user.username}")
    template = InvoicePDFTemplate.get_template(page_size)
    current_app.logger.info(f"[PDF_TEMPLATE] Template retrieved - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: {bool(template.template_json)}, HasDesignJSON: {bool(template.design_json)}")

    if request.method == "POST":
        current_app.logger.info(f"[PDF_TEMPLATE] Action: template_save, PageSize: '{page_size}', User: {current_user.username}")
        html_template = request.form.get("invoice_pdf_template_html", "")
        css_template = request.form.get("invoice_pdf_template_css", "")
        design_json = request.form.get("design_json", "")
        template_json = request.form.get("template_json", "")  # ReportLab template JSON
        date_format = request.form.get("date_format", "%d.%m.%Y")  # Date format for this template

        current_app.logger.info(f"[PDF_TEMPLATE] Form data received - PageSize: '{page_size}', HTML length: {len(html_template)}, CSS length: {len(css_template)}, DesignJSON length: {len(design_json)}, TemplateJSON length: {len(template_json)}")

        # Validate and ensure template_json is present
        import json
        template_json_dict = None
        if template_json and template_json.strip():
            try:
                current_app.logger.info(f"[PDF_TEMPLATE] Parsing template JSON - PageSize: '{page_size}', JSON length: {len(template_json)}")
                template_json_dict = json.loads(template_json)
                # Ensure page size matches in JSON
                json_page_size = template_json_dict.get("page", {}).get("size")
                current_app.logger.info(f"[PDF_TEMPLATE] Template JSON page size before update: '{json_page_size}', Target PageSize: '{page_size}'")
                if "page" in template_json_dict and "size" in template_json_dict["page"]:
                    template_json_dict["page"]["size"] = page_size
                else:
                    # Add page size if missing
                    if "page" not in template_json_dict:
                        template_json_dict["page"] = {}
                    template_json_dict["page"]["size"] = page_size
                
                # CRITICAL: Ensure page dimensions (width/height) match the page size
                # This fixes layout issues when templates are customized
                from app.utils.pdf_template_schema import get_page_dimensions_mm
                template_page_config = template_json_dict.get("page", {})
                expected_dims = get_page_dimensions_mm(page_size)
                current_width = template_page_config.get("width")
                current_height = template_page_config.get("height")
                
                if current_width != expected_dims["width"] or current_height != expected_dims["height"]:
                    current_app.logger.info(
                        f"[PDF_TEMPLATE] Updating template page dimensions - PageSize: '{page_size}', "
                        f"Old: {current_width}x{current_height}mm, New: {expected_dims['width']}x{expected_dims['height']}mm, User: {current_user.username}"
                    )
                    template_page_config["width"] = expected_dims["width"]
                    template_page_config["height"] = expected_dims["height"]
                    template_json_dict["page"] = template_page_config
                
                template_json = json.dumps(template_json_dict)
                element_count = len(template_json_dict.get("elements", []))
                current_app.logger.info(f"[PDF_TEMPLATE] Template JSON parsed and updated - PageSize: '{page_size}', Elements: {element_count}, JSON length: {len(template_json)}")
            except json.JSONDecodeError as e:
                current_app.logger.error(f"[PDF_TEMPLATE] Invalid template_json provided - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}")
                flash(_("Invalid template JSON format. Please try again."), "error")
                return redirect(url_for("admin.pdf_layout", size=page_size))
        else:
            # If no template_json provided, generate default
            current_app.logger.warning(f"[PDF_TEMPLATE] No template_json provided, generating default - PageSize: '{page_size}', User: {current_user.username}")
            from app.utils.pdf_template_schema import get_default_template
            template_json_dict = get_default_template(page_size)
            template_json = json.dumps(template_json_dict)
            element_count = len(template_json_dict.get("elements", []))
            current_app.logger.info(f"[PDF_TEMPLATE] Generated default template JSON - PageSize: '{page_size}', Elements: {element_count}, User: {current_user.username}")

        # Normalize @page size in CSS to match the selected page size before saving
        # This ensures that saved templates always have the correct page size
        if css_template:
            from app.utils.pdf_generator import update_page_size_in_css, validate_page_size_in_css
            
            current_app.logger.info(f"[PDF_TEMPLATE] Normalizing CSS @page size - PageSize: '{page_size}', CSS length: {len(css_template)}")
            css_template = update_page_size_in_css(css_template, page_size)
            
            # Validate after normalization
            is_valid, found_sizes = validate_page_size_in_css(css_template, page_size)
            if not is_valid:
                current_app.logger.warning(
                    f"[PDF_TEMPLATE] CSS @page size normalization issue - PageSize: '{page_size}', Found sizes: {found_sizes}, User: {current_user.username}"
                )
            else:
                current_app.logger.info(f"[PDF_TEMPLATE] CSS @page size normalized successfully - PageSize: '{page_size}'")

        # Validate template_json before saving
        if not template_json or not template_json.strip():
            current_app.logger.error(f"[PDF_TEMPLATE] ERROR: template_json is empty - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
            flash(_("Error: Template JSON is empty. Please try saving again."), "error")
            return redirect(url_for("admin.pdf_layout", size=page_size))
        
        # Validate that template_json is valid JSON
        try:
            import json
            template_json_dict_validate = json.loads(template_json)
            if not isinstance(template_json_dict_validate, dict) or "page" not in template_json_dict_validate:
                current_app.logger.error(f"[PDF_TEMPLATE] ERROR: template_json is invalid (missing 'page' property) - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
                flash(_("Error: Template JSON is invalid. Please try saving again."), "error")
                return redirect(url_for("admin.pdf_layout", size=page_size))
            element_count = len(template_json_dict_validate.get("elements", []))
            current_app.logger.info(f"[PDF_TEMPLATE] Template JSON validated before save - PageSize: '{page_size}', Elements: {element_count}, JSON length: {len(template_json)}, TemplateID: {template.id}, User: {current_user.username}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"[PDF_TEMPLATE] ERROR: template_json is not valid JSON - PageSize: '{page_size}', TemplateID: {template.id}, Error: {str(e)}, User: {current_user.username}")
            flash(_("Error: Template JSON is not valid JSON. Please try saving again."), "error")
            return redirect(url_for("admin.pdf_layout", size=page_size))

        # Update template (save both legacy HTML/CSS and new JSON format)
        current_app.logger.info(f"[PDF_TEMPLATE] Updating template in database - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
        template.template_html = html_template
        template.template_css = css_template
        template.design_json = design_json
        template.template_json = template_json  # ReportLab template JSON (always present now)
        template.date_format = date_format  # Date format for this template
        template.updated_at = datetime.utcnow()

        # For backwards compatibility, also update Settings when saving A4 (default)
        if page_size == "A4":
            current_app.logger.info(f"[PDF_TEMPLATE] Also updating Settings for A4 default - User: {current_user.username}")
            settings_obj = Settings.get_settings()
            settings_obj.invoice_pdf_template_html = html_template
            settings_obj.invoice_pdf_template_css = css_template
            settings_obj.invoice_pdf_design_json = design_json

        current_app.logger.info(f"[PDF_TEMPLATE] Committing template to database - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
        if not safe_commit("admin_update_pdf_layout"):
            from flask_babel import gettext as _
            current_app.logger.error(f"[PDF_TEMPLATE] Database commit failed - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
            flash(_("Could not update PDF layout due to a database error."), "error")
        else:
            from flask_babel import gettext as _
            # Verify that template_json was actually saved
            db.session.refresh(template)
            if template.template_json and template.template_json.strip() and template.template_json == template_json:
                current_app.logger.info(f"[PDF_TEMPLATE] Template saved successfully - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: True, JSON length: {len(template.template_json)}, User: {current_user.username}")
                flash(_("PDF layout updated successfully"), "success")
            else:
                current_app.logger.error(f"[PDF_TEMPLATE] WARNING: Template saved but template_json verification failed - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: {bool(template.template_json)}, User: {current_user.username}")
                flash(_("PDF layout saved but template JSON verification failed. Please check the template."), "warning")
        return redirect(url_for("admin.pdf_layout", size=page_size))

    # Get all templates for dropdown
    all_templates = InvoicePDFTemplate.get_all_templates()
    current_app.logger.info(f"[PDF_TEMPLATE] Loaded all templates for dropdown - Count: {len(all_templates)}, PageSize: '{page_size}', User: {current_user.username}")

    # DON'T call ensure_template_json() here - it may overwrite saved templates
    # Template should already have JSON if it was saved properly
    # Only validate JSON if it exists - don't generate defaults that might overwrite saved templates
    if template.template_json:
        try:
            import json
            template_json_check = json.loads(template.template_json)
            element_count = len(template_json_check.get("elements", []))
            json_page_size = template_json_check.get("page", {}).get("size", "unknown")
            current_app.logger.info(f"[PDF_TEMPLATE] Template JSON validated - PageSize: '{page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}, TemplateID: {template.id}")
        except Exception as e:
            current_app.logger.warning(f"[PDF_TEMPLATE] Template JSON validation check failed - PageSize: '{page_size}', Error: {str(e)}, TemplateID: {template.id}")

    # Provide initial defaults to the template if no custom HTML/CSS saved
    initial_html = template.template_html or ""
    initial_css = template.template_css or ""
    design_json = template.design_json or ""
    template_json = template.template_json or ""
    current_app.logger.info(f"[PDF_TEMPLATE] Template loaded for editor - PageSize: '{page_size}', HTML length: {len(initial_html)}, CSS length: {len(initial_css)}, DesignJSON length: {len(design_json)}, TemplateJSON length: {len(template_json)}, TemplateID: {template.id}")

    # Fallback to legacy Settings if template is empty
    if not initial_html and not initial_css:
        settings_obj = Settings.get_settings()
        initial_html = settings_obj.invoice_pdf_template_html or ""
        initial_css = settings_obj.invoice_pdf_template_css or ""
        design_json = settings_obj.invoice_pdf_design_json or ""

    # Load default template if still empty
    try:
        if not initial_html:
            env = current_app.jinja_env
            html_src, _, _ = env.loader.get_source(env, "invoices/pdf_default.html")
            # Extract body only for editor
            try:
                import re as _re

                m = _re.search(r"<body[^>]*>([\s\S]*?)</body>", html_src, _re.IGNORECASE)
                initial_html = m.group(1).strip() if m else html_src
            except Exception as e:
                # Log but continue - template parsing failure is not critical
                current_app.logger.debug(f"Failed to parse PDF template HTML: {e}")
        if not initial_css:
            try:
                env = current_app.jinja_env
                css_src, _, _ = env.loader.get_source(env, "invoices/pdf_styles_default.css")
                initial_css = css_src
            except Exception as e:
                # Log but continue - CSS loading failure is not critical
                current_app.logger.debug(f"Failed to load default PDF CSS: {e}")
    except Exception as e:
        # Log but continue - PDF layout initialization failure is not critical
        current_app.logger.warning(f"Failed to initialize PDF layout defaults: {e}", exc_info=True)

    # Normalize @page size in initial CSS to match the selected page size
    # This ensures the editor always shows the correct page size
    if initial_css:
        from app.utils.pdf_generator import update_page_size_in_css
        initial_css = update_page_size_in_css(initial_css, page_size)

    return render_template(
        "admin/pdf_layout.html",
        settings=Settings.get_settings(),
        initial_html=initial_html,
        initial_css=initial_css,
        design_json=design_json,
        template_json=template_json,
        page_size=page_size,
        all_templates=all_templates,
        date_format=getattr(template, 'date_format', None) or '%d.%m.%Y',
    )


@admin_bp.route("/admin/pdf-layout/reset", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_reset():
    """Reset PDF layout to defaults (clear custom templates and regenerate default JSON)."""
    from app.models import InvoicePDFTemplate
    from app.utils.pdf_template_schema import get_default_template
    import json
    
    # Get page size from query parameter or form, default to A4
    page_size = request.args.get("size", request.form.get("page_size", "A4"))
    
    # Ensure valid page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        page_size = "A4"
    
    # Get or create template for this page size
    template = InvoicePDFTemplate.get_template(page_size)
    
    # Clear custom templates
    template.template_html = ""
    template.template_css = ""
    template.design_json = ""
    
    # Regenerate default JSON template
    default_json = get_default_template(page_size)
    template.template_json = json.dumps(default_json)
    template.updated_at = datetime.utcnow()
    
    # Also clear legacy Settings for A4
    if page_size == "A4":
        settings_obj = Settings.get_settings()
        settings_obj.invoice_pdf_template_html = ""
        settings_obj.invoice_pdf_template_css = ""
        settings_obj.invoice_pdf_design_json = ""
    
    if not safe_commit("admin_reset_pdf_layout"):
        flash(_("Could not reset PDF layout due to a database error."), "error")
    else:
        flash(_("PDF layout reset to defaults"), "success")
    return redirect(url_for("admin.pdf_layout", size=page_size))


@admin_bp.route("/admin/quote-pdf-layout", methods=["GET", "POST"])
@limiter.limit("30 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def quote_pdf_layout():
    """Edit PDF quote layout template (HTML and CSS) by page size."""
    from app.models import QuotePDFTemplate

    # Get page size from query parameter or form, default to A4
    page_size_raw = request.args.get("size", request.form.get("page_size", "A4"))
    current_app.logger.info(f"[PDF_TEMPLATE] Action: quote_template_editor_request, PageSize: '{page_size_raw}', Method: {request.method}, User: {current_user.username}")

    # Ensure valid page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(f"[PDF_TEMPLATE] Invalid page size '{page_size_raw}', defaulting to A4, User: {current_user.username}")
        page_size = "A4"
    else:
        page_size = page_size_raw

    current_app.logger.info(f"[PDF_TEMPLATE] Final validated PageSize: '{page_size}', Method: {request.method}, User: {current_user.username}")

    # Get or create template for this page size (ensures JSON exists)
    current_app.logger.info(f"[PDF_TEMPLATE] Retrieving quote template from database - PageSize: '{page_size}', User: {current_user.username}")
    template = QuotePDFTemplate.get_template(page_size)
    current_app.logger.info(f"[PDF_TEMPLATE] Quote template retrieved - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: {bool(template.template_json)}, HasDesignJSON: {bool(template.design_json)}")

    if request.method == "POST":
        current_app.logger.info(f"[PDF_TEMPLATE] Action: quote_template_save, PageSize: '{page_size}', User: {current_user.username}")
        html_template = request.form.get("quote_pdf_template_html", "")
        css_template = request.form.get("quote_pdf_template_css", "")
        design_json = request.form.get("design_json", "")
        template_json = request.form.get("template_json", "")  # ReportLab template JSON
        date_format = request.form.get("date_format", "%d.%m.%Y")  # Date format for this template

        current_app.logger.info(f"[PDF_TEMPLATE] Form data received - PageSize: '{page_size}', HTML length: {len(html_template)}, CSS length: {len(css_template)}, DesignJSON length: {len(design_json)}, TemplateJSON length: {len(template_json)}")

        # Validate and ensure template_json is present
        import json
        template_json_dict = None
        if template_json and template_json.strip():
            try:
                current_app.logger.info(f"[PDF_TEMPLATE] Parsing quote template JSON - PageSize: '{page_size}', JSON length: {len(template_json)}")
                template_json_dict = json.loads(template_json)
                # Ensure page size matches in JSON
                json_page_size = template_json_dict.get("page", {}).get("size")
                current_app.logger.info(f"[PDF_TEMPLATE] Quote template JSON page size before update: '{json_page_size}', Target PageSize: '{page_size}'")
                if "page" in template_json_dict and "size" in template_json_dict["page"]:
                    template_json_dict["page"]["size"] = page_size
                else:
                    # Add page size if missing
                    if "page" not in template_json_dict:
                        template_json_dict["page"] = {}
                    template_json_dict["page"]["size"] = page_size
                
                # CRITICAL: Ensure page dimensions (width/height) match the page size
                # This fixes layout issues when templates are customized
                from app.utils.pdf_template_schema import get_page_dimensions_mm
                template_page_config = template_json_dict.get("page", {})
                expected_dims = get_page_dimensions_mm(page_size)
                current_width = template_page_config.get("width")
                current_height = template_page_config.get("height")
                
                if current_width != expected_dims["width"] or current_height != expected_dims["height"]:
                    current_app.logger.info(
                        f"[PDF_TEMPLATE] Updating quote template page dimensions - PageSize: '{page_size}', "
                        f"Old: {current_width}x{current_height}mm, New: {expected_dims['width']}x{expected_dims['height']}mm, User: {current_user.username}"
                    )
                    template_page_config["width"] = expected_dims["width"]
                    template_page_config["height"] = expected_dims["height"]
                    template_json_dict["page"] = template_page_config
                
                template_json = json.dumps(template_json_dict)
                element_count = len(template_json_dict.get("elements", []))
                current_app.logger.info(f"[PDF_TEMPLATE] Quote template JSON parsed and updated - PageSize: '{page_size}', Elements: {element_count}, JSON length: {len(template_json)}")
            except json.JSONDecodeError as e:
                current_app.logger.error(f"[PDF_TEMPLATE] Invalid quote template_json provided - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}")
                flash(_("Invalid template JSON format. Please try again."), "error")
                return redirect(url_for("admin.quote_pdf_layout", size=page_size))
        else:
            # If no template_json provided, generate default
            current_app.logger.warning(f"[PDF_TEMPLATE] No quote template_json provided, generating default - PageSize: '{page_size}', User: {current_user.username}")
            from app.utils.pdf_template_schema import get_default_template
            template_json_dict = get_default_template(page_size)
            template_json = json.dumps(template_json_dict)
            element_count = len(template_json_dict.get("elements", []))
            current_app.logger.info(f"[PDF_TEMPLATE] Generated default quote template JSON - PageSize: '{page_size}', Elements: {element_count}, User: {current_user.username}")

        # Normalize @page size in CSS to match the selected page size before saving
        # This ensures that saved templates always have the correct page size
        if css_template:
            from app.utils.pdf_generator import update_page_size_in_css, validate_page_size_in_css

            current_app.logger.info(f"[PDF_TEMPLATE] Normalizing quote CSS @page size - PageSize: '{page_size}', CSS length: {len(css_template)}")
            css_template = update_page_size_in_css(css_template, page_size)

            # Validate after normalization
            is_valid, found_sizes = validate_page_size_in_css(css_template, page_size)
            if not is_valid:
                current_app.logger.warning(
                    f"[PDF_TEMPLATE] Quote CSS @page size normalization issue - PageSize: '{page_size}', Found sizes: {found_sizes}, User: {current_user.username}"
                )
            else:
                current_app.logger.info(f"[PDF_TEMPLATE] Quote CSS @page size normalized successfully - PageSize: '{page_size}'")

        # Update template (save both legacy HTML/CSS and new JSON format)
        current_app.logger.info(f"[PDF_TEMPLATE] Updating quote template in database - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
        template.template_html = html_template
        template.template_css = css_template
        template.design_json = design_json
        # Validate template_json before saving
        if not template_json or not template_json.strip():
            current_app.logger.error(f"[PDF_TEMPLATE] ERROR: Quote template_json is empty - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
            flash(_("Error: Template JSON is empty. Please try saving again."), "error")
            return redirect(url_for("admin.quote_pdf_layout", size=page_size))
        
        # Validate that template_json is valid JSON
        try:
            import json
            template_json_dict_validate = json.loads(template_json)
            if not isinstance(template_json_dict_validate, dict) or "page" not in template_json_dict_validate:
                current_app.logger.error(f"[PDF_TEMPLATE] ERROR: Quote template_json is invalid (missing 'page' property) - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
                flash(_("Error: Template JSON is invalid. Please try saving again."), "error")
                return redirect(url_for("admin.quote_pdf_layout", size=page_size))
            element_count = len(template_json_dict_validate.get("elements", []))
            current_app.logger.info(f"[PDF_TEMPLATE] Quote template JSON validated before save - PageSize: '{page_size}', Elements: {element_count}, JSON length: {len(template_json)}, TemplateID: {template.id}, User: {current_user.username}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"[PDF_TEMPLATE] ERROR: Quote template_json is not valid JSON - PageSize: '{page_size}', TemplateID: {template.id}, Error: {str(e)}, User: {current_user.username}")
            flash(_("Error: Template JSON is not valid JSON. Please try saving again."), "error")
            return redirect(url_for("admin.quote_pdf_layout", size=page_size))
        
        template.template_json = template_json  # ReportLab template JSON (always present now)
        template.date_format = date_format  # Date format for this template
        template.updated_at = datetime.utcnow()

        current_app.logger.info(f"[PDF_TEMPLATE] Committing quote template to database - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
        if not safe_commit("admin_update_quote_pdf_layout"):
            current_app.logger.error(f"[PDF_TEMPLATE] Quote template database commit failed - PageSize: '{page_size}', TemplateID: {template.id}, User: {current_user.username}")
            flash(_("Could not update PDF layout due to a database error."), "error")
        else:
            # Verify that template_json was actually saved
            db.session.refresh(template)
            if template.template_json and template.template_json.strip() and template.template_json == template_json:
                current_app.logger.info(f"[PDF_TEMPLATE] Quote template saved successfully - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: True, JSON length: {len(template.template_json)}, User: {current_user.username}")
                flash(_("PDF layout updated successfully"), "success")
            else:
                current_app.logger.error(f"[PDF_TEMPLATE] WARNING: Quote template saved but template_json verification failed - PageSize: '{page_size}', TemplateID: {template.id}, HasJSON: {bool(template.template_json)}, User: {current_user.username}")
                flash(_("PDF layout saved but template JSON verification failed. Please check the template."), "warning")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))

    # Get all templates for dropdown
    all_templates = QuotePDFTemplate.get_all_templates()
    current_app.logger.info(f"[PDF_TEMPLATE] Loaded all quote templates for dropdown - Count: {len(all_templates)}, PageSize: '{page_size}', User: {current_user.username}")

    # DON'T call ensure_template_json() here - it may overwrite saved templates
    # Template should already have JSON if it was saved properly
    # Only validate JSON if it exists - don't generate defaults that might overwrite saved templates
    if template.template_json:
        try:
            import json
            template_json_check = json.loads(template.template_json)
            element_count = len(template_json_check.get("elements", []))
            json_page_size = template_json_check.get("page", {}).get("size", "unknown")
            current_app.logger.info(f"[PDF_TEMPLATE] Quote template JSON validated - PageSize: '{page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}, TemplateID: {template.id}")
        except Exception as e:
            current_app.logger.warning(f"[PDF_TEMPLATE] Quote template JSON validation check failed - PageSize: '{page_size}', Error: {str(e)}, TemplateID: {template.id}")

    # Provide initial defaults
    initial_html = template.template_html or ""
    initial_css = template.template_css or ""
    design_json = template.design_json or ""
    template_json = template.template_json or ""
    current_app.logger.info(f"[PDF_TEMPLATE] Quote template loaded for editor - PageSize: '{page_size}', HTML length: {len(initial_html)}, CSS length: {len(initial_css)}, DesignJSON length: {len(design_json)}, TemplateJSON length: {len(template_json)}, TemplateID: {template.id}")

    # Load default template if empty
    try:
        if not initial_html:
            env = current_app.jinja_env
            html_src, _unused1, _unused2 = env.loader.get_source(env, "quotes/pdf_default.html")
            try:
                import re as _re

                m = _re.search(r"<body[^>]*>([\s\S]*?)</body>", html_src, _re.IGNORECASE)
                initial_html = m.group(1).strip() if m else html_src
            except Exception:
                pass
        if not initial_css:
            env = current_app.jinja_env
            css_src, _unused3, _unused4 = env.loader.get_source(env, "quotes/pdf_styles_default.css")
            initial_css = css_src
    except Exception:
        pass

    # Normalize @page size in initial CSS to match the selected page size
    # This ensures the editor always shows the correct page size
    if initial_css:
        from app.utils.pdf_generator import update_page_size_in_css
        initial_css = update_page_size_in_css(initial_css, page_size)

    return render_template(
        "admin/quote_pdf_layout.html",
        settings=Settings.get_settings(),
        initial_html=initial_html,
        initial_css=initial_css,
        design_json=design_json,
        template_json=template_json,
        page_size=page_size,
        all_templates=all_templates,
        date_format=getattr(template, 'date_format', None) or '%d.%m.%Y',
    )


@admin_bp.route("/admin/quote-pdf-layout/reset", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def quote_pdf_layout_reset():
    """Reset quote PDF layout to defaults (clear custom templates and regenerate default JSON)."""
    from app.models import QuotePDFTemplate
    from app.utils.pdf_template_schema import get_default_template
    import json

    # Get page size from query parameter or form, default to A4
    page_size = request.args.get("size", request.form.get("page_size", "A4"))

    # Ensure valid page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        page_size = "A4"

    # Get or create template for this page size
    template = QuotePDFTemplate.get_template(page_size)

    # Clear custom templates
    template.template_html = ""
    template.template_css = ""
    template.design_json = ""
    
    # Regenerate default JSON template
    default_json = get_default_template(page_size)
    template.template_json = json.dumps(default_json)
    template.updated_at = datetime.utcnow()

    if not safe_commit("admin_reset_quote_pdf_layout"):
        flash(_("Could not reset PDF layout due to a database error."), "error")
    else:
        flash(_("PDF layout reset to defaults"), "success")
    return redirect(url_for("admin.quote_pdf_layout", size=page_size))


@admin_bp.route("/admin/quote-pdf-layout/export-json/<page_size>", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def quote_pdf_layout_export_json(page_size):
    """Export quote PDF template as JSON file."""
    from app.models import QuotePDFTemplate
    from io import BytesIO
    
    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        flash(_("Invalid page size"), "error")
        return redirect(url_for("admin.quote_pdf_layout", size="A4"))
    
    # Get template
    template = QuotePDFTemplate.query.filter_by(page_size=page_size).first()
    if not template:
        flash(_("Template not found for this page size"), "error")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))
    
    # Get template JSON
    template_json = template.template_json or "{}"
    
    # Create file-like object
    output = BytesIO()
    output.write(template_json.encode('utf-8'))
    output.seek(0)
    
    # Return as downloadable file
    filename = f"quote_pdf_template_{page_size}.json"
    return send_file(
        output,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )


@admin_bp.route("/admin/quote-pdf-layout/import-json", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def quote_pdf_layout_import_json():
    """Import quote PDF template from JSON file."""
    from app.models import QuotePDFTemplate
    from app.utils.pdf_template_schema import get_page_dimensions_mm
    import json
    
    # Get page size from form or detect from JSON
    page_size = request.form.get("page_size", "A4")
    
    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        page_size = "A4"
    
    # Check if file was uploaded
    if 'json_file' not in request.files:
        flash(_("No file uploaded"), "error")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))
    
    file = request.files['json_file']
    if file.filename == '':
        flash(_("No file selected"), "error")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))
    
    # Read and parse JSON
    try:
        file_content = file.read().decode('utf-8')
        template_json_dict = json.loads(file_content)
        
        # Validate JSON structure
        if not isinstance(template_json_dict, dict) or "page" not in template_json_dict:
            flash(_("Invalid template JSON format. Missing 'page' property."), "error")
            return redirect(url_for("admin.quote_pdf_layout", size=page_size))
        
        # Detect page size from JSON if not provided
        json_page_size = template_json_dict.get("page", {}).get("size")
        if json_page_size and json_page_size in valid_sizes:
            page_size = json_page_size
        
        # Update page size in JSON
        template_json_dict["page"]["size"] = page_size
        
        # Ensure page dimensions match
        expected_dims = get_page_dimensions_mm(page_size)
        template_page_config = template_json_dict.get("page", {})
        template_page_config["width"] = expected_dims["width"]
        template_page_config["height"] = expected_dims["height"]
        template_json_dict["page"] = template_page_config
        
        # Get or create template
        template = QuotePDFTemplate.get_template(page_size)
        
        # Update template JSON
        template.template_json = json.dumps(template_json_dict)
        template.updated_at = datetime.utcnow()
        
        if not safe_commit("admin_import_quote_pdf_layout_json"):
            flash(_("Could not import template due to a database error."), "error")
        else:
            flash(_("Template imported successfully"), "success")
        
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))
        
    except json.JSONDecodeError as e:
        flash(_("Invalid JSON file: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))
    except Exception as e:
        current_app.logger.error(f"Error importing quote PDF template JSON: {e}", exc_info=True)
        flash(_("Error importing template: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.quote_pdf_layout", size=page_size))


@admin_bp.route("/admin/pdf-layout/export-json/<page_size>", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_export_json(page_size):
    """Export invoice PDF template as JSON file."""
    from app.models import InvoicePDFTemplate
    from io import BytesIO
    
    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        flash(_("Invalid page size"), "error")
        return redirect(url_for("admin.pdf_layout", size="A4"))
    
    # Get template
    template = InvoicePDFTemplate.query.filter_by(page_size=page_size).first()
    if not template:
        flash(_("Template not found for this page size"), "error")
        return redirect(url_for("admin.pdf_layout", size=page_size))
    
    # Get template JSON
    template_json = template.template_json or "{}"
    
    # Create file-like object
    output = BytesIO()
    output.write(template_json.encode('utf-8'))
    output.seek(0)
    
    # Return as downloadable file
    filename = f"invoice_pdf_template_{page_size}.json"
    return send_file(
        output,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )


@admin_bp.route("/admin/pdf-layout/import-json", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_import_json():
    """Import invoice PDF template from JSON file."""
    from app.models import InvoicePDFTemplate
    from app.utils.pdf_template_schema import get_page_dimensions_mm
    import json
    
    # Get page size from form or detect from JSON
    page_size = request.form.get("page_size", "A4")
    
    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        page_size = "A4"
    
    # Check if file was uploaded
    if 'json_file' not in request.files:
        flash(_("No file uploaded"), "error")
        return redirect(url_for("admin.pdf_layout", size=page_size))
    
    file = request.files['json_file']
    if file.filename == '':
        flash(_("No file selected"), "error")
        return redirect(url_for("admin.pdf_layout", size=page_size))
    
    # Read and parse JSON
    try:
        file_content = file.read().decode('utf-8')
        template_json_dict = json.loads(file_content)
        
        # Validate JSON structure
        if not isinstance(template_json_dict, dict) or "page" not in template_json_dict:
            flash(_("Invalid template JSON format. Missing 'page' property."), "error")
            return redirect(url_for("admin.pdf_layout", size=page_size))
        
        # Detect page size from JSON if not provided
        json_page_size = template_json_dict.get("page", {}).get("size")
        if json_page_size and json_page_size in valid_sizes:
            page_size = json_page_size
        
        # Update page size in JSON
        template_json_dict["page"]["size"] = page_size
        
        # Ensure page dimensions match
        expected_dims = get_page_dimensions_mm(page_size)
        template_page_config = template_json_dict.get("page", {})
        template_page_config["width"] = expected_dims["width"]
        template_page_config["height"] = expected_dims["height"]
        template_json_dict["page"] = template_page_config
        
        # Get or create template
        template = InvoicePDFTemplate.get_template(page_size)
        
        # Update template JSON
        template.template_json = json.dumps(template_json_dict)
        template.updated_at = datetime.utcnow()
        
        if not safe_commit("admin_import_pdf_layout_json"):
            flash(_("Could not import template due to a database error."), "error")
        else:
            flash(_("Template imported successfully"), "success")
        
        return redirect(url_for("admin.pdf_layout", size=page_size))
        
    except json.JSONDecodeError as e:
        flash(_("Invalid JSON file: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.pdf_layout", size=page_size))
    except Exception as e:
        current_app.logger.error(f"Error importing invoice PDF template JSON: {e}", exc_info=True)
        flash(_("Error importing template: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.pdf_layout", size=page_size))


@admin_bp.route("/admin/pdf-layout/debug", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_debug():
    """Debug endpoint to show what's saved in the database"""
    settings_obj = Settings.get_settings()

    html = settings_obj.invoice_pdf_template_html or ""
    css = settings_obj.invoice_pdf_template_css or ""
    design_json = settings_obj.invoice_pdf_design_json or ""

    # Check for bugs
    has_all_bug = "invoice.items.all()" in html
    has_if_bug = "invoice.items and invoice.items.all()" in html

    # Get invoice info for testing
    from app.models import Invoice

    test_invoice = Invoice.query.order_by(Invoice.id.desc()).first()

    debug_info = {
        "saved_template": {
            "html_length": len(html),
            "css_length": len(css),
            "design_json_length": len(design_json),
            "has_html": bool(html),
            "has_bugs": has_all_bug or has_if_bug,
            "bugs_found": [],
        },
        "test_invoice": {
            "exists": test_invoice is not None,
            "invoice_number": test_invoice.invoice_number if test_invoice else None,
            "items_count": test_invoice.items.count() if test_invoice else 0,
        },
    }

    if has_all_bug:
        debug_info["saved_template"]["bugs_found"].append("invoice.items.all() found in template")
    if has_if_bug:
        debug_info["saved_template"]["bugs_found"].append("invoice.items and invoice.items.all() found in template")

    # Show snippets of problematic code
    if has_all_bug or has_if_bug:
        import re

        matches = re.finditer(r".{0,50}invoice\.items\.all\(\).{0,50}", html)
        debug_info["saved_template"]["bug_snippets"] = [m.group() for m in matches]

    return jsonify(debug_info)


@admin_bp.route("/admin/pdf-layout/default", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_default():
    """Return default HTML and CSS template sources for the PDF layout editor."""
    try:
        env = current_app.jinja_env
        # Get raw template sources, not rendered
        html_src, _, _ = env.loader.get_source(env, "invoices/pdf_default.html")
        # Extract only the body content for GrapesJS
        try:
            import re as _re

            match = _re.search(r"<body[^>]*>([\s\S]*?)</body>", html_src, _re.IGNORECASE)
            if match:
                html_src = match.group(1).strip()
        except Exception:
            pass
    except Exception:
        html_src = "<div class=\"wrapper\"><h1>{{ _('INVOICE') }} {{ invoice.invoice_number }}</h1></div>"
    try:
        css_src, _, _ = env.loader.get_source(env, "invoices/pdf_styles_default.css")
    except Exception:
        css_src = ""
    return jsonify(
        {
            "html": html_src,
            "css": css_src,
        }
    )


@admin_bp.route("/admin/pdf-layout/preview", methods=["POST"])
@limiter.limit("60 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def pdf_layout_preview():
    """Render a live preview of the provided HTML/CSS or JSON template using an invoice context."""
    html = request.form.get("html", "")
    css = request.form.get("css", "")
    template_json_str = request.form.get("template_json", "")  # JSON template from editor
    page_size_raw = request.form.get("page_size", "A4")  # Get page size from form
    invoice_id = request.form.get("invoice_id", type=int)
    
    current_app.logger.info(f"[PDF_PREVIEW] Action: invoice_preview_request, PageSize: '{page_size_raw}', HTML length: {len(html)}, CSS length: {len(css)}, TemplateJSON length: {len(template_json_str)}, InvoiceID: {invoice_id}, User: {current_user.username}")
    
    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(f"[PDF_PREVIEW] Invalid page size '{page_size_raw}', defaulting to A4, User: {current_user.username}")
        page_size = "A4"
    else:
        page_size = page_size_raw
    
    current_app.logger.info(f"[PDF_PREVIEW] Final validated PageSize: '{page_size}', TemplateJSON provided: {bool(template_json_str and template_json_str.strip())}")
    
    # CRITICAL: Always load saved template_json from database for preview
    # This ensures we use the ACTUAL saved template, not what's in the form (which might be empty)
    from app.models import InvoicePDFTemplate
    template_json_parsed = None
    saved_template = InvoicePDFTemplate.query.filter_by(page_size=page_size).first()
    if saved_template and saved_template.template_json and saved_template.template_json.strip():
        import json
        try:
            current_app.logger.info(f"[PDF_PREVIEW] Loading saved template JSON from database - PageSize: '{page_size}', TemplateID: {saved_template.id}, JSON length: {len(saved_template.template_json)}")
            template_json_parsed = json.loads(saved_template.template_json)
            element_count = len(template_json_parsed.get("elements", []))
            json_page_size = template_json_parsed.get("page", {}).get("size", "unknown")
            current_app.logger.info(f"[PDF_PREVIEW] Saved template JSON loaded - PageSize: '{page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"[PDF_PREVIEW] Failed to parse saved template JSON - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}", exc_info=True)
            template_json_parsed = None
    
    # If form provided template_json, use it (for live editing preview)
    if not template_json_parsed and template_json_str and template_json_str.strip():
        import json
        try:
            current_app.logger.info(f"[PDF_PREVIEW] Parsing form-provided JSON template - PageSize: '{page_size}', JSON length: {len(template_json_str)}")
            template_json_parsed = json.loads(template_json_str)
            element_count = len(template_json_parsed.get("elements", []))
            json_page_size = template_json_parsed.get("page", {}).get("size", "unknown")
            current_app.logger.info(f"[PDF_PREVIEW] Form JSON template parsed - PageSize: '{page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}")
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"[PDF_PREVIEW] Invalid form template_json - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}")
            template_json_parsed = None
    
    invoice = None
    if invoice_id:
        invoice = Invoice.query.get(invoice_id)
        if invoice is None:
            flash(_("Invoice not found"), "error")
            return redirect(url_for("admin.settings"))
    if invoice is None:
        invoice = Invoice.query.order_by(Invoice.id.desc()).first()
    settings_obj = Settings.get_settings()

    # Provide a minimal mock invoice if none exists to avoid template errors
    from types import SimpleNamespace

    if invoice is None:
        from datetime import date

        invoice = SimpleNamespace(
            invoice_number="0000",
            issue_date=date.today(),
            due_date=date.today(),
            status="draft",
            client_name="Sample Client",
            client_email="",
            client_address="",
            project=SimpleNamespace(name="Sample Project", description=""),
            items=[],
            extra_goods=[],
            subtotal=0.0,
            tax_rate=0.0,
            tax_amount=0.0,
            total_amount=0.0,
            notes="",
            terms="",
        )
    # Ensure at least one sample item to avoid undefined 'item' in templates that reference it outside loops
    sample_item = SimpleNamespace(
        description="Sample item", quantity=1.0, unit_price=0.0, total_amount=0.0, time_entry_ids=""
    )

    # Create a wrapper object with converted Query objects to lists
    # We can't modify SQLAlchemy model attributes directly, so we create a wrapper
    invoice_wrapper = SimpleNamespace()

    # Copy all simple attributes from the invoice
    for attr in [
        "id",
        "invoice_number",
        "project_id",
        "client_name",
        "client_email",
        "client_address",
        "client_id",
        "issue_date",
        "due_date",
        "status",
        "subtotal",
        "tax_rate",
        "tax_amount",
        "total_amount",
        "currency_code",
        "notes",
        "terms",
        "payment_date",
        "payment_method",
        "payment_reference",
        "payment_notes",
        "amount_paid",
        "payment_status",
        "created_by",
        "created_at",
        "updated_at",
    ]:
        try:
            setattr(invoice_wrapper, attr, getattr(invoice, attr))
        except AttributeError:
            pass

    # Copy relationship attributes (project, client)
    try:
        invoice_wrapper.project = invoice.project
    except (AttributeError, RuntimeError) as e:
        current_app.logger.debug(f"Could not access invoice.project for invoice {invoice.id}: {e}")
        invoice_wrapper.project = SimpleNamespace(name="Sample Project", description="")

    try:
        invoice_wrapper.client = invoice.client
    except (AttributeError, RuntimeError) as e:
        current_app.logger.debug(f"Could not access invoice.client for invoice {invoice.id}: {e}")
        invoice_wrapper.client = None

    # Convert items from Query to list
    try:
        if hasattr(invoice, "items") and hasattr(invoice.items, "all"):
            # It's a SQLAlchemy Query object - call .all() to get list
            items_list = invoice.items.all()
            if not items_list:
                # No items in database, add sample
                items_list = [sample_item]
            invoice_wrapper.items = items_list
        elif hasattr(invoice, "items") and isinstance(invoice.items, list):
            # Already a list
            invoice_wrapper.items = invoice.items if invoice.items else [sample_item]
        else:
            # Fallback
            invoice_wrapper.items = [sample_item]
    except Exception as e:
        print(f"Error converting invoice items: {e}")
        invoice_wrapper.items = [sample_item]

    # Convert extra_goods from Query to list
    try:
        if hasattr(invoice, "extra_goods") and hasattr(invoice.extra_goods, "all"):
            invoice_wrapper.extra_goods = invoice.extra_goods.all()
        elif hasattr(invoice, "extra_goods") and isinstance(invoice.extra_goods, list):
            invoice_wrapper.extra_goods = invoice.extra_goods
        else:
            invoice_wrapper.extra_goods = []
    except Exception:
        invoice_wrapper.extra_goods = []

    # Convert expenses from Query to list
    try:
        if hasattr(invoice, "expenses") and hasattr(invoice.expenses, "all"):
            invoice_wrapper.expenses = invoice.expenses.all()
        elif hasattr(invoice, "expenses") and isinstance(invoice.expenses, list):
            invoice_wrapper.expenses = invoice.expenses
        else:
            invoice_wrapper.expenses = []
    except Exception:
        invoice_wrapper.expenses = []

    # Use the wrapper instead of the original invoice
    invoice = invoice_wrapper
    
    # CRITICAL: Always use template_json for preview - convert to HTML/CSS with actual invoice data
    if template_json_parsed:
        try:
            # Convert JSON template to HTML/CSS with actual invoice data for better table rendering
            html, css = _convert_json_template_to_html_css(template_json_parsed, page_size, invoice=invoice, quote=None, settings=settings_obj)
            items_count = len(invoice.items) if hasattr(invoice, 'items') and invoice.items else 0
            current_app.logger.info(f"[PDF_PREVIEW] JSON template converted with invoice data - PageSize: '{page_size}', HTML length: {len(html)}, CSS length: {len(css)}, Items count: {items_count}")
        except Exception as e:
            current_app.logger.error(f"[PDF_PREVIEW] Failed to convert JSON template with invoice data - PageSize: '{page_size}', Error: {str(e)}", exc_info=True)
            # Fall back to empty HTML/CSS
            html = "<div class='invoice-wrapper'></div>"
            css = ""
    else:
        # No template_json available - this should not happen if template was saved
        current_app.logger.error(f"[PDF_PREVIEW] No template JSON available for preview - PageSize: '{page_size}', SavedTemplateExists: {saved_template is not None}, SavedTemplateHasJSON: {saved_template.template_json if saved_template else False}, User: {current_user.username}")
        html = "<div class='invoice-wrapper'><p style='color:red; padding:20px;'>Error: No template found. Please save a template first.</p></div>"
        css = ""

    # CRITICAL: Load the saved template CSS for this page size and merge with editor CSS
    # The editor generates minimal CSS, but we need the full template CSS for proper preview
    from app.utils.pdf_generator import update_page_size_in_css, validate_page_size_in_css
    import re
    
    saved_css = None  # Initialize saved_css to avoid UnboundLocalError
    if saved_template:
        current_app.logger.info(f"[PDF_PREVIEW] Retrieved saved invoice template - PageSize: '{page_size}', TemplateID: {saved_template.id}, HasCSS: {bool(saved_template.template_css)}")
        if saved_template.template_css and saved_template.template_css.strip():
            # Use the saved template CSS as base, but normalize it first to ensure correct @page size
            saved_css = saved_template.template_css
            # CRITICAL: Normalize the saved template CSS to ensure it has the correct @page size
            saved_css = update_page_size_in_css(saved_css, page_size)
            current_app.logger.info(f"[PDF_PREVIEW] Using saved invoice template CSS - PageSize: '{page_size}', CSS length: {len(saved_css)}, TemplateID: {saved_template.id}")
        
        # If editor provided CSS, merge it (editor CSS takes precedence for @page rules)
        if css and css.strip():
            # Extract @page rule from editor CSS if present
            editor_page_match = re.search(r"@page\s*\{[^}]*\}", css, re.IGNORECASE | re.DOTALL)
            if editor_page_match:
                # Editor has @page rule - normalize it and use it, merge with saved CSS
                editor_page_rule = editor_page_match.group(0)
                # Normalize editor's @page rule to correct size FIRST
                editor_page_rule = update_page_size_in_css(editor_page_rule, page_size)
                # Remove @page from saved CSS and add normalized editor's @page rule
                if saved_css:
                    saved_css_no_page = re.sub(r"@page\s*\{[^}]*\}", "", saved_css, flags=re.IGNORECASE | re.DOTALL)
                else:
                    saved_css_no_page = ""
                # Remove @page rule from editor CSS and merge
                editor_css_no_page = css.replace(editor_page_rule, "").strip()
                css = editor_page_rule + "\n" + saved_css_no_page
                if editor_css_no_page:
                    css = css + "\n" + editor_css_no_page
            else:
                # No @page in editor CSS, use saved CSS (already normalized) and add editor CSS
                if saved_css:
                    css = saved_css + "\n" + css
                # else: css already has the editor CSS, no need to merge
        else:
            # No editor CSS, use saved template CSS (already normalized) if available
            if saved_css:
                css = saved_css
    elif not css or not css.strip():
        # No template CSS and no editor CSS - create default with correct page size
        css = f"@page {{\n    size: {page_size};\n    margin: 2cm;\n}}\n"

    # Normalize @page size in CSS to match the selected page size
    # This ensures preview matches what will be exported
    if css:
        # Always normalize @page size to ensure it matches the selected page size
        css_before = css
        css = update_page_size_in_css(css, page_size)
        
        # Log if normalization changed anything
        if css != css_before:
            current_app.logger.debug(f"PDF Preview - CSS @page size normalized from template/editor to {page_size}")
        
        # Validate after normalization
        is_valid, found_sizes = validate_page_size_in_css(css, page_size)
        if not is_valid:
            current_app.logger.warning(
                f"Invoice PDF preview CSS @page size normalization failed for {page_size}. "
                f"Found sizes: {found_sizes}. Forcing correct size."
            )
            # Force add @page rule if validation failed
            if "@page" not in css:
                css = f"@page {{\n    size: {page_size};\n    margin: 2cm;\n}}\n\n" + css
            else:
                # Try to fix it by replacing any existing @page size
                # Use a more robust regex that handles quotes and whitespace
                css = re.sub(
                    r"size\s*:\s*['\"]?[^;}\n]+['\"]?",
                    f"size: {page_size}",
                    css,
                    flags=re.IGNORECASE | re.MULTILINE
                )
    else:
        # No CSS provided, add default @page rule
        css = update_page_size_in_css("", page_size)
    
    # Final validation and logging
    is_valid, found_sizes = validate_page_size_in_css(css, page_size)
    if is_valid:
        current_app.logger.info(f"[PDF_PREVIEW] CSS validated successfully - PageSize: '{page_size}', Final CSS length: {len(css)}, Final HTML length: {len(html)}")
    else:
        current_app.logger.error(f"[PDF_PREVIEW] CSS validation FAILED - PageSize: '{page_size}', Found sizes: {found_sizes}, User: {current_user.username}")

    # Helper: remove @page rules from HTML inline styles when separate CSS exists
    # This matches the fix used in PDF exports to avoid conflicts with WeasyPrint
    def remove_page_rule_from_html(html_text):
        """Remove @page rules from HTML inline styles to avoid conflicts with separate CSS"""
        import re
        
        def remove_from_style_tag(match):
            style_content = match.group(2)
            # Remove @page rule from style content
            # Need to handle nested @bottom-center rules properly
            # Match @page { ... } including any nested rules
            brace_count = 0
            page_pattern = r"@page\s*\{"
            page_match = re.search(page_pattern, style_content, re.IGNORECASE)
            
            if page_match:
                start = page_match.start()
                # Find matching closing brace
                end = len(style_content)
                for i in range(page_match.end() - 1, len(style_content)):
                    if style_content[i] == "{":
                        brace_count += 1
                    elif style_content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                # Remove the @page rule
                style_content = style_content[:start] + style_content[end:]
                # Clean up any double newlines or extra whitespace
                style_content = re.sub(r"\n\s*\n", "\n", style_content)
            
            return f"{match.group(1)}{style_content}{match.group(3)}"
        
        # Match <style> tags and remove @page rules from them
        style_pattern = r"(<style[^>]*>)(.*?)(</style>)"
        if re.search(style_pattern, html_text, re.IGNORECASE | re.DOTALL):
            html_text = re.sub(style_pattern, remove_from_style_tag, html_text, flags=re.IGNORECASE | re.DOTALL)
        
        return html_text
    
    # Apply @page rule removal fix: if we have separate CSS and HTML with inline styles,
    # remove @page rules from HTML to ensure the separate CSS @page rule is used
    html_has_inline_styles = html and "<style>" in html
    if html_has_inline_styles and css and css.strip():
        # Check if HTML has @page rules
        import re
        html_page_rules = re.findall(r"@page\s*\{[^}]*\}", html, re.IGNORECASE | re.DOTALL)
        if html_page_rules:
            current_app.logger.debug(
                f"PDF preview: Found {len(html_page_rules)} @page rule(s) in HTML inline styles - removing them"
            )
            # Remove @page rules from HTML inline styles (keep everything else)
            html = remove_page_rule_from_html(html)
            current_app.logger.debug("PDF preview: Removed @page rules from HTML inline styles")

    # Helper: sanitize Jinja blocks to fix entities/smart quotes inserted by editor
    def _sanitize_jinja_blocks(raw: str) -> str:
        try:
            import re as _re
            import html as _html

            smart_map = {
                "\u201c": '"',
                "\u201d": '"',  # “ ” -> "
                "\u2018": "'",
                "\u2019": "'",  # ‘ ’ -> '
                "\u00a0": " ",  # nbsp
                "\u200b": "",
                "\u200c": "",
                "\u200d": "",  # zero-width
            }

            def _fix_quotes(s: str) -> str:
                for k, v in smart_map.items():
                    s = s.replace(k, v)
                return s

            def _clean(match):
                open_tag = match.group(1)
                inner = match.group(2)
                # Remove any HTML tags GrapesJS may have inserted inside Jinja braces
                inner = _re.sub(r"</?[^>]+?>", "", inner)
                # Decode HTML entities
                inner = _html.unescape(inner)
                # Fix smart quotes and nbsp
                inner = _fix_quotes(inner)
                # Trim excessive whitespace around pipes and parentheses
                inner = _re.sub(r"\s+\|\s+", " | ", inner)
                inner = _re.sub(r"\(\s+", "(", inner)
                inner = _re.sub(r"\s+\)", ")", inner)
                # Normalize _("...") -> _('...')
                inner = inner.replace('_("', "_('").replace('")', "')")
                return f"{open_tag}{inner}{' }}' if open_tag == '{{ ' else ' %}'}"

            pattern = _re.compile(r"({{\s|{%\s)([\s\S]*?)(?:}}|%})")
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

        def _format_date(value, format="medium"):
            try:
                # Use DD.MM.YYYY format for invoices and quotes
                return value.strftime("%d.%m.%Y") if value else ""
            except Exception:
                return str(value) if value else ""

        def _format_money(value):
            try:
                return f"{float(value):,.2f} {settings_obj.currency}"
            except Exception:
                return f"{value} {settings_obj.currency}"

        # Helper function for logo - converts to base64 data URI
        def _get_logo_base64(logo_path):
            try:
                if not logo_path or not os.path.exists(logo_path):
                    return None
                import base64
                import mimetypes

                with open(logo_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                mime_type, _ = mimetypes.guess_type(logo_path)
                if not mime_type:
                    mime_type = "image/png"
                return f"data:{mime_type};base64,{data}"
            except Exception as e:
                print(f"Error loading logo: {e}")
                return None

        current_app.logger.info(f"[PDF_PREVIEW] Rendering template string - PageSize: '{page_size}', InvoiceID: {invoice_id}, Sanitized HTML length: {len(sanitized)}")
        body_html = render_template_string(
            sanitized,
            invoice=invoice,
            settings=settings_obj,
            Path=_Path,
            format_date=_format_date,
            format_money=_format_money,
            get_logo_base64=_get_logo_base64,
            item=sample_item,
        )
        current_app.logger.info(f"[PDF_PREVIEW] Template rendered successfully - PageSize: '{page_size}', Rendered HTML length: {len(body_html)}")
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        current_app.logger.error(f"[PDF_PREVIEW] Template render error - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}", exc_info=True)
        body_html = (
            f"<div style='color:red; padding:20px; border:2px solid red; margin:20px;'><h3>Template error:</h3><pre>{str(e)}</pre><pre>{error_details}</pre></div>"
            + sanitized
        )
    # Get page dimensions for preview styling
    page_dimensions = InvoicePDFTemplate.PAGE_SIZES.get(page_size, InvoicePDFTemplate.PAGE_SIZES['A4'])
    page_width_mm = page_dimensions['width']
    page_height_mm = page_dimensions['height']
    # Convert mm to pixels at 96 DPI (standard browser DPI for PDF preview)
    # 1 inch = 25.4mm, 96 DPI = 96 pixels per inch
    # Account for margins (typically 20mm = ~75px at 96 DPI)
    margin_px = int((20 / 25.4) * 96)  # 20mm margin in pixels
    # Don't subtract margins from page dimensions - margins are applied to content, not page size
    # Calculate full page dimensions at 96 DPI for browser preview
    page_width_px = int((page_width_mm / 25.4) * 96)
    page_height_px = int((page_height_mm / 25.4) * 96)
    
    # Build complete HTML page with embedded styles
    # Build complete HTML page with embedded styles
    # For preview, scale to fit viewport while maintaining aspect ratio
    page_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice Preview ({page_size})</title>
    <style>{css}
/* Preview-specific styles - completely new approach */
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
html {{
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: auto !important;
    overflow-x: auto !important;
    overflow-y: auto !important;
    background-color: #e5e7eb !important;
}}
body {{
    width: 100% !important;
    min-width: 100% !important;
    margin: 0 !important;
    padding: 20px !important;
    padding-top: 20px !important;
    overflow: auto !important;
    overflow-x: auto !important;
    overflow-y: auto !important;
    background-color: #e5e7eb !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    min-height: 100vh !important;
}}
.preview-container {{
    background: white;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    border-radius: 8px;
    overflow: visible;
    position: relative;
    width: {page_width_px}px;
    min-width: {page_width_px}px;
    max-width: {page_width_px}px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    transition: transform 0.2s ease;
    transform-origin: top center;
    margin-top: 20px;
}}
.preview-container .invoice-wrapper,
.preview-container .quote-wrapper {{
    width: {page_width_px}px !important;
    min-width: {page_width_px}px !important;
    max-width: {page_width_px}px !important;
    height: {page_height_px}px !important;
    min-height: {page_height_px}px !important;
    max-height: {page_height_px}px !important;
    box-sizing: border-box !important;
    overflow: visible !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background: transparent !important;
    position: relative;
    /* CSS zoom on container will scale this proportionally */
}}
</style>
<!-- Zoom is now controlled by the parent iframe's JavaScript -->
<script>
// Minimal script - zoom is handled by parent window
(function() {{
    // Ensure container maintains correct dimensions
    const container = document.querySelector('.preview-container');
    if (container) {{
        container.style.width = {page_width_px} + 'px';
        container.style.minWidth = {page_width_px} + 'px';
        container.style.maxWidth = {page_width_px} + 'px';
    }}
}})();
</script>
</head>
<body>
<div class="preview-container">
{body_html}
</div>
</body>
</html>"""
    current_app.logger.info(f"[PDF_PREVIEW] Returning invoice preview HTML - PageSize: '{page_size}', Total HTML length: {len(page_html)}, PageWidth: {page_width_px}px, PageHeight: {page_height_px}px, User: {current_user.username}")
    return page_html


@admin_bp.route("/admin/quote-pdf-layout/preview", methods=["POST"])
@limiter.limit("60 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def quote_pdf_layout_preview():
    """Render a live preview of the provided HTML/CSS or JSON template using a quote context."""
    # Extract and validate page_size FIRST, before any other processing
    page_size_raw = request.form.get("page_size", "A4")
    html = request.form.get("html", "")
    css = request.form.get("css", "")
    template_json_str = request.form.get("template_json", "")  # JSON template from editor
    quote_id = request.form.get("quote_id", type=int)
    
    current_app.logger.info(f"[PDF_PREVIEW] Action: quote_preview_request, PageSize: '{page_size_raw}', HTML length: {len(html)}, CSS length: {len(css)}, TemplateJSON length: {len(template_json_str)}, QuoteID: {quote_id}, User: {current_user.username}")
    
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(f"[PDF_PREVIEW] Invalid page size '{page_size_raw}', defaulting to A4, User: {current_user.username}")
        page_size = "A4"
    else:
        page_size = page_size_raw
    
    current_app.logger.info(f"[PDF_PREVIEW] Final validated PageSize: '{page_size}', TemplateJSON provided: {bool(template_json_str and template_json_str.strip())}")
    
    # Store template_json for later conversion with quote data
    template_json_parsed = None
    if template_json_str and template_json_str.strip():
        import json
        try:
            current_app.logger.info(f"[PDF_PREVIEW] Parsing quote JSON template - PageSize: '{page_size}', JSON length: {len(template_json_str)}")
            template_json_parsed = json.loads(template_json_str)
            element_count = len(template_json_parsed.get("elements", []))
            json_page_size = template_json_parsed.get("page", {}).get("size", "unknown")
            current_app.logger.info(f"[PDF_PREVIEW] Quote JSON template parsed - PageSize: '{page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}")
            # Will convert to HTML/CSS after quote data is loaded below
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"[PDF_PREVIEW] Invalid quote template_json, falling back to HTML/CSS - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}")
            template_json_parsed = None
            # Fall through to use provided HTML/CSS
    quote = None
    if quote_id:
        quote = Quote.query.get(quote_id)
        if quote is None:
            flash(_("Quote not found"), "error")
            return redirect(url_for("admin.settings"))
    if quote is None:
        quote = Quote.query.order_by(Quote.id.desc()).first()
    settings_obj = Settings.get_settings()

    # Provide a minimal mock quote if none exists to avoid template errors
    from types import SimpleNamespace

    if quote is None:
        from datetime import date, datetime

        quote = SimpleNamespace(
            id=1,
            quote_number="Q-0001",
            title="Sample Quote",
            description="Sample quote description",
            status="draft",
            client_id=1,
            client=SimpleNamespace(
                name="Sample Client",
                email="client@example.com",
                address="123 Sample Street\nSample City, ST 12345",
                phone="+1 234 567 8900",
            ),
            project_id=None,
            project=None,
            items=[],
            subtotal=0.0,
            discount_type=None,
            discount_amount=0.0,
            discount_reason=None,
            coupon_code=None,
            tax_rate=0.0,
            tax_amount=0.0,
            total_amount=0.0,
            currency_code="EUR",
            valid_until=date.today(),
            sent_at=None,
            accepted_at=None,
            notes="",
            terms="",
            payment_terms=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=1,
        )
    # Ensure at least one sample item to avoid undefined 'item' in templates that reference it outside loops
    sample_item = SimpleNamespace(description="Sample item", quantity=1.0, unit_price=0.0, total_amount=0.0)

    # Create a wrapper object with converted Query objects to lists
    quote_wrapper = SimpleNamespace()

    # Copy all simple attributes from the quote
    for attr in [
        "id",
        "quote_number",
        "title",
        "description",
        "status",
        "client_id",
        "project_id",
        "subtotal",
        "discount_type",
        "discount_amount",
        "discount_reason",
        "coupon_code",
        "tax_rate",
        "tax_amount",
        "total_amount",
        "currency_code",
        "valid_until",
        "sent_at",
        "accepted_at",
        "notes",
        "terms",
        "payment_terms",
        "created_at",
        "updated_at",
        "created_by",
    ]:
        try:
            setattr(quote_wrapper, attr, getattr(quote, attr))
        except AttributeError:
            pass

    # Copy relationship attributes (project, client)
    try:
        quote_wrapper.project = quote.project
    except (AttributeError, RuntimeError) as e:
        current_app.logger.debug(f"Could not access quote.project for quote {quote.id}: {e}")
        quote_wrapper.project = None

    try:
        quote_wrapper.client = quote.client
    except (AttributeError, RuntimeError) as e:
        current_app.logger.debug(f"Could not access quote.client for quote {quote.id}: {e}")
        quote_wrapper.client = SimpleNamespace(
            name="Sample Client",
            email="client@example.com",
            address="123 Sample Street\nSample City, ST 12345",
            phone="+1 234 567 8900",
        )

    # Convert items from Query to list
    try:
        if hasattr(quote, "items") and hasattr(quote.items, "all"):
            # It's a SQLAlchemy Query object - call .all() to get list
            items_list = quote.items.all()
            if not items_list:
                # No items in database, add sample
                items_list = [sample_item]
            quote_wrapper.items = items_list
        elif hasattr(quote, "items") and isinstance(quote.items, list):
            # Already a list
            quote_wrapper.items = quote.items if quote.items else [sample_item]
        else:
            # Fallback
            quote_wrapper.items = [sample_item]
    except Exception as e:
        print(f"Error converting quote items: {e}")
        quote_wrapper.items = [sample_item]

    # Use the wrapper instead of the original quote
    quote = quote_wrapper
    
    # If we have template_json, convert it to HTML/CSS for preview with actual quote data
    if template_json_parsed:
        try:
            # Convert JSON template to HTML/CSS with actual quote data for better table rendering
            html, css = _convert_json_template_to_html_css(template_json_parsed, page_size, invoice=None, quote=quote, settings=settings_obj)
            items_count = len(quote.items) if hasattr(quote, 'items') and quote.items else 0
            current_app.logger.info(f"[PDF_PREVIEW] Quote JSON template converted with quote data - PageSize: '{page_size}', HTML length: {len(html)}, CSS length: {len(css)}, Items count: {items_count}")
        except Exception as e:
            current_app.logger.error(f"[PDF_PREVIEW] Failed to convert quote JSON template with quote data - PageSize: '{page_size}', Error: {str(e)}", exc_info=True)
            # Fall back to empty HTML/CSS
            html = "<div class='quote-wrapper'></div>"
            css = ""


    # CRITICAL: Load the saved template CSS for this page size and merge with editor CSS
    # The editor generates minimal CSS, but we need the full template CSS for proper preview
    from app.models import QuotePDFTemplate
    from app.utils.pdf_generator import update_page_size_in_css, validate_page_size_in_css
    import re
    
    template = QuotePDFTemplate.query.filter_by(page_size=page_size).first()
    saved_css = None  # Initialize saved_css to avoid UnboundLocalError
    if template:
        current_app.logger.info(f"[PDF_PREVIEW] Retrieved saved quote template - PageSize: '{page_size}', TemplateID: {template.id}, HasCSS: {bool(template.template_css)}")
        if template.template_css and template.template_css.strip():
            # Use the saved template CSS as base, but normalize it first to ensure correct @page size
            saved_css = template.template_css
            # CRITICAL: Normalize the saved template CSS to ensure it has the correct @page size
            saved_css = update_page_size_in_css(saved_css, page_size)
            current_app.logger.info(f"[PDF_PREVIEW] Using saved quote template CSS - PageSize: '{page_size}', CSS length: {len(saved_css)}, TemplateID: {template.id}")
        
        # If editor provided CSS, merge it (editor CSS takes precedence for @page rules)
        if css and css.strip():
            # Extract @page rule from editor CSS if present
            editor_page_match = re.search(r"@page\s*\{[^}]*\}", css, re.IGNORECASE | re.DOTALL)
            if editor_page_match:
                # Editor has @page rule - normalize it and use it, merge with saved CSS
                editor_page_rule = editor_page_match.group(0)
                # Normalize editor's @page rule to correct size FIRST
                editor_page_rule = update_page_size_in_css(editor_page_rule, page_size)
                # Remove @page from saved CSS and add normalized editor's @page rule
                if saved_css:
                    saved_css_no_page = re.sub(r"@page\s*\{[^}]*\}", "", saved_css, flags=re.IGNORECASE | re.DOTALL)
                else:
                    saved_css_no_page = ""
                # Remove @page rule from editor CSS and merge
                editor_css_no_page = css.replace(editor_page_rule, "").strip()
                css = editor_page_rule + "\n" + saved_css_no_page
                if editor_css_no_page:
                    css = css + "\n" + editor_css_no_page
            else:
                # No @page in editor CSS, use saved CSS (already normalized) and add editor CSS
                if saved_css:
                    css = saved_css + "\n" + css
                # else: css already has the editor CSS, no need to merge
        else:
            # No editor CSS, use saved template CSS (already normalized) if available
            if saved_css:
                css = saved_css
    elif not css or not css.strip():
        # No template CSS and no editor CSS - create default with correct page size
        css = f"@page {{\n    size: {page_size};\n    margin: 2cm;\n}}\n"

    # Normalize @page size in CSS to match the selected page size
    # This ensures preview matches what will be exported
    if css:
        # Always normalize @page size to ensure it matches the selected page size
        css_before = css
        css = update_page_size_in_css(css, page_size)
        
        # Log if normalization changed anything
        if css != css_before:
            current_app.logger.debug(f"Quote PDF Preview - CSS @page size normalized from template/editor to {page_size}")
        
        # Validate after normalization
        is_valid, found_sizes = validate_page_size_in_css(css, page_size)
        if not is_valid:
            current_app.logger.warning(
                f"[PDF_PREVIEW] Quote CSS @page size normalization failed - PageSize: '{page_size}', Found sizes: {found_sizes}, User: {current_user.username}"
            )
            # Force add @page rule if validation failed
            if "@page" not in css:
                css = f"@page {{\n    size: {page_size};\n    margin: 2cm;\n}}\n\n" + css
            else:
                # Try to fix it by replacing any existing @page size
                # Use a more robust regex that handles quotes and whitespace
                css = re.sub(
                    r"size\s*:\s*['\"]?[^;}\n]+['\"]?",
                    f"size: {page_size}",
                    css,
                    flags=re.IGNORECASE | re.MULTILINE
                )
    else:
        # No CSS provided, add default @page rule
        css = update_page_size_in_css("", page_size)
    
    # Final validation and logging
    is_valid, found_sizes = validate_page_size_in_css(css, page_size)
    if is_valid:
        current_app.logger.info(f"[PDF_PREVIEW] Quote CSS validated successfully - PageSize: '{page_size}', Final CSS length: {len(css)}, Final HTML length: {len(html)}")
    else:
        current_app.logger.error(f"[PDF_PREVIEW] Quote CSS validation FAILED - PageSize: '{page_size}', Found sizes: {found_sizes}, User: {current_user.username}")

    # Helper: remove @page rules from HTML inline styles when separate CSS exists
    # This matches the fix used in PDF exports to avoid conflicts with WeasyPrint
    def remove_page_rule_from_html(html_text):
        """Remove @page rules from HTML inline styles to avoid conflicts with separate CSS"""
        import re
        
        def remove_from_style_tag(match):
            style_content = match.group(2)
            # Remove @page rule from style content
            # Need to handle nested @bottom-center rules properly
            # Match @page { ... } including any nested rules
            brace_count = 0
            page_pattern = r"@page\s*\{"
            page_match = re.search(page_pattern, style_content, re.IGNORECASE)
            
            if page_match:
                start = page_match.start()
                # Find matching closing brace
                end = len(style_content)
                for i in range(page_match.end() - 1, len(style_content)):
                    if style_content[i] == "{":
                        brace_count += 1
                    elif style_content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                # Remove the @page rule
                style_content = style_content[:start] + style_content[end:]
                # Clean up any double newlines or extra whitespace
                style_content = re.sub(r"\n\s*\n", "\n", style_content)
            
            return f"{match.group(1)}{style_content}{match.group(3)}"
        
        # Match <style> tags and remove @page rules from them
        style_pattern = r"(<style[^>]*>)(.*?)(</style>)"
        if re.search(style_pattern, html_text, re.IGNORECASE | re.DOTALL):
            html_text = re.sub(style_pattern, remove_from_style_tag, html_text, flags=re.IGNORECASE | re.DOTALL)
        
        return html_text
    
    # Apply @page rule removal fix: if we have separate CSS and HTML with inline styles,
    # remove @page rules from HTML to ensure the separate CSS @page rule is used
    html_has_inline_styles = html and "<style>" in html
    if html_has_inline_styles and css and css.strip():
        # Check if HTML has @page rules
        import re
        html_page_rules = re.findall(r"@page\s*\{[^}]*\}", html, re.IGNORECASE | re.DOTALL)
        if html_page_rules:
            current_app.logger.debug(
                f"PDF preview: Found {len(html_page_rules)} @page rule(s) in HTML inline styles - removing them"
            )
            # Remove @page rules from HTML inline styles (keep everything else)
            html = remove_page_rule_from_html(html)
            current_app.logger.debug("PDF preview: Removed @page rules from HTML inline styles")

    # Helper: sanitize Jinja blocks to fix entities/smart quotes inserted by editor
    def _sanitize_jinja_blocks(raw: str) -> str:
        try:
            import re as _re
            import html as _html

            smart_map = {
                "\u201c": '"',
                "\u201d": '"',  # " " -> "
                "\u2018": "'",
                "\u2019": "'",  # ' ' -> '
                "\u00a0": " ",  # nbsp
                "\u200b": "",
                "\u200c": "",
                "\u200d": "",  # zero-width
            }

            def _fix_quotes(s: str) -> str:
                for k, v in smart_map.items():
                    s = s.replace(k, v)
                return s

            def _clean(match):
                open_tag = match.group(1)
                inner = match.group(2)
                # Remove any HTML tags GrapesJS may have inserted inside Jinja braces
                inner = _re.sub(r"</?[^>]+?>", "", inner)
                # Decode HTML entities
                inner = _html.unescape(inner)
                # Fix smart quotes and nbsp
                inner = _fix_quotes(inner)
                # Trim excessive whitespace around pipes and parentheses
                inner = _re.sub(r"\s+\|\s+", " | ", inner)
                inner = _re.sub(r"\(\s+", "(", inner)
                inner = _re.sub(r"\s+\)", ")", inner)
                # Normalize _("...") -> _('...')
                inner = inner.replace('_("', "_('").replace('")', "')")
                return f"{open_tag}{inner}{' }}' if open_tag == '{{ ' else ' %}'}"

            pattern = _re.compile(r"({{\s|{%\s)([\s\S]*?)(?:}}|%})")
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

        def _format_date(value, format="medium"):
            try:
                # Use DD.MM.YYYY format for invoices and quotes
                return value.strftime("%d.%m.%Y") if value else ""
            except Exception:
                return str(value) if value else ""

        def _format_money(value):
            try:
                return f"{float(value):,.2f} {settings_obj.currency}"
            except Exception:
                return f"{value} {settings_obj.currency}"

        # Helper function for logo - converts to base64 data URI
        def _get_logo_base64(logo_path):
            try:
                if not logo_path or not os.path.exists(logo_path):
                    return None
                import base64
                import mimetypes

                with open(logo_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                mime_type, _ = mimetypes.guess_type(logo_path)
                if not mime_type:
                    mime_type = "image/png"
                return f"data:{mime_type};base64,{data}"
            except Exception as e:
                print(f"Error loading logo: {e}")
                return None

        current_app.logger.info(f"[PDF_PREVIEW] Rendering quote template string - PageSize: '{page_size}', QuoteID: {quote_id}, Sanitized HTML length: {len(sanitized)}")
        body_html = render_template_string(
            sanitized,
            quote=quote,
            settings=settings_obj,
            Path=_Path,
            format_date=_format_date,
            format_money=_format_money,
            get_logo_base64=_get_logo_base64,
            item=sample_item,
        )
        current_app.logger.info(f"[PDF_PREVIEW] Quote template rendered successfully - PageSize: '{page_size}', Rendered HTML length: {len(body_html)}")
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        current_app.logger.error(f"[PDF_PREVIEW] Quote template render error - PageSize: '{page_size}', Error: {str(e)}, User: {current_user.username}", exc_info=True)
        body_html = (
            f"<div style='color:red; padding:20px; border:2px solid red; margin:20px;'><h3>Template error:</h3><pre>{str(e)}</pre><pre>{error_details}</pre></div>"
            + sanitized
        )
    # Get page dimensions for preview styling
    from app.models import QuotePDFTemplate
    page_dimensions = QuotePDFTemplate.PAGE_SIZES.get(page_size, QuotePDFTemplate.PAGE_SIZES['A4'])
    page_width_mm = page_dimensions['width']
    page_height_mm = page_dimensions['height']
    # Convert mm to pixels at 96 DPI (standard browser DPI for PDF preview)
    # 1 inch = 25.4mm, 96 DPI = 96 pixels per inch
    # Account for margins (typically 20mm = ~75px at 96 DPI)
    margin_px = int((20 / 25.4) * 96)  # 20mm margin in pixels
    # Don't subtract margins from page dimensions - margins are applied to content, not page size
    page_width_px = int((page_width_mm / 25.4) * 96)
    page_height_px = int((page_height_mm / 25.4) * 96)
    
    # Build complete HTML page with embedded styles
    # For preview, scale to fit viewport while maintaining aspect ratio
    page_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quote Preview ({page_size})</title>
    <style>{css}
/* Preview-specific styles - completely new approach */
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
html {{
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: auto !important;
    overflow-x: auto !important;
    overflow-y: auto !important;
    background-color: #e5e7eb !important;
}}
body {{
    width: 100% !important;
    min-width: 100% !important;
    margin: 0 !important;
    padding: 20px !important;
    padding-top: 20px !important;
    overflow: auto !important;
    overflow-x: auto !important;
    overflow-y: auto !important;
    background-color: #e5e7eb !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    min-height: 100vh !important;
}}
.preview-container {{
    background: white;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    border-radius: 8px;
    overflow: visible;
    position: relative;
    width: {page_width_px}px;
    min-width: {page_width_px}px;
    max-width: {page_width_px}px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    transition: transform 0.2s ease;
    transform-origin: top center;
    margin-top: 20px;
}}
.preview-container .invoice-wrapper,
.preview-container .quote-wrapper {{
    width: {page_width_px}px !important;
    min-width: {page_width_px}px !important;
    max-width: {page_width_px}px !important;
    height: {page_height_px}px !important;
    min-height: {page_height_px}px !important;
    max-height: {page_height_px}px !important;
    box-sizing: border-box !important;
    overflow: visible !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background: transparent !important;
    position: relative;
    /* CSS zoom on container will scale this proportionally */
}}
</style>
<!-- Zoom is now controlled by the parent iframe's JavaScript -->
<script>
// Minimal script - zoom is handled by parent window
(function() {{
    // Ensure container maintains correct dimensions
    const container = document.querySelector('.preview-container');
    if (container) {{
        container.style.width = {page_width_px} + 'px';
        container.style.minWidth = {page_width_px} + 'px';
        container.style.maxWidth = {page_width_px} + 'px';
    }}
}})();
</script>
</head>
<body>
<div class="preview-container">
{body_html}
</div>
</body>
</html>"""
    current_app.logger.info(f"[PDF_PREVIEW] Returning quote preview HTML - PageSize: '{page_size}', Total HTML length: {len(page_html)}, PageWidth: {page_width_px}px, PageHeight: {page_height_px}px, User: {current_user.username}")
    return page_html


@admin_bp.route("/admin/upload-logo", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def upload_logo():
    """Upload company logo"""
    if "logo" not in request.files:
        flash(_("No logo file selected"), "error")
        return redirect(url_for("admin.settings"))

    file = request.files["logo"]
    if file.filename == "":
        flash(_("No logo file selected"), "error")
        return redirect(url_for("admin.settings"))

    if file and allowed_logo_file(file.filename):
        # Generate unique filename
        file_extension = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"company_logo_{uuid.uuid4().hex[:8]}.{file_extension}"

        # Basic server-side validation: verify image type
        try:
            from PIL import Image

            file.stream.seek(0)
            img = Image.open(file.stream)
            img.verify()
            file.stream.seek(0)
        except Exception:
            flash(_("Invalid image file."), "error")
            return redirect(url_for("admin.settings"))

        # Save file
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # Log successful save
        current_app.logger.info(f"Logo saved successfully: {file_path}")
        current_app.logger.info(f"File exists check: {os.path.exists(file_path)}")
        current_app.logger.info(
            f'File size: {os.path.getsize(file_path) if os.path.exists(file_path) else "N/A"} bytes'
        )

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
        if not safe_commit("admin_upload_logo"):
            flash(_("Could not save logo due to a database error. Please check server logs."), "error")
            return redirect(url_for("admin.settings"))

        flash(
            _(
                'Company logo uploaded successfully! You can see it in the "Current Company Logo" section above. It will appear on invoices and PDF documents.'
            ),
            "success",
        )
    else:
        flash(_("Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, SVG, WEBP"), "error")

    return redirect(url_for("admin.settings"))


@admin_bp.route("/admin/remove-logo", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
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
        settings_obj.company_logo_filename = ""
        if not safe_commit("admin_remove_logo"):
            flash(_("Could not remove logo due to a database error. Please check server logs."), "error")
            return redirect(url_for("admin.settings"))
        flash(_("Company logo removed successfully. Upload a new logo in the section below if needed."), "success")
    else:
        flash(_("No logo to remove"), "info")

    return redirect(url_for("admin.settings"))


@admin_bp.route("/admin/template-image/upload", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def upload_template_image():
    """Upload an image for use in PDF templates"""
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime
    from flask import url_for

    # File upload configuration - only images
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    UPLOAD_FOLDER = "app/static/uploads/template_images"
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Only images (PNG, JPG, JPEG, GIF, WEBP) are allowed"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": f"File size exceeds maximum allowed size ({MAX_FILE_SIZE / (1024*1024):.0f} MB)"}), 400

    # Save file
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"template_{timestamp}_{original_filename}"

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Return URL for the image
    image_url = url_for("admin.serve_template_image", filename=filename)
    
    return jsonify({
        "success": True,
        "image_url": image_url,
        "filename": filename
    })


@admin_bp.route("/uploads/template_images/<path:filename>")
def serve_template_image(filename):
    """Serve uploaded template images (public route so images can be embedded in PDFs)"""
    from flask import send_from_directory
    import os
    
    upload_folder = os.path.join(current_app.root_path, "..", "app/static/uploads/template_images")
    return send_from_directory(upload_folder, filename)


# Public route to serve uploaded logos from the static uploads directory
@admin_bp.route("/uploads/logos/<path:filename>")
def serve_uploaded_logo(filename):
    """Serve company logo files stored under static/uploads/logos.
    This route is intentionally public so logos render on unauthenticated pages
    like the login screen and in favicons.
    """
    try:
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, filename)

        if not os.path.exists(file_path):
            current_app.logger.error(f"Logo file not found: {file_path}")
            return "Logo file not found", 404

        return send_from_directory(upload_folder, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving logo {filename}: {str(e)}")
        return "Error serving logo", 500


@admin_bp.route("/admin/backups")
@login_required
@admin_or_permission_required("manage_backups")
def backups_management():
    """Backups management page"""
    # Get list of existing backups
    backups_dir = get_backup_root_dir(current_app)
    backups = []

    if os.path.exists(backups_dir):
        for filename in os.listdir(backups_dir):
            if filename.endswith(".zip") and not filename.startswith("restore_"):
                filepath = os.path.join(backups_dir, filename)
                stat = os.stat(filepath)
                backups.append(
                    {
                        "filename": filename,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_mtime),
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    }
                )

    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)

    return render_template("admin/backups.html", backups=backups, backups_dir=backups_dir)


@admin_bp.route("/admin/backup/create", methods=["POST"])
@login_required
@admin_or_permission_required("manage_backups")
def create_backup_manual():
    """Create manual backup and return the archive for download."""
    try:
        archive_path = create_backup(current_app)
        if not archive_path or not os.path.exists(archive_path):
            flash(_("Backup failed: archive not created"), "error")
            return redirect(url_for("admin.backups_management"))
        # Stream file to user
        return send_file(archive_path, as_attachment=True)
    except Exception as e:
        flash(_("Backup failed: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.backups_management"))


@admin_bp.route("/admin/backup/download/<filename>")
@login_required
@admin_or_permission_required("manage_backups")
def download_backup(filename):
    """Download an existing backup file"""
    # Security: only allow downloading .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith(".zip"):
        flash(_("Invalid file type"), "error")
        return redirect(url_for("admin.backups_management"))

    backups_dir = get_backup_root_dir(current_app)
    filepath = os.path.join(backups_dir, filename)

    if not os.path.exists(filepath):
        flash(_("Backup file not found"), "error")
        return redirect(url_for("admin.backups_management"))

    return send_file(filepath, as_attachment=True)


@admin_bp.route("/admin/backup/delete/<filename>", methods=["POST"])
@login_required
@admin_or_permission_required("manage_backups")
def delete_backup(filename):
    """Delete a backup file"""
    # Security: only allow deleting .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith(".zip"):
        flash(_("Invalid file type"), "error")
        return redirect(url_for("admin.backups_management"))

    backups_dir = get_backup_root_dir(current_app)
    filepath = os.path.join(backups_dir, filename)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(_('Backup "%(filename)s" deleted successfully', filename=filename), "success")
        else:
            flash(_("Backup file not found"), "error")
    except Exception as e:
        flash(_("Failed to delete backup: %(error)s", error=str(e)), "error")

    return redirect(url_for("admin.backups_management"))


@admin_bp.route("/admin/restore", methods=["GET", "POST"])
@admin_bp.route("/admin/restore/<filename>", methods=["POST"])
@limiter.limit("3 per minute", methods=["POST"])  # heavy operation
@login_required
@admin_or_permission_required("manage_backups")
def restore(filename=None):
    """Restore from an uploaded backup archive or existing backup file."""
    if request.method == "POST":
        backups_dir = get_backup_root_dir(current_app)

        # If restoring from an existing backup file
        if filename:
            filename = secure_filename(filename)
            if not filename.lower().endswith(".zip"):
                flash(_("Invalid file type. Please select a .zip backup archive."), "error")
                return redirect(url_for("admin.backups_management"))
            temp_path = os.path.join(backups_dir, filename)
            if not os.path.exists(temp_path):
                flash(_("Backup file not found."), "error")
                return redirect(url_for("admin.backups_management"))
            # Copy to temp location for processing
            actual_restore_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{filename}")
            shutil.copy2(temp_path, actual_restore_path)
            temp_path = actual_restore_path
        # If uploading a new backup file
        elif "backup_file" in request.files and request.files["backup_file"].filename != "":
            file = request.files["backup_file"]
            uploaded_filename = secure_filename(file.filename)
            if not uploaded_filename.lower().endswith(".zip"):
                flash(_("Invalid file type. Please upload a .zip backup archive."), "error")
                return redirect(url_for("admin.restore"))
            # Save temporarily under project backups
            os.makedirs(backups_dir, exist_ok=True)
            temp_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{uploaded_filename}")
            file.save(temp_path)
        else:
            flash(_("No backup file provided"), "error")
            return redirect(url_for("admin.restore"))

        # Initialize progress state
        token = uuid.uuid4().hex[:8]
        RESTORE_PROGRESS[token] = {"status": "starting", "percent": 0, "message": "Queued"}

        def progress_cb(label, percent):
            RESTORE_PROGRESS[token] = {"status": "running", "percent": int(percent), "message": label}

        # Capture the real Flask app object for use in a background thread
        app_obj = current_app._get_current_object()

        def _do_restore():
            try:
                RESTORE_PROGRESS[token] = {"status": "running", "percent": 5, "message": "Starting restore"}
                success, message = restore_backup(app_obj, temp_path, progress_callback=progress_cb)
                RESTORE_PROGRESS[token] = {
                    "status": "done" if success else "error",
                    "percent": 100 if success else RESTORE_PROGRESS[token].get("percent", 0),
                    "message": message,
                }
            except Exception as e:
                RESTORE_PROGRESS[token] = {
                    "status": "error",
                    "percent": RESTORE_PROGRESS[token].get("percent", 0),
                    "message": str(e),
                }
            finally:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        # Run restore in background to keep request responsive
        t = threading.Thread(target=_do_restore, daemon=True)
        t.start()

        flash(_("Restore started. You can monitor progress on this page."), "info")
        return redirect(url_for("admin.restore", token=token))
    # GET
    token = request.args.get("token")
    progress = RESTORE_PROGRESS.get(token) if token else None
    return render_template("admin/restore.html", progress=progress, token=token)


@admin_bp.route("/admin/system")
@login_required
@admin_or_permission_required("view_system_info")
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
        dialect = engine.dialect.name if engine else ""
        if dialect == "sqlite":
            db_size_bytes = (
                db.session.execute(
                    text("SELECT page_count * page_size AS size FROM pragma_page_count(), pragma_page_size()")
                ).scalar()
                or 0
            )
        elif dialect in ("postgresql", "postgres"):
            db_size_bytes = db.session.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
        else:
            db_size_bytes = 0
    except Exception:
        db_size_bytes = 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2) if db_size_bytes else 0

    return render_template(
        "admin/system_info.html",
        total_users=total_users,
        total_projects=total_projects,
        total_entries=total_entries,
        active_timers=active_timers,
        db_size_mb=db_size_mb,
    )


@admin_bp.route("/admin/oidc/debug")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_debug():
    """OIDC Configuration Debug Dashboard"""
    from app.config import Config
    from app import oauth

    # Gather OIDC configuration
    oidc_config = {
        "enabled": False,
        "auth_method": getattr(Config, "AUTH_METHOD", "local"),
        "issuer": getattr(Config, "OIDC_ISSUER", None),
        "client_id": getattr(Config, "OIDC_CLIENT_ID", None),
        "client_secret_set": bool(getattr(Config, "OIDC_CLIENT_SECRET", None)),
        "redirect_uri": getattr(Config, "OIDC_REDIRECT_URI", None),
        "scopes": getattr(Config, "OIDC_SCOPES", "openid profile email"),
        "username_claim": getattr(Config, "OIDC_USERNAME_CLAIM", "preferred_username"),
        "email_claim": getattr(Config, "OIDC_EMAIL_CLAIM", "email"),
        "full_name_claim": getattr(Config, "OIDC_FULL_NAME_CLAIM", "name"),
        "groups_claim": getattr(Config, "OIDC_GROUPS_CLAIM", "groups"),
        "admin_group": getattr(Config, "OIDC_ADMIN_GROUP", None),
        "admin_emails": getattr(Config, "OIDC_ADMIN_EMAILS", []),
        "post_logout_redirect": getattr(Config, "OIDC_POST_LOGOUT_REDIRECT_URI", None),
    }

    # Check if OIDC is enabled
    auth_method = (oidc_config["auth_method"] or "local").strip().lower()
    oidc_config["enabled"] = auth_method in ("oidc", "both")

    # Try to get OIDC client metadata
    metadata = None
    metadata_error = None
    well_known_url = None

    if oidc_config["enabled"] and oidc_config["issuer"]:
        try:
            client = oauth.create_client("oidc")
            if client:
                metadata = client.load_server_metadata()
                well_known_url = f"{oidc_config['issuer'].rstrip('/')}/.well-known/openid-configuration"
        except Exception as e:
            metadata_error = str(e)
            well_known_url = (
                f"{oidc_config['issuer'].rstrip('/')}/.well-known/openid-configuration"
                if oidc_config["issuer"]
                else None
            )

    # Get OIDC users from database
    oidc_users = []
    try:
        oidc_users = (
            User.query.filter(User.oidc_issuer.isnot(None), User.oidc_sub.isnot(None))
            .order_by(User.last_login.desc())
            .all()
        )
    except Exception:
        pass

    return render_template(
        "admin/oidc_debug.html",
        oidc_config=oidc_config,
        metadata=metadata,
        metadata_error=metadata_error,
        well_known_url=well_known_url,
        oidc_users=oidc_users,
    )


@admin_bp.route("/admin/oidc/test")
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_test():
    """Test OIDC configuration by fetching discovery document with enhanced DNS testing"""
    from app.config import Config
    from app import oauth
    from app.utils.oidc_metadata import (
        fetch_oidc_metadata,
        test_dns_resolution,
        resolve_hostname_multiple_strategies,
        detect_docker_environment,
    )
    from urllib.parse import urlparse

    auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    if auth_method not in ("oidc", "both"):
        flash(_('OIDC is not enabled. Set AUTH_METHOD to "oidc" or "both".'), "warning")
        return redirect(url_for("admin.oidc_debug"))

    issuer = getattr(Config, "OIDC_ISSUER", None)
    if not issuer:
        flash(_("OIDC_ISSUER is not configured"), "error")
        return redirect(url_for("admin.oidc_debug"))

    # Parse hostname
    try:
        parsed = urlparse(issuer)
        hostname = parsed.netloc.split(":")[0]
    except Exception as e:
        flash(_("✗ Failed to parse issuer URL: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.oidc_debug"))

    # Test 1: Test DNS resolution with multiple strategies
    flash(_("Testing DNS resolution with multiple strategies..."), "info")
    dns_strategy = current_app.config.get("OIDC_DNS_RESOLUTION_STRATEGY", "auto")
    
    # Test all strategies
    strategies_to_test = ["socket", "getaddrinfo"] if dns_strategy == "auto" or dns_strategy == "both" else [dns_strategy]
    dns_results = {}
    
    for strategy in strategies_to_test:
        success, ip, error, strategy_used = resolve_hostname_multiple_strategies(
            hostname, timeout=5, strategy=strategy, use_cache=False
        )
        dns_results[strategy] = {
            "success": success,
            "ip": ip,
            "error": error,
            "strategy_used": strategy_used,
        }
        if success:
            # Mask IP for display (show only first octet)
            masked_ip = ip.split('.')[0] + ".xxx.xxx.xxx" if ip and '.' in ip else "N/A"
            flash(
                _("✓ DNS resolution successful using %(strategy)s strategy: %(ip)s", 
                  strategy=strategy, ip=masked_ip),
                "success",
            )
        else:
            flash(
                _("✗ DNS resolution failed using %(strategy)s strategy: %(error)s", 
                  strategy=strategy, error=error or "Unknown error"),
                "warning",
            )
    
    # Check Docker environment
    if detect_docker_environment():
        flash(_("ℹ Docker environment detected - internal service names may be available"), "info")
    
    # Test 2: Fetch discovery document using enhanced metadata fetcher
    well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    use_ip_directly = current_app.config.get("OIDC_USE_IP_DIRECTLY", True)
    use_docker_internal = current_app.config.get("OIDC_USE_DOCKER_INTERNAL", True)
    max_retries = int(current_app.config.get("OIDC_METADATA_RETRY_ATTEMPTS", 3))
    timeout = int(current_app.config.get("OIDC_METADATA_FETCH_TIMEOUT", 10))
    
    try:
        current_app.logger.info("OIDC Test: Fetching discovery document from %s", well_known_url)
        metadata, metadata_error, diagnostics = fetch_oidc_metadata(
            issuer,
            max_retries=max_retries,
            retry_delay=2,
            timeout=timeout,
            use_dns_test=True,
            dns_strategy=dns_strategy,
            use_ip_directly=use_ip_directly,
            use_docker_internal=use_docker_internal,
        )
        
        if metadata:
            discovery_doc = metadata
            flash(_("✓ Discovery document fetched successfully from %(url)s", url=well_known_url), "success")
            if diagnostics:
                dns_info = diagnostics.get("dns_resolution", {})
                strategy_used = dns_info.get("strategy", "unknown")
                flash(
                    _("✓ DNS strategy used: %(strategy)s", strategy=strategy_used),
                    "info",
                )
            current_app.logger.info("OIDC Test: Discovery document retrieved, issuer=%s", discovery_doc.get("issuer"))
        else:
            flash(_("✗ Failed to fetch discovery document: %(error)s", error=metadata_error or "Unknown error"), "error")
            current_app.logger.error("OIDC Test: Failed to fetch discovery document: %s", metadata_error)
            return redirect(url_for("admin.oidc_debug"))
    except Exception as e:
        flash(_("✗ Unexpected error: %(error)s", error=str(e)), "error")
        current_app.logger.error("OIDC Test: Unexpected error: %s", str(e))
        return redirect(url_for("admin.oidc_debug"))
    
    # Ensure discovery_doc is defined
    if 'discovery_doc' not in locals():
        flash(_("✗ Failed to retrieve discovery document"), "error")
        return redirect(url_for("admin.oidc_debug"))

    # Test 2: Check if OAuth client is registered
    try:
        client = oauth.create_client("oidc")
        if client:
            flash(_("✓ OAuth client is registered in application"), "success")
            current_app.logger.info("OIDC Test: OAuth client registered")
        else:
            flash(_("✗ OAuth client is not registered"), "error")
            current_app.logger.error("OIDC Test: OAuth client not registered")
    except Exception as e:
        flash(_("✗ Failed to create OAuth client: %(error)s", error=str(e)), "error")
        current_app.logger.error("OIDC Test: Failed to create OAuth client: %s", str(e))

    # Test 3: Verify required endpoints are present
    required_endpoints = ["authorization_endpoint", "token_endpoint", "userinfo_endpoint"]
    for endpoint in required_endpoints:
        if endpoint in discovery_doc:
            flash(_("✓ %(endpoint)s: %(url)s", endpoint=endpoint, url=discovery_doc[endpoint]), "info")
        else:
            flash(_("✗ Missing %(endpoint)s in discovery document", endpoint=endpoint), "warning")

    # Test 4: Check supported scopes
    supported_scopes = discovery_doc.get("scopes_supported", [])
    requested_scopes = getattr(Config, "OIDC_SCOPES", "openid profile email").split()
    for scope in requested_scopes:
        if scope in supported_scopes:
            flash(_('✓ Scope "%(scope)s" is supported by provider', scope=scope), "info")
        else:
            flash(
                _(
                    '⚠ Scope "%(scope)s" may not be supported by provider (supported: %(supported)s)',
                    scope=scope,
                    supported=", ".join(supported_scopes),
                ),
                "warning",
            )

    # Test 5: Check claims
    supported_claims = discovery_doc.get("claims_supported", [])
    if supported_claims:
        flash(_("ℹ Provider supports claims: %(claims)s", claims=", ".join(supported_claims)), "info")

        # Check if configured claims are supported
        claim_checks = {
            "username": getattr(Config, "OIDC_USERNAME_CLAIM", "preferred_username"),
            "email": getattr(Config, "OIDC_EMAIL_CLAIM", "email"),
            "full_name": getattr(Config, "OIDC_FULL_NAME_CLAIM", "name"),
            "groups": getattr(Config, "OIDC_GROUPS_CLAIM", "groups"),
        }

        for claim_type, claim_name in claim_checks.items():
            if claim_name in supported_claims:
                flash(
                    _(
                        '✓ Configured %(claim_type)s claim "%(claim_name)s" is supported',
                        claim_type=claim_type,
                        claim_name=claim_name,
                    ),
                    "info",
                )
            else:
                flash(
                    _(
                        '⚠ Configured %(claim_type)s claim "%(claim_name)s" not in supported claims list (may still work)',
                        claim_type=claim_type,
                        claim_name=claim_name,
                    ),
                    "warning",
                )

    flash(_("OIDC configuration test completed"), "info")
    return redirect(url_for("admin.oidc_debug"))


@admin_bp.route("/admin/oidc/user/<int:user_id>")
@login_required
@admin_or_permission_required("view_users")
def oidc_user_detail(user_id):
    """View OIDC details for a specific user"""
    user = User.query.get_or_404(user_id)

    return render_template("admin/oidc_user_detail.html", user=user)


# ==================== OIDC Setup Wizard ====================


@admin_bp.route("/admin/oidc/setup-wizard")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_setup_wizard():
    """Guided OIDC setup wizard"""
    from app.config import Config
    
    # Get current configuration if any
    current_config = {
        "auth_method": getattr(Config, "AUTH_METHOD", "local"),
        "issuer": getattr(Config, "OIDC_ISSUER", ""),
        "client_id": getattr(Config, "OIDC_CLIENT_ID", ""),
        "client_secret_set": bool(getattr(Config, "OIDC_CLIENT_SECRET", None)),
        "redirect_uri": getattr(Config, "OIDC_REDIRECT_URI", ""),
        "scopes": getattr(Config, "OIDC_SCOPES", "openid profile email"),
        "username_claim": getattr(Config, "OIDC_USERNAME_CLAIM", "preferred_username"),
        "email_claim": getattr(Config, "OIDC_EMAIL_CLAIM", "email"),
        "full_name_claim": getattr(Config, "OIDC_FULL_NAME_CLAIM", "name"),
        "groups_claim": getattr(Config, "OIDC_GROUPS_CLAIM", "groups"),
        "admin_group": getattr(Config, "OIDC_ADMIN_GROUP", ""),
        "admin_emails": ",".join(getattr(Config, "OIDC_ADMIN_EMAILS", [])),
        "post_logout_redirect": getattr(Config, "OIDC_POST_LOGOUT_REDIRECT_URI", ""),
    }
    
    # Generate redirect URI if not set
    if not current_config["redirect_uri"]:
        current_config["redirect_uri"] = url_for("auth.oidc_callback", _external=True)
    
    return render_template("admin/oidc_setup_wizard.html", current_config=current_config)


@admin_bp.route("/admin/oidc/setup-wizard/test-connection", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_wizard_test_connection():
    """Test DNS resolution and metadata fetch for OIDC issuer"""
    from app.utils.oidc_metadata import fetch_oidc_metadata, test_dns_resolution, resolve_hostname_multiple_strategies
    from urllib.parse import urlparse
    
    data = request.get_json() or {}
    issuer = data.get("issuer", "").strip()
    
    if not issuer:
        return jsonify({"success": False, "error": "Issuer URL is required"}), 400
    
    # Validate URL format
    try:
        parsed = urlparse(issuer)
        if not parsed.scheme or not parsed.netloc:
            return jsonify({"success": False, "error": "Invalid URL format"}), 400
        hostname = parsed.netloc.split(":")[0]
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid URL: {str(e)}"}), 400
    
    result = {
        "success": False,
        "dns_resolved": False,
        "metadata": None,
        "error": None,
        "hostname": hostname,
    }
    
    # Test DNS resolution with multiple strategies
    dns_strategy = current_app.config.get("OIDC_DNS_RESOLUTION_STRATEGY", "auto")
    dns_success, dns_ip, dns_error, dns_strategy_used = test_dns_resolution(hostname, timeout=5, strategy=dns_strategy)
    result["dns_resolved"] = dns_success
    result["dns_strategy"] = dns_strategy_used
    result["dns_ip"] = dns_ip  # Will be masked in response
    if not dns_success:
        result["error"] = dns_error
        return jsonify(result), 200  # Return 200 but with success=False
    
    # Fetch metadata
    use_ip_directly = current_app.config.get("OIDC_USE_IP_DIRECTLY", True)
    use_docker_internal = current_app.config.get("OIDC_USE_DOCKER_INTERNAL", True)
    metadata, metadata_error, diagnostics = fetch_oidc_metadata(
        issuer,
        max_retries=3,
        retry_delay=2,
        timeout=10,
        use_dns_test=False,  # Already tested DNS
        dns_strategy=dns_strategy,
        use_ip_directly=use_ip_directly,
        use_docker_internal=use_docker_internal,
    )
    
    if diagnostics:
        result["diagnostics"] = diagnostics
    
    if metadata:
        result["success"] = True
        result["metadata"] = metadata
    else:
        result["error"] = metadata_error
    
    return jsonify(result), 200


@admin_bp.route("/admin/oidc/setup-wizard/validate-config", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_wizard_validate_config():
    """Validate OIDC configuration"""
    from urllib.parse import urlparse
    
    data = request.get_json() or {}
    errors = []
    
    # Validate issuer
    issuer = data.get("issuer", "").strip()
    if not issuer:
        errors.append({"field": "issuer", "message": "Issuer URL is required"})
    else:
        try:
            parsed = urlparse(issuer)
            if not parsed.scheme or not parsed.netloc:
                errors.append({"field": "issuer", "message": "Invalid URL format"})
            elif parsed.scheme not in ("http", "https"):
                errors.append({"field": "issuer", "message": "URL must use http or https"})
        except Exception as e:
            errors.append({"field": "issuer", "message": f"Invalid URL: {str(e)}"})
    
    # Validate client ID
    if not data.get("client_id", "").strip():
        errors.append({"field": "client_id", "message": "Client ID is required"})
    
    # Validate client secret
    if not data.get("client_secret", "").strip():
        errors.append({"field": "client_secret", "message": "Client Secret is required"})
    
    # Validate auth method
    auth_method = data.get("auth_method", "").strip().lower()
    if auth_method not in ("oidc", "both"):
        errors.append({"field": "auth_method", "message": "Auth method must be 'oidc' or 'both'"})
    
    # Validate redirect URI if provided
    redirect_uri = data.get("redirect_uri", "").strip()
    if redirect_uri:
        try:
            parsed = urlparse(redirect_uri)
            if not parsed.scheme or not parsed.netloc:
                errors.append({"field": "redirect_uri", "message": "Invalid redirect URI format"})
        except Exception as e:
            errors.append({"field": "redirect_uri", "message": f"Invalid redirect URI: {str(e)}"})
    
    if errors:
        return jsonify({"valid": False, "errors": errors}), 200
    
    return jsonify({"valid": True, "errors": []}), 200


@admin_bp.route("/admin/oidc/setup-wizard/generate-config", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_oidc")
def oidc_wizard_generate_config():
    """Generate environment variable configuration from wizard data"""
    
    data = request.get_json() or {}
    
    # Get base URL for redirect URI generation
    base_url = request.host_url.rstrip("/")
    if not data.get("redirect_uri"):
        redirect_uri = f"{base_url}/auth/oidc/callback"
    else:
        redirect_uri = data.get("redirect_uri", "").strip()
    
    # Build environment variables
    env_vars = {
        "AUTH_METHOD": data.get("auth_method", "oidc"),
        "OIDC_ISSUER": data.get("issuer", ""),
        "OIDC_CLIENT_ID": data.get("client_id", ""),
        "OIDC_CLIENT_SECRET": data.get("client_secret", ""),
        "OIDC_REDIRECT_URI": redirect_uri,
    }
    
    # Optional settings
    if data.get("scopes"):
        env_vars["OIDC_SCOPES"] = data.get("scopes")
    
    if data.get("username_claim"):
        env_vars["OIDC_USERNAME_CLAIM"] = data.get("username_claim")
    
    if data.get("email_claim"):
        env_vars["OIDC_EMAIL_CLAIM"] = data.get("email_claim")
    
    if data.get("full_name_claim"):
        env_vars["OIDC_FULL_NAME_CLAIM"] = data.get("full_name_claim")
    
    if data.get("groups_claim"):
        env_vars["OIDC_GROUPS_CLAIM"] = data.get("groups_claim")
    
    if data.get("admin_group"):
        env_vars["OIDC_ADMIN_GROUP"] = data.get("admin_group")
    
    if data.get("admin_emails"):
        env_vars["OIDC_ADMIN_EMAILS"] = data.get("admin_emails")
    
    if data.get("post_logout_redirect"):
        env_vars["OIDC_POST_LOGOUT_REDIRECT_URI"] = data.get("post_logout_redirect")
    
    # Generate .env format
    env_lines = []
    for key, value in env_vars.items():
        if value:  # Only include non-empty values
            # Escape special characters in value
            if " " in str(value) or "#" in str(value) or "$" in str(value):
                value = f'"{value}"'
            env_lines.append(f"{key}={value}")
    
    env_content = "\n".join(env_lines)
    
    # Generate Docker Compose format
    docker_compose_lines = ["      # OIDC Configuration"]
    for key, value in env_vars.items():
        if value:
            docker_compose_lines.append(f'      - {key}="{value}"')
    
    docker_compose_content = "\n".join(docker_compose_lines)
    
    return jsonify({
        "success": True,
        "env_content": env_content,
        "docker_compose_content": docker_compose_content,
        "redirect_uri": redirect_uri,
    }), 200


# ==================== API Token Management ====================


@admin_bp.route("/admin/api-tokens")
@login_required
@admin_required
def api_tokens():
    """API tokens management page"""
    from app.models import ApiToken

    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()

    return render_template("admin/api_tokens.html", tokens=tokens, users=users, now=datetime.utcnow())


@admin_bp.route("/admin/api-tokens", methods=["POST"])
@login_required
@admin_required
def create_api_token():
    """Create a new API token"""
    from app.models import ApiToken

    data = request.get_json() or {}

    # Validate input
    if not data.get("name"):
        return jsonify({"error": "Token name is required"}), 400
    if not data.get("user_id"):
        return jsonify({"error": "User ID is required"}), 400
    if not data.get("scopes"):
        return jsonify({"error": "At least one scope is required"}), 400

    # Verify user exists
    user = User.query.get(data["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user:
        return jsonify({"error": "Invalid user"}), 400

    # Create token
    try:
        api_token, plain_token = ApiToken.create_token(
            user_id=data["user_id"],
            name=data["name"],
            description=data.get("description", ""),
            scopes=data["scopes"],
            expires_days=data.get("expires_days"),
        )

        db.session.add(api_token)
        db.session.commit()

        current_app.logger.info(
            f"API token '{data['name']}' created for user {user.username} by {current_user.username}"
        )

        return (
            jsonify({"message": "API token created successfully", "token": plain_token, "token_id": api_token.id}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create API token: {e}")
        return jsonify({"error": "Failed to create token"}), 500


@admin_bp.route("/admin/api-tokens/<int:token_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_api_token(token_id):
    """Toggle API token active status"""
    from app.models import ApiToken

    token = ApiToken.query.get_or_404(token_id)
    token.is_active = not token.is_active

    try:
        db.session.commit()
        status = "activated" if token.is_active else "deactivated"
        current_app.logger.info(f"API token '{token.name}' {status} by {current_user.username}")
        return jsonify({"message": f"Token {status} successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to toggle API token: {e}")
        return jsonify({"error": "Failed to update token"}), 500


@admin_bp.route("/admin/api-tokens/<int:token_id>", methods=["DELETE"])
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
        current_app.logger.info(f"API token '{token_name}' deleted by {current_user.username}")
        return jsonify({"message": "Token deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete API token: {e}")
        return jsonify({"error": "Failed to delete token"}), 500


# ==================== Email Configuration Management ====================


@admin_bp.route("/admin/email")
@login_required
@admin_or_permission_required("manage_settings")
def email_support():
    """Email configuration and testing page"""
    from app.utils.email import check_email_configuration

    # Get email configuration status
    email_status = check_email_configuration()

    # Log dashboard access
    app_module.log_event("admin.email_support_viewed", user_id=current_user.id)
    app_module.track_event(current_user.id, "admin.email_support_viewed", {})

    return render_template("admin/email_support.html", email_status=email_status)


@admin_bp.route("/admin/email/test", methods=["POST"])
@limiter.limit("5 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def test_email():
    """Send a test email"""
    from app.utils.email import send_test_email

    data = request.get_json() or {}
    recipient = data.get("recipient")

    if not recipient:
        current_app.logger.warning(f"[EMAIL TEST API] No recipient provided by user {current_user.username}")
        return jsonify({"success": False, "message": "Recipient email is required"}), 400

    current_app.logger.info(f"[EMAIL TEST API] Test email request from user {current_user.username} to {recipient}")

    # Send test email
    sender_name = current_user.username or "TimeTracker Admin"
    success, message = send_test_email(recipient, sender_name)

    # Log the test
    current_app.logger.info(f"[EMAIL TEST API] Result: {'SUCCESS' if success else 'FAILED'} - {message}")
    app_module.log_event("admin.email_test_sent", user_id=current_user.id, recipient=recipient, success=success)
    app_module.track_event(current_user.id, "admin.email_test_sent", {"success": success, "configured": success})

    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 500


@admin_bp.route("/admin/email/config-status", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def email_config_status():
    """Get current email configuration status (for AJAX polling)"""
    from app.utils.email import check_email_configuration

    email_status = check_email_configuration()
    return jsonify(email_status), 200


@admin_bp.route("/admin/email/configure", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@admin_or_permission_required("manage_settings")
def save_email_config():
    """Save email configuration to database"""
    from app.utils.email import reload_mail_config

    data = request.get_json() or {}

    current_app.logger.info(f"[EMAIL CONFIG] Saving email configuration by user {current_user.username}")

    # Get settings
    settings = Settings.get_settings()

    # Update email configuration
    settings.mail_enabled = data.get("enabled", False)
    settings.mail_server = data.get("server", "").strip()
    settings.mail_port = int(data.get("port", 587))
    settings.mail_use_tls = data.get("use_tls", True)
    settings.mail_use_ssl = data.get("use_ssl", False)
    settings.mail_username = data.get("username", "").strip()

    # Only update password if provided (non-empty)
    password = data.get("password", "").strip()
    if password:
        settings.mail_password = password
        current_app.logger.info("[EMAIL CONFIG] Password updated")

    settings.mail_default_sender = data.get("default_sender", "").strip()

    current_app.logger.info(
        f"[EMAIL CONFIG] Settings: enabled={settings.mail_enabled}, "
        f"server={settings.mail_server}:{settings.mail_port}, "
        f"tls={settings.mail_use_tls}, ssl={settings.mail_use_ssl}"
    )

    # Validate
    if settings.mail_enabled and not settings.mail_server:
        current_app.logger.warning("[EMAIL CONFIG] Validation failed: mail server required")
        return jsonify({"success": False, "message": "Mail server is required when email is enabled"}), 400

    if settings.mail_use_tls and settings.mail_use_ssl:
        current_app.logger.warning("[EMAIL CONFIG] Validation failed: both TLS and SSL enabled")
        return jsonify({"success": False, "message": "Cannot use both TLS and SSL. Please choose one."}), 400

    # Save to database
    if not safe_commit("admin_save_email_config"):
        current_app.logger.error("[EMAIL CONFIG] Failed to save to database")
        return jsonify({"success": False, "message": "Failed to save email configuration to database"}), 500

    current_app.logger.info("[EMAIL CONFIG] ✓ Configuration saved to database")

    # Reload mail configuration
    if settings.mail_enabled:
        current_app.logger.info("[EMAIL CONFIG] Reloading mail configuration...")
        reload_result = reload_mail_config(current_app._get_current_object())
        current_app.logger.info(f"[EMAIL CONFIG] Mail config reload: {'SUCCESS' if reload_result else 'FAILED'}")

    # Log the change
    app_module.log_event("admin.email_config_saved", user_id=current_user.id, enabled=settings.mail_enabled)
    app_module.track_event(
        current_user.id, "admin.email_config_saved", {"enabled": settings.mail_enabled, "source": "database"}
    )

    current_app.logger.info("[EMAIL CONFIG] ✓ Email configuration update complete")

    return jsonify({"success": True, "message": "Email configuration saved successfully"}), 200


@admin_bp.route("/admin/email/get-config", methods=["GET"])
@login_required
@admin_or_permission_required("manage_settings")
def get_email_config():
    """Get current email configuration from database"""
    settings = Settings.get_settings()

    return (
        jsonify(
            {
                "enabled": settings.mail_enabled,
                "server": settings.mail_server or "",
                "port": settings.mail_port or 587,
                "use_tls": settings.mail_use_tls if settings.mail_use_tls is not None else True,
                "use_ssl": settings.mail_use_ssl if settings.mail_use_ssl is not None else False,
                "username": settings.mail_username or "",
                "password_set": bool(settings.mail_password),
                "default_sender": settings.mail_default_sender or "",
            }
        ),
        200,
    )


# ==================== Email Template Management ====================


@admin_bp.route("/admin/email-templates")
@login_required
@admin_or_permission_required("manage_settings")
def list_email_templates():
    """List all email templates"""
    from app.models import InvoiceTemplate

    templates = InvoiceTemplate.query.order_by(InvoiceTemplate.name).all()

    return render_template("admin/email_templates/list.html", templates=templates)


@admin_bp.route("/admin/email-templates/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def create_email_template():
    """Create a new email template"""
    from app.models import InvoiceTemplate

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        html = request.form.get("html", "").strip()
        css = request.form.get("css", "").strip()
        is_default = request.form.get("is_default") == "on"

        # Validate
        if not name:
            flash(_("Template name is required"), "error")
            return render_template("admin/email_templates/create.html")

        # Check for duplicate name
        existing = InvoiceTemplate.query.filter_by(name=name).first()
        if existing:
            flash(_("A template with this name already exists"), "error")
            return render_template(
                "admin/email_templates/create.html", name=name, description=description, html=html, css=css
            )

        # If setting as default, unset other defaults
        if is_default:
            InvoiceTemplate.query.update({InvoiceTemplate.is_default: False})

        # Create template
        template = InvoiceTemplate(
            name=name,
            description=description if description else None,
            html=html if html else None,
            css=css if css else None,
            is_default=is_default,
        )

        db.session.add(template)
        if not safe_commit("create_email_template", {"name": name}):
            flash(_("Could not create email template due to a database error."), "error")
            return render_template("admin/email_templates/create.html")

        flash(_("Email template created successfully"), "success")
        return redirect(url_for("admin.list_email_templates"))

    return render_template("admin/email_templates/create.html")


@admin_bp.route("/admin/email-templates/<int:template_id>")
@login_required
@admin_or_permission_required("manage_settings")
def view_email_template(template_id):
    """View email template details"""
    from app.models import InvoiceTemplate

    template = InvoiceTemplate.query.get_or_404(template_id)

    return render_template("admin/email_templates/view.html", template=template)


@admin_bp.route("/admin/email-templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def edit_email_template(template_id):
    """Edit email template"""
    from app.models import InvoiceTemplate

    template = InvoiceTemplate.query.get_or_404(template_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        html = request.form.get("html", "").strip()
        css = request.form.get("css", "").strip()
        is_default = request.form.get("is_default") == "on"

        # Validate
        if not name:
            flash(_("Template name is required"), "error")
            return render_template("admin/email_templates/edit.html", template=template)

        # Check for duplicate name (excluding current template)
        existing = InvoiceTemplate.query.filter(InvoiceTemplate.name == name, InvoiceTemplate.id != template_id).first()
        if existing:
            flash(_("A template with this name already exists"), "error")
            return render_template("admin/email_templates/edit.html", template=template)

        # If setting as default, unset other defaults
        if is_default:
            InvoiceTemplate.query.filter(InvoiceTemplate.id != template_id).update({InvoiceTemplate.is_default: False})

        # Update template
        template.name = name
        template.description = description if description else None
        template.html = html if html else None
        template.css = css if css else None
        template.is_default = is_default
        template.updated_at = datetime.utcnow()

        if not safe_commit("edit_email_template", {"template_id": template_id}):
            flash(_("Could not update email template due to a database error."), "error")
            return render_template("admin/email_templates/edit.html", template=template)

        flash(_("Email template updated successfully"), "success")
        return redirect(url_for("admin.view_email_template", template_id=template_id))

    return render_template("admin/email_templates/edit.html", template=template)


@admin_bp.route("/admin/email-templates/<int:template_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def delete_email_template(template_id):
    """Delete email template"""
    from app.models import InvoiceTemplate

    template = InvoiceTemplate.query.get_or_404(template_id)
    template_name = template.name

    # Check if template is in use
    if template.invoices.count() > 0 or template.recurring_invoices.count() > 0:
        flash(_("Cannot delete template that is in use by invoices or recurring invoices"), "error")
        return redirect(url_for("admin.list_email_templates"))

    db.session.delete(template)
    if not safe_commit("delete_email_template", {"template_id": template_id}):
        flash(_("Could not delete email template due to a database error."), "error")
    else:
        flash(_('Email template "%(name)s" deleted successfully', name=template_name), "success")

    return redirect(url_for("admin.list_email_templates"))


# ==================== Integration Setup Routes ====================


@admin_bp.route("/admin/integrations")
@login_required
@admin_required
def list_integrations_admin():
    """List all integrations (admin view). Redirect to main integrations page."""
    return redirect(url_for("integrations.list_integrations"))


@admin_bp.route("/admin/integrations/<provider>/setup", methods=["GET", "POST"])
@login_required
@admin_required
def integration_setup(provider):
    """Setup page for configuring integration OAuth credentials. Redirect to main integrations manage page."""
    return redirect(url_for("integrations.manage_integration", provider=provider))
