"""
PDF Generation utility for invoices
Uses WeasyPrint to generate professional PDF invoices
"""

import os
import html as html_lib
from datetime import datetime
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from app.models import Settings
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
    
    def __init__(self, invoice, settings=None):
        self.invoice = invoice
        self.settings = settings or Settings.get_settings()
    
    def generate_pdf(self):
        """Generate PDF content and return as bytes"""
        use_custom_html = bool((self.settings.invoice_pdf_template_html or '').strip())
        use_custom_css = bool((self.settings.invoice_pdf_template_css or '').strip())
        if use_custom_html or use_custom_css:
            html_content, css_content = self._render_from_custom_template()
        else:
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
        html_doc = HTML(string=html_content, base_url=base_url)
        css_doc = CSS(string=css_content, font_config=font_config)
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc], font_config=font_config)
        
        return pdf_bytes
    def _render_from_custom_template(self):
        """Render HTML and CSS from custom templates stored in settings, with fallback to default template."""
        html_template = (self.settings.invoice_pdf_template_html or '').strip()
        css_template = (self.settings.invoice_pdf_template_css or '').strip()
        html = ''
        if css_template:
            css = css_template
        else:
            try:
                from flask import render_template as _render_tpl
                css = _render_tpl('invoices/pdf_styles_default.css')
            except Exception:
                css = self._generate_css()
        try:
            # Render using Flask's Jinja environment to include app filters and _()
            if html_template:
                from flask import render_template_string
                html = render_template_string(html_template, invoice=self.invoice, settings=self.settings, Path=Path)
        except Exception:
            html = ''
        if not html:
            try:
                # Import helper functions for template
                from app.utils.template_filters import get_logo_base64
                from babel.dates import format_date as babel_format_date
                
                def format_date(value, format='medium'):
                    """Format date for template"""
                    if babel_format_date:
                        return babel_format_date(value, format=format)
                    return value.strftime('%Y-%m-%d') if value else ''
                
                def format_money(value):
                    """Format money for template"""
                    try:
                        return f"{float(value):,.2f}"
                    except Exception:
                        return str(value)
                
                html = render_template('invoices/pdf_default.html', 
                                     invoice=self.invoice, 
                                     settings=self.settings, 
                                     Path=Path,
                                     get_logo_base64=get_logo_base64,
                                     format_date=format_date,
                                     format_money=format_money)
            except Exception as e:
                # Log the exception for debugging
                import traceback
                print(f"Error rendering PDF template: {e}")
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
                            <div class="label">{_('Issue Date')}</div><div class="value">{(babel_format_date(self.invoice.issue_date) if babel_format_date else self.invoice.issue_date.strftime('%Y-%m-%d'))}</div>
                            <div class="label">{_('Due Date')}</div><div class="value">{(babel_format_date(self.invoice.due_date) if babel_format_date else self.invoice.due_date.strftime('%Y-%m-%d'))}</div>
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
        return html_lib.escape(value) if value else ''
    
    def _nl2br(self, value):
        if not value:
            return ''
        return self._escape(value).replace('\n', '<br>')
    
    def _get_company_logo_html(self):
        """Generate HTML for company logo if available"""
        if self.settings.has_logo():
            logo_path = self.settings.get_logo_path()
            if logo_path and os.path.exists(logo_path):
                # Use base64 data URI for reliable PDF embedding (works better with WeasyPrint)
                try:
                    import base64
                    import mimetypes
                    
                    with open(logo_path, 'rb') as logo_file:
                        logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
                    
                    # Detect MIME type
                    mime_type, _ = mimetypes.guess_type(logo_path)
                    if not mime_type:
                        # Default to PNG if can't detect
                        mime_type = 'image/png'
                    
                    data_uri = f'data:{mime_type};base64,{logo_data}'
                    return f'<img src="{data_uri}" alt="Company Logo" class="company-logo">'
                except Exception as e:
                    # Fallback to file URI if base64 fails
                    try:
                        file_url = Path(logo_path).resolve().as_uri()
                    except Exception:
                        file_url = f'file://{logo_path}'
                    return f'<img src="{file_url}" alt="Company Logo" class="company-logo">'
        return ''
    
    def _get_company_tax_info(self):
        """Generate HTML for company tax information"""
        if self.settings.company_tax_id:
            return f'<div class="company-tax">Tax ID: {self.settings.company_tax_id}</div>'
        return ''
    
    def _get_client_email_html(self):
        """Generate HTML for client email if available"""
        if self.invoice.client_email:
            return f'<div class="client-email">{self.invoice.client_email}</div>'
        return ''
    
    def _get_client_address_html(self):
        """Generate HTML for client address if available"""
        if self.invoice.client_address:
            return f'<div class="client-address">{self.invoice.client_address}</div>'
        return ''
    
    def _get_project_description_html(self):
        """Generate HTML for project description if available"""
        if self.invoice.project.description:
            return f'<div class="project-description">{self.invoice.project.description}</div>'
        return ''
    
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
                description_parts.append(f"<br><small class='good-description'>{self._escape(good.description)}</small>")
            if good.sku:
                description_parts.append(f"<br><small class='good-sku'>{_('SKU')}: {self._escape(good.sku)}</small>")
            if good.category:
                description_parts.append(f"<br><small class='good-category'>{_('Category')}: {self._escape(good.category.title())}</small>")
            
            description_html = ''.join(description_parts)
            
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
        
        return ''.join(rows)
    
    def _get_time_entry_info_html(self, item):
        """Generate HTML for time entry information if available"""
        if item.time_entry_ids:
            count = len(item.time_entry_ids.split(','))
            return f'<br><small class="time-entry-info">Generated from {count} time entries</small>'
        return ''
    
    def _generate_totals_rows(self):
        """Generate HTML rows for invoice totals"""
        rows = []
        
        # Subtotal
        rows.append(f"""
        <tr>
            <td colspan="3" class="num">Subtotal:</td>
            <td class="num">{self._format_currency(self.invoice.subtotal)}</td>
        </tr>
        """)
        
        # Tax if applicable
        if self.invoice.tax_rate > 0:
            rows.append(f"""
            <tr>
                <td colspan="3" class="num">Tax ({self.invoice.tax_rate:.2f}%):</td>
                <td class="num">{self._format_currency(self.invoice.tax_amount)}</td>
            </tr>
            """)
        
        # Total
        rows.append(f"""
        <tr>
            <td colspan="3" class="num">Total Amount:</td>
            <td class="num">{self._format_currency(self.invoice.total_amount)}</td>
        </tr>
        """)
        
        return ''.join(rows)
    
    def _get_additional_info_html(self):
        """Generate HTML for additional invoice information"""
        html_parts = []
        
        if self.invoice.notes:
            html_parts.append(f"""
            <div class="notes-section">
                <h4>{_('Notes:')}</h4>
                <p>{self.invoice.notes}</p>
            </div>
            """)
        
        if self.invoice.terms:
            html_parts.append(f"""
            <div class="terms-section">
                <h4>{_('Terms:')}</h4>
                <p>{self.invoice.terms}</p>
            </div>
            """)
        
        if html_parts:
            return f'<div class="additional-info">{"".join(html_parts)}</div>'
        return ''
    
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
        return ''
    
    def _generate_css(self):
        """Generate CSS styles for the invoice"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .invoice-container {
            max-width: 100%;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2em;
            border-bottom: 2px solid #007bff;
            padding-bottom: 1em;
        }
        
        .company-info {
            flex: 1;
        }
        
        .company-logo {
            max-width: 150px;
            max-height: 80px;
            display: block;
            margin-left: auto;
            margin-right: 0;
            margin-bottom: 1em;
        }
        
        .company-name {
            font-size: 24pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 0.5em 0;
        }
        
        .company-address {
            margin-bottom: 0.5em;
            line-height: 1.3;
        }
        
        .company-contact {
            margin-bottom: 0.5em;
        }
        
        .company-contact span {
            display: block;
            margin-bottom: 0.2em;
            font-size: 10pt;
        }
        
        .company-tax {
            font-size: 10pt;
            color: #666;
        }
        
        .invoice-info {
            text-align: right;
            min-width: 200px;
        }
        
        .logo-container {
            text-align: right;
            margin-bottom: 1em;
        }
        
        .invoice-title {
            font-size: 28pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 1em 0;
        }
        
        .invoice-details .detail-row {
            margin-bottom: 0.5em;
        }
        
        .detail-row .label {
            font-weight: bold;
            margin-right: 0.5em;
        }
        
        .status-draft { color: #6c757d; }
        .status-sent { color: #17a2b8; }
        .status-paid { color: #28a745; }
        .status-overdue { color: #dc3545; }
        .status-cancelled { color: #343a40; }
        
        .client-section, .project-section {
            margin-bottom: 2em;
        }
        
        .client-section h3, .project-section h3 {
            font-size: 14pt;
            font-weight: bold;
            color: #007bff;
            margin: 0 0 0.5em 0;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 0.3em;
        }
        
        .client-name {
            font-weight: bold;
            font-size: 14pt;
            margin-bottom: 0.5em;
        }
        
        .client-email, .client-address, .project-description {
            margin-bottom: 0.3em;
            color: #666;
        }
        
        .items-section {
            margin-bottom: 2em;
        }
        
        .invoice-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1em;
        }
        
        .invoice-table th,
        .invoice-table td {
            border: 1px solid #dee2e6;
            padding: 0.75em;
            text-align: left;
        }
        
        .invoice-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }
        
        .description { width: 40%; }
        .quantity { width: 15%; text-align: center; }
        .unit-price { width: 20%; text-align: right; }
        .total { width: 25%; text-align: right; }
        
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        
        .time-entry-info {
            color: #6c757d;
            font-style: italic;
        }
        
        .subtotal { background-color: #f8f9fa; }
        .tax { background-color: #fff3cd; }
        .total { background-color: #d1ecf1; font-weight: bold; }
        
        .additional-info {
            margin-bottom: 2em;
        }
        
        .notes-section, .terms-section {
            margin-bottom: 1em;
        }
        
        .notes-section h4, .terms-section h4 {
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }
        
        .footer {
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #dee2e6;
        }
        
        .payment-info {
            margin-bottom: 1em;
        }
        
        .payment-info h4 {
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }
        
        .bank-info {
            color: #666;
            line-height: 1.3;
        }
        
        .terms h4 {
            font-size: 12pt;
            font-weight: bold;
            color: #495057;
            margin: 0 0 0.5em 0;
        }
        
        .terms p {
            color: #666;
            line-height: 1.3;
        }
        
        /* Utility classes */
        .nl2br {
            white-space: pre-line;
        }
        """
