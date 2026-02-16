# Invoice Extra Goods PDF Export

## Overview

The TimeTracker invoice system now includes **extra goods** (products, services, materials, licenses) in PDF exports. This enhancement allows invoices to include both time-based billing items and additional goods/products in a single professional PDF document.

## Feature Description

### What's New

- **Extra Goods in PDF**: Invoice PDFs now automatically include all extra goods associated with an invoice
- **Rich Details**: Each good displays its name, description, SKU, category, quantity, unit price, and total amount
- **Consistent Formatting**: Extra goods are displayed in the same table as regular invoice items with appropriate styling
- **Dual PDF Support**: Both WeasyPrint (primary) and ReportLab (fallback) generators support extra goods

### What Are Extra Goods?

Extra goods are additional products or services that can be added to invoices beyond time-based billing. They include:

- **Products**: Physical items (hardware, equipment, supplies)
- **Services**: Additional services not tracked by time entries (licenses, subscriptions, one-time services)
- **Materials**: Consumables or raw materials used in projects
- **Licenses**: Software licenses, certifications, permits
- **Other**: Miscellaneous goods and services

## Technical Implementation

### Files Modified

1. **`app/utils/pdf_generator.py`**
   - Modified `_generate_items_rows()` to include extra goods
   - Added formatting for good name, description, SKU, and category

2. **`app/templates/invoices/pdf_default.html`**
   - Added loop to render extra goods in the invoice items table
   - Included conditional display of description, SKU, and category

3. **`app/utils/pdf_generator_fallback.py`**
   - Modified `_build_items_table()` to include extra goods
   - Added multi-line description support for ReportLab

4. **`tests/test_invoices.py`**
   - Added 6 comprehensive tests covering unit and smoke testing
   - Tests for both primary and fallback PDF generators

### Data Flow

```
Invoice Model
  ├── items (InvoiceItem) - Time-based billing items
  └── extra_goods (ExtraGood) - Additional products/services
                                    ↓
                          PDF Generator reads both
                                    ↓
                        Renders in single table
                                    ↓
                      Professional PDF output
```

### PDF Structure

The invoice PDF table now includes:

1. **Header Row**: Description | Quantity (Hours) | Unit Price | Total Amount
2. **Invoice Items**: Regular time-based billing entries
3. **Extra Goods**: Additional products/services with:
   - Primary name (bold)
   - Description (if available)
   - SKU code (if available)
   - Category (product/service/material/license/other)
4. **Footer Rows**: Subtotal | Tax | Total Amount

## Usage Examples

### Adding Extra Goods to an Invoice

```python
from app.models import ExtraGood
from decimal import Decimal

# Create an extra good
good = ExtraGood(
    name='Software License',
    description='Annual premium license',
    category='license',
    quantity=Decimal('1.00'),
    unit_price=Decimal('299.99'),
    sku='LIC-2024-001',
    created_by=current_user.id,
    invoice_id=invoice.id
)

db.session.add(good)
db.session.commit()

# Recalculate invoice totals to include the good
invoice.calculate_totals()
db.session.commit()
```

### Generating PDF with Extra Goods

```python
from app.utils.pdf_generator import InvoicePDFGenerator

# Generate PDF (automatically includes extra goods)
generator = InvoicePDFGenerator(invoice)
pdf_bytes = generator.generate_pdf()

# Save or send the PDF
with open('invoice.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

## Testing

### Running Tests

Run all invoice tests including extra goods tests:

```bash
# All invoice tests
pytest tests/test_invoices.py -v

# Only extra goods tests
pytest tests/test_invoices.py -k "extra_goods" -v

# Unit tests only
pytest tests/test_invoices.py -m unit -k "extra_goods" -v

# Smoke tests only
pytest tests/test_invoices.py -m smoke -k "extra_goods" -v
```

### Test Coverage

The implementation includes:

- **6 new tests** covering extra goods in PDF export
- **Unit tests**: Verify goods are included and properly formatted
- **Smoke tests**: End-to-end PDF generation without errors
- **Both generators**: Tests for WeasyPrint and ReportLab generators

### Test Results Expected

All tests should pass:
- ✅ `test_invoice_with_extra_goods` - Association test
- ✅ `test_pdf_generator_includes_extra_goods` - Content inclusion
- ✅ `test_pdf_generator_extra_goods_formatting` - Formatting verification
- ✅ `test_pdf_fallback_generator_includes_extra_goods` - Fallback generator
- ✅ `test_pdf_export_with_extra_goods_smoke` - Primary PDF generation
- ✅ `test_pdf_export_fallback_with_extra_goods_smoke` - Fallback PDF generation

## User Interface

### How Extra Goods Appear in PDF

**Example PDF Output:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ INVOICE #INV-20241024-001                                                │
├────────────────────┬─────────────┬──────────────┬──────────────────────┤
│ Description        │ Qty (Hours) │ Unit Price   │ Total Amount         │
├────────────────────┼─────────────┼──────────────┼──────────────────────┤
│ Web Development    │ 40.00       │ 85.00 EUR    │ 3,400.00 EUR         │
│   (Time entries)   │             │              │                      │
├────────────────────┼─────────────┼──────────────┼──────────────────────┤
│ SSL Certificate    │ 1.00        │ 89.00 EUR    │ 89.00 EUR            │
│   Wildcard SSL     │             │              │                      │
│   SKU: SSL-001     │             │              │                      │
│   Category: Service│             │              │                      │
├────────────────────┼─────────────┼──────────────┼──────────────────────┤
│ Server Credits     │ 12.00       │ 50.00 EUR    │ 600.00 EUR           │
│   Category: Service│             │              │                      │
├────────────────────┴─────────────┴──────────────┼──────────────────────┤
│                                     Subtotal:   │ 4,089.00 EUR         │
│                                     Tax (20%):  │ 817.80 EUR           │
│                                     Total:      │ 4,906.80 EUR         │
└─────────────────────────────────────────────────┴──────────────────────┘
```

