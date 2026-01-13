from flask import Blueprint
from app.utils.timezone import (
    utc_to_local,
    format_local_datetime,
    format_user_datetime,
)

try:
    import markdown as _md
    import bleach
except Exception:
    _md = None
    bleach = None


def register_template_filters(app):
    """Register custom template filters for the application"""

    @app.template_filter("local_datetime")
    def local_datetime_filter(utc_dt, format_str="%Y-%m-%d %H:%M"):
        """Convert UTC datetime to local timezone for display"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, format_str)

    @app.template_filter("local_date")
    def local_date_filter(utc_dt):
        """Convert UTC datetime to local date only"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, "%Y-%m-%d")

    @app.template_filter("local_time")
    def local_time_filter(utc_dt):
        """Convert UTC datetime to local time only"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, "%H:%M")

    @app.template_filter("local_datetime_short")
    def local_datetime_short_filter(utc_dt):
        """Convert UTC datetime to local timezone in short format"""
        if utc_dt is None:
            return ""
        return format_local_datetime(utc_dt, "%m/%d %H:%M")

    @app.template_filter("user_datetime")
    def user_datetime_filter(dt, format_str="%Y-%m-%d %H:%M"):
        """Format datetime using the authenticated user's timezone preference."""
        if dt is None:
            return ""
        return format_user_datetime(dt, format_str=format_str)

    @app.template_filter("user_date")
    def user_date_filter(dt, format_str="%Y-%m-%d"):
        """Format date using the authenticated user's timezone preference."""
        if dt is None:
            return ""
        return format_user_datetime(dt, format_str=format_str)

    @app.template_filter("user_time")
    def user_time_filter(dt, format_str="%H:%M"):
        """Format time using the authenticated user's timezone preference."""
        if dt is None:
            return ""
        return format_user_datetime(dt, format_str=format_str)

    @app.template_filter("nl2br")
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if text is None:
            return ""
        # Handle different line break types (Windows \r\n, Mac \r, Unix \n)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.replace("\n", "<br>")

    @app.template_filter("markdown")
    def markdown_filter(text):
        """Render markdown to safe HTML using bleach sanitation, preserving rich text styling."""
        if not text:
            return ""

        # Check if text appears to be pure HTML (starts with < and looks like HTML document)
        # Only treat as HTML if it starts with a tag and doesn't look like markdown
        import re

        # More specific check: HTML should start with a tag and not be markdown list/bullet syntax
        is_html = (
            re.match(r"^\s*<[a-z]", text, re.IGNORECASE)
            and not re.match(r"^\s*[-*+]\s+", text)  # Not markdown list
            and not re.match(r"^\s*\d+\.\s+", text)
        )  # Not numbered list

        if is_html:
            if bleach is None:
                try:
                    from markupsafe import escape

                    return escape(text)
                except Exception:
                    return text
            # Allow style attributes for rich text preservation
            allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union(
                {
                    "p",
                    "pre",
                    "code",
                    "img",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "table",
                    "thead",
                    "tbody",
                    "tr",
                    "th",
                    "td",
                    "hr",
                    "br",
                    "ul",
                    "ol",
                    "li",
                    "strong",
                    "em",
                    "b",
                    "i",
                    "u",
                    "s",
                    "strike",
                    "blockquote",
                    "a",
                    "div",
                    "span",
                    "sub",
                    "sup",
                    "del",
                    "ins",
                    "mark",
                    "small",
                    "big",
                }
            )
            # Build allowed_attrs with style support for common rich text elements
            allowed_attrs = {
                **bleach.sanitizer.ALLOWED_ATTRIBUTES,
                "a": ["href", "title", "rel", "target", "style"],
                "img": ["src", "alt", "title", "style", "width", "height"],
                "p": ["style", "class", "id"],
                "div": ["style", "class", "id"],
                "span": ["style", "class", "id"],
                "h1": ["style", "class", "id"],
                "h2": ["style", "class", "id"],
                "h3": ["style", "class", "id"],
                "h4": ["style", "class", "id"],
                "h5": ["style", "class", "id"],
                "h6": ["style", "class", "id"],
                "strong": ["style", "class", "id"],
                "em": ["style", "class", "id"],
                "b": ["style", "class", "id"],
                "i": ["style", "class", "id"],
                "u": ["style", "class", "id"],
                "s": ["style", "class", "id"],
                "strike": ["style", "class", "id"],
                "blockquote": ["style", "class", "id"],
                "ul": ["style", "class", "id", "type"],
                "ol": ["style", "class", "id", "type", "start"],
                "li": ["style", "class", "id"],
                "table": ["style", "class", "id"],
                "thead": ["style", "class", "id"],
                "tbody": ["style", "class", "id"],
                "tr": ["style", "class", "id"],
                "th": ["style", "class", "id"],
                "td": ["style", "class", "id"],
            }
            return bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs, strip=True)

        # Process as markdown
        if _md is None:
            # Fallback: escape and basic nl2br
            try:
                from markupsafe import escape
            except Exception:
                return text
            return escape(text).replace("\n", "<br>")

        # Convert markdown to HTML
        html = _md.markdown(text, extensions=["extra", "sane_lists", "smarty", "codehilite"])
        if bleach is None:
            return html

        # Sanitize the HTML output from markdown
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union(
            {
                "p",
                "pre",
                "code",
                "img",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
                "hr",
                "br",
                "ul",
                "ol",
                "li",
                "strong",
                "em",
                "b",
                "i",
                "u",
                "s",
                "strike",
                "blockquote",
                "a",
                "div",
                "span",
                "sub",
                "sup",
                "del",
                "ins",
                "mark",
                "small",
                "big",
            }
        )
        # Build allowed_attrs with style support for common rich text elements
        allowed_attrs = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            "a": ["href", "title", "rel", "target", "style"],
            "img": ["src", "alt", "title", "style", "width", "height"],
            "p": ["style", "class", "id"],
            "div": ["style", "class", "id"],
            "span": ["style", "class", "id"],
            "h1": ["style", "class", "id"],
            "h2": ["style", "class", "id"],
            "h3": ["style", "class", "id"],
            "h4": ["style", "class", "id"],
            "h5": ["style", "class", "id"],
            "h6": ["style", "class", "id"],
            "strong": ["style", "class", "id"],
            "em": ["style", "class", "id"],
            "b": ["style", "class", "id"],
            "i": ["style", "class", "id"],
            "u": ["style", "class", "id"],
            "s": ["style", "class", "id"],
            "strike": ["style", "class", "id"],
            "blockquote": ["style", "class", "id"],
            "ul": ["style", "class", "id", "type"],
            "ol": ["style", "class", "id", "type", "start"],
            "li": ["style", "class", "id"],
            "table": ["style", "class", "id"],
            "thead": ["style", "class", "id"],
            "tbody": ["style", "class", "id"],
            "tr": ["style", "class", "id"],
            "th": ["style", "class", "id"],
            "td": ["style", "class", "id"],
        }
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)

    # Additional filters for PDFs / i18n-friendly formatting
    import datetime

    try:
        from babel.dates import format_date as babel_format_date
    except Exception:
        babel_format_date = None

    @app.template_filter("format_date")
    def format_date_filter(value, format="medium"):
        if not value:
            return ""
        if isinstance(value, (datetime.date, datetime.datetime)):
            try:
                if babel_format_date:
                    if format == "full":
                        return babel_format_date(value, format="full")
                    if format == "long":
                        return babel_format_date(value, format="long")
                    if format == "short":
                        return babel_format_date(value, format="short")
                    return babel_format_date(value, format="medium")
                return value.strftime("%Y-%m-%d")
            except Exception:
                return value.strftime("%Y-%m-%d")
        return str(value)

    @app.template_filter("format_money")
    def format_money_filter(value):
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return str(value)

    @app.template_filter("timeago")
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

    @app.template_filter("currency_symbol")
    def currency_symbol_filter(currency_code):
        """Convert currency code to symbol"""
        if not currency_code:
            return "$"

        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CNY": "¥",
            "INR": "₹",
            "AUD": "A$",
            "CAD": "C$",
            "CHF": "CHF",
            "SEK": "kr",
            "NOK": "kr",
            "DKK": "kr",
            "PLN": "zł",
            "CZK": "Kč",
            "RUB": "₽",
            "BRL": "R$",
            "ZAR": "R",
            "MXN": "MX$",
            "SGD": "S$",
            "HKD": "HK$",
            "NZD": "NZ$",
            "KRW": "₩",
            "TRY": "₺",
            "AED": "د.إ",
            "SAR": "﷼",
        }

        return currency_symbols.get(currency_code.upper(), currency_code)

    @app.template_filter("currency_icon")
    def currency_icon_filter(currency_code):
        """Convert currency code to FontAwesome icon class"""
        if not currency_code:
            return "fa-dollar-sign"

        currency_icons = {
            "USD": "fa-dollar-sign",
            "EUR": "fa-euro-sign",
            "GBP": "fa-pound-sign",
            "JPY": "fa-yen-sign",
            "CNY": "fa-yen-sign",
            "INR": "fa-rupee-sign",
            "RUB": "fa-ruble-sign",
            "BRL": "fa-dollar-sign",
            "TRY": "fa-lira-sign",
        }

        return currency_icons.get(currency_code.upper(), "fa-dollar-sign")


