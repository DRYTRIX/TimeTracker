# Invoice Expenses Feature

## Overview

The TimeTracker application now supports adding expenses to invoices. This feature allows you to track billable expenses such as travel, meals, accommodation, and other project-related costs, and include them directly in client invoices.

## Key Features

- **Link expenses to invoices**: Associate billable expenses with specific invoices
- **Automatic total calculation**: Expenses are automatically included in invoice subtotals and tax calculations
- **Multiple expense categories**: Support for travel, meals, accommodation, supplies, software, equipment, services, marketing, training, and other categories
- **Expense tracking**: Track vendor information, receipts, dates, and detailed descriptions
- **PDF and CSV export**: Expenses are included in invoice PDF and CSV exports
- **Flexible workflow**: Add expenses during invoice creation or edit existing invoices to add/remove expenses

## How It Works

### 1. Creating Billable Expenses

Expenses must be created and marked as billable before they can be added to invoices. To create a billable expense:

1. Navigate to the Expenses section
2. Click "Add Expense"
3. Fill in the expense details:
   - **Title**: Short description (e.g., "Travel to Client Meeting")
   - **Description**: Detailed information about the expense
   - **Category**: Select from available categories (travel, meals, accommodation, etc.)
   - **Amount**: The expense amount (excluding tax)
   - **Tax Amount**: If applicable, the tax amount
   - **Date**: When the expense was incurred
   - **Vendor**: Who you paid (optional)
   - **Billable**: Check this box to make the expense available for invoicing
4. Save the expense

### 2. Adding Expenses to Invoices

There are two ways to add expenses to invoices:

#### Method 1: Generate from Time, Costs & Goods

1. Open an existing invoice or create a new one
2. Click "Generate from Time/Costs" in the Quick Actions panel
3. In the "Uninvoiced Billable Expenses" section, select the expenses you want to add
4. You can also select time entries, project costs, and extra goods at the same time
5. Click "Add Selected to Invoice"

The selected expenses will be linked to the invoice and appear in the Expenses section.

#### Method 2: Direct Edit

1. Open an invoice in edit mode
2. Navigate to the "Expenses" section
3. Click "Add Expense" to go to the Generate from Time/Costs page
4. Alternatively, expenses can be managed through the invoice edit form

### 3. Viewing Expenses on Invoices

Expenses appear in several places:

**Invoice Edit View**:
- Expenses section shows all linked expenses
- Read-only fields display expense details
- Unlink button to remove expenses from the invoice

**Invoice View**:
- Dedicated "Expenses" table showing:
  - Title
  - Description
  - Category
  - Date
  - Vendor
  - Amount

**Live Preview Panel**:
- Shows expense count and total
- Updates in real-time as you add/remove expenses

### 4. Invoice Calculations

Expenses affect invoice totals as follows:

1. **Subtotal**: Sum of all items + expenses + extra goods
2. **Tax**: Applied to the subtotal (including expenses)
3. **Total**: Subtotal + Tax

Example:
```
Items:          $1,000.00
Expenses:       $  165.00  (includes $15 expense tax)
Goods:          $  500.00
----------------------------
Subtotal:       $1,665.00
Tax (10%):      $  166.50
----------------------------
Total:          $1,831.50
```

### 5. Unlinking Expenses

To remove an expense from an invoice:

1. Open the invoice in edit mode
2. Find the expense in the Expenses section
3. Click the "Unlink" button (shows an unlink icon)
4. Confirm the action
5. Save the invoice

**Note**: Unlinking an expense does NOT delete it; it simply removes the association with the invoice. The expense will become available for other invoices again.

## Expense States

Expenses can be in the following states:

- **Pending**: Waiting for approval
- **Approved**: Approved and ready for invoicing (if billable)
- **Rejected**: Not approved
- **Reimbursed**: Already paid back to the employee
- **Invoiced**: Linked to a client invoice

Only **approved, billable, and uninvoiced** expenses can be added to invoices.

## PDF and CSV Exports

### PDF Export

Expenses are displayed in the invoice PDF with the following information:
- Expense title
- Description (if available)
- Category
- Vendor (if available)
- Date
- Total amount (including tax)

### CSV Export

Expenses are included in invoice CSV exports with:
- Title with category in parentheses
- Quantity: 1
- Unit price: Total expense amount
- Total: Total expense amount

## API Integration

If you're using the TimeTracker API, you can work with expenses through the following endpoints:

- `GET /api/expenses` - Get all expenses
- `POST /api/expenses` - Create a new expense
- `GET /api/expenses/{id}` - Get expense details
- `PUT /api/expenses/{id}` - Update an expense
- `DELETE /api/expenses/{id}` - Delete an expense
- `POST /api/expenses/{id}/mark-as-invoiced` - Link expense to invoice
- `POST /api/expenses/{id}/unmark-as-invoiced` - Unlink expense from invoice

## Database Schema

The expense-invoice relationship uses the following fields in the `expenses` table:

```sql
invoiced BOOLEAN DEFAULT FALSE          -- Whether the expense is linked to an invoice
invoice_id INTEGER                      -- Foreign key to invoices table
billable BOOLEAN DEFAULT FALSE          -- Whether the expense can be invoiced
```

The relationship is defined in the models as:
- `Invoice.expenses` - Dynamic relationship to get all expenses for an invoice
- `Expense.invoice` - Relationship to get the invoice for an expense

## Best Practices

1. **Mark expenses as billable**: Only expenses marked as billable will appear in the invoice generation interface
2. **Approve expenses first**: It's recommended to approve expenses before adding them to invoices
3. **Include detailed descriptions**: Add vendor and description information to help clients understand the charges
4. **Use appropriate categories**: Categorize expenses correctly for better reporting and clarity
5. **Track receipts**: Upload receipts for expenses to maintain proper documentation
6. **Review before finalizing**: Check the expense section in the live preview before sending invoices

## Troubleshooting

**Q: I don't see any expenses when generating from time/costs**

A: Ensure that:
- The expenses are marked as billable
- The expenses are approved
- The expenses are associated with the correct project
- The expenses haven't already been invoiced

**Q: The invoice total doesn't include my expense**

A: Make sure you've saved the invoice after adding the expense. The totals are recalculated when you save.

**Q: Can I edit expense details from the invoice?**

A: No, expense details are read-only when viewing them on an invoice. You must edit the expense directly from the Expenses section.

**Q: What happens if I delete an invoice with expenses?**

A: The expenses are automatically unlinked and become available for other invoices. The expenses themselves are not deleted.

## Future Enhancements

Potential future improvements to the expense feature:

- Bulk expense import
- Expense approval workflow integration
- Multi-currency expense support
- Expense templates
- Automated expense categorization
- Integration with accounting systems

## Related Documentation

- [Expense Management Guide](EXPENSE_MANAGEMENT.md)
- [Invoice Creation Guide](INVOICE_CREATION.md)
- [PDF Customization](PDF_LAYOUT_CUSTOMIZATION.md)
- [API Documentation](API_DOCUMENTATION.md)

