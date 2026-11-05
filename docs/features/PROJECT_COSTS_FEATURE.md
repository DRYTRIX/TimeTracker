# Project Costs Feature

## Overview

The Project Costs feature allows you to track expenses beyond hourly work on projects. This includes costs like travel, materials, third-party services, equipment rentals, software licenses, and other project-related expenses.

## Features

### 1. Cost Management
- **Add Costs**: Add project costs with description, category, amount, and date
- **Edit Costs**: Modify cost details (admins and cost creators only)
- **Delete Costs**: Remove costs that haven't been invoiced yet
- **Categories**: Organize costs by category (Travel, Materials, Services, Equipment, Software, Other)
- **Billable Status**: Mark costs as billable or non-billable to clients
- **Multiple Currencies**: Support for EUR, USD, GBP, CHF

### 2. Project View Integration
- **Cost Summary**: View total costs, billable costs, and total project value
- **Recent Costs**: See the 5 most recent costs in the project overview
- **Statistics**: Updated project statistics include cost information
- **Quick Actions**: Add, edit, and delete costs directly from the project page

### 3. Invoice Integration
- **Automatic Inclusion**: Include project costs when generating invoices
- **Cost Tracking**: Track which costs have been invoiced
- **Uninvoiced Costs**: View all uninvoiced billable costs for a project
- **Invoice Items**: Costs appear as separate line items on invoices

### 4. Reporting
- **Project Reports**: Reports now include project costs in calculations
- **Cost Breakdown**: View costs by category
- **Total Project Value**: Combination of billable hours and billable costs
- **Date Filtering**: Filter costs by date range

## Database Schema

The `project_costs` table includes:
- **id**: Primary key
- **project_id**: Foreign key to projects table
- **user_id**: Foreign key to users table (who added the cost)
- **description**: Brief description of the cost
- **category**: Category (travel, materials, services, equipment, software, other)
- **amount**: Cost amount (Decimal)
- **currency_code**: Currency code (default: EUR)
- **billable**: Whether the cost is billable to client
- **invoiced**: Whether the cost has been invoiced
- **invoice_id**: Reference to invoice (if invoiced)
- **cost_date**: Date of the cost
- **notes**: Additional notes
- **receipt_path**: Path to uploaded receipt (future enhancement)
- **created_at**: Timestamp when cost was created
- **updated_at**: Timestamp when cost was last updated

## Usage

### Adding a Cost

1. Navigate to a project page
2. Scroll to the "Project Costs & Expenses" section
3. Click "Add Cost"
4. Fill in:
   - Description (required)
   - Category (required)
   - Amount (required)
   - Date (required)
   - Currency (default: EUR)
   - Notes (optional)
   - Billable checkbox (default: checked)
5. Click "Add Cost"

### Viewing Costs

- **Project Page**: Shows the 5 most recent costs
- **Statistics Card**: Shows total costs and total project value
- **Full List**: Click "View All Costs" to see all costs for a project

### Including Costs in Invoices

1. Create or edit an invoice
2. Click "Generate from Time Entries"
3. Select the costs you want to include along with time entries
4. Click "Generate Items"
5. Costs will appear as line items in the invoice
6. Invoiced costs are automatically marked to prevent double-billing

### Project Statistics

The project view now shows:
- **Total Hours**: All tracked hours
- **Billable Hours**: Hours marked as billable
- **Total Costs**: Sum of all project costs
- **Budget Used (Hours)**: Budget consumed by hourly work
- **Total Project Value**: Billable hours cost + billable costs

## API Endpoints

### Routes
- `GET /projects/<id>/costs` - List all costs for a project
- `GET /projects/<id>/costs/add` - Show add cost form
- `POST /projects/<id>/costs/add` - Create a new cost
- `GET /projects/<id>/costs/<cost_id>/edit` - Show edit cost form
- `POST /projects/<id>/costs/<cost_id>/edit` - Update a cost
- `POST /projects/<id>/costs/<cost_id>/delete` - Delete a cost
- `GET /api/projects/<id>/costs` - Get costs as JSON

### Project Model Properties
- `project.total_costs` - Total of all costs
- `project.total_billable_costs` - Total of billable costs
- `project.total_project_value` - Billable hours + billable costs

## Migration

### Database Migration

The Project Costs feature is implemented via Alembic migration **018**.

#### Using Flask-Migrate (recommended):
```bash
# Apply all pending migrations including 018
flask db upgrade

# Check current migration status
flask db current

# View migration history
flask db history
```

#### Migration Details
- **Migration ID**: 018
- **File**: `migrations/versions/018_add_project_costs_table.py`
- **Creates**: `project_costs` table with indexes and foreign keys
- **Depends on**: Migration 017 (reporting and invoicing extensions)