## API Integration

### REST API Endpoints

Extra goods are automatically included when using invoice API endpoints:

```bash
# Generate and download invoice PDF
GET /invoices/{invoice_id}/pdf

# Response: PDF file with extra goods included
Content-Type: application/pdf
Content-Disposition: attachment; filename="invoice-{number}.pdf"
```

### Custom Templates

**Recommended: use `invoice.all_line_items`** for the items table in custom JSON templates (e.g. in the PDF Designer). The **Items Table** element in the PDF Designer (Admin > PDF Layout) uses this data source by default. This single list contains time-based items, extra goods, and expenses in one combined table, so all line types appear in the PDF. The default template and Items Table element use this.

**Backward compatibility:** Templates that use `invoice.items` for the table data source are still supported. The PDF generator automatically appends extra goods and expenses to the table when it detects `invoice.items`, so all line types are included in the exported PDF.

The admin PDF Designer preview now uses the same data: it resolves the table’s data source (e.g. `invoice.all_line_items` or `invoice.items`) and shows the same rows in the preview as in the exported PDF.

You can also loop over extra goods explicitly in HTML/Jinja templates:

```jinja2
{% for good in invoice.extra_goods %}
<tr>
    <td>
        {{ good.name }}
        {% if good.description %}
            <br><small>{{ good.description }}</small>
        {% endif %}
        {% if good.sku %}
            <br><small>SKU: {{ good.sku }}</small>
        {% endif %}
    </td>
    <td>{{ good.quantity }}</td>
    <td>{{ format_money(good.unit_price) }}</td>
    <td>{{ format_money(good.total_amount) }}</td>
</tr>
{% endfor %}
```

## Benefits

### For Users

- **Comprehensive Billing**: Include both time-based and product-based charges in one invoice
- **Professional Presentation**: Goods display with full details (SKU, category, description)
- **Accurate Totals**: All goods automatically included in invoice calculations
- **Flexibility**: Mix time entries and products/services as needed

### For Developers

- **Clean Code**: Minimal changes, leveraging existing structures
- **Full Test Coverage**: Unit and smoke tests ensure reliability
- **Backward Compatible**: Existing invoices without goods still work perfectly
- **Easy to Extend**: Simple to add more good attributes in the future

## Troubleshooting

### Common Issues

**Issue**: Extra goods (or other line items) not appearing in PDF
- **Solution**: Use `invoice.all_line_items` as the table data source in the PDF Designer so the table includes items, extra goods, and expenses. If you use a custom template with `invoice.items`, the generator now appends extra goods and expenses automatically.
- **Solution**: Ensure goods are associated with `invoice_id` correctly
- **Check**: Run `invoice.extra_goods` to verify goods are linked

**Issue**: Totals don't include goods
- **Solution**: Call `invoice.calculate_totals()` after adding goods
- **Check**: Verify `invoice.subtotal` includes good amounts

**Issue**: PDF generation fails with goods
- **Solution**: Check that all required good fields are populated (name, quantity, unit_price)
- **Check**: Review test cases for proper good creation examples

## Future Enhancements

Potential improvements for future versions:

1. **Good Images**: Display product images in PDFs
2. **Grouped Display**: Option to group goods by category
3. **Discount Support**: Apply discounts to individual goods
4. **Tax Per Item**: Different tax rates for different goods
5. **Inventory Integration**: Link goods to inventory management
6. **Localization**: Translate good categories and labels

## Related Documentation

- [Invoice System Overview](ENHANCED_INVOICE_SYSTEM_README.md)
- [Extra Goods Model](../app/models/extra_good.py)
- [PDF Generation Utilities](../app/utils/pdf_generator.py)
- [Testing Guide](../tests/README.md)

## Changelog

### Version 1.0.0 (2024-10-24)

**Added:**
- Extra goods support in PDF export (WeasyPrint)
- Extra goods support in fallback PDF export (ReportLab)
- Rich formatting for good details (name, description, SKU, category)
- 6 comprehensive unit and smoke tests
- Documentation for feature usage

**Modified:**
- `app/utils/pdf_generator.py` - Enhanced `_generate_items_rows()`
- `app/templates/invoices/pdf_default.html` - Added extra goods rendering
- `app/utils/pdf_generator_fallback.py` - Enhanced `_build_items_table()`
- `tests/test_invoices.py` - Added extra goods test suite

**Technical Notes:**
- No database migrations required (extra_goods table already exists)
- No breaking changes to existing functionality
- Backward compatible with all existing invoices

## Support

For issues, questions, or feature requests related to extra goods in invoice PDFs:

1. Check existing documentation
2. Review test cases for usage examples
3. Verify good model fields are correctly populated
4. Ensure invoice totals are recalculated after adding goods

---

**Last Updated**: October 24, 2024  
**Author**: TimeTracker Development Team  
**Version**: 1.0.0

