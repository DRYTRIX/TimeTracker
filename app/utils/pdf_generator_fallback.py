"""
Fallback PDF Generation utility for invoices using ReportLab
This is used when WeasyPrint is not available due to system dependencies
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen import canvas
from app.models import Settings
from flask import current_app
from flask_babel import gettext as _

class InvoicePDFGeneratorFallback:
    """Generate PDF invoices with company branding using ReportLab"""
    
    def __init__(self, invoice, settings=None):
        self.invoice = invoice
        self.settings = settings or Settings.get_settings()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#007bff')
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=colors.HexColor('#007bff'),
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.HexColor('#007bff')
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    def generate_pdf(self):
        """Generate PDF content and return as bytes"""
        # Create a temporary file to store the PDF
        import tempfile
        import io
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Generate the PDF
            doc = SimpleDocTemplate(
                tmp_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Build the story (content)
            story = self._build_story()
            
            # Build the PDF with page numbers
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
            
            # Read the generated PDF
            with open(tmp_path, 'rb') as f:
                pdf_bytes = f.read()
            
            return pdf_bytes
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _build_story(self):
        """Build the PDF content story"""
        story = []
        
        # Header section
        story.extend(self._build_header())
        story.append(Spacer(1, 20))
        
        # Client and project information
        story.extend(self._build_client_section())
        story.append(Spacer(1, 20))
        
        # Invoice items table
        story.extend(self._build_items_table())
        story.append(Spacer(1, 20))
        
        # Additional information
        story.extend(self._build_additional_info())
        story.append(Spacer(1, 20))
        
        # Footer
        story.extend(self._build_footer())
        
        return story
    
    def _build_header(self):
        """Build the header section with company info and invoice details"""
        story = []
        
        # Company information (left side)
        company_info = []
        company_info.append(Paragraph(self.settings.company_name, self.styles['CompanyName']))
        
        if self.settings.company_address:
            company_info.append(Paragraph(self.settings.company_address, self.styles['NormalText']))
        
        if self.settings.company_email:
            company_info.append(Paragraph(f"Email: {self.settings.company_email}", self.styles['NormalText']))
        
        if self.settings.company_phone:
            company_info.append(Paragraph(f"Phone: {self.settings.company_phone}", self.styles['NormalText']))
        
        if self.settings.company_website:
            company_info.append(Paragraph(f"Website: {self.settings.company_website}", self.styles['NormalText']))
        
        if self.settings.company_tax_id:
            company_info.append(Paragraph(f"Tax ID: {self.settings.company_tax_id}", self.styles['NormalText']))
        
        # Invoice information (right side)
        invoice_info = []
        
        # Add logo if available (top right) using Image flowable
        if self.settings.has_logo():
            logo_path = self.settings.get_logo_path()
            if logo_path and os.path.exists(logo_path):
                try:
                    img = Image(logo_path, width=4*cm, height=2*cm, kind='proportional')
                    invoice_info.append(img)
                    invoice_info.append(Spacer(1, 6))
                except Exception:
                    # Fallback to text if image fails
                    invoice_info.append(Paragraph("[Company Logo]", self.styles['NormalText']))
        
        invoice_info.append(Paragraph(_("INVOICE"), self.styles['InvoiceTitle']))
        invoice_info.append(Paragraph(_("Invoice #: %(num)s", num=self.invoice.invoice_number), self.styles['NormalText']))
        try:
            from babel.dates import format_date as babel_format_date
            issue_label = _("Issue Date: %(date)s", date=babel_format_date(self.invoice.issue_date))
            due_label = _("Due Date: %(date)s", date=babel_format_date(self.invoice.due_date))
        except Exception:
            issue_label = _("Issue Date: %(date)s", date=self.invoice.issue_date.strftime('%Y-%m-%d'))
            due_label = _("Due Date: %(date)s", date=self.invoice.due_date.strftime('%Y-%m-%d'))
        invoice_info.append(Paragraph(issue_label, self.styles['NormalText']))
        invoice_info.append(Paragraph(due_label, self.styles['NormalText']))
        invoice_info.append(Paragraph(f"Status: {self.invoice.status.title()}", self.styles['NormalText']))
        
        # Create a table to layout company info and invoice info side by side
        header_data = [[company_info, invoice_info]]
        header_table = Table(header_data, colWidths=[9*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(header_table)
        return story
    
    def _build_client_section(self):
        """Build the client and project information section"""
        story = []
        
        # Client information
        story.append(Paragraph("Bill To:", self.styles['SectionHeader']))
        story.append(Paragraph(self.invoice.client_name, self.styles['NormalText']))
        
        if self.invoice.client_email:
            story.append(Paragraph(self.invoice.client_email, self.styles['NormalText']))
        
        if self.invoice.client_address:
            story.append(Paragraph(self.invoice.client_address, self.styles['NormalText']))
        
        story.append(Spacer(1, 12))
        
        # Project information
        story.append(Paragraph("Project:", self.styles['SectionHeader']))
        story.append(Paragraph(self.invoice.project.name, self.styles['NormalText']))
        
        if self.invoice.project.description:
            story.append(Paragraph(self.invoice.project.description, self.styles['NormalText']))
        
        return story
    
    def _build_items_table(self):
        """Build the invoice items table including extra goods"""
        story = []
        
        story.append(Paragraph(_("Invoice Items"), self.styles['SectionHeader']))
        
        # Table headers
        headers = [_("Description"), _("Quantity (Hours)"), _("Unit Price"), _("Total Amount")]
        
        # Table data
        data = [headers]
        
        # Add regular invoice items
        for item in self.invoice.items:
            row = [
                item.description,
                f"{item.quantity:.2f}",
                self._format_currency(item.unit_price),
                self._format_currency(item.total_amount)
            ]
            data.append(row)
        
        # Add extra goods
        for good in self.invoice.extra_goods:
            # Build description with additional details
            description_parts = [good.name]
            if good.description:
                description_parts.append(f"\n{good.description}")
            if good.sku:
                description_parts.append(f"\nSKU: {good.sku}")
            if good.category:
                description_parts.append(f"\nCategory: {good.category.title()}")
            
            description = '\n'.join(description_parts)
            
            row = [
                description,
                f"{good.quantity:.2f}",
                self._format_currency(good.unit_price),
                self._format_currency(good.total_amount)
            ]
            data.append(row)
        
        # Add totals
        data.append(['', '', _('Subtotal:'), self._format_currency(self.invoice.subtotal)])
        
        if self.invoice.tax_rate > 0:
            data.append(['', '', _('Tax (%(rate).2f%%):', rate=self.invoice.tax_rate), self._format_currency(self.invoice.tax_amount)])
        
        data.append(['', '', _('Total Amount:'), self._format_currency(self.invoice.total_amount)])
        
        # Create table
        table = Table(data, colWidths=[9*cm, 3*cm, 3*cm, 3*cm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#eef2ff')),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#e2e8f0'))
        ]))
        
        story.append(table)
        return story

    def _format_currency(self, value):
        """Format numeric currency with thousands separators and 2 decimals."""
        try:
            return f"{float(value):,.2f} {self.settings.currency}"
        except Exception:
            return f"{value} {self.settings.currency}"

    def _add_page_number(self, canv, doc):
        """Add page number at the bottom-right of each page."""
        page_num = canv.getPageNumber()
        text = f"Page {page_num}"
        canv.setFont('Helvetica', 9)
        try:
            canv.setFillColor(colors.HexColor('#666666'))
        except Exception:
            pass
        x = doc.leftMargin + doc.width
        y = doc.bottomMargin - 0.5*cm
        canv.drawRightString(x, y, text)
    
    def _build_additional_info(self):
        """Build additional information section"""
        story = []
        
        if self.invoice.notes:
            story.append(Paragraph(_("Notes:"), self.styles['SectionHeader']))
            story.append(Paragraph(self.invoice.notes, self.styles['NormalText']))
            story.append(Spacer(1, 12))
        
        if self.invoice.terms:
            story.append(Paragraph(_("Terms:"), self.styles['SectionHeader']))
            story.append(Paragraph(self.invoice.terms, self.styles['NormalText']))
            story.append(Spacer(1, 12))
        
        return story
    
    def _build_footer(self):
        """Build the footer section"""
        story = []
        
        # Payment information
        if self.settings.company_bank_info:
            story.append(Paragraph(_("Payment Information:"), self.styles['SectionHeader']))
            story.append(Paragraph(self.settings.company_bank_info, self.styles['NormalText']))
            story.append(Spacer(1, 12))
        
        # Terms and conditions
        story.append(Paragraph(_("Terms & Conditions:"), self.styles['SectionHeader']))
        story.append(Paragraph(self.settings.invoice_terms, self.styles['NormalText']))
        
        return story
