# Payment Tracking Feature

## Overview

The Payment Tracking feature provides comprehensive payment management capabilities for invoices in the TimeTracker application. It allows users to record, track, and manage payments received against invoices, including support for partial payments, multiple payment methods, payment gateways, and detailed payment history.

## Features

### Core Functionality

- **Payment Recording**: Record payments against invoices with detailed information
- **Multiple Payment Methods**: Support for various payment methods (bank transfer, cash, check, credit card, PayPal, Stripe, etc.)
- **Payment Status Tracking**: Track payment status (completed, pending, failed, refunded)
- **Partial Payments**: Support for multiple partial payments against a single invoice
- **Payment Gateway Integration**: Track gateway transaction IDs and processing fees
- **Payment History**: View complete payment history for each invoice
- **Filtering and Search**: Filter payments by status, method, date range, and invoice
- **Payment Statistics**: View payment statistics and analytics

### Payment Model Fields

The Payment model includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| invoice_id | Integer | Foreign key to invoice |
| amount | Decimal(10,2) | Payment amount |
| currency | String(3) | Currency code (e.g., EUR, USD) |
| payment_date | Date | Date payment was received |
| method | String(50) | Payment method |
| reference | String(100) | Transaction reference or check number |
| notes | Text | Additional payment notes |
| status | String(20) | Payment status (completed, pending, failed, refunded) |
| received_by | Integer | User who recorded the payment |
| gateway_transaction_id | String(255) | Payment gateway transaction ID |
| gateway_fee | Decimal(10,2) | Gateway processing fee |
| net_amount | Decimal(10,2) | Net amount after fees |
| created_at | DateTime | Payment record creation timestamp |
| updated_at | DateTime | Last update timestamp |

## Usage

### Recording a Payment

1. Navigate to **Payments** → **Record Payment** or click **Record Payment** on an invoice
2. Select the invoice (if not pre-selected)
3. Enter payment details:
   - **Amount**: Payment amount received
   - **Currency**: Currency code (defaults to invoice currency)
   - **Payment Date**: Date payment was received
   - **Payment Method**: Select from available methods
   - **Status**: Payment status (default: completed)
   - **Reference**: Transaction ID, check number, etc.
   - **Gateway Transaction ID**: For payment gateway transactions
   - **Gateway Fee**: Processing fee charged by gateway
   - **Notes**: Additional information
4. Click **Record Payment**

### Viewing Payments

#### Payment List View

Navigate to **Payments** to see all payments. The list view includes:

- Summary cards showing:
  - Total number of payments
  - Total payment amount
  - Completed payments count and amount
  - Total gateway fees
- Filterable table with:
  - Payment ID
  - Invoice number (clickable)
  - Amount and currency
  - Payment date
  - Payment method
  - Status badge
  - Actions (View, Edit)

#### Individual Payment View

Click on a payment to view detailed information including:

- Payment amount and status
- Payment date and method
- Reference and transaction IDs
- Gateway fee and net amount
- Received by information
- Related invoice details
- Creation and update timestamps
- Notes

### Editing a Payment

1. Navigate to the payment detail view
2. Click **Edit Payment**
3. Update the desired fields
4. Click **Update Payment**

**Note**: Editing a payment will automatically update the invoice's payment status and outstanding amount.

### Deleting a Payment

1. Navigate to the payment detail view
2. Click **Delete Payment**
3. Confirm the deletion

**Note**: Deleting a payment will automatically adjust the invoice's payment status and outstanding amount.

### Filtering Payments

Use the filters on the payment list page to narrow down results:

- **Status**: Filter by payment status
- **Payment Method**: Filter by payment method
- **Date Range**: Filter by payment date range (from/to)
- **Invoice**: View payments for a specific invoice

### Invoice Integration

#### Payment History on Invoice

Each invoice view now includes a Payment History section showing:

- List of all payments made against the invoice
- Payment date, amount, method, reference, and status
- Total amount paid
- Outstanding amount
- Quick link to add new payment

#### Payment Status on Invoice

Invoices display:

- **Total Amount**: Invoice total
- **Amount Paid**: Sum of completed payments
- **Outstanding Amount**: Remaining balance
- **Payment Status**: Badge showing payment status (unpaid, partially paid, fully paid)

## Payment Methods

Supported payment methods include:

- Bank Transfer
- Cash
- Check
- Credit Card
- Debit Card
- PayPal
- Stripe
- Wire Transfer
- Other

## Payment Statuses

### Completed
Payment has been successfully received and processed.

### Pending
Payment is awaiting confirmation or processing.

### Failed
Payment attempt failed or was declined.

### Refunded
Payment was refunded to the customer.

## API Endpoints

### List Payments
```
GET /payments
```
Query parameters:
- `status`: Filter by status
- `method`: Filter by payment method
- `date_from`: Filter by start date
- `date_to`: Filter by end date
- `invoice_id`: Filter by invoice

### View Payment
```
GET /payments/<payment_id>
```

### Create Payment
```
GET /payments/create
POST /payments/create
```

