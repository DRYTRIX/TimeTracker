"""
PDF Generation utility for invoices and quotes
Uses ReportLab to generate professional PDF documents

Note: This module has been migrated from WeasyPrint to ReportLab for better reliability
and fewer system dependencies. Legacy WeasyPrint imports remain for backward compatibility
but are not actively used in the new implementation.
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
from app.models import Settings, InvoicePDFTemplate, QuotePDFTemplate
from app import db
from flask import current_app
from flask_babel import gettext as _

try:
    from babel.dates import format_date as babel_format_date
except Exception:
    babel_format_date = None
from pathlib import Path
from flask import render_template


def update_page_size_in_css(css_text, page_size):
    """
    Update @page size property to match the specified page size.
    
    This function handles:
    - Replacing existing @page size property
    - Adding @page size property if missing
    - Handling nested @page rules (e.g., @bottom-center)
    - Multiple @page rules (updates all of them)
    
    Args:
        css_text: CSS string that may contain @page rules
        page_size: Target page size (e.g., "A4", "Letter")
    
    Returns:
        Updated CSS string with correct @page size
    """
    import re
    
    if not css_text or not page_size:
        return css_text
    
    # Find all @page rules (may have multiple)
    page_pattern = r"@page\s*\{"
    matches = list(re.finditer(page_pattern, css_text, re.IGNORECASE | re.MULTILINE))
    
    if not matches:
        # No @page rule exists - add one at the beginning
        new_page_rule = (
            f"@page {{\n            size: {page_size};\n            margin: 2cm;\n        }}\n\n"
        )
        return new_page_rule + css_text
    
    # Process matches in reverse order to maintain positions
    for match in reversed(matches):
        start_pos = match.start()
        # Find matching closing brace, accounting for nested braces
        brace_count = 0
        end_pos = len(css_text)
        
        for i in range(match.end() - 1, len(css_text)):
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
            # Replace existing size property - handle any whitespace, quotes, and values
            # Match: size: "A5" or size: A5 or size:A5 etc.
            updated_block = re.sub(
                r"size\s*:\s*['\"]?[^;}\n]+['\"]?",
                f"size: {page_size}",
                page_block,
                flags=re.IGNORECASE | re.MULTILINE,
            )
            css_text = css_text[:start_pos] + updated_block + css_text[end_pos:]
        else:
            # Add size property after @page {
            updated_block = re.sub(
                r"(@page\s*\{)",
                r"\1\n            size: " + page_size + r";",
                page_block,
                count=1,
                flags=re.IGNORECASE,
            )
            css_text = css_text[:start_pos] + updated_block + css_text[end_pos:]
    
    return css_text


def update_wrapper_dimensions_in_css(css_text, page_size):
    """
    Update wrapper dimensions (width, height, max-width, max-height) in CSS to match page size.
    
    This function updates the .invoice-wrapper and .quote-wrapper dimensions to match
    the selected page size. Dimensions are calculated at 72 DPI for PDF.
    
    Args:
        css_text: CSS string that may contain wrapper dimension definitions
        page_size: Target page size (e.g., "A4", "A5", "Letter")
    
    Returns:
        Updated CSS string with correct wrapper dimensions
    """
    if not css_text or not page_size:
        return css_text
    
    # Standard page sizes (shared by both InvoicePDFTemplate and QuotePDFTemplate)
    PAGE_SIZES = {
        "A4": {"width": 210, "height": 297},
        "Letter": {"width": 216, "height": 279},
        "Legal": {"width": 216, "height": 356},
        "A3": {"width": 297, "height": 420},
        "A5": {"width": 148, "height": 210},
        "Tabloid": {"width": 279, "height": 432},
    }
    
    # Get page dimensions
    page_dimensions = PAGE_SIZES.get(page_size)
    if not page_dimensions:
        return css_text
    
    # Calculate dimensions in pixels at 72 DPI (PDF standard)
    width_mm = page_dimensions['width']
    height_mm = page_dimensions['height']
    width_px = int((width_mm / 25.4) * 72)
    height_px = int((height_mm / 25.4) * 72)
    
    import re
    
    # Pattern to match wrapper dimension properties
    # Match: width: 420px, width:420px, width: 420px !important, etc.
    dimension_patterns = [
        (r'\.invoice-wrapper\s*\{[^}]*?)(width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.invoice-wrapper\s*\{[^}]*?)(height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
        (r'\.invoice-wrapper\s*\{[^}]*?)(max-width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.invoice-wrapper\s*\{[^}]*?)(max-height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
        (r'\.invoice-wrapper\s*\{[^}]*?)(min-width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.invoice-wrapper\s*\{[^}]*?)(min-height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(max-width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(max-height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(min-width\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{width_px}px\\3'),
        (r'\.quote-wrapper\s*\{[^}]*?)(min-height\s*:\s*)\d+px(\s*!important)?', 
         f'\\1\\2{height_px}px\\3'),
    ]
    
    updated_css = css_text
    for pattern, replacement in dimension_patterns:
        updated_css = re.sub(pattern, replacement, updated_css, flags=re.IGNORECASE | re.DOTALL)
    
    # Also update html, body dimensions if they exist
    updated_css = re.sub(
        r'(html,\s*body\s*\{[^}]*?)(width\s*:\s*)\d+px(\s*!important)?',
        f'\\1\\2{width_px}px\\3',
        updated_css,
        flags=re.IGNORECASE | re.DOTALL
    )
    updated_css = re.sub(
        r'(html,\s*body\s*\{[^}]*?)(height\s*:\s*)\d+px(\s*!important)?',
        f'\\1\\2{height_px}px\\3',
        updated_css,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    return updated_css


def validate_page_size_in_css(css_text, expected_page_size):
    """
    Validate that CSS contains the correct @page size.
    
    Args:
        css_text: CSS string to validate
        expected_page_size: Expected page size (e.g., "A4", "Letter")
    
    Returns:
        tuple: (is_valid: bool, found_sizes: list) - True if all @page rules have correct size
    """
    import re
    
    if not css_text or not expected_page_size:
        return False, []
    
    # Find all @page rules and check their size
    page_rules = re.findall(r"@page\s*\{[^}]*\}", css_text, re.IGNORECASE | re.DOTALL)
    found_sizes = []
    
    for rule in page_rules:
        size_match = re.search(r"size\s*:\s*['\"]?([^;}\n'\"]+)['\"]?", rule, re.IGNORECASE)
        if size_match:
            found_size = size_match.group(1).strip()
            found_sizes.append(found_size)
            # Remove quotes if present (double-check)
            found_size = found_size.strip('"\'')
            if found_size != expected_page_size:
                return False, found_sizes
    
    # If we found @page rules, all should have the correct size
    if page_rules and not found_sizes:
        return False, []  # @page rules exist but no size specified
    
    # If no @page rules, that's also a problem
    if not page_rules:
        return False, []
    
    return True, found_sizes


class InvoicePDFGenerator:
    """Generate PDF invoices with company branding"""

    def __init__(self, invoice, settings=None, page_size="A4"):
        self.invoice = invoice
        self.settings = settings or Settings.get_settings()
        self.page_size = page_size or "A4"

    def generate_pdf(self):
        """Generate PDF content and return as bytes using ReportLab"""
        import sys
        import json
        from flask import current_app

        def debug_print(msg):
            """Print debug message to stdout with immediate flush for Docker visibility"""
            print(msg, file=sys.stdout, flush=True)
            print(msg, file=sys.stderr, flush=True)
            # Also log using Flask logger if available
            try:
                current_app.logger.info(msg)
            except Exception:
                pass

        invoice_id = getattr(self.invoice, 'id', 'N/A')
        invoice_number = getattr(self.invoice, 'invoice_number', 'N/A')
        
        debug_print(f"\n[PDF_EXPORT] PDF GENERATOR - InvoiceID: {invoice_id}, InvoiceNumber: {invoice_number}, PageSize: {self.page_size}")
        debug_print(f"{'='*80}\n")
        current_app.logger.info(f"[PDF_EXPORT] Starting PDF generation - InvoiceID: {invoice_id}, InvoiceNumber: {invoice_number}, PageSize: '{self.page_size}'")

        # Get template for the specified page size
        from app.models import InvoicePDFTemplate

        # CRITICAL: Expire all cached objects to ensure we get the latest saved template
        db.session.expire_all()
        
        current_app.logger.info(f"[PDF_EXPORT] Querying database for template - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
        
        # CRITICAL: Do a completely fresh query using raw SQL to bypass any ORM caching
        # This ensures we get the absolute latest data from the database
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT id, page_size, template_json, updated_at FROM invoice_pdf_templates WHERE page_size = :page_size"),
            {"page_size": self.page_size}
        ).first()
        
        template_json_raw_from_db = None
        template = None
        
        if result:
            template_id, page_size_db, template_json_raw_from_db, updated_at = result
            current_app.logger.info(f"[PDF_EXPORT] Template found via raw query - PageSize: '{page_size_db}', TemplateID: {template_id}, UpdatedAt: {updated_at}, TemplateJSONLength: {len(template_json_raw_from_db) if template_json_raw_from_db else 0}, InvoiceID: {invoice_id}")
            # Now get the full template object for use (for other attributes if needed)
            template = InvoicePDFTemplate.query.get(template_id)
            # CRITICAL: Use template_json directly from raw query, not from ORM object (which might be cached)
            if template_json_raw_from_db:
                template.template_json = template_json_raw_from_db
            # Force refresh all other attributes
            db.session.refresh(template)
        else:
            current_app.logger.warning(f"[PDF_EXPORT] Template not found for PageSize: '{self.page_size}', creating default - InvoiceID: {invoice_id}")
            template = InvoicePDFTemplate.get_template(self.page_size)
            template_json_raw_from_db = template.template_json
        
        # Store template as instance variable for use in format_date
        self.template = template
        
        debug_print(f"[DEBUG] Retrieved template: page_size={template.page_size}, id={template.id}")
        template_json_to_use = template_json_raw_from_db if template_json_raw_from_db else template.template_json
        template_json_length = len(template_json_to_use) if template_json_to_use else 0
        template_json_preview = (template_json_to_use[:100] + "...") if template_json_to_use and len(template_json_to_use) > 100 else (template_json_to_use or "(empty)")
        # Also get a hash/fingerprint of the JSON to verify it's actually the saved one
        import hashlib
        template_json_hash = hashlib.md5(template_json_to_use.encode('utf-8')).hexdigest()[:16] if template_json_to_use else "none"
        current_app.logger.info(f"[PDF_EXPORT] Template retrieved - PageSize: '{template.page_size}', TemplateID: {template.id}, HasJSON: {bool(template_json_to_use)}, JSONLength: {template_json_length}, JSONHash: {template_json_hash}, JSONPreview: {template_json_preview}, UpdatedAt: {template.updated_at}, InvoiceID: {invoice_id}")

        # Get or generate ReportLab template JSON
        template_json_dict = None
        # CRITICAL: Use template_json_raw_from_db (from raw query) - this is the absolute latest from database
        # template_json_to_use is already set above
        # Check if template_json exists and is not empty/whitespace
        if template_json_to_use and template_json_to_use.strip():
            try:
                current_app.logger.info(f"[PDF_EXPORT] Parsing template JSON - PageSize: '{self.page_size}', JSON length: {len(template_json_to_use)}, InvoiceID: {invoice_id}")
                template_json_dict = json.loads(template_json_to_use)
                element_count = len(template_json_dict.get("elements", []))
                json_page_size = template_json_dict.get("page", {}).get("size", "unknown")
                # Get first few element types for debugging
                element_types = [elem.get("type", "unknown") for elem in template_json_dict.get("elements", [])[:5]]
                debug_print(f"[DEBUG] Found ReportLab template JSON (length: {len(template_json_to_use)})")
                current_app.logger.info(f"[PDF_EXPORT] Template JSON parsed successfully - PageSize: '{self.page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}, FirstElementTypes: {element_types}, InvoiceID: {invoice_id}")
            except Exception as e:
                debug_print(f"[WARNING] Failed to parse template_json: {e}")
                template_json_preview_use = (template_json_to_use[:100] + "...") if template_json_to_use and len(template_json_to_use) > 100 else (template_json_to_use or "(empty)")
                current_app.logger.error(f"[PDF_EXPORT] Failed to parse template JSON - PageSize: '{self.page_size}', Error: {str(e)}, JSONPreview: {template_json_preview_use}, InvoiceID: {invoice_id}", exc_info=True)
                template_json_dict = None
        else:
            current_app.logger.warning(f"[PDF_EXPORT] Template JSON is empty or whitespace - PageSize: '{self.page_size}', TemplateID: {template.id}, TemplateJSONIsNone: {template_json_to_use is None}, TemplateJSONIsEmpty: {not template_json_to_use or not template_json_to_use.strip()}, RawQueryResult: {template_json_raw_from_db is not None if 'template_json_raw_from_db' in locals() else 'N/A'}, InvoiceID: {invoice_id}")

        # If no JSON template exists, ensure it's populated with default (will save to database if empty)
        if not template_json_dict:
            debug_print(f"[DEBUG] No template JSON found, ensuring default template JSON for page size {self.page_size}")
            current_app.logger.info(
                f"[PDF_EXPORT] Template JSON is empty, ensuring default template - PageSize: '{self.page_size}', "
                f"TemplateID: {template.id}, InvoiceID: {invoice_id}"
            )
            
            # Call ensure_template_json() which will populate with default if empty/invalid
            # This saves the default to the database, so it's available for future exports
            # It only saves if template_json is truly empty/invalid, not if it's a valid custom template
            template.ensure_template_json()
            
            # Re-query template_json from database to get the updated value (avoid ORM caching)
            db.session.expire(template)
            result_updated = db.session.execute(
                text("SELECT template_json FROM invoice_pdf_templates WHERE id = :template_id"),
                {"template_id": template.id}
            ).first()
            
            if result_updated and result_updated[0]:
                template_json_to_use = result_updated[0]
                try:
                    template_json_dict = json.loads(template_json_to_use)
                    element_count = len(template_json_dict.get("elements", []))
                    debug_print(f"[DEBUG] Retrieved default template JSON with {element_count} elements (saved to DB)")
                    current_app.logger.info(
                        f"[PDF_EXPORT] Default template JSON retrieved from database - PageSize: '{self.page_size}', "
                        f"Elements: {element_count}, InvoiceID: {invoice_id}"
                    )
                except Exception as e:
                    current_app.logger.error(f"[PDF_EXPORT] Failed to parse template JSON after ensure_template_json() - PageSize: '{self.page_size}', Error: {str(e)}, InvoiceID: {invoice_id}", exc_info=True)
                    # Fall back to generating default in memory if parsing fails
                    from app.utils.pdf_template_schema import get_default_template
                    template_json_dict = get_default_template(self.page_size)
            else:
                # Fallback: generate default in memory if ensure_template_json() didn't work
                current_app.logger.warning(f"[PDF_EXPORT] ensure_template_json() didn't populate template_json, using in-memory default - PageSize: '{self.page_size}', TemplateID: {template.id}, InvoiceID: {invoice_id}")
                from app.utils.pdf_template_schema import get_default_template
                template_json_dict = get_default_template(self.page_size)
        else:
            # CRITICAL: Ensure template page size and dimensions match the requested page size
            # This fixes layout issues when templates were customized but dimensions don't match
            template_page_config = template_json_dict.get("page", {})
            template_page_size = template_page_config.get("size", self.page_size)
            
            if template_page_size != self.page_size:
                current_app.logger.warning(
                    f"[PDF_EXPORT] Template page size mismatch - TemplatePageSize: '{template_page_size}', "
                    f"RequestedPageSize: '{self.page_size}', InvoiceID: {invoice_id}. "
                    f"Updating template to match requested page size."
                )
                # Update template page size to match requested size
                template_page_config["size"] = self.page_size
                template_json_dict["page"] = template_page_config
            
            # Ensure page dimensions are correct for the requested page size
            from app.utils.pdf_template_schema import PAGE_SIZE_DIMENSIONS_MM
            if self.page_size in PAGE_SIZE_DIMENSIONS_MM:
                expected_dims = PAGE_SIZE_DIMENSIONS_MM[self.page_size]
                current_width = template_page_config.get("width")
                current_height = template_page_config.get("height")
                
                if current_width != expected_dims["width"] or current_height != expected_dims["height"]:
                    current_app.logger.info(
                        f"[PDF_EXPORT] Correcting template page dimensions - PageSize: '{self.page_size}', "
                        f"Old: {current_width}x{current_height}mm, New: {expected_dims['width']}x{expected_dims['height']}mm, InvoiceID: {invoice_id}"
                    )
                    template_page_config["width"] = expected_dims["width"]
                    template_page_config["height"] = expected_dims["height"]
                    template_json_dict["page"] = template_page_config
            
            # Update element positions if they exceed page bounds (due to page size change)
            # This helps fix layout issues when switching between page sizes
            if template_page_size != self.page_size:
                page_dims = PAGE_SIZE_DIMENSIONS_MM.get(self.page_size, {"width": 210, "height": 297})
                page_width_pt = (page_dims["width"] / 25.4) * 72  # Convert mm to points
                page_height_pt = (page_dims["height"] / 25.4) * 72
                
                elements = template_json_dict.get("elements", [])
                adjusted_count = 0
                for element in elements:
                    x = element.get("x", 0)
                    y = element.get("y", 0)
                    width = element.get("width", 0)
                    height = element.get("height", 0)
                    
                    # Check if element is outside page bounds
                    if x + width > page_width_pt or y + height > page_height_pt:
                        # Scale element to fit within page (proportional scaling)
                        if x + width > page_width_pt:
                            scale_x = (page_width_pt - 20) / (x + width)  # Leave 20pt margin
                            element["x"] = x * scale_x
                            element["width"] = width * scale_x
                            adjusted_count += 1
                        if y + height > page_height_pt:
                            scale_y = (page_height_pt - 20) / (y + height)  # Leave 20pt margin
                            element["y"] = y * scale_y
                            element["height"] = height * scale_y
                            adjusted_count += 1
                
                if adjusted_count > 0:
                    current_app.logger.info(
                        f"[PDF_EXPORT] Adjusted {adjusted_count} elements to fit page size '{self.page_size}' - InvoiceID: {invoice_id}"
                    )

        # Always use ReportLab template renderer with JSON
        debug_print(f"[DEBUG] Using ReportLab template renderer for page size {self.page_size}")
        from app.utils.pdf_generator_reportlab import ReportLabTemplateRenderer
        from app.utils.pdf_template_schema import validate_template_json
        
        # Validate template JSON
        current_app.logger.info(f"[PDF_EXPORT] Validating template JSON - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
        is_valid, error = validate_template_json(template_json_dict)
        if not is_valid:
            debug_print(f"[ERROR] Template JSON validation failed: {error}")
            current_app.logger.error(f"[PDF_EXPORT] Template JSON validation failed - PageSize: '{self.page_size}', Error: {error}, InvoiceID: {invoice_id}")
            # Even if validation fails, try to render with default fallback
            return self._generate_pdf_with_default()
        else:
            current_app.logger.info(f"[PDF_EXPORT] Template JSON validation passed - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
        
        # Prepare data context for template rendering
        current_app.logger.info(f"[PDF_EXPORT] Preparing template context - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
        data_context = self._prepare_template_context()
        
        # Render PDF using ReportLab
        current_app.logger.info(f"[PDF_EXPORT] Creating ReportLab renderer - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
        renderer = ReportLabTemplateRenderer(template_json_dict, data_context, self.page_size)
        try:
            current_app.logger.info(f"[PDF_EXPORT] Starting ReportLab render - PageSize: '{self.page_size}', InvoiceID: {invoice_id}")
            pdf_bytes = renderer.render_to_bytes()
            pdf_size_bytes = len(pdf_bytes)
            debug_print(f"[DEBUG] ReportLab PDF generated successfully - size: {pdf_size_bytes} bytes")
            current_app.logger.info(f"[PDF_EXPORT] ReportLab PDF generated successfully - PageSize: '{self.page_size}', PDFSize: {pdf_size_bytes} bytes, InvoiceID: {invoice_id}")
            return pdf_bytes
        except Exception as e:
            debug_print(f"[ERROR] ReportLab rendering failed: {e}")
            import traceback
            debug_print(traceback.format_exc())
            current_app.logger.error(f"[PDF_EXPORT] ReportLab rendering failed - PageSize: '{self.page_size}', Error: {str(e)}, InvoiceID: {invoice_id}", exc_info=True)
            # Fall back to default generation
            return self._generate_pdf_with_default()
    
    def _prepare_template_context(self):
        """Prepare data context for template rendering"""
        # Convert SQLAlchemy objects to simple structures for template
        from types import SimpleNamespace
        
        # Create invoice wrapper
        invoice_wrapper = SimpleNamespace()
        for attr in ['id', 'invoice_number', 'issue_date', 'due_date', 'status', 
                     'client_name', 'client_email', 'client_address', 'client_id',
                     'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 
                     'notes', 'terms']:
            try:
                setattr(invoice_wrapper, attr, getattr(self.invoice, attr))
            except AttributeError:
                pass
        
        # Convert relationships to lists
        try:
            if hasattr(self.invoice.items, "all"):
                invoice_wrapper.items = self.invoice.items.all()
            else:
                invoice_wrapper.items = list(self.invoice.items) if self.invoice.items else []
        except Exception:
            invoice_wrapper.items = []
        
        try:
            if hasattr(self.invoice.extra_goods, "all"):
                invoice_wrapper.extra_goods = self.invoice.extra_goods.all()
            else:
                invoice_wrapper.extra_goods = list(self.invoice.extra_goods) if self.invoice.extra_goods else []
        except Exception:
            invoice_wrapper.extra_goods = []
        
        try:
            if hasattr(self.invoice, "expenses") and hasattr(self.invoice.expenses, "all"):
                invoice_wrapper.expenses = self.invoice.expenses.all()
            else:
                invoice_wrapper.expenses = list(self.invoice.expenses) if hasattr(self.invoice, "expenses") and self.invoice.expenses else []
        except Exception:
            invoice_wrapper.expenses = []

        # Build combined all_line_items for PDF table (items + extra_goods + expenses)
        # Each entry has: description, quantity, unit_price, total_amount
        all_line_items = []
        for item in invoice_wrapper.items:
            all_line_items.append(
                SimpleNamespace(
                    description=getattr(item, "description", str(item)) or "",
                    quantity=getattr(item, "quantity", 1),
                    unit_price=getattr(item, "unit_price", 0),
                    total_amount=getattr(item, "total_amount", 0),
                )
            )
        for good in invoice_wrapper.extra_goods:
            desc_parts = [getattr(good, "name", str(good)) or ""]
            if getattr(good, "description", None):
                desc_parts.append(str(good.description))
            if getattr(good, "sku", None):
                desc_parts.append(f"SKU: {good.sku}")
            if getattr(good, "category", None):
                desc_parts.append(f"Category: {good.category.title()}")
            all_line_items.append(
                SimpleNamespace(
                    description="\n".join(desc_parts),
                    quantity=getattr(good, "quantity", 1),
                    unit_price=getattr(good, "unit_price", 0),
                    total_amount=getattr(good, "total_amount", 0),
                )
            )
        for expense in invoice_wrapper.expenses:
            desc_parts = [getattr(expense, "title", str(expense)) or ""]
            if getattr(expense, "description", None):
                desc_parts.append(str(expense.description))
            amt = getattr(expense, "total_amount", None) or getattr(expense, "amount", 0)
            all_line_items.append(
                SimpleNamespace(
                    description="\n".join(desc_parts),
                    quantity=1,
                    unit_price=amt,
                    total_amount=amt,
                )
            )
        invoice_wrapper.all_line_items = all_line_items

        # Project
        invoice_wrapper.project = self.invoice.project

        # Client (for PEPPOL compliance when setting is on)
        invoice_wrapper.client = getattr(self.invoice, "client", None)

        # Settings
        settings_wrapper = SimpleNamespace()
        for attr in ['company_name', 'company_address', 'company_email', 'company_phone', 
                     'company_website', 'company_tax_id', 'currency', 'invoice_terms',
                     'company_bank_info']:
            try:
                setattr(settings_wrapper, attr, getattr(self.settings, attr))
            except AttributeError:
                pass
        
        # Add helper methods
        def has_logo():
            return self.settings.has_logo()
        def get_logo_path():
            return self.settings.get_logo_path()
        settings_wrapper.has_logo = has_logo
        settings_wrapper.get_logo_path = get_logo_path
        
        # Helper functions for templates
        from app.utils.template_filters import get_logo_base64, get_image_base64
        from babel.dates import format_date as babel_format_date
        
        def format_date(value, format="medium"):
            try:
                # Use DD.MM.YYYY format for invoices and quotes
                return value.strftime("%d.%m.%Y") if value else ""
            except Exception:
                return str(value) if value else ""
        
        def format_money(value):
            try:
                return f"{float(value):,.2f} {self.settings.currency}"
            except Exception:
                return f"{value} {self.settings.currency}"

        # PEPPOL compliance: include when invoices_peppol_compliant is on
        result = {
            'invoice': invoice_wrapper,
            'settings': settings_wrapper,
            'get_logo_base64': get_logo_base64,
            'format_date': format_date,
            'format_money': format_money,
        }
        if getattr(self.settings, "invoices_peppol_compliant", False):
            client = getattr(self.invoice, "client", None)
            result['peppol_compliance'] = {
                'enabled': True,
                'seller_endpoint_id': (getattr(self.settings, "peppol_sender_endpoint_id", None) or "").strip(),
                'seller_scheme_id': (getattr(self.settings, "peppol_sender_scheme_id", None) or "").strip(),
                'seller_vat': (getattr(self.settings, "company_tax_id", None) or "").strip(),
                'buyer_endpoint_id': (client.get_custom_field("peppol_endpoint_id", "") or "").strip() if client else "",
                'buyer_scheme_id': (client.get_custom_field("peppol_scheme_id", "") or "").strip() if client else "",
                'buyer_vat': (client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "") or "").strip() if client else "",
            }
        return result
    
    def _generate_pdf_with_default(self):
        """Generate PDF using default fallback ReportLab generator"""
        from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback
        fallback = InvoicePDFGeneratorFallback(self.invoice, settings=self.settings)
        return fallback.generate_pdf()


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

        def update_page_size_in_html(html_text):
            """Update @page size property in HTML's inline <style> tags"""
            import re

            # Find and update @page rules in <style> tags
            def update_style_tag(match):
                style_content = match.group(2)  # Content inside <style> tag
                updated_content = update_page_size_in_css(style_content, self.page_size)
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

            css_to_use = update_page_size_in_css(css_template, self.page_size)
            
            # Update wrapper dimensions to match page size (fixes hardcoded dimension issues)
            css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
            debug_print(f"[DEBUG] Updated wrapper dimensions in template CSS for page size: {self.page_size}")

            # Validate @page size after update
            is_valid, found_sizes = validate_page_size_in_css(css_to_use, self.page_size)
            if not is_valid:
                debug_print(f"[ERROR] @page size validation failed! Expected '{self.page_size}', found: {found_sizes}")
                current_app.logger.warning(
                    f"PDF template CSS @page size mismatch. Expected '{self.page_size}', found: {found_sizes}"
                )
            else:
                debug_print(f"[DEBUG] ✓ CSS template @page size correctly updated and validated: '{self.page_size}'")
        elif extracted_inline_css:
            # Only inline styles exist - extract and use them
            css_to_use = update_page_size_in_css(extracted_inline_css, self.page_size)
            css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
        else:
            # No CSS provided, use default
            try:
                from flask import render_template as _render_tpl

                css_to_use = _render_tpl("invoices/pdf_styles_default.css")
                css_to_use = update_page_size_in_css(css_to_use, self.page_size)
                css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
            except Exception:
                css_to_use = self._generate_css()

        # Ensure @page rule has correct size - this is critical for PDF generation
        css = css_to_use
        
        # Add comprehensive overflow prevention CSS
        overflow_css = get_overflow_prevention_css()
        css = css + "\n" + overflow_css
        
        # Import helper functions for template
        from app.utils.template_filters import get_logo_base64, get_image_base64
        from babel.dates import format_date as babel_format_date

        # Get date format from template, default to %d.%m.%Y
        date_format_str = getattr(self.template, 'date_format', '%d.%m.%Y') if hasattr(self, 'template') and self.template else '%d.%m.%Y'
        
        def format_date(value, format="medium"):
            """Format date for template"""
            # Use date format from template settings
            return value.strftime(date_format_str) if value else ""

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

        # Load decorative images
        try:
            from app.models import InvoiceImage
            decorative_images = InvoiceImage.get_invoice_images(self.invoice.id)
        except Exception:
            decorative_images = []
        invoice_data.decorative_images = decorative_images

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
                    get_image_base64=get_image_base64,
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
                    get_image_base64=get_image_base64,
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


