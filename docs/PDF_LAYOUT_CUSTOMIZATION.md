# PDF Layout Customization Guide

## Overview

TimeTracker provides a powerful system-wide PDF layout editor that allows administrators to customize the appearance of invoice PDFs. This feature enables you to:

- Customize the HTML structure of invoice PDFs
- Apply custom CSS styling
- Use Jinja2 template variables to display dynamic data
- Preview changes in real-time
- Save and reuse custom templates across all invoices

## Accessing the PDF Layout Editor

### Admin Access Required

To access the PDF layout editor:

1. Log in as an administrator
2. Navigate to **Admin** → **PDF Layout** in the sidebar
3. The PDF Layout Editor page will open

**URL:** `/admin/pdf-layout`

**Required Permission:** `manage_settings` or admin role

## Using the PDF Layout Editor

### Interface Overview

The PDF Layout Editor is powered by **Konva.js** and consists of three main sections:

1. **Element Library (Left Sidebar)**: Drag-and-drop elements organized by category
   - Basic Elements (text, shapes, lines, decorative images)
   - Company Information (logo, name, address, contact details)
   - Invoice Data (numbers, dates, client info, totals)
   - Advanced Elements (QR codes, watermarks, page numbers)

2. **Canvas Workspace (Center)**: Visual canvas representing your invoice page (A4 size)
   - Click elements from sidebar to add to canvas
   - Drag elements to reposition
   - Resize using transform handles
   - Toolbar with zoom, delete, and alignment tools

3. **Properties Panel (Right Sidebar)**: Edit properties of selected element
   - Position (X/Y coordinates)
   - Text content and styling (font, size, color)
   - Shape properties (fill, stroke, dimensions)
   - Layer order controls (z-index)
   - Live preview of generated PDF

### Editing Workflow

1. **Add Elements**: Click elements from left sidebar to add to canvas
2. **Position**: Drag elements to desired locations or use X/Y properties
3. **Customize**: Select elements and edit properties in right panel
4. **Align**: Use toolbar alignment tools for precise positioning
5. **Layer**: Manage z-index with layer order controls
6. **Preview**: Click "Generate Preview" to see rendered result
7. **Save**: Click "Save Design" to apply system-wide
8. **Reset**: If needed, click "Reset" to restore defaults

### Quick Start

For a beginner-friendly guide, see [PDF Editor Quick Start](./PDF_EDITOR_QUICK_START.md)

For comprehensive feature documentation, see [Enhanced PDF Editor Features](./PDF_EDITOR_ENHANCED_FEATURES.md)

## Available Template Variables

### Invoice Variables

```jinja
{{ invoice.invoice_number }}           # Invoice number (e.g., "INV-2024-001")
{{ invoice.issue_date }}                # Issue date
{{ invoice.due_date }}                  # Due date
{{ invoice.status }}                    # Status (draft, sent, paid, etc.)
{{ invoice.client_name }}               # Client name
{{ invoice.client_email }}              # Client email
{{ invoice.client_address }}            # Client address
{{ invoice.subtotal }}                  # Subtotal amount
{{ invoice.tax_rate }}                  # Tax rate percentage
{{ invoice.tax_amount }}                # Tax amount
{{ invoice.total_amount }}              # Total amount
{{ invoice.notes }}                     # Invoice notes
{{ invoice.terms }}                     # Invoice terms
```

### Project Variables

```jinja
{{ invoice.project.name }}              # Project name
{{ invoice.project.description }}       # Project description
```

### Invoice Items Loop

For the combined items table (time entries, extra goods, and expenses), use `invoice.all_line_items` in the PDF Designer:

```jinja
{% for item in invoice.all_line_items %}
    {{ item.description }}              # Item description
    {{ item.quantity }}                 # Quantity
    {{ item.unit_price }}               # Unit price
    {{ item.total_amount }}             # Line total
{% endfor %}
```

For invoice items only (time-based billing):

```jinja
{% for item in invoice.items %}
    {{ item.description }}              # Item description
    {{ item.quantity }}                 # Quantity (hours or units)
    {{ item.unit_price }}               # Unit price
    {{ item.total_amount }}             # Line total
    {{ item.time_entry_ids }}           # Associated time entry IDs
{% endfor %}
```

### Extra Goods Loop

