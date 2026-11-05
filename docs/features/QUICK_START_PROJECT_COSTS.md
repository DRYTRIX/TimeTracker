# Quick Start: Project Costs Feature

## 🚀 Installation (3 Steps)

### Step 1: Run Database Migration
Choose one method:

```bash
# Method A: SQL (Recommended for simplicity)
psql -U timetracker -d timetracker -f migrations/add_project_costs.sql

# Method B: Python script (for Docker)
python docker/migrate-add-project-costs.py

# Method C: Alembic
alembic upgrade head
```

### Step 2: Restart Application
```bash
# Docker
docker-compose restart

# Manual
# Stop and restart your Flask application
```

### Step 3: Verify
1. Open TimeTracker in browser
2. Go to any project
3. Look for "Project Costs & Expenses" section
4. Click "Add Cost" to test

## ✨ Quick Usage Guide

### Add a Project Cost
1. Navigate to a project page
2. Scroll to "Project Costs & Expenses"
3. Click "Add Cost" button
4. Fill in the form:
   - **Description**: What the cost is for (e.g., "Travel to client site")
   - **Category**: Select from dropdown (Travel, Materials, Services, Equipment, Software, Other)
   - **Amount**: Cost amount
   - **Date**: When the cost occurred
   - **Currency**: Select currency (default: EUR)
   - **Billable**: Check if this should be billed to client
   - **Notes**: Optional additional details
5. Click "Add Cost"

### Include Costs in Invoice
1. Create or open an invoice for a project
2. Click "Generate from Time Entries"
3. You'll see two sections:
   - **Time Entries**: Select hours to bill
   - **Project Costs**: Select costs to bill
4. Check the costs you want to include
5. Click "Generate Items"
6. Costs appear as line items in the invoice

### View Project Costs
Project page shows:
- **Total Costs**: All costs for the project
- **Billable Costs**: Costs marked as billable
- **Total Project Value**: Billable hours + billable costs
- **Recent Costs**: Table of latest 5 costs
- **Actions**: Edit/Delete buttons for each cost

## 📊 What You Get

### Project Page
✅ Cost summary cards
✅ Recent costs table
✅ Total project value calculation
✅ Add/Edit/Delete functionality

### Invoice Generation
✅ Include costs with time entries
✅ Automatic invoiced tracking
✅ Prevents double-billing

### Reports
✅ Costs included in project reports
✅ Total project value calculations
✅ Cost breakdown by category

### Statistics
✅ Updated project statistics
✅ Total costs
✅ Billable costs
✅ Combined project value

## 🎨 Features

- **6 Cost Categories**: Travel, Materials, Services, Equipment, Software, Other
- **Multi-currency**: EUR, USD, GBP, CHF
- **Billable Tracking**: Mark costs as billable or internal
- **Invoice Integration**: Seamless inclusion in invoices
- **Permission Control**: Users can only edit their own costs (admins can edit all)
- **Protection**: Invoiced costs cannot be deleted

## 📝 Example Scenarios

### Scenario 1: Travel Expense
```
Description: "Flight to Berlin for client meeting"
Category: Travel
Amount: 350.00
Currency: EUR
Date: 2024-01-15
Billable: Yes
```

### Scenario 2: Software License
```
Description: "Adobe Creative Cloud subscription - January"
Category: Software
Amount: 79.99
Currency: USD
Date: 2024-01-01
Billable: Yes
Notes: "Monthly subscription for design work"
```

### Scenario 3: Materials
```
Description: "Prototype materials and supplies"
Category: Materials
Amount: 150.00
Currency: EUR
Date: 2024-01-10
Billable: No
Notes: "Internal research and development"
```

## 🔒 Permissions

| Action | User (Creator) | User (Not Creator) | Admin |
|--------|----------------|-------------------|--------|
| Add Cost | ✅ | ✅ | ✅ |
| View Cost | ✅ | ✅ | ✅ |
| Edit Own Cost | ✅ | ❌ | ✅ |
| Delete Own Cost (uninvoiced) | ✅ | ❌ | ✅ |
| Edit Any Cost | ❌ | ❌ | ✅ |
| Delete Any Cost (uninvoiced) | ❌ | ❌ | ✅ |
| Delete Invoiced Cost | ❌ | ❌ | ❌ |

## 🐛 Troubleshooting

**Q: Migration says "table already exists"**
A: The table is already created. You can skip the migration or verify it was done correctly.

**Q: Can't see costs section on project page**
A: Restart your application and clear browser cache. Ensure migration ran successfully.

**Q: Can't delete a cost**
A: Check if the cost has been invoiced. Invoiced costs cannot be deleted. If not invoiced, ensure you have permission (creator or admin).

**Q: Costs not in reports**
A: Verify your date filter includes the cost dates and the project filter includes the right project.

## 📚 Full Documentation

For complete details, see:
- **`PROJECT_COSTS_FEATURE.md`** - Full feature documentation
- **`PROJECT_COSTS_IMPLEMENTATION_SUMMARY.md`** - Technical implementation details

## 🎯 Key Files

### Models
- `app/models/project_cost.py` - ProjectCost model

### Routes
- `app/routes/projects.py` - Cost CRUD routes (lines 345-597)
- `app/routes/invoices.py` - Invoice with costs (lines 314-436)

### Templates
- `templates/projects/add_cost.html` - Add cost form
- `templates/projects/edit_cost.html` - Edit cost form
- `templates/projects/view.html` - Project page with costs (lines 220-330)

### Migrations
- `migrations/add_project_costs.sql` - SQL migration (easiest)
- `docker/migrate-add-project-costs.py` - Python migration
- `migrations/versions/add_project_costs_table.py` - Alembic migration

## 🌟 Tips

1. **Use Categories Consistently**: Stick to the predefined categories for better reporting
2. **Add Notes**: Use the notes field for details that might be needed later
3. **Check Billable**: Always verify billable status before adding
4. **Regular Invoicing**: Invoice costs regularly to keep track of what's billed
5. **Review Before Invoicing**: Check all costs are correct before generating invoices

## ✅ Next Steps

1. ✅ Run database migration
2. ✅ Restart application
3. ✅ Test adding a cost
4. ✅ Test including cost in invoice
5. ✅ Train users on new feature
6. ✅ Review project costs regularly

---

**Need help?** Check the full documentation or review the code in the files listed above.
