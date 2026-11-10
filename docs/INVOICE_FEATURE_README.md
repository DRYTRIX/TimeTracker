# Invoice Generation Feature - TimeTracker

## Overview

The Invoice Generation feature completes the billing workflow in TimeTracker by providing a comprehensive system for creating, managing, and tracking client invoices. This feature integrates seamlessly with the existing time tracking and project management systems to automate the billing process.

## Features

### 🧾 Core Invoice Management
- **Create Invoices**: Generate professional invoices for clients
- **Invoice Items**: Add line items with descriptions, quantities, and unit prices
- **Tax Calculation**: Automatic tax calculations with configurable rates
- **Status Tracking**: Track invoice status (draft, sent, paid, overdue, cancelled)
- **Unique Numbering**: Automatic invoice number generation (INV-YYYYMMDD-XXX format)

### ⏰ Time Integration
- **Generate from Time**: Automatically create invoice items from tracked time entries
- **Smart Grouping**: Group time entries by task or project for organized billing
- **Billing Prevention**: Prevent double-billing of time entries across invoices
- **Project Rates**: Use project hourly rates for automatic calculations

### 💰 Financial Features
- **Automatic Totals**: Real-time calculation of subtotals, tax, and final amounts
- **Currency Support**: Full currency support through system settings
- **Tax Management**: Configurable tax rates per invoice
- **Payment Tracking**: Monitor outstanding and overdue amounts

### 📊 Management & Reporting
- **Invoice Dashboard**: Overview of all invoices with summary statistics
- **Status Management**: Easy status updates and workflow management
- **Export Options**: CSV export for external accounting systems
- **Duplicate Invoices**: Create recurring invoices quickly
- **Search & Filter**: Find invoices by client, project, or status

## Database Schema

### Invoices Table
```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    project_id INTEGER REFERENCES projects(id),
    client_name VARCHAR(200) NOT NULL,
    client_email VARCHAR(200),
    client_address TEXT,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    notes TEXT,
    terms TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Invoice Items Table
```sql
CREATE TABLE invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id),
    description VARCHAR(500) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    time_entry_ids VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## User Interface

### Invoice List Page (`/invoices`)
- **Summary Cards**: Total invoices, amounts, outstanding, and overdue
- **Invoice Table**: Sortable list with status indicators and actions
- **Quick Actions**: Create, edit, view, and manage invoices
- **Status Management**: Update invoice status with one click

### Create Invoice (`/invoices/create`)
- **Project Selection**: Choose from billable projects
- **Client Information**: Enter client details and billing address
- **Invoice Settings**: Set due date, tax rate, notes, and terms
- **Auto-fill**: Client name automatically populated from project

### Edit Invoice (`/invoices/edit`)
- **Dynamic Line Items**: Add, remove, and edit invoice items
- **Real-time Calculations**: Automatic total updates as you type
- **Project Integration**: Use project hourly rates for items
- **Time Generation**: Generate items from time entries

### View Invoice (`/invoices/view`)
- **Professional Layout**: Clean, printable invoice format
- **Status Actions**: Change status, generate from time, export
- **Item Details**: View all line items with time entry references
- **Financial Summary**: Clear breakdown of totals and tax

### Generate from Time (`/invoices/generate-from-time`)
- **Time Entry Selection**: Choose which time entries to bill
- **Smart Grouping**: Automatic grouping by task or project
- **Preview Totals**: See estimated amounts before generation
- **Billing Prevention**: Avoid double-billing of time entries

## API Endpoints

### Invoice Management
- `GET /invoices` - List all invoices
- `POST /invoices/create` - Create new invoice
- `GET /invoices/<id>` - View invoice details
- `POST /invoices/<id>/edit` - Edit invoice
- `POST /invoices/<id>/delete` - Delete invoice
- `POST /invoices/<id>/status` - Update invoice status

### Time Integration
- `GET /invoices/<id>/generate-from-time` - Show time entry selection
- `POST /invoices/<id>/generate-from-time` - Generate items from time

### Export & Utilities
- `GET /invoices/<id>/export/csv` - Export invoice as CSV
- `GET /invoices/<id>/duplicate` - Duplicate existing invoice

## Workflow

### 1. Create Invoice
1. Navigate to Invoices → Create Invoice
2. Select project and set client details
3. Configure due date, tax rate, and terms
4. Save invoice (creates draft status)

