"""
PDF Generation utility for invoices
Uses WeasyPrint to generate professional PDF invoices
"""

import os
import html as html_lib
from datetime import datetime

try:
    # Try importing WeasyPrint. This may fail on systems without native deps.
    from weasyprint import HTML, CSS  # type: ignore
    from weasyprint.text.fonts import FontConfiguration  # type: ignore

    _WEASYPRINT_AVAILABLE = True
except Exception:
    # Defer to fallback implementation at runtime
    HTML = None  # type: ignore
    CSS = None  # type: ignore
    FontConfiguration = None  # type: ignore
    _WEASYPRINT_AVAILABLE = False
from app.models import Settings, InvoicePDFTemplate
from app import db
from flask import current_app
from flask_babel import gettext as _

try:
    from babel.dates import format_date as babel_format_date
except Exception:
    babel_format_date = None
from pathlib import Path
from flask import render_template


class InvoicePDFGenerator:
    """Generate PDF invoices with company branding"""

    def __init__(self, invoice, settings=None, page_size="A4"):
        self.invoice = invoice
        self.settings = settings or Settings.get_settings()
        self.page_size = page_size or "A4"

    def generate_pdf(self):
        """Generate PDF content and return as bytes"""
        # If WeasyPrint isn't available or explicitly disabled, use the fallback
        if (not _WEASYPRINT_AVAILABLE) or os.getenv("DISABLE_WEASYPRINT", "").lower() in ("1", "true", "yes"):
            from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

            fallback = InvoicePDFGeneratorFallback(self.invoice, settings=self.settings)
            return fallback.generate_pdf()
        # Enable debugging - output directly to stdout for Docker console visibility
        import sys

        # Force unbuffered output to stdout - this ensures Docker sees it immediately
        def debug_print(msg):
            """Print debug message to stdout with immediate flush for Docker visibility"""
            print(msg, file=sys.stdout, flush=True)
            # Also try stderr
            print(msg, file=sys.stderr, flush=True)

        # Header - make it very visible
        print("\n" + "=" * 80, file=sys.stdout, flush=True)
        print("PDF GENERATOR generate_pdf() CALLED", file=sys.stdout, flush=True)
        print("=" * 80, file=sys.stdout, flush=True)
        debug_print(f"\nPDF GENERATOR DEBUG - Page Size: {self.page_size}")
        debug_print(f"{'='*80}\n")

        # Get template for the specified page size
        # Refresh the template from DB to ensure we have the latest version
        from app.models import InvoicePDFTemplate

        db.session.expire_all()  # Clear any cached data
        template = InvoicePDFTemplate.query.filter_by(page_size=self.page_size).first()
        if not template:
            template = InvoicePDFTemplate.get_template(self.page_size)

        debug_print(f"[DEBUG] Retrieved template: page_size={template.page_size}, id={template.id}")

        # Verify we got the correct template
        if template.page_size != self.page_size:
            debug_print(f"[WARNING] Template page_size mismatch! Expected {self.page_size}, got {template.page_size}")
            # This should never happen, but handle it just in case
            template = InvoicePDFTemplate.query.filter_by(page_size=self.page_size).first()
            if not template:
                template = InvoicePDFTemplate.get_template(self.page_size)

        # Check if this size-specific template has content
        # Use raw content - preserve exact content as saved
        template_html = template.template_html or ""
        template_css = template.template_css or ""

        debug_print(f"[DEBUG] Template content - HTML length={len(template_html)}, CSS length={len(template_css)}")

        if template_html:
            html_preview = template_html[:200].replace("\n", "\\n")
            debug_print(f"[DEBUG] Template HTML preview (first 200 chars): {html_preview}")

        if template_css:
            css_preview = template_css[:200].replace("\n", "\\n")
            debug_print(f"[DEBUG] Template CSS preview (first 200 chars): {css_preview}")

            # Check for @page rules in CSS
            import re

            page_rules = re.findall(r"@page\s*\{[^}]*\}", template_css, re.IGNORECASE | re.DOTALL)
            if page_rules:
                debug_print(f"[DEBUG] Found {len(page_rules)} @page rule(s) in template CSS:")
                for i, rule in enumerate(page_rules):
                    debug_print(f"[DEBUG]   @page rule {i+1}: {rule[:100]}")

        # Check if template has meaningful content (not just whitespace)
        has_custom_template = bool(template_html.strip() or template_css.strip())

        # Only use this template if it has content for this specific size
        if has_custom_template:
            debug_print(f"[DEBUG] Using custom template for page size {self.page_size}")
            # Use the template for this specific page size
            html_content, css_content = self._render_from_custom_template(template)
        else:
            # No template for this size - check if there's a legacy Settings template
            # This matches the editor's fallback behavior
            settings_html = (self.settings.invoice_pdf_template_html or "").strip()
            settings_css = (self.settings.invoice_pdf_template_css or "").strip()

            if settings_html or settings_css:
                # Use legacy Settings template, but ensure page size is correct
                from types import SimpleNamespace

                legacy_template = SimpleNamespace()
                legacy_template.page_size = self.page_size
                legacy_template.template_html = settings_html
                legacy_template.template_css = settings_css
                html_content, css_content = self._render_from_custom_template(legacy_template)
            else:
                # No templates at all, use default generation
                html_content = self._generate_html()
                css_content = self._generate_css()

        # Configure fonts
        font_config = FontConfiguration()

        # Create PDF (avoid passing unexpected args to PDF class)
        base_url = None
        try:
            base_url = current_app.root_path
        except Exception:
            base_url = None
        # Final verification: ensure CSS has correct @page size using the same logic as update_page_size_in_css
        # This is critical - WeasyPrint uses @page rules from stylesheets
        import re

        debug_print("[DEBUG] Final CSS verification - checking @page rules")

        # Check what @page size is in CSS before update
        if "@page" in css_content:
            page_size_match = re.search(
                r"@page\s*\{[^}]*?size\s*:\s*([^;}\n]+)", css_content, re.IGNORECASE | re.DOTALL
            )
            if page_size_match:
                found_size = page_size_match.group(1).strip()
                debug_print(f"[DEBUG] Found @page size in CSS: '{found_size}' (expected: '{self.page_size}')")
            else:
                debug_print("[DEBUG] @page rule exists but no size property found")

        # Re-apply update_page_size_in_css to ensure correctness (this handles nested braces properly)
        if "@page" in css_content:
            # Use the same function that's defined in _render_from_custom_template
            # But we need to call it here, so define a helper
            def final_update_page_size(css_text):
                """Final update of @page size - same logic as update_page_size_in_css"""
                page_match = re.search(r"@page\s*\{", css_text, re.IGNORECASE | re.MULTILINE)
                if page_match:
                    start_pos = page_match.start()
                    brace_count = 0
                    end_pos = len(css_text)
                    for i in range(page_match.end() - 1, len(css_text)):
                        if css_text[i] == "{":
                            brace_count += 1
                        elif css_text[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    page_block = css_text[start_pos:end_pos]
                    if re.search(r"size\s*:", page_block, re.IGNORECASE):
                        updated_block = re.sub(
                            r"size\s*:\s*[^;}\n]+",
                            f"size: {self.page_size};",
                            page_block,
                            flags=re.IGNORECASE | re.MULTILINE,
                        )
                        css_text = css_text[:start_pos] + updated_block + css_text[end_pos:]
                        debug_print("[DEBUG] Updated @page size in CSS block")
                return css_text

            css_content = final_update_page_size(css_content)

            # Verify after update
            page_size_match_after = re.search(
                r"@page\s*\{[^}]*?size\s*:\s*([^;}\n]+)", css_content, re.IGNORECASE | re.DOTALL
            )
            if page_size_match_after:
                found_size_after = page_size_match_after.group(1).strip()
                debug_print(f"[DEBUG] After update - @page size in CSS: '{found_size_after}'")
                if found_size_after != self.page_size:
                    debug_print(
                        f"[ERROR] @page size still incorrect! Expected '{self.page_size}', found '{found_size_after}'"
                    )
                else:
                    debug_print(f"[DEBUG] ✓ @page size is correct: '{found_size_after}'")

        debug_print(f"[DEBUG] Generating PDF with WeasyPrint")
        debug_print(f"[DEBUG]   - HTML length: {len(html_content)}")
        debug_print(f"[DEBUG]   - CSS length: {len(css_content)}")

        # Log final CSS @page rule that will be used
        if "@page" in css_content:
            page_rule_match = re.search(r"(@page\s*\{[^}]*\})", css_content, re.IGNORECASE | re.DOTALL)
            if page_rule_match:
                final_page_rule = page_rule_match.group(1)[:150]  # First 150 chars
                debug_print(f"[DEBUG] Final @page rule being used: {final_page_rule}")

        html_doc = HTML(string=html_content, base_url=base_url)
        css_doc = CSS(string=css_content, font_config=font_config)
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc], font_config=font_config)

        debug_print(f"[DEBUG] PDF generated successfully - size: {len(pdf_bytes)} bytes")
        debug_print(f"{'='*80}\n")

        return pdf_bytes

    def _render_from_custom_template(self, template=None):
        """Render HTML and CSS from custom templates stored in database, with fallback to default template."""
        # Define debug_print for this method scope
        import sys

        def debug_print(msg):
            """Print debug message to stdout with immediate flush for Docker visibility"""
            print(msg, file=sys.stdout, flush=True)
            print(msg, file=sys.stderr, flush=True)

        if template:
            # Ensure template matches the selected page size
            if hasattr(template, "page_size") and template.page_size != self.page_size:
                # Template doesn't match - this shouldn't happen, but handle it
                # Get the correct template
                from app.models import InvoicePDFTemplate

                correct_template = InvoicePDFTemplate.query.filter_by(page_size=self.page_size).first()
                if correct_template:
                    template = correct_template
                else:
                    # Couldn't find correct template - use default generation instead
                    raise ValueError(f"Template for page size {self.page_size} not found")

            # Don't strip - preserve exact content as saved (whitespace might be important)
            html_template = template.template_html or ""
            css_template = template.template_css or ""
        else:
            # No template provided - this should not happen in normal flow
            # If it does, we can't proceed without a template
            raise ValueError(f"No template provided for page size {self.page_size}. This is a bug.")
        html = ""

        def update_page_size_in_css(css_text):
            """Update @page size property to match selected page size"""
            import re

            # Find @page rule and update its size property
            # Handle nested @bottom-center rules by finding matching braces
            page_match = re.search(r"@page\s*\{", css_text, re.IGNORECASE | re.MULTILINE)
            if page_match:
                start_pos = page_match.start()
                # Find matching closing brace, accounting for nested braces
                brace_count = 0
                pos = page_match.end() - 1
                end_pos = len(css_text)
                for i in range(page_match.end() - 1, len(css_text)):
                    if css_text[i] == "{":
                        brace_count += 1
                    elif css_text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break

                page_block = css_text[start_pos:end_pos]

                # Replace or add size property
                if re.search(r"size\s*:", page_block, re.IGNORECASE):
                    # Replace existing size property - handle any whitespace and values
                    # Match: size: A4; or size: A4 ; or size:Letter; etc.
                    # Use a more robust pattern that handles various formats
                    updated_block = re.sub(
                        r"size\s*:\s*[^;}\n]+",
                        f"size: {self.page_size}",
                        page_block,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                    css_text = css_text[:start_pos] + updated_block + css_text[end_pos:]
                else:
                    # Add size property after @page {
                    updated_block = re.sub(
                        r"(@page\s*\{)",
                        r"\1\n            size: " + self.page_size + r";",
                        page_block,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    css_text = css_text[:start_pos] + updated_block + css_text[end_pos:]
            else:
                # Add @page rule at the beginning if it doesn't exist
                new_page_rule = (
                    f"@page {{\n            size: {self.page_size};\n            margin: 2cm;\n        }}\n\n"
                )
                css_text = new_page_rule + css_text

            return css_text

        def update_page_size_in_html(html_text):
            """Update @page size property in HTML's inline <style> tags"""
            import re

            # Find and update @page rules in <style> tags
            def update_style_tag(match):
                style_content = match.group(2)  # Content inside <style> tag
                updated_content = update_page_size_in_css(style_content)
                return f"{match.group(1)}{updated_content}{match.group(3)}"

            # Match <style> tags (with or without attributes)
            style_pattern = r"(<style[^>]*>)(.*?)(</style>)"
            if re.search(style_pattern, html_text, re.IGNORECASE | re.DOTALL):
                html_text = re.sub(style_pattern, update_style_tag, html_text, flags=re.IGNORECASE | re.DOTALL)

            return html_text

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
                    pos = page_match.end() - 1
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

        # Handle CSS: When both HTML (with inline styles) and separate CSS exist,
        # extract inline styles, merge with separate CSS, and remove from HTML to avoid conflicts
        import re

        css_to_use = ""
        html_inline_styles_extracted = False

        # Extract inline styles from HTML if present
        extracted_inline_css = ""
        if html_template and "<style>" in html_template:
            style_match = re.search(r"<style[^>]*>(.*?)</style>", html_template, re.IGNORECASE | re.DOTALL)
            if style_match:
                extracted_inline_css = style_match.group(1)
                html_inline_styles_extracted = True

        if css_template and css_template.strip():
            # Use separate CSS template - this is the authoritative source
            # Don't merge with inline styles - the CSS template should contain everything needed
            # (Editor saves both HTML with styles AND CSS, but CSS is the clean source)
            debug_print(f"[DEBUG] Using separate CSS template (length: {len(css_template)})")

            # Check @page size before update
            import re

            before_match = re.search(r"@page\s*\{[^}]*?size\s*:\s*([^;}\n]+)", css_template, re.IGNORECASE | re.DOTALL)
            if before_match:
                before_size = before_match.group(1).strip()
                debug_print(f"[DEBUG] CSS template @page size BEFORE update: '{before_size}'")

            css_to_use = update_page_size_in_css(css_template)

            # Check @page size after update
            after_match = re.search(r"@page\s*\{[^}]*?size\s*:\s*([^;}\n]+)", css_to_use, re.IGNORECASE | re.DOTALL)
            if after_match:
                after_size = after_match.group(1).strip()
                debug_print(f"[DEBUG] CSS template @page size AFTER update: '{after_size}'")
                if after_size != self.page_size:
                    debug_print(f"[ERROR] @page size update failed! Expected '{self.page_size}', got '{after_size}'")
                else:
                    debug_print(f"[DEBUG] ✓ CSS template @page size correctly updated to '{after_size}'")
        elif extracted_inline_css:
            # Only inline styles exist - extract and use them
            css_to_use = update_page_size_in_css(extracted_inline_css)
        else:
            # No CSS provided, use default
            try:
                from flask import render_template as _render_tpl

                css_to_use = _render_tpl("invoices/pdf_styles_default.css")
                css_to_use = update_page_size_in_css(css_to_use)
            except Exception:
                css_to_use = self._generate_css()

        # Ensure @page rule has correct size - this is critical for PDF generation
        css = css_to_use
        # Import helper functions for template
        from app.utils.template_filters import get_logo_base64
        from babel.dates import format_date as babel_format_date

        def format_date(value, format="medium"):
            """Format date for template"""
            if babel_format_date:
                return babel_format_date(value, format=format)
            return value.strftime("%Y-%m-%d") if value else ""

        def format_money(value):
            """Format money for template"""
            try:
                return f"{float(value):,.2f}"
            except Exception:
                return str(value)

        # Convert lazy='dynamic' relationships to lists for template rendering
        # This ensures {% for item in invoice.items %} works correctly
        try:
            if hasattr(self.invoice.items, "all"):
                # It's a SQLAlchemy Query object - need to call .all()
                invoice_items = self.invoice.items.all()
            else:
                # Already a list or other iterable
                invoice_items = list(self.invoice.items) if self.invoice.items else []
        except Exception:
            invoice_items = []

        try:
            if hasattr(self.invoice.extra_goods, "all"):
                # It's a SQLAlchemy Query object - need to call .all()
                invoice_extra_goods = self.invoice.extra_goods.all()
            else:
                # Already a list or other iterable
                invoice_extra_goods = list(self.invoice.extra_goods) if self.invoice.extra_goods else []
        except Exception:
            invoice_extra_goods = []

        # Create a wrapper object that has the converted lists
        from types import SimpleNamespace

        invoice_data = SimpleNamespace()
        # Copy all attributes from original invoice
        for attr in dir(self.invoice):
            if not attr.startswith("_"):
                try:
                    setattr(invoice_data, attr, getattr(self.invoice, attr))
                except Exception:
                    pass
        # Override with converted lists
        invoice_data.items = invoice_items
        invoice_data.extra_goods = invoice_extra_goods

        # Convert expenses from Query to list
        try:
            if hasattr(self.invoice, "expenses") and hasattr(self.invoice.expenses, "all"):
                invoice_expenses = self.invoice.expenses.all()
            else:
                invoice_expenses = list(self.invoice.expenses) if self.invoice.expenses else []
        except Exception:
            invoice_expenses = []
        invoice_data.expenses = invoice_expenses

        try:
            # Render using Flask's Jinja environment to include app filters and _()
            if html_template:
                from flask import render_template_string

                # When we have separate CSS, remove @page rules from HTML inline styles
                # to ensure the separate CSS @page rule is used (WeasyPrint uses first @page it finds)
                # Keep all other inline styles (like positioning) to preserve layout
                if html_inline_styles_extracted and css_template:
                    # Check if HTML has @page rules
                    import re

                    html_page_rules = re.findall(r"@page\s*\{[^}]*\}", html_template, re.IGNORECASE | re.DOTALL)
                    if html_page_rules:
                        debug_print(
                            f"[DEBUG] Found {len(html_page_rules)} @page rule(s) in HTML inline styles - removing them"
                        )
                        for i, rule in enumerate(html_page_rules):
                            debug_print(f"[DEBUG]   HTML @page rule {i+1}: {rule[:80]}")

                    # Remove @page rules from HTML inline styles (keep everything else)
                    html_template_updated = remove_page_rule_from_html(html_template)
                    debug_print("[DEBUG] Removed @page rules from HTML inline styles")
                else:
                    # No separate CSS or no inline styles - use template as-is or update inline @page
                    if html_template and "<style>" in html_template:
                        # Update @page size in HTML inline styles
                        html_template_updated = update_page_size_in_html(html_template)
                    else:
                        html_template_updated = html_template
                html = render_template_string(
                    html_template_updated,
                    invoice=invoice_data,  # Use wrapped object with lists
                    settings=self.settings,
                    Path=Path,
                    get_logo_base64=get_logo_base64,
                    format_date=format_date,
                    format_money=format_money,
                    now=datetime.now(),
                )
        except Exception as e:
            # Log the exception for debugging
            import traceback

            print(f"Error rendering custom PDF template: {e}")
            print(traceback.format_exc())
            html = ""

        if not html:
            try:
                html = render_template(
                    "invoices/pdf_default.html",
                    invoice=invoice_data,  # Use wrapped object with lists
                    settings=self.settings,
                    Path=Path,
                    get_logo_base64=get_logo_base64,
                    format_date=format_date,
                    format_money=format_money,
                    now=datetime.now(),
                )
            except Exception as e:
                # Log the exception for debugging
                import traceback

                print(f"Error rendering default PDF template: {e}")
                print(traceback.format_exc())
                html = f"<html><body><h1>{_('Invoice')} {self.invoice.invoice_number}</h1></body></html>"
        return html, css

    def _generate_html(self):
        """Generate HTML content for the invoice"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{_('Invoice')} {self.invoice.invoice_number}</title>
            <style>
            :root {{
                --primary: #2563eb;
                --primary-600: #1d4ed8;
                --text: #0f172a;
                --muted: #475569;
                --border: #e2e8f0;
                --bg: #ffffff;
                --bg-alt: #f8fafc;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                color: var(--text);
                margin: 0;
                padding: 0;
                background: var(--bg);
                font-size: 12pt;
            }}
            .wrapper {{
                padding: 24px 28px;
            }}
            .invoice-header {{
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                border-bottom: 2px solid var(--border);
                padding-bottom: 16px;
                margin-bottom: 18px;
            }}
            .brand {{ display: flex; gap: 16px; align-items: center; }}
            .company-logo {{ max-width: 140px; max-height: 70px; display: block; }}
            .company-name {{ font-size: 22pt; font-weight: 700; margin: 0; color: var(--primary); }}
            .company-meta span {{ display: block; color: var(--muted); font-size: 10pt; }}
            .invoice-meta {{ text-align: right; }}
            .invoice-title {{ font-size: 26pt; font-weight: 800; color: var(--primary); margin: 0 0 8px 0; }}
            .meta-grid {{ display: grid; grid-template-columns: auto auto; gap: 4px 16px; font-size: 10.5pt; }}
            .label {{ color: var(--muted); font-weight: 600; }}
            .value {{ color: var(--text); font-weight: 600; }}

            .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 18px; }}
            .card {{ background: var(--bg-alt); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }}
            .section-title {{ font-size: 12pt; font-weight: 700; color: var(--primary-600); margin: 0 0 8px 0; }}
            .small {{ color: var(--muted); font-size: 10pt; }}

            table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
            thead {{ display: table-header-group; }}
            tfoot {{ display: table-footer-group; }}
            thead th {{ background: var(--bg-alt); color: var(--muted); font-weight: 700; border: 1px solid var(--border); padding: 10px; font-size: 10.5pt; text-align: left; }}
            tbody td {{ border: 1px solid var(--border); padding: 10px; font-size: 10.5pt; }}
            tfoot td {{ border: 1px solid var(--border); padding: 10px; font-weight: 700; }}
            .num {{ text-align: right; }}
            .desc {{ width: 50%; }}

            /* Pagination controls */
            tr, td, th {{ break-inside: avoid; page-break-inside: avoid; }}
            .card, .invoice-header, .two-col {{ break-inside: avoid; page-break-inside: avoid; }}
            h4 {{ break-after: avoid; }}

            .totals {{ margin-top: 6px; }}
            .note {{ margin-top: 10px; }}
            .footer {{ border-top: 1px solid var(--border); margin-top: 18px; padding-top: 10px; color: var(--muted); font-size: 10pt; }}
            </style>
        </head>
        <body>
            <div class="wrapper">
                <!-- Header -->
                <div class="invoice-header">
                    <div class="brand">
                        {self._get_company_logo_html()}
                        <div>
                            <h1 class="company-name">{self._escape(self.settings.company_name)}</h1>
                            <div class="company-meta small">
                                <span>{self._nl2br(self.settings.company_address)}</span>
                                <span>{_('Email')}: {self._escape(self.settings.company_email)}  ·  {_('Phone')}: {self._escape(self.settings.company_phone)}</span>
                                <span>{_('Website')}: {self._escape(self.settings.company_website)}</span>
                                {self._get_company_tax_info()}
                            </div>
                        </div>
                    </div>
                    <div class="invoice-meta">
                        <div class="invoice-title">{_('INVOICE')}</div>
                        <div class="meta-grid">
                            <div class="label">{_('Invoice #')}</div><div class="value">{self.invoice.invoice_number}</div>
                            <div class="label">{_('Issue Date')}</div><div class="value">{self.invoice.issue_date.strftime('%Y-%m-%d') if self.invoice.issue_date else ''}</div>
                            <div class="label">{_('Due Date')}</div><div class="value">{self.invoice.due_date.strftime('%Y-%m-%d') if self.invoice.due_date else ''}</div>
                            <div class="label">{_('Status')}</div><div class="value">{_(self.invoice.status.title())}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Client Information -->
                <div class="two-col">
                    <div class="card">
                        <div class="section-title">{_('Bill To')}</div>
                        <div><strong>{self._escape(self.invoice.client_name)}</strong></div>
                        {self._get_client_email_html()}
                        {self._get_client_address_html()}
                    </div>
                    <div class="card">
                        <div class="section-title">{_('Project')}</div>
                        <div><strong>{self._escape(self.invoice.project.name)}</strong></div>
                        {self._get_project_description_html()}
                    </div>
                </div>
                
                <!-- Invoice Items -->
                <div>
                    <table>
                        <thead>
                            <tr>
                                <th class="desc">{_('Description')}</th>
                                <th class="num">{_('Quantity (Hours)')}</th>
                                <th class="num">{_('Unit Price')}</th>
                                <th class="num">{_('Total Amount')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {self._generate_items_rows()}
                        </tbody>
                        <tfoot>
                            {self._generate_totals_rows()}
                        </tfoot>
                    </table>
                </div>
                
                <!-- Additional Information -->
                {self._get_additional_info_html()}
                
                <!-- Footer -->
                <div class="footer">
                    {self._get_payment_info_html()}
                    <div><strong>{_('Terms & Conditions:')}</strong> {self._escape(self.settings.invoice_terms)}</div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _escape(self, value):
        return html_lib.escape(value) if value else ""

    def _nl2br(self, value):
        if not value:
            return ""
        return self._escape(value).replace("\n", "<br>")

    def _get_company_logo_html(self):
        """Generate HTML for company logo if available"""
        if self.settings.has_logo():
            logo_path = self.settings.get_logo_path()
            if logo_path and os.path.exists(logo_path):
                # Use base64 data URI for reliable PDF embedding (works better with WeasyPrint)
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

                    data_uri = f"data:{mime_type};base64,{logo_data}"
                    return f'<img src="{data_uri}" alt="Company Logo" class="company-logo">'
                except Exception as e:
                    # Fallback to file URI if base64 fails
                    try:
                        file_url = Path(logo_path).resolve().as_uri()
                    except Exception:
                        file_url = f"file://{logo_path}"
                    return f'<img src="{file_url}" alt="Company Logo" class="company-logo">'
        return ""

    def _get_company_tax_info(self):
        """Generate HTML for company tax information"""
        if self.settings.company_tax_id:
            return f'<div class="company-tax">Tax ID: {self.settings.company_tax_id}</div>'
        return ""

    def _get_client_email_html(self):
        """Generate HTML for client email if available"""
        if self.invoice.client_email:
            return f'<div class="client-email">{self.invoice.client_email}</div>'
        return ""

    def _get_client_address_html(self):
        """Generate HTML for client address if available"""
        if self.invoice.client_address:
            return f'<div class="client-address">{self.invoice.client_address}</div>'
        return ""

    def _get_project_description_html(self):
        """Generate HTML for project description if available"""
        if self.invoice.project.description:
            return f'<div class="project-description">{self.invoice.project.description}</div>'
        return ""

    def _generate_items_rows(self):
        """Generate HTML rows for invoice items and extra goods"""
        rows = []

        # Add regular invoice items
        for item in self.invoice.items:
            row = f"""
            <tr>
                <td>
                    {self._escape(item.description)}
                    {self._get_time_entry_info_html(item)}
                </td>
                <td class="num">{item.quantity:.2f}</td>
                <td class="num">{self._format_currency(item.unit_price)}</td>
                <td class="num">{self._format_currency(item.total_amount)}</td>
            </tr>
            """
            rows.append(row)

        # Add extra goods
        for good in self.invoice.extra_goods:
            # Build description with category and SKU if available
            description_parts = [self._escape(good.name)]
            if good.description:
                description_parts.append(
                    f"<br><small class='good-description'>{self._escape(good.description)}</small>"
                )
            if good.sku:
                description_parts.append(f"<br><small class='good-sku'>{_('SKU')}: {self._escape(good.sku)}</small>")
            if good.category:
                description_parts.append(
                    f"<br><small class='good-category'>{_('Category')}: {self._escape(good.category.title())}</small>"
                )

            description_html = "".join(description_parts)

            row = f"""
            <tr>
                <td>
                    {description_html}
                </td>
                <td class="num">{good.quantity:.2f}</td>
                <td class="num">{self._format_currency(good.unit_price)}</td>
                <td class="num">{self._format_currency(good.total_amount)}</td>
            </tr>
            """
            rows.append(row)

        return "".join(rows)

    def _get_time_entry_info_html(self, item):
        """Generate HTML for time entry information if available"""
        if item.time_entry_ids:
            count = len(item.time_entry_ids.split(","))
            return f'<br><small class="time-entry-info">Generated from {count} time entries</small>'
        return ""

    def _generate_totals_rows(self):
        """Generate HTML rows for invoice totals"""
        rows = []

        # Subtotal
        rows.append(
            f"""
        <tr>
            <td colspan="3" class="num">Subtotal:</td>
            <td class="num">{self._format_currency(self.invoice.subtotal)}</td>
        </tr>
        """
        )

        # Tax if applicable
        if self.invoice.tax_rate > 0:
            rows.append(
                f"""
            <tr>
                <td colspan="3" class="num">Tax ({self.invoice.tax_rate:.2f}%):</td>
                <td class="num">{self._format_currency(self.invoice.tax_amount)}</td>
            </tr>
            """
            )

        # Total
        rows.append(
            f"""
        <tr>
            <td colspan="3" class="num">Total Amount:</td>
            <td class="num">{self._format_currency(self.invoice.total_amount)}</td>
        </tr>
        """
        )

        return "".join(rows)

    def _get_additional_info_html(self):
        """Generate HTML for additional invoice information"""
        html_parts = []

        if self.invoice.notes:
            html_parts.append(
                f"""
            <div class="notes-section">
                <h4>{_('Notes:')}</h4>
                <p>{self.invoice.notes}</p>
            </div>
            """
            )

        if self.invoice.terms:
            html_parts.append(
                f"""
            <div class="terms-section">
                <h4>{_('Terms:')}</h4>
                <p>{self.invoice.terms}</p>
            </div>
            """
            )

        if html_parts:
            return f'<div class="additional-info">{"".join(html_parts)}</div>'
        return ""

    def _format_currency(self, value):
        """Format numeric currency with thousands separators and 2 decimals."""
        try:
            return f"{float(value):,.2f} {self.settings.currency}"
        except Exception:
            return f"{value} {self.settings.currency}"

    def _get_payment_info_html(self):
        """Generate HTML for payment information"""
        if self.settings.company_bank_info:
            return f"""
            <h4>{_('Payment Information:')}</h4>
            <div class="bank-info">{self.settings.company_bank_info}</div>
            """
        return ""

    def _generate_css(self):
        """Generate CSS styles for the invoice"""
        # Get page size, defaulting to A4
        page_size = self.page_size or "A4"
        # Use .format() instead of f-string to avoid escaping all CSS braces
        return """
        @page {{
            size: {page_size};
            margin: 2cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        
        .invoice-container {{
            max-width: 100%;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2em;
            border-bottom: 2px solid #007bff;
            padding-bottom: 1em;
        }}
        
        .company-info {{
            flex: 1;
        }}
        
        .company-logo {{
            max-width: 150px;
            max-height: 80px;
            display: block;
            margin-left: auto;
            margin-right: 0;
            margin-bottom: 1em;
        }}
        
        .company-name {{
            font-size: 24pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 0.5em 0;
        }}
        
        .company-address {{
            margin-bottom: 0.5em;
            line-height: 1.3;
        }}
        
        .company-contact {{
            margin-bottom: 0.5em;
        }}
        
        .company-contact span {{
            display: block;
            margin-bottom: 0.2em;
            font-size: 10pt;
        }}
        
        .company-tax {{
            font-size: 10pt;
            color: #666;
        }}
        
        .invoice-info {{
            text-align: right;
            min-width: 200px;
        }}
        
        .logo-container {{
            text-align: right;
            margin-bottom: 1em;
        }}
        
        .invoice-title {{
            font-size: 28pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 1em 0;
        }}
        
        .invoice-details .detail-row {{
            margin-bottom: 0.5em;
        }}
        
        .detail-row .label {{
            font-weight: bold;
            margin-right: 0.5em;
        }}
        
        .status-draft {{ color: #6c757d; }}
        .status-sent {{ color: #17a2b8; }}
        .status-paid {{ color: #28a745; }}
        .status-overdue {{ color: #dc3545; }}
        .status-cancelled {{ color: #343a40; }}
        
        .client-section, .project-section {{
            margin-bottom: 2em;
        }}
        
        .client-section h3, .project-section h3 {{
            font-size: 14pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 0.5em 0;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 0.3em;
        }}
        
        .client-name {{
            font-weight: bold;
            font-size: 14pt;
            margin-bottom: 0.5em;
        }}
        
        .client-email, .client-address, .project-description {{
            margin-bottom: 0.3em;
            color: #666;
        }}
        
        .items-section {{
            margin-bottom: 2em;
        }}
        
        .invoice-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1em;
        }}
        
        .invoice-table th,
        .invoice-table td {{
            border: 1px solid #dee2e6;
            padding: 0.75em;
            text-align: left;
        }}
        
        .invoice-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }}
        
        .description {{ width: 40%; }}
        .quantity {{ width: 15%; text-align: center; }}
        .unit-price {{ width: 20%; text-align: right; }}
        .total {{ width: 25%; text-align: right; }}
        
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        
        .time-entry-info {{
            color: #6c757d;
            font-style: italic;
        }}
        
        .subtotal {{ background-color: #f8f9fa; }}
        .tax {{ background-color: #fff3cd; }}
        .total {{ background-color: #d1ecf1; font-weight: bold; }}
        
        .additional-info {{
            margin-bottom: 2em;
        }}
        
        .notes-section, .terms-section {{
            margin-bottom: 1em;
        }}
        
        .notes-section h4, .terms-section h4 {{
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }}
        
        .footer {{
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #dee2e6;
        }}
        
        .payment-info {{
            margin-bottom: 1em;
        }}
        
        .payment-info h4 {{
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }}
        
        .bank-info {{
            color: #666;
            line-height: 1.3;
        }}
        
        .terms h4 {{
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }}
        
        .terms p {{
            color: #666;
            line-height: 1.3;
        }}
        
        /* Utility classes */
        .nl2br {{
            white-space: pre-line;
        }}
        """.format(
            page_size=page_size
        )
