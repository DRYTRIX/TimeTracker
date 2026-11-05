# Project Costs Migration Instructions

## Overview
This document provides instructions for migrating the database to add the `project_costs` table using Alembic.

## Migration File
**Location:** `migrations/versions/018_add_project_costs_table.py`

**Revision:** 018  
**Previous Revision:** 017  
**Description:** Adds project_costs table for tracking project expenses beyond hourly work

## Pre-Migration Checklist

Before running the migration:

1. ✅ **Backup your database**
   ```bash
   # PostgreSQL backup example
   pg_dump -U timetracker timetracker > backup_before_project_costs_$(date +%Y%m%d).sql
   ```

2. ✅ **Check current migration status**
   ```bash
   # In your project directory with Flask app context
   flask db current
   # Or using alembic directly
   alembic current
   ```

   Expected output: `017 (head)` or similar

3. ✅ **Review the migration**
   ```bash
   cat migrations/versions/018_add_project_costs_table.py
   ```

## Running the Migration

### Method 1: Using Flask-Migrate (Recommended)

```bash
# Navigate to project directory
cd /path/to/TimeTracker

# Activate virtual environment if needed
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Run the migration
flask db upgrade

# Verify the migration
flask db current
```

Expected output after upgrade:
```
INFO  [alembic.runtime.migration] Running upgrade 017 -> 018, Add project costs table for tracking expenses
```

### Method 2: Using Alembic Directly

```bash
# Navigate to project directory
cd /path/to/TimeTracker

# Run the migration
alembic upgrade head

# Verify
alembic current
```

### Method 3: Using Docker

```bash
# If running in Docker
docker-compose exec app flask db upgrade

# Or restart the container (if auto-migration is enabled)
docker-compose restart app
```

### Method 4: Python Script (Docker Environments)

```bash
# If you prefer the standalone script
python docker/migrate-add-project-costs.py
```

### Method 5: Raw SQL (Manual)

```bash
# Only if Alembic is not available
psql -U timetracker -d timetracker -f migrations/add_project_costs.sql
```

## Verification Steps

After running the migration, verify it was successful:

### 1. Check Migration Status
```bash
flask db current
# Should show: 018 (head)
```

### 2. Verify Table Creation
```bash
psql -U timetracker -d timetracker -c "\d project_costs"
```

Expected output should show:
- Columns: id, project_id, user_id, description, category, amount, etc.
- Indexes: ix_project_costs_project_id, ix_project_costs_user_id, etc.
- Foreign keys: fk_project_costs_project_id, fk_project_costs_user_id, etc.

### 3. Check Application Logs
```bash
tail -f logs/timetracker.log
```

Look for any errors related to project_costs

### 4. Test in Application
1. Log in to TimeTracker
2. Navigate to any project
3. Look for "Project Costs & Expenses" section
4. Try adding a test cost

## Rollback (If Needed)

If you need to rollback the migration:

```bash
# Using Flask-Migrate
flask db downgrade

# Or using Alembic
alembic downgrade -1

# To downgrade to a specific revision
flask db downgrade 017
# or
alembic downgrade 017
```

**Warning:** Rolling back will **delete the project_costs table** and all data in it!

## Troubleshooting

### Issue: "Table already exists"

**Problem:** The migration script tries to create a table that already exists.

**Solution:** The migration includes a check for table existence. If you see this error:
1. Verify the table actually exists: `\d project_costs` in psql
2. If it exists and is correct, manually mark the migration as complete:
   ```bash
   alembic stamp 018
   ```

### Issue: "Cannot find revision 017"

**Problem:** The previous migration (017) doesn't exist or wasn't run.

**Solution:**
1. Check current revision: `flask db current`
2. Upgrade to 017 first: `flask db upgrade 017`
3. Then upgrade to 018: `flask db upgrade`

### Issue: Foreign key constraint fails

**Problem:** Referenced tables (projects, users, invoices) don't exist.

**Solution:**
1. Ensure you're at migration 017 before running this
2. The migration checks for invoices table existence before creating that FK
3. Run previous migrations first: `flask db upgrade`

### Issue: "Cannot connect to database"

**Problem:** Database connection parameters are incorrect.