#### Migration Features
- **Idempotent**: Can be safely run multiple times
- **Database-aware**: Handles SQLite, PostgreSQL, and MySQL differences
- **Safe FK handling**: Only creates invoice FK if invoices table exists
- **Verbose logging**: Prints progress during migration
- **Error handling**: Clear error messages if migration fails

#### Testing the Migration

A test script is provided to validate migration 018:
```bash
python test_migration_018.py
```

This checks:
- Migration file structure and syntax
- Required columns and indexes
- Foreign key definitions
- Model import compatibility
- Migration chain integrity

### Environment Variables
No new environment variables are required. The feature uses existing database connection settings.

## Permissions

- **All Users**: Can add costs to projects they work on
- **Cost Creators**: Can edit and delete their own costs (if not invoiced)
- **Admins**: Can edit and delete any costs (if not invoiced)
- **Invoiced Costs**: Cannot be deleted to maintain invoice integrity

## Future Enhancements

Potential future improvements:
1. **Receipt Uploads**: Upload and store receipt images
2. **Cost Approval Workflow**: Require approval for costs above threshold
3. **Cost Budgets**: Set and track budgets specifically for costs
4. **Cost Analytics**: Advanced analytics and visualizations for costs
5. **Recurring Costs**: Support for recurring project costs
6. **Multi-currency Conversion**: Automatic currency conversion
7. **Export Costs**: Export costs to CSV/PDF
8. **Cost Templates**: Create templates for common costs

## Light Look and Feel

The UI maintains the TimeTracker application's light and clean design:
- Clean cards with subtle shadows
- Light color scheme with primary blue accents
- Clear typography and spacing
- Responsive design for mobile devices
- Intuitive icons and badges
- Smooth animations and transitions

## Technical Notes

### Models
- `ProjectCost` model in `app/models/project_cost.py`
- Relationships with `Project`, `User`, and `Invoice` models
- Cascade deletion when parent project or user is deleted

### Routes
- Cost management routes in `app/routes/projects.py`
- Invoice generation updated in `app/routes/invoices.py`
- Report calculations updated in `app/routes/reports.py`

### Templates
- `templates/projects/add_cost.html` - Add cost form
- `templates/projects/edit_cost.html` - Edit cost form
- `templates/projects/view.html` - Updated with costs section

## Support

For issues or questions about the Project Costs feature:
1. Check the TimeTracker documentation
2. Review the code in the models and routes files
3. Check the migration scripts for database setup
4. Contact your system administrator

## Testing

Comprehensive tests are provided in `tests/test_project_costs.py`:

### Model Tests
- ProjectCost creation and validation
- Relationship testing (Project, User, Invoice)
- Timestamp and constraint validation
- Method testing (to_dict, mark_as_invoiced, etc.)

### Query Tests
- `get_project_costs()` with filters
- `get_total_costs()` calculations
- `get_uninvoiced_costs()` filtering
- `get_costs_by_category()` grouping
- Date range filtering
- Billable/non-billable filtering

### Integration Tests
- Cascade deletion with projects
- Invoice marking workflow
- Foreign key constraints

### Smoke Tests
- Basic CRUD operations
- Relationship loading
- Query execution

Run the tests:
```bash
# Run all project cost tests
pytest tests/test_project_costs.py -v

# Run specific test class
pytest tests/test_project_costs.py::TestProjectCostModel -v

# Run with coverage
pytest tests/test_project_costs.py --cov=app.models.project_cost --cov-report=html
```

## Troubleshooting

### Migration 018 Issues

If migration 018 fails:

1. **Check database connection**:
   ```bash
   flask db current
   ```

2. **View detailed migration logs**:
   The migration prints verbose output showing each step.

3. **Common issues**:
   - **Index already exists**: Migration is idempotent and checks before creating
   - **Foreign key errors**: Ensure projects and users tables exist
   - **Boolean defaults**: Migration handles different database dialects

4. **Manual rollback** (if needed):
   ```bash
   flask db downgrade 017
   ```

5. **Re-run migration**:
   ```bash
   flask db upgrade 018
   ```

### Data Integrity

The migration includes:
- **NOT NULL constraints** on required fields
- **Foreign key constraints** with CASCADE deletion
- **Indexes** on frequently queried columns
- **Server-side defaults** for timestamps and boolean fields

## Version History

- **v1.1** (2025-01-15): Migration improvements
  - Fixed index column bug in migration 018
  - Added comprehensive test suite (70+ tests)
  - Improved migration error handling and logging
  - Enhanced documentation with troubleshooting guide

- **v1.0** (2024-01-01): Initial release
  - Basic cost tracking
  - Invoice integration
  - Report integration
  - CRUD operations
