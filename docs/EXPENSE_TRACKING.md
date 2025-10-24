# Expense Tracking Feature

## Overview

The Expense Tracking feature allows users to record, manage, and track business expenses within the TimeTracker application. This comprehensive system includes expense creation, approval workflows, reimbursement tracking, and integration with projects, clients, and invoicing.

## Table of Contents

1. [Features](#features)
2. [User Roles and Permissions](#user-roles-and-permissions)
3. [Creating Expenses](#creating-expenses)
4. [Approval Workflow](#approval-workflow)
5. [Reimbursement Process](#reimbursement-process)
6. [Expense Categories](#expense-categories)
7. [Filtering and Search](#filtering-and-search)
8. [Export and Reporting](#export-and-reporting)
9. [Integration](#integration)
10. [API Endpoints](#api-endpoints)
11. [Database Schema](#database-schema)

## Features

### Core Features

- **Expense Recording**: Track expenses with detailed information including amount, category, vendor, and receipts
- **Multi-Currency Support**: Record expenses in different currencies (EUR, USD, GBP, CHF)
- **Tax Tracking**: Separate tax amount tracking for accurate financial reporting
- **Receipt Management**: Upload and attach receipt files to expenses
- **Approval Workflow**: Multi-stage approval process with admin oversight
- **Reimbursement Tracking**: Track which expenses have been reimbursed
- **Billable Expenses**: Mark expenses as billable to clients
- **Project/Client Association**: Link expenses to specific projects and clients
- **Tags and Notes**: Add tags and detailed notes for better organization
- **Dashboard Analytics**: Visual analytics and summaries of expense data
- **Export Functionality**: Export expense data to CSV format

### Advanced Features

- **Status Tracking**: Track expenses through pending, approved, rejected, and reimbursed states
- **Date Range Filtering**: Filter expenses by date ranges
- **Category Analytics**: View spending breakdown by category
- **Payment Method Tracking**: Record payment methods used for expenses
- **Bulk Operations**: Perform operations on multiple expenses efficiently
- **Integration with Invoicing**: Link billable expenses to client invoices

## User Roles and Permissions

### Regular Users

**Can:**
- Create new expenses
- View their own expenses
- Edit pending expenses they created
- Delete their own pending expenses
- Add receipts and documentation
- View expense status and approval information

**Cannot:**
- Approve or reject expenses
- Mark expenses as reimbursed
- View other users' expenses
- Edit approved or reimbursed expenses

### Admin Users

**Can:**
- All regular user permissions
- View all expenses from all users
- Approve or reject pending expenses
- Mark expenses as reimbursed
- Edit any expense regardless of status
- Delete any expense
- Access full expense analytics dashboard

## Creating Expenses

### Basic Expense Creation

1. Navigate to **Insights → Expenses** in the sidebar
2. Click **New Expense** button
3. Fill in required fields:
   - **Title**: Short description of the expense
   - **Category**: Select from predefined categories
   - **Amount**: Expense amount (excluding tax)
   - **Expense Date**: Date the expense was incurred

### Optional Fields

- **Description**: Detailed description of the expense
- **Tax Amount**: Separate tax amount
- **Currency**: Currency code (default: EUR)
- **Project**: Associate with a project
- **Client**: Associate with a client
- **Payment Method**: How the expense was paid
- **Payment Date**: When payment was made
- **Vendor**: Name of the vendor/supplier
- **Receipt Number**: Receipt or invoice number
- **Receipt File**: Upload receipt image or PDF
- **Tags**: Comma-separated tags for organization
- **Notes**: Additional notes
- **Billable**: Mark if expense should be billed to client
- **Reimbursable**: Mark if expense should be reimbursed

### Example: Creating a Travel Expense

```
Title: Flight to Berlin Client Meeting
Description: Round-trip flight for Q4 business review
Category: Travel
Amount: 450.00
Tax Amount: 45.00
Currency: EUR
Expense Date: 2025-10-20
Payment Method: Company Card
Vendor: Lufthansa
Project: [Select Project]
Client: [Select Client]
Billable: ✓ (checked)
Reimbursable: ✗ (unchecked)
Tags: travel, client-meeting, Q4
```

## Approval Workflow

### States

1. **Pending**: Newly created expense awaiting approval
2. **Approved**: Expense approved by admin
3. **Rejected**: Expense rejected with reason
4. **Reimbursed**: Approved expense that has been reimbursed

### Approval Process

#### For Users:
1. Create expense with all required information
2. Submit expense (automatically set to "Pending" status)
3. Wait for admin review
4. Receive notification of approval or rejection
5. If approved and reimbursable, wait for reimbursement

#### For Admins:
1. Navigate to expense list
2. Filter by status: "Pending"
3. Click on expense to view details
4. Review all information, receipts, and documentation
5. Choose action:
   - **Approve**: Approves the expense (optionally add approval notes)
   - **Reject**: Rejects the expense (must provide rejection reason)

### Rejection Reasons

When rejecting an expense, admins must provide a clear reason:
- Missing or invalid receipt
- Expense not covered by company policy
- Incorrect category
- Amount exceeds limit
- Duplicate expense
- Other (with explanation)

## Reimbursement Process

### For Reimbursable Expenses

1. User creates expense and marks it as "Reimbursable"
2. Admin approves the expense
3. Finance processes reimbursement outside the system
4. Admin marks expense as "Reimbursed" in the system
5. Expense status changes to "Reimbursed" with timestamp

### Tracking Reimbursements

- Dashboard shows count of pending reimbursements
- Filter expenses by reimbursement status
- View reimbursement date and details
- Export reimbursement reports

## Expense Categories

The system provides predefined expense categories:

- **Travel**: Flights, trains, taxis, car rentals
- **Meals**: Business meals, client entertainment
- **Accommodation**: Hotels, short-term rentals
- **Supplies**: Office supplies, materials
- **Software**: Software licenses, subscriptions
- **Equipment**: Hardware, tools, equipment purchases
- **Services**: Professional services, consultants
- **Marketing**: Advertising, promotional materials
- **Training**: Courses, conferences, professional development
- **Other**: Miscellaneous expenses

### Category Analytics

View spending breakdown by category:
- Total amount per category
- Number of expenses per category
- Percentage of total spending
- Trend analysis over time

## Filtering and Search

### Available Filters

- **Search**: Search by title, vendor, notes, or description
- **Status**: Filter by approval status (pending, approved, rejected, reimbursed)
- **Category**: Filter by expense category
- **Project**: Filter by associated project
- **Client**: Filter by associated client
- **User**: (Admin only) Filter by user who created expense
- **Date Range**: Filter by expense date range
- **Billable**: Filter billable/non-billable expenses
- **Reimbursable**: Filter reimbursable/non-reimbursable expenses

### Search Examples

```
Search: "conference"
Status: Approved
Category: Travel
Date Range: 2025-01-01 to 2025-03-31
Billable: Yes
```

## Export and Reporting

### CSV Export

Export filtered expenses to CSV format including:
- Date
- Title
- Category
- Amount
- Tax
- Total
- Currency
- Status
- Vendor
- Payment Method
- Project
- Client
- User
- Billable flag
- Reimbursable flag
- Invoiced flag
- Receipt number
- Notes

### Dashboard Analytics

The expense dashboard provides:
- Total expense count and amount for date range
- Pending approval count
- Pending reimbursement count
- Status breakdown (pending, approved, rejected, reimbursed)
- Category breakdown with amounts
- Recent expenses list
- Visual charts and graphs

### Accessing the Dashboard

1. Navigate to **Insights → Expenses**
2. Click **View Dashboard** in the summary card
3. Adjust date range as needed
4. View analytics and statistics

## Integration

### With Projects

- Associate expenses with specific projects
- View project-specific expense totals
- Include expenses in project cost analysis
- Track billable vs. non-billable project expenses

### With Clients

- Link expenses to client accounts
- Generate client-specific expense reports
- Include billable expenses in client invoices
- Track client-related spending

### With Invoicing

- Mark expenses as billable to clients
- Track which expenses have been invoiced
- Link expenses to specific invoices
- Automatically include billable expenses in invoice generation

## API Endpoints

### List Expenses

```
GET /api/expenses
Query Parameters:
  - status: Filter by status
  - category: Filter by category
  - project_id: Filter by project
  - start_date: Start date (YYYY-MM-DD)
  - end_date: End date (YYYY-MM-DD)

Response:
{
  "expenses": [...],
  "count": 10
}
```

### Get Single Expense

```
GET /api/expenses/<expense_id>

Response:
{
  "id": 1,
  "title": "Travel Expense",
  "category": "travel",
  "amount": 150.00,
  ...
}
```

### Create Expense (via Web Form)

```
POST /expenses/create
Form Data:
  - title: string (required)
  - category: string (required)
  - amount: decimal (required)
  - expense_date: date (required)
  - [additional optional fields]
```

### Approve Expense

```
POST /expenses/<expense_id>/approve
Form Data:
  - approval_notes: string (optional)
```

### Reject Expense

```
POST /expenses/<expense_id>/reject
Form Data:
  - rejection_reason: string (required)
```

### Mark as Reimbursed

```
POST /expenses/<expense_id>/reimburse
```

## Database Schema

### Expenses Table

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    client_id INTEGER,
    
    -- Expense details
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
    tax_amount NUMERIC(10, 2),
    tax_rate NUMERIC(5, 2),
    
    -- Payment information
    payment_method VARCHAR(50),
    payment_date DATE,
    
    -- Status and approval
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by INTEGER,
    approved_at DATETIME,
    rejection_reason TEXT,
    
    -- Billing and invoicing
    billable BOOLEAN NOT NULL DEFAULT 0,
    reimbursable BOOLEAN NOT NULL DEFAULT 1,
    invoiced BOOLEAN NOT NULL DEFAULT 0,
    invoice_id INTEGER,
    reimbursed BOOLEAN NOT NULL DEFAULT 0,
    reimbursed_at DATETIME,
    
    -- Date and metadata
    expense_date DATE NOT NULL,
    receipt_path VARCHAR(500),
    receipt_number VARCHAR(100),
    vendor VARCHAR(200),
    notes TEXT,
    tags VARCHAR(500),
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX ix_expenses_user_id ON expenses(user_id);
CREATE INDEX ix_expenses_project_id ON expenses(project_id);
CREATE INDEX ix_expenses_client_id ON expenses(client_id);
CREATE INDEX ix_expenses_expense_date ON expenses(expense_date);
CREATE INDEX ix_expenses_user_date ON expenses(user_id, expense_date);
CREATE INDEX ix_expenses_status_date ON expenses(status, expense_date);
CREATE INDEX ix_expenses_project_date ON expenses(project_id, expense_date);
```

## Best Practices

### For Users

1. **Be Detailed**: Provide clear titles and descriptions
2. **Attach Receipts**: Always upload receipt documentation
3. **Timely Submission**: Submit expenses promptly while details are fresh
4. **Accurate Categorization**: Choose the most appropriate category
5. **Complete Information**: Fill in all relevant optional fields
6. **Project Association**: Link to projects when applicable
7. **Tag Appropriately**: Use tags for easier searching and filtering

### For Admins

1. **Prompt Review**: Review expenses in a timely manner
2. **Clear Communication**: Provide detailed reasons for rejections
3. **Consistent Policy**: Apply expense policies consistently
4. **Documentation Check**: Verify receipt documentation before approval
5. **Amount Verification**: Verify amounts match receipts
6. **Policy Compliance**: Ensure expenses comply with company policy
7. **Regular Audits**: Periodically audit expense patterns

## Troubleshooting

### Common Issues

**Problem**: Can't upload receipt file
- **Solution**: Ensure file is PNG, JPG, GIF, or PDF format under 10MB

**Problem**: Can't edit approved expense
- **Solution**: Only admins can edit approved expenses. Contact admin if changes needed.

**Problem**: Expense not showing in project costs
- **Solution**: Ensure expense is linked to the project and approved

**Problem**: Can't delete expense
- **Solution**: Only pending expenses can be deleted by regular users

**Problem**: Total amount calculation seems wrong
- **Solution**: Check that tax amount is entered correctly; total = amount + tax

## Future Enhancements

Planned features for future releases:
- Automated expense import from credit card statements
- Mobile app for expense submission
- OCR for automatic receipt data extraction
- Approval routing based on amount thresholds
- Multi-level approval workflows
- Expense budget tracking and alerts
- Mileage tracking and calculation
- Per diem calculations
- Corporate card integration
- Real-time currency conversion

## Support

For questions or issues with the Expense Tracking feature:
- Check this documentation
- Review inline help text in the application
- Contact your system administrator
- Check the application logs for error details

## Related Documentation

- [Invoicing Guide](./INVOICING.md)
- [Project Cost Tracking](./PROJECT_COSTS.md)
- [User Roles and Permissions](./PERMISSIONS.md)
- [API Documentation](./API.md)