### 2. Generate Items from Time
1. Open draft invoice
2. Click "Generate from Time Entries"
3. Select time entries to include
4. Review grouped items and totals
5. Generate invoice items

### 3. Customize & Review
1. Edit invoice details and line items
2. Adjust quantities, descriptions, or prices
3. Add manual line items if needed
4. Review totals and calculations

### 4. Send & Track
1. Update status to "Sent"
2. Monitor payment status
3. Update to "Paid" when received
4. Track overdue invoices automatically

## Integration Points

### With Existing Features
- **Projects**: Uses project hourly rates and client information
- **Time Tracking**: Integrates with time entries for billing
- **Tasks**: Groups time by tasks when available
- **User Management**: Tracks who created each invoice
- **Settings**: Uses system currency and timezone settings

### Data Flow
```
Time Entries → Invoice Generation → Invoice Items → Totals Calculation → Invoice
     ↓              ↓                    ↓              ↓              ↓
  Billable      Group by Task      Line Items      Tax & Total    Status Tracking
  Hours         or Project         with Rates      Calculation    & Management
```

## Security & Permissions

### Access Control
- **Regular Users**: Can create and manage their own invoices
- **Admin Users**: Can view and manage all invoices
- **Project Access**: Users can only invoice projects they have access to

### Data Validation
- **Required Fields**: Invoice number, project, client, due date
- **Numeric Validation**: Hours, rates, and amounts
- **Date Validation**: Due dates must be in the future
- **Unique Constraints**: Invoice numbers must be unique

## Configuration

### System Settings
- **Currency**: Set in system settings (default: EUR)
- **Timezone**: Affects date displays and calculations
- **Rounding**: Time rounding for billing accuracy

### Project Settings
- **Hourly Rate**: Set per project for automatic calculations
- **Billable Flag**: Only billable projects can have invoices
- **Billing Reference**: Optional reference for external systems

## Testing

### Test Coverage
- **Model Tests**: Invoice and InvoiceItem creation and validation
- **Calculation Tests**: Tax and total calculations
- **Integration Tests**: Time entry to invoice generation
- **Permission Tests**: User access control

### Running Tests
```bash
# Run all invoice tests
pytest tests/test_invoices.py -v

# Run specific test
pytest tests/test_invoices.py::test_invoice_creation -v
```

## Deployment

### Database Migration
The invoice tables are automatically created when the application starts. For existing installations:

1. **Automatic**: Tables created on first run
2. **Manual**: Run database initialization script
3. **Migration**: Use Flask-Migrate for schema updates

### Dependencies
- **Core**: Flask, SQLAlchemy (already included)
- **Database**: PostgreSQL/SQLite (already supported)
- **Frontend**: Bootstrap 5, Font Awesome (already included)

## Recurring invoices and overdue reminders

Automated recurring billing and past-due detection are implemented. See **[Invoice reminders and recurring](features/INVOICE_REMINDERS_AND_RECURRING.md)** for scheduler times, flows, and limitations (one-shot overdue notify; no fixed subscription line items on recurring templates).

## Future Enhancements

### Planned Features
- Configurable multi-step payment / dunning reminders (`InvoiceReminderSchedule` schema exists but is unused)
- Fixed line items on recurring invoice templates (today: unbilled time only)
- Deeper payment gateway and installment workflows (see [Payment tracking](PAYMENT_TRACKING.md))

### API Extensions
- **Webhook Support**: Emit `invoice.overdue` when the overdue job runs (documented in places; not emitted today)
- **Bulk Operations**: Mass invoice operations
- **Reporting API**: Invoice analytics and reporting

## Troubleshooting

### Common Issues
1. **Invoice Numbers**: Ensure unique invoice numbers
2. **Time Entry Billing**: Check for already-billed entries
3. **Calculations**: Verify tax rates and rounding
4. **Permissions**: Check user access to projects

### Debug Information
- **Logs**: Check application logs for errors
- **Database**: Verify table structure and data integrity
- **Permissions**: Confirm user roles and project access

## Support

### Documentation
- **User Guide**: In-app help and tooltips
- **API Reference**: Endpoint documentation
- **Code Comments**: Inline code documentation

### Community
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Community support and ideas
- **Contributing**: Guidelines for code contributions

---

**Note**: This feature completes the billing workflow by providing a professional invoice system that integrates seamlessly with TimeTracker's existing time tracking and project management capabilities.
