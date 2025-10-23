# Extra Goods Feature

## Overview

The Extra Goods feature allows you to add physical products, services, materials, licenses, and other billable items to both projects and invoices. This extends the time-tracking functionality to support full product and service billing.

## Features

### Core Functionality

- **Add extra goods to projects**: Track products and services associated with a project
- **Add extra goods to invoices**: Include products and services directly on invoices
- **Multiple categories**: Organize goods as products, services, materials, licenses, or other
- **Flexible pricing**: Set quantity and unit price with automatic total calculation
- **SKU/Product codes**: Track items with unique identifiers
- **Billable/Non-billable**: Mark items as billable or non-billable
- **Multi-currency support**: Each good can have its own currency code

### Integration

- **Invoice generation**: Automatically include project extra goods when generating invoices from time entries
- **Cost tracking**: Extra goods work alongside project costs for comprehensive billing
- **Reporting**: Goods are included in project totals and invoice calculations

## Data Model

### ExtraGood Model

```python
class ExtraGood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Links (can be associated with project, invoice, or both)
    project_id = db.Column(db.Integer, nullable=True)
    invoice_id = db.Column(db.Integer, nullable=True)
    
    # Good details
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    
    # Pricing
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Billing
    billable = db.Column(db.Boolean, default=True, nullable=False)
    sku = db.Column(db.String(100), nullable=True)
    
    # Metadata
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
```

### Categories

- **product**: Physical or digital products
- **service**: Additional services beyond time-tracked work
- **material**: Materials and supplies used in the project
- **license**: Software licenses, permits, or other licenses
- **other**: Any other type of good or service

## Usage

### Adding Extra Goods to a Project

1. Navigate to the project view page
2. Click "Add Extra Good" or navigate to `/projects/<id>/goods/add`
3. Fill in the form:
   - Name (required)
   - Description (optional)
   - Category (required)
   - SKU/Product Code (optional)
   - Quantity (required, default: 1)
   - Unit Price (required)
   - Currency (default: EUR)
   - Billable checkbox (default: checked)
4. Click "Add Good"

### Adding Extra Goods to an Invoice

#### Method 1: Direct Addition

1. Navigate to invoice edit page
2. In the "Extra Goods" section, click "Add Good"
3. Fill in the good details inline:
   - Name
   - Description
   - Category
   - Quantity
   - Unit Price
   - SKU (optional)
4. Click "Save Changes"

#### Method 2: Generate from Project

1. Navigate to invoice edit page
2. Click "Generate from Time/Costs/Goods"
3. Select extra goods from the project
4. Click "Add Selected to Invoice"
5. Project goods will be copied to the invoice

### Managing Extra Goods

#### Editing

- For project goods: Navigate to `/projects/<id>/goods/<good_id>/edit`
- For invoice goods: Edit directly in the invoice edit form

#### Deleting

- Project goods can only be deleted if not yet added to an invoice
- Invoice goods are deleted when you remove them from the invoice edit form

#### Viewing

- Project goods list: `/projects/<id>/goods`
- Invoice goods: Displayed on invoice view and edit pages

## API Endpoints

### Project Extra Goods

- `GET /projects/<id>/goods` - List all goods for a project
- `POST /projects/<id>/goods/add` - Add a new good to a project
- `GET /projects/<id>/goods/<good_id>/edit` - Edit form
- `POST /projects/<id>/goods/<good_id>/edit` - Update a good
- `POST /projects/<id>/goods/<good_id>/delete` - Delete a good
- `GET /api/projects/<id>/goods` - JSON API for project goods

### Invoice Extra Goods

Extra goods for invoices are managed through the invoice edit form:
- `GET /invoices/<id>/edit` - Shows invoice with extra goods
- `POST /invoices/<id>/edit` - Updates invoice including extra goods

## Database Migration

The extra goods feature requires database migration `021_add_extra_goods_table.py`.

To apply the migration:

```bash
# Using Alembic
alembic upgrade head

# Or using Flask-Migrate
flask db upgrade
```

## Calculations

### Invoice Totals

When calculating invoice totals, extra goods are included:

```python
items_total = sum(item.total_amount for item in invoice.items)
goods_total = sum(good.total_amount for good in invoice.extra_goods)
subtotal = items_total + goods_total
tax_amount = subtotal * (tax_rate / 100)
total_amount = subtotal + tax_amount
```

### Project Value

Extra goods contribute to the total project value:

```python
total_value = (billable_hours * hourly_rate) + billable_costs + billable_extra_goods
```

## Best Practices

1. **Use SKU codes**: For recurring products, use SKU codes for easy identification
2. **Categorize correctly**: Choose the appropriate category for easier reporting
3. **Set billable flag**: Mark non-billable items appropriately to exclude from client billing
4. **Link to projects first**: Add goods to projects, then include them in invoices for better tracking
5. **Update totals**: The system automatically updates totals, but verify before sending invoices

## Permissions

- **Admin users**: Full access to create, edit, and delete extra goods
- **Regular users**: Can add goods they created; cannot delete goods added to invoices

## Reporting and Analytics

Extra goods data is available for:
- Project cost tracking and budgeting
- Invoice generation and billing
- Category-based analysis
- Client billing summaries

## Troubleshooting

### Common Issues

**Good won't delete from project**
- Check if the good has been added to an invoice
- Goods added to invoices cannot be deleted from projects

**Total amount incorrect**
- The system auto-calculates `total_amount = quantity * unit_price`
- If you need to override, modify quantity or unit price

**Good not appearing on invoice**
- Ensure the good is marked as billable
- Check that `invoice_id` is not already set to another invoice
- Verify the good belongs to the project linked to the invoice

## Future Enhancements

Potential future improvements:
- Inventory tracking integration
- Automated pricing from product catalog
- Volume discounts
- Tax rules per product category
- Multi-unit conversions

## Support

For issues or questions about the extra goods feature:
1. Check the application logs for error details
2. Verify database migration is applied
3. Review the model tests in `tests/test_extra_good_model.py`
4. Check the route implementations in `app/routes/invoices.py` and `app/routes/projects.py`