def get_overflow_prevention_css():
    """
    Get comprehensive CSS rules to prevent content overflow beyond page boundaries.
    This should be applied to all PDF exports and previews.
    
    Returns:
        CSS string with overflow prevention rules
    """
    return """
    /* Comprehensive overflow prevention for PDF exports */
    html, body {
        margin: 0;
        padding: 0;
        overflow: hidden;
        box-sizing: border-box;
    }
    
    /* Ensure all wrapper containers respect page boundaries and clip overflow */
    .invoice-wrapper,
    .quote-wrapper,
    .wrapper,
    div[class*="wrapper"],
    div[class*="container"] {
        overflow: hidden !important;
        box-sizing: border-box !important;
        position: relative;
        /* Clip content that extends beyond wrapper boundaries - use strict clipping */
        clip-path: inset(0) !important;
        /* Additional clipping for absolutely positioned children */
        contain: layout style paint;
    }
    
    /* Clip absolutely positioned elements that might overflow page boundaries */
    [style*="position:absolute"],
    [style*="position: fixed"],
    .element, .text-element, .rectangle-element, .circle-element, .line-element {
        box-sizing: border-box;
        /* Ensure positioned elements are clipped by parent wrapper */
        /* Elements must not exceed wrapper boundaries */
        contain: layout style paint;
    }
    
    /* Ensure wrapper strictly clips all children - prevent any overflow */
    .invoice-wrapper,
    .quote-wrapper,
    .wrapper {
        /* Make wrapper a containing block for absolutely positioned children */
        position: relative !important;
        /* Strict clipping - ensure nothing extends beyond wrapper */
        overflow: hidden !important;
        clip-path: inset(0) !important;
    }
    
    /* Constrain absolutely positioned elements to wrapper boundaries */
    /* Elements positioned outside wrapper boundaries will be clipped */
    .invoice-wrapper [style*="position:absolute"],
    .invoice-wrapper [style*="position: fixed"],
    .quote-wrapper [style*="position:absolute"],
    .quote-wrapper [style*="position: fixed"],
    .wrapper [style*="position:absolute"],
    .wrapper [style*="position: fixed"] {
        /* Elements must stay within wrapper - will be clipped by parent overflow */
        box-sizing: border-box;
        contain: layout style paint;
        /* Ensure elements don't extend beyond parent boundaries */
        max-width: 100%;
        max-height: 100%;
    }
    
    /* Specifically constrain elements that might overflow */
    .invoice-wrapper .element,
    .invoice-wrapper .text-element,
    .invoice-wrapper .rectangle-element,
    .invoice-wrapper .circle-element,
    .invoice-wrapper .line-element,
    .quote-wrapper .element,
    .quote-wrapper .text-element,
    .quote-wrapper .rectangle-element,
    .quote-wrapper .circle-element,
    .quote-wrapper .line-element {
        box-sizing: border-box;
        contain: layout style paint;
        /* Prevent overflow beyond wrapper */
        overflow: hidden;
    }
    
    /* Prevent tables from overflowing */
    table {
        max-width: 100%;
        table-layout: auto;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    /* Prevent images from overflowing */
    img {
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }
    
    /* Prevent text from overflowing containers */
    * {
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    """