**Solution:**
1. Check your `.env` file or environment variables
2. Verify database is running: `docker-compose ps` or `systemctl status postgresql`
3. Test connection: `psql -U timetracker -d timetracker`

### Issue: Permission denied

**Problem:** Database user doesn't have permission to create tables.

**Solution:**
```sql
-- Grant necessary permissions (run as postgres superuser)
GRANT CREATE ON DATABASE timetracker TO timetracker;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO timetracker;
```

## Post-Migration

After successful migration:

1. ✅ **Restart Application**
   ```bash
   # Docker
   docker-compose restart app

   # Systemd
   sudo systemctl restart timetracker

   # Manual
   # Stop and start your Flask application
   ```

2. ✅ **Clear Application Cache**
   ```bash
   # If using Redis
   redis-cli FLUSHALL

   # Browser cache
   # Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   ```

3. ✅ **Test Core Functionality**
   - [ ] View a project
   - [ ] Add a cost
   - [ ] Edit a cost
   - [ ] Delete a cost
   - [ ] Generate an invoice with costs
   - [ ] View project reports

4. ✅ **Update Documentation**
   - Inform team about new feature
   - Share `PROJECT_COSTS_FEATURE.md` with users
   - Update internal wiki/docs if applicable

## Migration Details

### What Gets Created

**Table:** `project_costs`
- Primary key: `id`
- Foreign keys: `project_id`, `user_id`, `invoice_id`
- Indexes: On project_id, user_id, cost_date, invoice_id

**Columns:**
- `id`: Integer, Primary Key
- `project_id`: Integer, NOT NULL, Foreign Key to projects
- `user_id`: Integer, NOT NULL, Foreign Key to users
- `description`: String(500), NOT NULL
- `category`: String(50), NOT NULL
- `amount`: Numeric(10,2), NOT NULL
- `currency_code`: String(3), NOT NULL, Default 'EUR'
- `billable`: Boolean, NOT NULL, Default TRUE
- `invoiced`: Boolean, NOT NULL, Default FALSE
- `invoice_id`: Integer, NULL, Foreign Key to invoices
- `cost_date`: Date, NOT NULL
- `notes`: Text, NULL
- `receipt_path`: String(500), NULL
- `created_at`: DateTime, NOT NULL, Default CURRENT_TIMESTAMP
- `updated_at`: DateTime, NOT NULL, Default CURRENT_TIMESTAMP

### Database Size Impact

Estimated size per cost entry: ~300 bytes

Example capacity:
- 1,000 costs ≈ 300 KB
- 10,000 costs ≈ 3 MB
- 100,000 costs ≈ 30 MB

## Support

For issues or questions:
1. Check `PROJECT_COSTS_FEATURE.md` for feature documentation
2. Review `PROJECT_COSTS_IMPLEMENTATION_SUMMARY.md` for technical details
3. Check application logs: `logs/timetracker.log`
4. Verify database state: `psql -U timetracker -d timetracker`

## Emergency Rollback Script

If you need to manually remove the table:

```sql
-- WARNING: This will delete all project cost data!
-- Only use if rollback through Alembic fails

-- Drop foreign keys first
ALTER TABLE project_costs DROP CONSTRAINT IF EXISTS fk_project_costs_invoice_id;
ALTER TABLE project_costs DROP CONSTRAINT IF EXISTS fk_project_costs_user_id;
ALTER TABLE project_costs DROP CONSTRAINT IF EXISTS fk_project_costs_project_id;

-- Drop indexes
DROP INDEX IF EXISTS ix_project_costs_invoice_id;
DROP INDEX IF EXISTS ix_project_costs_cost_date;
DROP INDEX IF EXISTS ix_project_costs_user_id;
DROP INDEX IF EXISTS ix_project_costs_project_id;

-- Drop table
DROP TABLE IF EXISTS project_costs;

-- Mark migration as rolled back
-- (Run this through Alembic, not SQL)
-- alembic downgrade 017
```

## Next Steps

After successful migration:
- Read: `QUICK_START_PROJECT_COSTS.md` for usage guide
- Read: `PROJECT_COSTS_FEATURE.md` for full feature documentation
- Train users on the new functionality
- Monitor application performance
- Set up any necessary backups for the new data