```jinja
{% for good in invoice.extra_goods %}
    {{ good.name }}                     # Good/product name
    {{ good.description }}              # Description
    {{ good.sku }}                      # SKU code
    {{ good.category }}                 # Category
    {{ good.quantity }}                 # Quantity
    {{ good.unit_price }}               # Unit price
    {{ good.total_amount }}             # Line total
{% endfor %}
```

### Settings Variables

```jinja
{{ settings.company_name }}             # Your company name
{{ settings.company_address }}          # Your company address
{{ settings.company_email }}            # Your company email
{{ settings.company_phone }}            # Your company phone
{{ settings.company_website }}          # Your company website
{{ settings.company_tax_id }}           # Your tax ID
{{ settings.company_bank_info }}        # Bank information
{{ settings.currency }}                 # Currency code (e.g., "USD")
{{ settings.invoice_terms }}            # Default invoice terms
```

### Helper Functions

```jinja
{{ format_date(invoice.issue_date) }}           # Format date using Babel
{{ format_money(invoice.total_amount) }}        # Format money with currency
{{ get_logo_base64(logo_path) }}                # Get logo as base64 data URI
{{ _('Label') }}                                # Translate text (i18n)
```

### Conditional Rendering

```jinja
{% if settings.has_logo() %}
    <img src="{{ get_logo_base64(settings.get_logo_path()) }}" alt="Company Logo">
{% endif %}

{% if invoice.tax_rate > 0 %}
    <tr>
        <td>Tax ({{ invoice.tax_rate }}%):</td>
        <td>{{ format_money(invoice.tax_amount) }}</td>
    </tr>
{% endif %}

{% if invoice.notes %}
    <div class="notes">{{ invoice.notes }}</div>
{% endif %}
```

## Example Templates

### Basic Invoice Template

```html
<div class="wrapper">
    <div class="invoice-header">
        <h1 class="company-name">{{ settings.company_name }}</h1>
        <div class="invoice-title">INVOICE</div>
    </div>
    
    <div class="meta">
        <p><strong>Invoice #:</strong> {{ invoice.invoice_number }}</p>
        <p><strong>Date:</strong> {{ format_date(invoice.issue_date) }}</p>
        <p><strong>Due:</strong> {{ format_date(invoice.due_date) }}</p>
    </div>
    
    <div class="client-info">
        <h3>Bill To:</h3>
        <p><strong>{{ invoice.client_name }}</strong></p>
        {% if invoice.client_email %}
        <p>{{ invoice.client_email }}</p>
        {% endif %}
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in invoice.items %}
            <tr>
                <td>{{ item.description }}</td>
                <td>{{ "%.2f"|format(item.quantity) }}</td>
                <td>{{ format_money(item.unit_price) }}</td>
                <td>{{ format_money(item.total_amount) }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="3">Subtotal:</td>
                <td>{{ format_money(invoice.subtotal) }}</td>
            </tr>
            {% if invoice.tax_rate > 0 %}
            <tr>
                <td colspan="3">Tax ({{ invoice.tax_rate }}%):</td>
                <td>{{ format_money(invoice.tax_amount) }}</td>
            </tr>
            {% endif %}
            <tr>
                <td colspan="3"><strong>Total:</strong></td>
                <td><strong>{{ format_money(invoice.total_amount) }}</strong></td>
            </tr>
        </tfoot>
    </table>
    
    <div class="footer">
        <p><strong>{{ _('Terms & Conditions:') }}</strong> {{ settings.invoice_terms }}</p>
    </div>
</div>
```

### Basic CSS Template

```css
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: Arial, sans-serif;
    font-size: 12pt;
    color: #333;
}

.wrapper {
    padding: 20px;
}

.invoice-header {
    display: flex;
    justify-content: space-between;
    border-bottom: 2px solid #007bff;
    padding-bottom: 15px;
    margin-bottom: 20px;
}

.company-name {
    font-size: 24pt;
    color: #007bff;
    margin: 0;
}

.invoice-title {
    font-size: 28pt;
    font-weight: bold;
    color: #007bff;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}

th {
    background-color: #f8f9fa;
    font-weight: bold;
}

tfoot td {
    font-weight: bold;
}

.footer {
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
}
```

## Best Practices

### 1. Test Your Templates

