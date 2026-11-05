# Enhanced Invoice System with PDF Export

## Overview

The TimeTracker application now includes a comprehensive invoice system with professional PDF export capabilities, company branding, and configurable settings. This enhancement transforms the basic invoice functionality into a professional billing solution.

## Features

### 🎯 Core Invoice Management
- **Create, edit, and manage invoices** with full CRUD operations
- **Generate invoice items from time entries** automatically
- **Flexible line item management** with quantity, unit price, and descriptions
- **Tax calculation** with configurable rates
- **Status tracking** (draft, sent, paid, overdue, cancelled)
- **Invoice numbering** with customizable prefixes and sequences

### 📄 Professional PDF Export
- **High-quality PDF generation** using WeasyPrint
- **Company branding integration** with logo, colors, and styling
- **Professional layout** with proper typography and spacing
- **Automatic page numbering** and formatting
- **Print-ready output** for professional presentation

### 🏢 Company Branding
- **Company information** (name, address, contact details)
- **Logo integration** with configurable file paths
- **Customizable styling** with brand colors
- **Professional header/footer** design
- **Tax ID and banking information** display

### ⚙️ Configurable Settings
- **Invoice defaults** (terms, notes, numbering)
- **Company branding** settings
- **PDF styling** options
- **Export preferences** and formatting

## Installation & Setup

### 1. Install Dependencies

Add the required PDF generation libraries to your environment:

```bash
pip install WeasyPrint==60.2 Pillow==10.1.0
```

Or update your `requirements.txt`:

```txt
# PDF Generation
WeasyPrint==60.2
Pillow==10.1.0
```

### 2. Database Migration

Run the company branding migration to add new fields:

```bash
python docker/migrate-add-company-branding.py
```

### 3. Configure Company Settings

Navigate to **Admin → Settings** and configure:

- **Company Branding**: Name, address, logo, contact info
- **Invoice Defaults**: Terms, notes, numbering preferences
- **PDF Settings**: Styling and formatting options

## Usage

### Creating Invoices

1. **Navigate to Invoices** → **Create New Invoice**
2. **Select project** and enter client details
3. **Set due date** and tax rate
4. **Add line items** manually or generate from time entries
5. **Save and manage** invoice status

### Generating PDFs

1. **View any invoice** in the system
2. **Click "Export PDF"** button
3. **Download professional PDF** with company branding

### Company Branding Setup

1. **Upload company logo** to accessible file path
2. **Configure company details** in settings
3. **Set invoice defaults** and terms
4. **Customize styling** preferences

## Technical Architecture

### PDF Generation Engine

```python
from app.utils.pdf_generator import InvoicePDFGenerator

# Generate PDF for invoice
pdf_generator = InvoicePDFGenerator(invoice, settings)
pdf_bytes = pdf_generator.generate_pdf()
```

**Features:**
- **WeasyPrint integration** for high-quality output
- **HTML/CSS templating** for flexible design
- **Font configuration** and typography control
- **Responsive layout** with proper page breaks

### Settings Model

```python
class Settings(db.Model):
    # Company branding
    company_name = db.Column(db.String(200))
    company_logo_path = db.Column(db.String(500))
    company_address = db.Column(db.Text)

    # Invoice defaults
    invoice_prefix = db.Column(db.String(10))
    invoice_start_number = db.Column(db.Integer)
    invoice_terms = db.Column(db.Text)
```

### Database Schema

#### Settings Table Extensions
```sql
-- Company branding fields
ALTER TABLE settings ADD COLUMN company_name VARCHAR(200) DEFAULT 'Your Company Name';
ALTER TABLE settings ADD COLUMN company_logo_path VARCHAR(500) DEFAULT '';
ALTER TABLE settings ADD COLUMN company_address TEXT DEFAULT 'Your Company Address';

-- Invoice default fields
ALTER TABLE settings ADD COLUMN invoice_prefix VARCHAR(10) DEFAULT 'INV';
ALTER TABLE settings ADD COLUMN invoice_start_number INTEGER DEFAULT 1000;
ALTER TABLE settings ADD COLUMN invoice_terms TEXT DEFAULT 'Payment is due within 30 days.';
```

## PDF Template Structure

### Header Section
- Company logo and branding
- Company contact information
- Invoice details (number, dates, status)

### Client Information
- Bill-to address and contact details
- Project information and description

### Invoice Items
- Professional table layout
- Quantity, unit price, and totals
- Time entry references (if applicable)

### Footer Section
- Payment instructions
- Terms and conditions
- Company notes

## Customization Options

### Logo Integration
```python
# In settings
company_logo_path = "/path/to/company/logo.png"

# In PDF template
if settings.company_logo_path and os.path.exists(settings.company_logo_path):
    return f'<img src="{settings.company_logo_path}" class="company-logo">'
```

