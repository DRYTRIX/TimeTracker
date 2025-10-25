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

    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Convert a datetime to a 'time ago' string (e.g., '2 hours ago')"""
        if dt is None:
            return ""
        
        # Import here to avoid circular imports
        from datetime import datetime, timezone
        
        # Ensure we're working with a timezone-aware datetime
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        
        # Calculate difference
        diff = now - dt
        
        # Convert to seconds
        seconds = diff.total_seconds()
        
        # Handle future dates
        if seconds < 0:
            return "just now"
        
        # Calculate time units
        minutes = seconds / 60
        hours = minutes / 60
        days = hours / 24
        weeks = days / 7
        months = days / 30
        years = days / 365
        
        # Return appropriate string
        if seconds < 60:
            return "just now"
        elif minutes < 60:
            m = int(minutes)
            return f"{m} minute{'s' if m != 1 else ''} ago"
        elif hours < 24:
            h = int(hours)
            return f"{h} hour{'s' if h != 1 else ''} ago"
        elif days < 7:
            d = int(days)
            return f"{d} day{'s' if d != 1 else ''} ago"
        elif weeks < 4:
            w = int(weeks)
            return f"{w} week{'s' if w != 1 else ''} ago"
        elif months < 12:
            mo = int(months)
            return f"{mo} month{'s' if mo != 1 else ''} ago"
        else:
            y = int(years)
            return f"{y} year{'s' if y != 1 else ''} ago"