Form data:
- `invoice_id` (required)
- `amount` (required)
- `currency`
- `payment_date` (required)
- `method`
- `reference`
- `status`
- `gateway_transaction_id`
- `gateway_fee`
- `notes`

### Edit Payment
```
GET /payments/<payment_id>/edit
POST /payments/<payment_id>/edit
```

### Delete Payment
```
POST /payments/<payment_id>/delete
```

### Payment Statistics
```
GET /api/payments/stats
```
Query parameters:
- `date_from`: Start date for statistics
- `date_to`: End date for statistics

Returns JSON with:
- Total payments count and amount
- Total fees and net amount
- Breakdown by payment method
- Breakdown by status
- Monthly statistics

## Database Schema

### Payments Table

```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3),
    payment_date DATE NOT NULL,
    method VARCHAR(50),
    reference VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    received_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    gateway_transaction_id VARCHAR(255),
    gateway_fee NUMERIC(10, 2),
    net_amount NUMERIC(10, 2),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX ix_payments_invoice_id ON payments(invoice_id);
CREATE INDEX ix_payments_payment_date ON payments(payment_date);
CREATE INDEX ix_payments_status ON payments(status);
CREATE INDEX ix_payments_received_by ON payments(received_by);
```

## Migration

The payment tracking feature includes an Alembic migration (`035_enhance_payments_table.py`) that:

1. Creates the payments table if it doesn't exist
2. Adds enhanced tracking fields (status, received_by, gateway fields)
3. Creates necessary indexes for performance
4. Sets up foreign key relationships

To apply the migration:

```bash
# Using Alembic
alembic upgrade head

# Or using Flask-Migrate
flask db upgrade
```

## Best Practices

### Recording Payments

1. **Record payments promptly**: Keep payment records up-to-date
2. **Use reference numbers**: Always include transaction IDs or check numbers
3. **Document gateway fees**: Record processing fees for accurate accounting
4. **Add notes**: Include any relevant context or special circumstances
5. **Verify amounts**: Double-check payment amounts match actual receipts

### Payment Status Management

1. **Pending payments**: Use for payments awaiting clearance
2. **Failed payments**: Record failed attempts for tracking
3. **Refunds**: Use refunded status and create negative payments if needed
4. **Partial payments**: Record each payment separately for clear audit trail

### Security and Permissions

1. Regular users can only manage payments for their own invoices
2. Admins can manage all payments
3. Payment deletion adjusts invoice status automatically
4. All payment actions are logged with user information

## Troubleshooting

### Payment Not Updating Invoice Status

- Ensure payment status is set to "completed"
- Verify invoice ID is correct
- Check that payment amount is valid
- Refresh the invoice page to see updates

### Gateway Fee Not Calculating

- Ensure gateway fee field is populated
- Payment model automatically calculates net amount
- Call `calculate_net_amount()` method if needed

### Missing Payment Methods

- Payment methods can be customized in the route handler
- Add new methods to the dropdown in create/edit templates
- Methods are stored as strings in the database

## Testing

The payment tracking feature includes comprehensive tests:

### Unit Tests (`tests/test_payment_model.py`)
- Payment model creation and validation
- Net amount calculation
- Payment-invoice relationships
- Payment-user relationships
- Multiple payments per invoice
- Status handling

### Route Tests (`tests/test_payment_routes.py`)
- All CRUD operations
- Access control and permissions
- Filtering and searching
- Invalid input handling
- Payment statistics API

### Smoke Tests (`tests/test_payment_smoke.py`)
- Basic functionality verification
- Template existence
- Database schema
- End-to-end workflow
- Integration with invoices

Run tests with:

```bash
# All payment tests
pytest tests/test_payment*.py

# Specific test file
pytest tests/test_payment_model.py -v

# Smoke tests only
pytest tests/test_payment_smoke.py -v
```

## Future Enhancements

Potential improvements for future versions:

1. **Payment Reminders**: Automated reminders for overdue invoices
2. **Payment Plans**: Support for installment payment schedules
3. **Recurring Payments**: Automatic payment processing for recurring invoices
4. **Payment Export**: Export payment history to CSV/Excel
5. **Payment Reconciliation**: Bank statement matching and reconciliation
6. **Multi-Currency**: Enhanced multi-currency support with exchange rates
7. **Payment Gateway Integration**: Direct integration with payment processors
8. **Payment Notifications**: Email notifications for payment receipt
9. **Payment Reports**: Advanced reporting and analytics
10. **Bulk Payment Import**: Import payments from CSV/Excel

## Related Features

- **Invoices**: Core invoicing functionality
- **Clients**: Client management and billing
- **Reports**: Financial reporting including payment analytics
- **Analytics**: Payment trends and statistics

## Support

For issues or questions about payment tracking:

1. Check this documentation
2. Review the test files for usage examples
3. Check the application logs for error messages
4. Consult the TimeTracker documentation

## Changelog

### Version 1.0 (2025-10-27)

Initial release of Payment Tracking feature:

- Complete payment CRUD operations
- Multiple payment methods support
- Payment status tracking
- Gateway integration support
- Payment filtering and search
- Invoice integration
- Comprehensive test coverage
- Full documentation