class QuotePDFGenerator:
    """Generate PDF quotes with company branding"""

    def __init__(self, quote, settings=None, page_size="A4"):
        self.quote = quote
        self.settings = settings or Settings.get_settings()
        self.page_size = page_size or "A4"

    def generate_pdf(self):
        """Generate PDF content and return as bytes using ReportLab"""
        import sys
        import json
        from flask import current_app

        def debug_print(msg):
            """Print debug message to stdout with immediate flush for Docker visibility"""
            print(msg, file=sys.stdout, flush=True)
            print(msg, file=sys.stderr, flush=True)
            # Also log using Flask logger if available
            try:
                current_app.logger.info(msg)
            except Exception:
                pass

        quote_id = getattr(self.quote, 'id', 'N/A')
        quote_number = getattr(self.quote, 'quote_number', 'N/A')
        
        debug_print(f"\n[PDF_EXPORT] QUOTE PDF GENERATOR - QuoteID: {quote_id}, QuoteNumber: {quote_number}, PageSize: {self.page_size}")
        debug_print(f"{'='*80}\n")
        current_app.logger.info(f"[PDF_EXPORT] Starting quote PDF generation - QuoteID: {quote_id}, QuoteNumber: {quote_number}, PageSize: '{self.page_size}'")

        # Get template for the specified page size
        # CRITICAL: Expire all cached objects to ensure we get the latest saved template
        db.session.expire_all()
        
        current_app.logger.info(f"[PDF_EXPORT] Querying database for quote template - PageSize: '{self.page_size}', QuoteID: {quote_id}")
        
        # CRITICAL: Do a completely fresh query using raw SQL to bypass any ORM caching
        # This ensures we get the absolute latest data from the database
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT id, page_size, template_json, updated_at FROM quote_pdf_templates WHERE page_size = :page_size"),
            {"page_size": self.page_size}
        ).first()
        
        template_json_raw_from_db = None
        template = None
        
        if result:
            template_id, page_size_db, template_json_raw_from_db, updated_at = result
            current_app.logger.info(f"[PDF_EXPORT] Quote template found via raw query - PageSize: '{page_size_db}', TemplateID: {template_id}, UpdatedAt: {updated_at}, TemplateJSONLength: {len(template_json_raw_from_db) if template_json_raw_from_db else 0}, QuoteID: {quote_id}")
            # Now get the full template object for use (for other attributes if needed)
            template = QuotePDFTemplate.query.get(template_id)
            # CRITICAL: Use template_json directly from raw query, not from ORM object (which might be cached)
            if template_json_raw_from_db:
                template.template_json = template_json_raw_from_db
            # Force refresh all other attributes
            db.session.refresh(template)
        else:
            current_app.logger.warning(f"[PDF_EXPORT] Quote template not found for PageSize: '{self.page_size}', creating default - QuoteID: {quote_id}")
            template = QuotePDFTemplate.get_template(self.page_size)
            template_json_raw_from_db = template.template_json
        
        # Store template as instance variable for use in format_date
        self.template = template

        debug_print(f"[DEBUG] Retrieved quote template: page_size={template.page_size}, id={template.id}")
        template_json_to_use = template_json_raw_from_db if template_json_raw_from_db else template.template_json
        template_json_length = len(template_json_to_use) if template_json_to_use else 0
        template_json_preview = (template_json_to_use[:100] + "...") if template_json_to_use and len(template_json_to_use) > 100 else (template_json_to_use or "(empty)")
        # Also get a hash/fingerprint of the JSON to verify it's actually the saved one
        import hashlib
        template_json_hash = hashlib.md5(template_json_to_use.encode('utf-8')).hexdigest()[:16] if template_json_to_use else "none"
        current_app.logger.info(f"[PDF_EXPORT] Quote template retrieved - PageSize: '{template.page_size}', TemplateID: {template.id}, HasJSON: {bool(template_json_to_use)}, JSONLength: {template_json_length}, JSONHash: {template_json_hash}, JSONPreview: {template_json_preview}, UpdatedAt: {template.updated_at}, QuoteID: {quote_id}")

        # Get or generate ReportLab template JSON
        template_json_dict = None
        # CRITICAL: Use template_json_raw_from_db (from raw query) - this is the absolute latest from database
        # template_json_to_use is already set above
        # Check if template_json exists and is not empty/whitespace
        if template_json_to_use and template_json_to_use.strip():
            try:
                current_app.logger.info(f"[PDF_EXPORT] Parsing quote template JSON - PageSize: '{self.page_size}', JSON length: {len(template_json_to_use)}, QuoteID: {quote_id}")
                template_json_dict = json.loads(template_json_to_use)
                element_count = len(template_json_dict.get("elements", []))
                json_page_size = template_json_dict.get("page", {}).get("size", "unknown")
                # Get first few element types for debugging
                element_types = [elem.get("type", "unknown") for elem in template_json_dict.get("elements", [])[:5]]
                debug_print(f"[DEBUG] Found ReportLab template JSON (length: {len(template_json_to_use)})")
                current_app.logger.info(f"[PDF_EXPORT] Quote template JSON parsed successfully - PageSize: '{self.page_size}', JSON PageSize: '{json_page_size}', Elements: {element_count}, FirstElementTypes: {element_types}, QuoteID: {quote_id}")
            except Exception as e:
                debug_print(f"[WARNING] Failed to parse template_json: {e}")
                template_json_preview_use = (template_json_to_use[:100] + "...") if template_json_to_use and len(template_json_to_use) > 100 else (template_json_to_use or "(empty)")
                current_app.logger.error(f"[PDF_EXPORT] Failed to parse quote template JSON - PageSize: '{self.page_size}', Error: {str(e)}, JSONPreview: {template_json_preview_use}, QuoteID: {quote_id}", exc_info=True)
                template_json_dict = None
        else:
            # Log why template_json is not being used
            reason = "template_json is None" if template_json_to_use is None else "template_json is empty or whitespace"
            current_app.logger.warning(f"[PDF_EXPORT] Quote template JSON is empty/whitespace - PageSize: '{self.page_size}', TemplateID: {template.id}, Reason: {reason}, TemplateJSONLength: {len(template_json_to_use) if template_json_to_use else 0}, QuoteID: {quote_id}")

        # If no JSON template exists, ensure it's populated with default (will save to database if empty)
        if not template_json_dict:
            debug_print(f"[DEBUG] No quote template JSON found, ensuring default template JSON for page size {self.page_size}")
            current_app.logger.info(
                f"[PDF_EXPORT] Quote template JSON is empty, ensuring default template - PageSize: '{self.page_size}', "
                f"TemplateID: {template.id}, QuoteID: {quote_id}"
            )
            
            # Call ensure_template_json() which will populate with default if empty/invalid
            # This saves the default to the database, so it's available for future exports
            # It only saves if template_json is truly empty/invalid, not if it's a valid custom template
            template.ensure_template_json()
            
            # Re-query template_json from database to get the updated value (avoid ORM caching)
            db.session.expire(template)
            result_updated = db.session.execute(
                text("SELECT template_json FROM quote_pdf_templates WHERE id = :template_id"),
                {"template_id": template.id}
            ).first()
            
            if result_updated and result_updated[0]:
                template_json_to_use = result_updated[0]
                try:
                    template_json_dict = json.loads(template_json_to_use)
                    element_count = len(template_json_dict.get("elements", []))
                    debug_print(f"[DEBUG] Retrieved default quote template JSON with {element_count} elements (saved to DB)")
                    current_app.logger.info(
                        f"[PDF_EXPORT] Default quote template JSON retrieved from database - PageSize: '{self.page_size}', "
                        f"Elements: {element_count}, QuoteID: {quote_id}"
                    )
                except Exception as e:
                    current_app.logger.error(f"[PDF_EXPORT] Failed to parse quote template JSON after ensure_template_json() - PageSize: '{self.page_size}', Error: {str(e)}, QuoteID: {quote_id}", exc_info=True)
                    # Fall back to generating default in memory if parsing fails
                    from app.utils.pdf_template_schema import get_default_template
                    template_json_dict = get_default_template(self.page_size)
            else:
                # Fallback: generate default in memory if ensure_template_json() didn't work
                current_app.logger.warning(f"[PDF_EXPORT] ensure_template_json() didn't populate quote template_json, using in-memory default - PageSize: '{self.page_size}', TemplateID: {template.id}, QuoteID: {quote_id}")
                from app.utils.pdf_template_schema import get_default_template
                template_json_dict = get_default_template(self.page_size)

        # Always use ReportLab template renderer with JSON
        debug_print(f"[DEBUG] Using ReportLab template renderer for page size {self.page_size}")
        from app.utils.pdf_generator_reportlab import ReportLabTemplateRenderer
        from app.utils.pdf_template_schema import validate_template_json
        
        # Validate template JSON
        current_app.logger.info(f"[PDF_EXPORT] Validating quote template JSON - PageSize: '{self.page_size}', QuoteID: {quote_id}")
        is_valid, error = validate_template_json(template_json_dict)
        if not is_valid:
            debug_print(f"[ERROR] Template JSON validation failed: {error}")
            current_app.logger.error(f"[PDF_EXPORT] Quote template JSON validation failed - PageSize: '{self.page_size}', Error: {error}, QuoteID: {quote_id}")
            # Even if validation fails, try to render with default fallback
            return self._generate_pdf_with_default()
        else:
            current_app.logger.info(f"[PDF_EXPORT] Quote template JSON validation passed - PageSize: '{self.page_size}', QuoteID: {quote_id}")
        
        # Prepare data context for template rendering
        current_app.logger.info(f"[PDF_EXPORT] Preparing quote template context - PageSize: '{self.page_size}', QuoteID: {quote_id}")
        data_context = self._prepare_quote_template_context()
        
        # Render PDF using ReportLab
        current_app.logger.info(f"[PDF_EXPORT] Creating ReportLab renderer for quote - PageSize: '{self.page_size}', QuoteID: {quote_id}")
        renderer = ReportLabTemplateRenderer(template_json_dict, data_context, self.page_size)
        try:
            current_app.logger.info(f"[PDF_EXPORT] Starting ReportLab render for quote - PageSize: '{self.page_size}', QuoteID: {quote_id}")
            pdf_bytes = renderer.render_to_bytes()
            pdf_size_bytes = len(pdf_bytes)
            debug_print(f"[DEBUG] ReportLab PDF generated successfully - size: {pdf_size_bytes} bytes")
            current_app.logger.info(f"[PDF_EXPORT] ReportLab quote PDF generated successfully - PageSize: '{self.page_size}', PDFSize: {pdf_size_bytes} bytes, QuoteID: {quote_id}")
            return pdf_bytes
        except Exception as e:
            debug_print(f"[ERROR] ReportLab rendering failed: {e}")
            import traceback
            debug_print(traceback.format_exc())
            current_app.logger.error(f"[PDF_EXPORT] ReportLab quote rendering failed - PageSize: '{self.page_size}', Error: {str(e)}, QuoteID: {quote_id}", exc_info=True)
            # Fall back to default generation
            return self._generate_pdf_with_default()
    
    def _prepare_quote_template_context(self):
        """Prepare data context for quote template rendering"""
        # Convert SQLAlchemy objects to simple structures for template
        from types import SimpleNamespace
        
        # Create quote wrapper
        quote_wrapper = SimpleNamespace()
        for attr in ['id', 'quote_number', 'title', 'description', 'status', 
                     'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 
                     'discount_type', 'discount_amount', 'discount_reason',
                     'coupon_code', 'currency_code', 'notes', 'terms', 
                     'valid_until', 'created_at', 'updated_at']:
            try:
                setattr(quote_wrapper, attr, getattr(self.quote, attr))
            except AttributeError:
                pass
        
        # Convert relationships to lists
        try:
            if hasattr(self.quote.items, "all"):
                quote_wrapper.items = self.quote.items.all()
            else:
                quote_wrapper.items = list(self.quote.items) if self.quote.items else []
        except Exception:
            quote_wrapper.items = []
        
        # Client
        if hasattr(self.quote, 'client') and self.quote.client:
            quote_wrapper.client = self.quote.client
        else:
            quote_wrapper.client = None
        
        # Project
        quote_wrapper.project = self.quote.project if hasattr(self.quote, 'project') else None
        
        # Settings
        settings_wrapper = SimpleNamespace()
        for attr in ['company_name', 'company_address', 'company_email', 'company_phone', 
                     'company_website', 'company_tax_id', 'currency']:
            try:
                setattr(settings_wrapper, attr, getattr(self.settings, attr))
            except AttributeError:
                pass
        
        def has_logo():
            return self.settings.has_logo()
        def get_logo_path():
            return self.settings.get_logo_path()
        settings_wrapper.has_logo = has_logo
        settings_wrapper.get_logo_path = get_logo_path
        
        # Helper functions for templates
        from app.utils.template_filters import get_logo_base64, get_image_base64
        from babel.dates import format_date as babel_format_date
        
        # Get date format from template, default to %d.%m.%Y
        date_format_str = getattr(self.template, 'date_format', '%d.%m.%Y') if hasattr(self, 'template') and self.template else '%d.%m.%Y'
        
        def format_date(value, format="medium"):
            try:
                # Use date format from template settings
                return value.strftime(date_format_str) if value else ""
            except Exception:
                return str(value) if value else ""
        
        def format_money(value):
            try:
                currency = getattr(quote_wrapper, 'currency_code', None) or self.settings.currency
                return f"{float(value):,.2f} {currency}"
            except Exception:
                currency = getattr(quote_wrapper, 'currency_code', None) or self.settings.currency
                return f"{value} {currency}"
        
        return {
            'quote': quote_wrapper,
            'invoice': quote_wrapper,  # Some templates use 'invoice' instead of 'quote'
            'settings': settings_wrapper,
            'get_logo_base64': get_logo_base64,
            'format_date': format_date,
            'format_money': format_money,
        }
    
    def _generate_pdf_with_default(self):
        """Generate PDF using default fallback ReportLab generator"""
        from app.utils.pdf_generator_fallback import QuotePDFGeneratorFallback
        fallback = QuotePDFGeneratorFallback(self.quote, settings=self.settings)
        return fallback.generate_pdf()

    def _render_from_custom_template(self, template=None):
        """Render HTML and CSS from custom templates stored in database, with fallback to default template."""
        import sys

        def debug_print(msg):
            """Print debug message to stdout with immediate flush for Docker visibility"""
            print(msg, file=sys.stdout, flush=True)
            print(msg, file=sys.stderr, flush=True)

        if template:
            # Ensure template matches the selected page size
            if hasattr(template, "page_size") and template.page_size != self.page_size:
                correct_template = QuotePDFTemplate.query.filter_by(page_size=self.page_size).first()
                if correct_template:
                    template = correct_template
                else:
                    raise ValueError(f"Template for page size {self.page_size} not found")

            html_template = template.template_html or ""
            css_template = template.template_css or ""
        else:
            raise ValueError(f"No template provided for page size {self.page_size}. This is a bug.")
        
        html = ""

        def remove_page_rule_from_html(html_text):
            """Remove @page rules from HTML inline styles to avoid conflicts with separate CSS"""
            import re

            def remove_from_style_tag(match):
                style_content = match.group(2)
                brace_count = 0
                page_pattern = r"@page\s*\{"
                page_match = re.search(page_pattern, style_content, re.IGNORECASE)

                if page_match:
                    start = page_match.start()
                    end = len(style_content)
                    for i in range(page_match.end() - 1, len(style_content)):
                        if style_content[i] == "{":
                            brace_count += 1
                        elif style_content[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    style_content = style_content[:start] + style_content[end:]
                    style_content = re.sub(r"\n\s*\n", "\n", style_content)

                return f"{match.group(1)}{style_content}{match.group(3)}"

            style_pattern = r"(<style[^>]*>)(.*?)(</style>)"
            if re.search(style_pattern, html_text, re.IGNORECASE | re.DOTALL):
                html_text = re.sub(style_pattern, remove_from_style_tag, html_text, flags=re.IGNORECASE | re.DOTALL)

            return html_text

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
            debug_print(f"[DEBUG] Using separate CSS template (length: {len(css_template)})")

            before_match = re.search(r"@page\s*\{[^}]*?size\s*:\s*([^;}\n]+)", css_template, re.IGNORECASE | re.DOTALL)
            if before_match:
                before_size = before_match.group(1).strip()
                debug_print(f"[DEBUG] CSS template @page size BEFORE update: '{before_size}'")

            css_to_use = update_page_size_in_css(css_template, self.page_size)
            
            # Update wrapper dimensions to match page size (fixes hardcoded dimension issues)
            css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
            debug_print(f"[DEBUG] Updated wrapper dimensions in template CSS for page size: {self.page_size}")

            # Validate @page size after update
            is_valid, found_sizes = validate_page_size_in_css(css_to_use, self.page_size)
            if not is_valid:
                debug_print(f"[ERROR] @page size validation failed! Expected '{self.page_size}', found: {found_sizes}")
                current_app.logger.warning(
                    f"Quote PDF template CSS @page size mismatch. Expected '{self.page_size}', found: {found_sizes}"
                )
            else:
                debug_print(f"[DEBUG] ✓ CSS template @page size correctly updated and validated: '{self.page_size}'")
        elif extracted_inline_css:
            css_to_use = update_page_size_in_css(extracted_inline_css, self.page_size)
            css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
        else:
            try:
                from flask import render_template as _render_tpl
                css_to_use = _render_tpl("quotes/pdf_styles_default.css")
                css_to_use = update_page_size_in_css(css_to_use, self.page_size)
                css_to_use = update_wrapper_dimensions_in_css(css_to_use, self.page_size)
            except Exception:
                css_to_use = self._generate_css()

        # Ensure @page rule has correct size
        css = css_to_use
        
        # Add comprehensive overflow prevention CSS
        overflow_css = get_overflow_prevention_css()
        css = css + "\n" + overflow_css
        
        # Import helper functions for template
        from app.utils.template_filters import get_logo_base64, get_image_base64
        from babel.dates import format_date as babel_format_date

        # Get date format from template, default to %d.%m.%Y
        date_format_str = getattr(self.template, 'date_format', '%d.%m.%Y') if hasattr(self, 'template') and self.template else '%d.%m.%Y'
        
        def format_date(value, format="medium"):
            """Format date for template"""
            # Use date format from template settings
            return value.strftime(date_format_str) if value else ""

        def format_money(value):
            """Format money for template"""
            try:
                return f"{float(value):,.2f}"
            except Exception:
                return str(value)

        # Convert lazy='dynamic' relationships to lists for template rendering
        try:
            if hasattr(self.quote.items, "all"):
                quote_items = self.quote.items.all()
            else:
                quote_items = list(self.quote.items) if self.quote.items else []
        except Exception:
            quote_items = []

        # Create a wrapper object that has the converted lists
        from types import SimpleNamespace

        quote_data = SimpleNamespace()
        # Copy all attributes from original quote
        for attr in dir(self.quote):
            if not attr.startswith("_"):
                try:
                    setattr(quote_data, attr, getattr(self.quote, attr))
                except Exception:
                    pass
        # Override with converted lists
        quote_data.items = quote_items

        # Load decorative images
        try:
            from app.models import QuoteImage
            decorative_images = QuoteImage.get_quote_images(self.quote.id)
        except Exception:
            decorative_images = []
        quote_data.decorative_images = decorative_images

        try:
            # Render using Flask's Jinja environment
            if html_template:
                from flask import render_template_string

                # When we have separate CSS, remove @page rules from HTML inline styles
                if html_inline_styles_extracted and css_template:
                    html_page_rules = re.findall(r"@page\s*\{[^}]*\}", html_template, re.IGNORECASE | re.DOTALL)
                    if html_page_rules:
                        debug_print(
                            f"[DEBUG] Found {len(html_page_rules)} @page rule(s) in HTML inline styles - removing them"
                        )
                    html_template_updated = remove_page_rule_from_html(html_template)
                    debug_print("[DEBUG] Removed @page rules from HTML inline styles")
                else:
                    html_template_updated = html_template
                
                html = render_template_string(
                    html_template_updated,
                    quote=quote_data,
                    settings=self.settings,
                    Path=Path,
                    get_logo_base64=get_logo_base64,
                    get_image_base64=get_image_base64,
                    format_date=format_date,
                    format_money=format_money,
                    now=datetime.now(),
                )
        except Exception as e:
            import traceback
            print(f"Error rendering custom quote PDF template: {e}")
            print(traceback.format_exc())
            html = ""

        if not html:
            try:
                html = render_template(
                    "quotes/pdf_default.html",
                    quote=quote_data,
                    settings=self.settings,
                    Path=Path,
                    get_logo_base64=get_logo_base64,
                    get_image_base64=get_image_base64,
                    format_date=format_date,
                    format_money=format_money,
                    now=datetime.now(),
                )
            except Exception as e:
                import traceback
                print(f"Error rendering default quote PDF template: {e}")
                print(traceback.format_exc())
                html = f"<html><body><h1>{_('Quote')} {self.quote.quote_number}</h1></body></html>"
        
        return html, css

    def _generate_html(self):
        """Generate HTML content for the quote"""
        return render_template("quotes/pdf_default.html", quote=self.quote, settings=self.settings)

    def _generate_css(self):
        """Generate CSS styles for the quote"""
        page_size = self.page_size or "A4"
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
        """.format(page_size=page_size)
