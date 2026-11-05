# Alembic Migration for Project Costs - README

## ✅ Migration is Ready!

The Alembic migration for the Project Costs feature has been properly configured and is ready to run.

## Migration Details

**File:** `migrations/versions/018_add_project_costs_table.py`

**Revision:** 018  
**Previous Revision:** 017  
**Status:** ✅ Ready to execute

## Quick Start

### Step 1: Backup Database (CRITICAL!)
```bash
# PostgreSQL
pg_dump -U timetracker timetracker > backup_$(date +%Y%m%d).sql

# Or if using Docker
docker-compose exec db pg_dump -U timetracker timetracker > backup_$(date +%Y%m%d).sql
```

### Step 2: Check Current Migration Status
```bash
# Using Flask-Migrate
flask db current

# Expected output: 017 (or similar)
```

### Step 3: Run the Migration
```bash
# Using Flask-Migrate (recommended)
flask db upgrade

# Or using Alembic directly
alembic upgrade head
```

### Step 4: Verify Success
```bash
# Check migration status
flask db current
# Expected output: 018 (head)

# Verify table was created
psql -U timetracker -d timetracker -c "\d project_costs"
```

### Step 5: Restart Application
```bash
# Docker
docker-compose restart app

# Or restart your Flask application server
```

## What the Migration Does

### Creates Table: `project_costs`

**Columns:**
- `id` - Primary key (Integer)
- `project_id` - Foreign key to projects (Integer, NOT NULL)
- `user_id` - Foreign key to users (Integer, NOT NULL)
- `description` - Cost description (String 500, NOT NULL)
- `category` - Cost category (String 50, NOT NULL)
- `amount` - Cost amount (Numeric 10,2, NOT NULL)
- `currency_code` - Currency (String 3, default 'EUR')
- `billable` - Whether billable (Boolean, default TRUE)
- `invoiced` - Whether invoiced (Boolean, default FALSE)
- `invoice_id` - Foreign key to invoices (Integer, NULL)
- `cost_date` - Date of cost (Date, NOT NULL)
- `notes` - Additional notes (Text, NULL)
- `receipt_path` - Path to receipt (String 500, NULL)
- `created_at` - Creation timestamp (DateTime)
- `updated_at` - Update timestamp (DateTime)

**Indexes:**
- `ix_project_costs_project_id` on `project_id`
- `ix_project_costs_user_id` on `user_id`
- `ix_project_costs_cost_date` on `cost_date`
- `ix_project_costs_invoice_id` on `invoice_id`

**Foreign Keys:**
- `fk_project_costs_project_id` → `projects(id)` ON DELETE CASCADE
- `fk_project_costs_user_id` → `users(id)` ON DELETE CASCADE
- `fk_project_costs_invoice_id` → `invoices(id)` ON DELETE SET NULL

## Safety Features

The migration includes:
- ✅ Table existence check (won't fail if table exists)
- ✅ Proper foreign key constraints
- ✅ Indexes for performance
- ✅ Safe rollback capability
- ✅ Follows existing migration chain (017 → 018)

## Alternative Migration Methods

If Alembic/Flask-Migrate is not available:

### Method 1: Direct SQL
```bash
psql -U timetracker -d timetracker -f migrations/add_project_costs.sql
```

### Method 2: Python Script (Docker)
```bash
python docker/migrate-add-project-costs.py
```

## Rollback (If Needed)

To rollback the migration:

```bash
# Using Flask-Migrate
flask db downgrade

# Or to specific revision
flask db downgrade 017

# Using Alembic
alembic downgrade -1
# or
alembic downgrade 017
```

**⚠️ WARNING:** Rollback will delete the `project_costs` table and all data!

## Verification Checklist

After migration, verify:

- [ ] Migration status shows 018
- [ ] Table `project_costs` exists
- [ ] All columns are present
- [ ] Indexes are created
- [ ] Foreign keys are in place
- [ ] Application starts without errors
- [ ] Can view project page
- [ ] Can add a test cost
- [ ] Can edit the test cost
- [ ] Can delete the test cost

## Expected Output

### Successful Migration
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 017 -> 018, Add project costs table for tracking expenses
```

### Verification Query
```sql
-- Run this to verify table structure
\d project_costs

-- Expected output shows:
-- Table "public.project_costs"
-- Column, Type, Collation, Nullable, Default
-- (all columns listed)
-- Indexes: (4 indexes listed)
-- Foreign-key constraints: (3 constraints listed)
```

## Troubleshooting

### "Table already exists"
The migration has safety checks. If you see this error:
```bash
# Mark migration as complete
alembic stamp 018
```

### "Cannot find revision 017"
Ensure previous migrations are run:
```bash
flask db upgrade 017
```

### "Foreign key constraint violation"
Ensure tables `projects`, `users`, and `invoices` exist:
```bash
psql -U timetracker -d timetracker -c "\dt"
```

### "Permission denied"
Grant necessary permissions:
```sql
GRANT CREATE ON DATABASE timetracker TO timetracker;
```

## Post-Migration Steps

1. **Restart Application**
   ```bash
   docker-compose restart app
   ```

2. **Clear Cache** (if applicable)
   ```bash
   redis-cli FLUSHALL  # if using Redis
   ```

3. **Test in Browser**
   - Navigate to a project
   - Look for "Project Costs & Expenses" section
   - Add a test cost

4. **Monitor Logs**
   ```bash
   tail -f logs/timetracker.log
   ```

## Migration Files Structure

```
TimeTracker/
├── migrations/
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── ...
│   │   ├── 017_reporting_invoicing_extensions.py
│   │   └── 018_add_project_costs_table.py  ← NEW
│   ├── add_project_costs.sql               ← Alternative
│   └── alembic.ini
├── docker/
│   └── migrate-add-project-costs.py        ← Alternative
└── MIGRATION_INSTRUCTIONS.md               ← Detailed guide
```

## Support & Documentation

- **Detailed Instructions:** `MIGRATION_INSTRUCTIONS.md`
- **Feature Documentation:** `PROJECT_COSTS_FEATURE.md`
- **Implementation Details:** `PROJECT_COSTS_IMPLEMENTATION_SUMMARY.md`
- **Quick Start:** `QUICK_START_PROJECT_COSTS.md`

## Migration Revision Chain

```
... → 016 → 017 → 018 (head)
              ↑      ↑
          Previous  Current
                   (project_costs)
```

## Testing the Migration

If you want to test before running on production:

1. **Create test database:**
   ```sql
   CREATE DATABASE timetracker_test;
   ```

2. **Restore backup to test database:**
   ```bash
   pg_restore -U timetracker -d timetracker_test backup.sql
   ```

3. **Run migration on test:**
   ```bash
   DB_NAME=timetracker_test flask db upgrade
   ```

4. **Verify on test:**
   ```bash
   psql -U timetracker -d timetracker_test -c "\d project_costs"
   ```

5. **If successful, run on production**

## Success Criteria

Migration is successful when:
- ✅ No error messages during upgrade
- ✅ Current revision is 018
- ✅ Table `project_costs` exists with all columns
- ✅ All 4 indexes are created
- ✅ All 3 foreign keys are in place
- ✅ Application starts without errors
- ✅ Project page shows costs section
- ✅ Can perform CRUD operations on costs

## Questions?

If you encounter issues:
1. Check logs: `logs/timetracker.log`
2. Verify database connection
3. Review `MIGRATION_INSTRUCTIONS.md`
4. Check database state: `\d project_costs`

---

**Ready to migrate?** Follow the Quick Start steps above!