def get_logo_base64(logo_path):
    """Convert logo file to base64 data URI for PDF embedding"""
    if not logo_path:
        return ""

    import os

    if not os.path.exists(logo_path):
        return ""

    try:
        import base64
        import mimetypes

        with open(logo_path, "rb") as logo_file:
            logo_data = base64.b64encode(logo_file.read()).decode("utf-8")

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(logo_path)
        if not mime_type:
            # Default to PNG if can't detect
            mime_type = "image/png"

        return f"data:{mime_type};base64,{logo_data}"
    except Exception as e:
        print(f"Error converting logo to base64: {e}")
        return ""


def get_image_base64(image_path):
    """Convert image file to base64 data URI for PDF embedding
    
    Args:
        image_path: Relative path to image file (e.g., 'app/static/uploads/invoice_images/file.png')
                    or absolute path
    
    Returns:
        Base64 data URI string or empty string on error
    """
    if not image_path:
        return ""

    import os
    from flask import current_app

    # Handle relative paths (from app root)
    if not os.path.isabs(image_path):
        full_path = os.path.join(current_app.root_path, "..", image_path)
    else:
        full_path = image_path

    if not os.path.exists(full_path):
        return ""

    try:
        import base64
        import mimetypes

        with open(full_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            # Default to PNG if can't detect
            mime_type = "image/png"

        return f"data:{mime_type};base64,{image_data}"
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return ""