### Styling Customization
```css
.company-name {
    font-size: 24pt;
    font-weight: bold;
    color: #007bff; /* Brand color */
}

.invoice-title {
    font-size: 28pt;
    color: #007bff;
}
```

### Content Customization
- **Company information** fields
- **Invoice defaults** and templates
- **Terms and conditions** text
- **Payment instructions** formatting

## File Structure

```
app/
├── models/
│   ├── invoice.py          # Invoice and InvoiceItem models
│   └── settings.py         # Enhanced settings with branding
├── routes/
│   └── invoices.py         # Invoice routes including PDF export
├── utils/
│   └── pdf_generator.py    # PDF generation utility
└── templates/
    └── invoices/
        ├── view.html        # Invoice view with PDF export
        ├── create.html      # Invoice creation form
        └── edit.html        # Invoice editing interface

templates/
└── admin/
    └── settings.html        # Enhanced settings with branding fields

docker/
├── migrate-add-company-branding.py  # Database migration
└── start-new.sh                     # Updated startup script
```

## API Endpoints

### Invoice Management
- `GET /invoices` - List all invoices
- `POST /invoices/create` - Create new invoice
- `GET /invoices/<id>` - View invoice details
- `POST /invoices/<id>/edit` - Edit invoice
- `DELETE /invoices/<id>` - Delete invoice

### Export Functions
- `GET /invoices/<id>/export/csv` - Export as CSV
- `GET /invoices/<id>/export/pdf` - Export as PDF

### Settings Management
- `GET /admin/settings` - View/edit system settings
- `POST /admin/settings` - Update system settings

## Configuration Examples

### Company Branding Setup
```python
# Example settings configuration
settings = Settings(
    company_name="Acme Corporation",
    company_address="123 Business St\nCity, State 12345",
    company_email="billing@acme.com",
    company_phone="+1 (555) 123-4567",
    company_logo_path="/app/static/images/acme-logo.png",
    company_tax_id="TAX-123456789",
    company_bank_info="Bank: First National Bank\nAccount: 1234-5678-9012"
)
```

### Invoice Defaults
```python
# Invoice numbering and defaults
settings.invoice_prefix = "ACME"
settings.invoice_start_number = 1000
settings.invoice_terms = "Net 30 days. Late payments subject to 1.5% monthly fee."
settings.invoice_notes = "Thank you for choosing Acme Corporation!"
```

## Troubleshooting

### PDF Generation Issues

**Problem**: "WeasyPrint not available" error
**Solution**: Install WeasyPrint and Pillow dependencies

**Problem**: Logo not displaying in PDF
**Solution**: Check file path and permissions for logo file

**Problem**: PDF styling issues
**Solution**: Verify CSS syntax and WeasyPrint compatibility

### Database Migration Issues

**Problem**: New fields not appearing
**Solution**: Run the migration script manually

**Problem**: Settings not saving
**Solution**: Check database permissions and table structure

## Performance Considerations

### PDF Generation
- **WeasyPrint processing** can be resource-intensive
- **Large invoices** may take longer to generate
- **Logo file size** affects PDF generation speed
- **Caching** recommended for frequently accessed invoices

### Database Optimization
- **Indexes** on invoice lookup fields
- **Settings caching** for company information
- **Connection pooling** for database operations

## Security Features

### Access Control
- **User-based permissions** for invoice access
- **Admin-only settings** modification
- **Secure file paths** for logo storage
- **Input validation** for all form fields

### Data Protection
- **SQL injection prevention** with parameterized queries
- **XSS protection** in template rendering
- **File upload validation** for logo files
- **CSRF protection** on all forms

## Future Enhancements

### Planned Features
- **Email integration** for invoice delivery
- **Payment gateway** integration
- **Invoice templates** customization
- **Batch PDF generation**
- **Digital signatures** support

### Customization Options
- **Theme system** for different company styles
- **Multi-language** support
- **Currency conversion** integration
- **Advanced reporting** and analytics

## Support & Maintenance

### Regular Tasks
- **Logo file management** and updates
- **Settings backup** and restoration
- **PDF template** maintenance
- **Performance monitoring** and optimization

### Updates & Patches
- **Dependency updates** for security
- **Template improvements** and bug fixes
- **Feature enhancements** and new capabilities
- **Compatibility** with new Flask versions

## Conclusion

The enhanced invoice system provides a professional, feature-rich solution for business billing needs. With PDF export capabilities, company branding integration, and comprehensive configuration options, it transforms TimeTracker into a complete business management tool.

The system is designed for scalability, maintainability, and ease of use, making it suitable for both small businesses and enterprise environments.
