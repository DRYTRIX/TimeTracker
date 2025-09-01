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

class InvoicePDFGenerator:
    """Generate PDF invoices with company branding"""
    
    def __init__(self, invoice, settings=None):
        self.invoice = invoice
        self.settings = settings or Settings.get_settings()
    
    def generate_pdf(self):
        """Generate PDF content and return as bytes"""
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
        css_doc = CSS(string=css_content)
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc])
        
        return pdf_bytes
    
    def _generate_html(self):
        """Generate HTML content for the invoice"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Invoice {self.invoice.invoice_number}</title>
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
            thead th {{ background: var(--bg-alt); color: var(--muted); font-weight: 700; border: 1px solid var(--border); padding: 10px; font-size: 10.5pt; text-align: left; }}
            tbody td {{ border: 1px solid var(--border); padding: 10px; font-size: 10.5pt; }}
            tfoot td {{ border: 1px solid var(--border); padding: 10px; font-weight: 700; }}
            .num {{ text-align: right; }}
            .desc {{ width: 50%; }}

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
                                <span>Email: {self._escape(self.settings.company_email)}  ·  Phone: {self._escape(self.settings.company_phone)}</span>
                                <span>Website: {self._escape(self.settings.company_website)}</span>
                                {self._get_company_tax_info()}
                            </div>
                        </div>
                    </div>
                    <div class="invoice-meta">
                        <div class="invoice-title">INVOICE</div>
                        <div class="meta-grid">
                            <div class="label">Invoice #</div><div class="value">{self.invoice.invoice_number}</div>
                            <div class="label">Issue Date</div><div class="value">{self.invoice.issue_date.strftime('%b %d, %Y')}</div>
                            <div class="label">Due Date</div><div class="value">{self.invoice.due_date.strftime('%b %d, %Y')}</div>
                            <div class="label">Status</div><div class="value">{self.invoice.status.title()}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Client Information -->
                <div class="two-col">
                    <div class="card">
                        <div class="section-title">Bill To</div>
                        <div><strong>{self._escape(self.invoice.client_name)}</strong></div>
                        {self._get_client_email_html()}
                        {self._get_client_address_html()}
                    </div>
                    <div class="card">
                        <div class="section-title">Project</div>
                        <div><strong>{self._escape(self.invoice.project.name)}</strong></div>
                        {self._get_project_description_html()}
                    </div>
                </div>
                
                <!-- Invoice Items -->
                <div>
                    <table>
                        <thead>
                            <tr>
                                <th class="desc">Description</th>
                                <th class="num">Quantity (Hours)</th>
                                <th class="num">Unit Price</th>
                                <th class="num">Total Amount</th>
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
                    <div><strong>Terms & Conditions:</strong> {self._escape(self.settings.invoice_terms)}</div>
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
                # Use file:// scheme so WeasyPrint can load local files
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
        """Generate HTML rows for invoice items"""
        rows = []
        for item in self.invoice.items:
            row = f"""
            <tr>
                <td>
                    {self._escape(item.description)}
                    {self._get_time_entry_info_html(item)}
                </td>
                <td class="num">{item.quantity:.2f}</td>
                <td class="num">{item.unit_price:.2f} {self.settings.currency}</td>
                <td class="num">{item.total_amount:.2f} {self.settings.currency}</td>
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
            <td class="num">{self.invoice.subtotal:.2f} {self.settings.currency}</td>
        </tr>
        """)
        
        # Tax if applicable
        if self.invoice.tax_rate > 0:
            rows.append(f"""
            <tr>
                <td colspan="3" class="num">Tax ({self.invoice.tax_rate:.2f}%):</td>
                <td class="num">{self.invoice.tax_amount:.2f} {self.settings.currency}</td>
            </tr>
            """)
        
        # Total
        rows.append(f"""
        <tr>
            <td colspan="3" class="num">Total Amount:</td>
            <td class="num">{self.invoice.total_amount:.2f} {self.settings.currency}</td>
        </tr>
        """)
        
        return ''.join(rows)
    
    def _get_additional_info_html(self):
        """Generate HTML for additional invoice information"""
        html_parts = []
        
        if self.invoice.notes:
            html_parts.append(f"""
            <div class="notes-section">
                <h4>Notes:</h4>
                <p>{self.invoice.notes}</p>
            </div>
            """)
        
        if self.invoice.terms:
            html_parts.append(f"""
            <div class="terms-section">
                <h4>Terms:</h4>
                <p>{self.invoice.terms}</p>
            </div>
            """)
        
        if html_parts:
            return f'<div class="additional-info">{"".join(html_parts)}</div>'
        return ''
    
    def _get_payment_info_html(self):
        """Generate HTML for payment information"""
        if self.settings.company_bank_info:
            return f"""
            <h4>Payment Information:</h4>
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