Always preview your templates with real invoice data before saving:
- Create a test invoice with various items
- Use the preview function to check rendering
- Test with and without optional fields (logo, notes, etc.)

### 2. Keep It Simple

- Start with the default template and modify incrementally
- Avoid overly complex layouts that may not render properly in PDF
- Test with different amounts of data (few items vs. many items)

### 3. Use CSS for Styling

- Keep HTML semantic and clean
- Apply all styling through CSS
- Use CSS variables for easy color/font customization

### 4. Handle Missing Data Gracefully

```jinja
{% if invoice.client_email %}
    <p>Email: {{ invoice.client_email }}</p>
{% endif %}
```

### 5. Maintain Consistent Branding

- Use company colors from your settings
- Include your logo using the `get_logo_base64()` helper
- Match font styles to your company branding

### 6. Consider Print Layout

```css
@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
    }
}

/* Avoid page breaks inside elements */
tr, td, th {
    page-break-inside: avoid;
}
```

## Troubleshooting

### Template Not Rendering

**Issue:** Template shows blank or errors in preview

**Solutions:**
- Check Jinja2 syntax for typos
- Ensure all `{% %}` blocks are properly closed
- Verify variable names match documentation
- Check browser console for JavaScript errors

### Variables Not Displaying

**Issue:** Variables show as `{{ variable_name }}` instead of actual values

**Solutions:**
- Ensure you're using correct variable names
- Check if the data exists (use `{% if variable %}` checks)
- Verify the variable is in scope for the template

### CSS Not Applied

**Issue:** Styling doesn't appear in preview or PDF

**Solutions:**
- Verify CSS syntax is valid
- Check for CSS selector specificity issues
- Ensure CSS is saved in the CSS field, not HTML
- Test CSS separately in preview

### Logo Not Displaying

**Issue:** Company logo doesn't appear in PDF

**Solutions:**
- Verify logo is uploaded in Settings
- Use `get_logo_base64()` helper function for reliable embedding
- Check logo file format (PNG, JPG, GIF supported)
- Ensure logo file size is reasonable (< 2MB)

### Rate Limiting Errors

**Issue:** Preview or save fails with "Too Many Requests"

**Solution:**
- Wait a minute before trying again
- Rate limits: 60 previews/minute, 30 saves/minute

### Items or Expenses Table Disappears After Save

**Issue:** After adding an Items Table or Expenses Table from the Invoice Data section and clicking Save, the tables disappear from the design and are not present in the generated PDF.

**Solutions:**
- Ensure you add the **Items Table** or **Expenses Table** elements from the left sidebar (Invoice Data section)
- Use **Reset** to restore the default layout, then re-add the Items Table and Expenses Table as needed
- The Items Table uses `invoice.all_line_items` and displays time-based items, extra goods, and expenses in one combined table
- See [Invoice Extra Goods PDF Export](INVOICE_EXTRA_GOODS_PDF_EXPORT.md) for details on the data sources

## API Endpoints

### GET `/admin/pdf-layout`
Display the PDF layout editor interface.

**Permissions:** Admin or `manage_settings`

### POST `/admin/pdf-layout`
Save custom PDF template.

**Parameters:**
- `invoice_pdf_template_html`: Custom HTML template
- `invoice_pdf_template_css`: Custom CSS styles

**Permissions:** Admin or `manage_settings`

### GET `/admin/pdf-layout/default`
Get default HTML and CSS templates.

**Response:** JSON with `html` and `css` keys

**Permissions:** Admin or `manage_settings`

### POST `/admin/pdf-layout/preview`
Generate preview of custom template.

**Parameters:**
- `html`: HTML template to preview
- `css`: CSS styles to apply
- `invoice_id` (optional): Specific invoice to preview

**Response:** Rendered HTML preview

**Permissions:** Admin or `manage_settings`

### POST `/admin/pdf-layout/reset`
Reset templates to defaults (clear custom templates).

**Permissions:** Admin or `manage_settings`

## Technical Details

### Template Rendering

1. **Priority**: Custom templates take precedence over defaults
2. **Engine**: Jinja2 template engine with Flask context
3. **PDF Generation**: WeasyPrint (fallback to ReportLab if unavailable)
4. **Storage**: Templates stored in Settings table in database

### Security Considerations

- All templates are sanitized before rendering
- CSRF protection on all POST endpoints
- Rate limiting prevents abuse
- Only admin users can modify templates
- Templates are executed server-side in controlled environment

