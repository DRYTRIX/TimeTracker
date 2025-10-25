from flask import Blueprint
from app.utils.timezone import utc_to_local, format_local_datetime
try:
    import markdown as _md
    import bleach
except Exception:
    _md = None
    bleach = None


def register_template_filters(app):
    """Register custom template filters for the application"""
    
    @app.template_filter('local_datetime')
    def local_datetime_filter(utc_dt, format_str='%Y-%m-%d %H:%M'):
        """Convert UTC datetime to local timezone for display"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, format_str)
    
    @app.template_filter('local_date')
    def local_date_filter(utc_dt):
        """Convert UTC datetime to local date only"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, '%Y-%m-%d')
    
    @app.template_filter('local_time')
    def local_time_filter(utc_dt):
        """Convert UTC datetime to local time only"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, '%H:%M')
    
    @app.template_filter('local_datetime_short')
    def local_datetime_short_filter(utc_dt):
        """Convert UTC datetime to local timezone in short format"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, '%m/%d %H:%M')
    
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if text is None:
            return ""
        # Handle different line break types (Windows \r\n, Mac \r, Unix \n)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text.replace('\n', '<br>')

    @app.template_filter('markdown')
    def markdown_filter(text):
        """Render markdown to safe HTML using bleach sanitation."""
        if not text:
            return ""
        if _md is None:
            # Fallback: escape and basic nl2br
            try:
                from markupsafe import escape
            except Exception:
                return text
            return escape(text).replace('\n', '<br>')

        html = _md.markdown(text, extensions=['extra', 'sane_lists', 'smarty'])
        if bleach is None:
            return html
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union({'p','pre','code','img','h1','h2','h3','h4','h5','h6','table','thead','tbody','tr','th','td','hr','br','ul','ol','li','strong','em','blockquote','a'})
        allowed_attrs = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            'a': ['href', 'title', 'rel', 'target'],
            'img': ['src', 'alt', 'title'],
        }
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)

    # Additional filters for PDFs / i18n-friendly formatting
    import datetime
    try:
        from babel.dates import format_date as babel_format_date
    except Exception:
        babel_format_date = None

    @app.template_filter('format_date')
    def format_date_filter(value, format='medium'):
        if not value:
            return ''
        if isinstance(value, (datetime.date, datetime.datetime)):
            try:
                if babel_format_date:
                    if format == 'full':
                        return babel_format_date(value, format='full')
                    if format == 'long':
                        return babel_format_date(value, format='long')
                    if format == 'short':
                        return babel_format_date(value, format='short')
                    return babel_format_date(value, format='medium')
                return value.strftime('%Y-%m-%d')
            except Exception:
                return value.strftime('%Y-%m-%d')
        return str(value)

    @app.template_filter('format_money')
    def format_money_filter(value):
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return str(value)
    
    def get_logo_base64(logo_path):
        """Convert logo file to base64 data URI for PDF embedding"""
        import os
        import base64
        import mimetypes
        
        if not logo_path:
            print("DEBUG: logo_path is None or empty")
            return None
            
        if not os.path.exists(logo_path):
            print(f"DEBUG: Logo file does not exist: {logo_path}")
            return None
        
        try:
            print(f"DEBUG: Reading logo from: {logo_path}")
            with open(logo_path, 'rb') as logo_file:
                logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(logo_path)
            if not mime_type:
                # Try to detect from file extension
                ext = os.path.splitext(logo_path)[1].lower()
                mime_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                    '.webp': 'image/webp'
                }
                mime_type = mime_map.get(ext, 'image/png')
            
            print(f"DEBUG: Logo encoded successfully, MIME type: {mime_type}, size: {len(logo_data)} bytes")
            return f'data:{mime_type};base64,{logo_data}'
        except Exception as e:
            print(f"DEBUG: Error encoding logo: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # Make get_logo_base64 available in templates as a global function
    app.jinja_env.globals.update(get_logo_base64=get_logo_base64)