### Performance

- Templates are cached per invoice generation
- Preview uses same rendering engine as PDF generation
- Large templates may take longer to render
- Optimize images and avoid external resources

## Internationalization (i18n)

Use the `_()` function to translate text:

```jinja
<th>{{ _('Description') }}</th>
<th>{{ _('Quantity') }}</th>
<th>{{ _('Price') }}</th>
```

Supported languages:
- English (en)
- German (de)
- French (fr)
- Italian (it)
- Dutch (nl)
- Finnish (fi)

## Advanced Features

### Page Numbers

```css
@page {
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10pt;
    }
}
```

### Conditional Styling

```jinja
<div class="status-{{ invoice.status }}">
    Status: {{ invoice.status|title }}
</div>
```

```css
.status-paid { color: green; }
.status-overdue { color: red; }
.status-draft { color: gray; }
```

### Custom Filters

```jinja
{{ invoice.client_name|upper }}
{{ invoice.total_amount|round(2) }}
{{ invoice.issue_date|string }}
```

## Migration from Old Templates

If you have existing invoice templates:

1. **Backup**: Export your current template code
2. **Test**: Create test invoices to validate
3. **Convert**: Adapt any custom logic to new format
4. **Preview**: Use preview function extensively
5. **Deploy**: Save and test with real invoices
6. **Monitor**: Check generated PDFs for issues

## Support and Resources

- **Default Template**: View source at `app/templates/invoices/pdf_default.html`
- **Default CSS**: View source at `templates/invoices/pdf_styles_default.css`
- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **WeasyPrint Documentation**: https://weasyprint.org/
- **CSS Print Styles**: https://www.smashingmagazine.com/2015/01/designing-for-print-with-css/

## Konva.js Visual Editor Features

### Keyboard Shortcuts

The visual editor supports these keyboard shortcuts:

- **Delete/Backspace**: Remove selected element
- **Ctrl+C**: Copy selected element
- **Ctrl+V**: Paste copied element (offset by 20px)
- **Ctrl+D**: Duplicate selected element
- **Arrow Keys**: Move element by 1px
- **Shift+Arrow Keys**: Move element by 10px

### Element Types

#### Text Elements
All text elements support:
- Custom text content (with Jinja2 variables)
- Font family (6 fonts available)
- Font size (pixels)
- Font style (normal, bold, italic)
- Text color (color picker)
- Width (for text wrapping)
- Opacity (0-100%)

#### Shape Elements
Rectangles and circles support:
- Fill color (interior)
- Stroke color (border)
- Stroke width (border thickness)
- Dimensions (width/height for rectangles, radius for circles)
- Opacity

#### Special Elements
- **Logo**: Displays uploaded company logo (if available)
- **Items Table**: Dynamic table with headers and item rows
- **QR Code**: Placeholder for QR code generation
- **Barcode**: Placeholder for barcode generation
- **Watermark**: Large, semi-transparent text overlay

### Alignment Tools

Use toolbar buttons to align selected elements:
- **Align Left**: Move to left edge
- **Center Horizontally**: Center on canvas
- **Align Right**: Move to right edge
- **Align Top**: Move to top edge
- **Center Vertically**: Center vertically
- **Align Bottom**: Move to bottom edge

### Layer Management

Control element stacking order:
- **Move Up**: Bring forward one layer
- **Move Down**: Send back one layer
- **Bring to Top**: Bring to front
- **Send to Bottom**: Send to back

## Changelog

### Version 2.0 (Current - Enhanced with Konva.js)
- **New**: Konva.js-powered visual editor
- **New**: Drag-and-drop element library with 30+ elements
- **New**: Real-time properties panel
- **New**: Shape elements (rectangles, circles)
- **New**: Alignment tools
- **New**: Layer management (z-index controls)
- **New**: Keyboard shortcuts
- **New**: Copy/paste/duplicate functionality
- **New**: Transform handles for resizing
- **New**: Live canvas editing with instant visual feedback
- **Improved**: Enhanced preview integration
- **Improved**: Better element positioning and sizing

### Version 1.0
- Initial PDF layout customization system
- GrapesJS visual editor (deprecated)
- Real-time preview
- System-wide template storage
- Jinja2 template variables
- Rate limiting and security features

