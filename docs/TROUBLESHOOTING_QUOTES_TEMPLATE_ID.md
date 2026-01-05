# Troubleshooting: Missing quotes.template_id Column

## Problem

You're seeing this error in your database logs:

```
ERROR: column quotes.template_id does not exist at character 2057
```

This occurs when the database schema is missing the `template_id` column in the `quotes` table, even though the application code expects it to exist.

## Root Cause

The `template_id` column should have been added by migration `051_rename_offers_to_quotes_and_add_features.py` or migration `102_add_missing_quotes_template_id.py`. If this column is missing, it means:

1. The migrations haven't been run yet, or
2. A migration failed partway through, or
3. The database was created before these migrations existed

## Solution

### Option 1: Run Database Migrations (Recommended)

The proper way to fix this is to run the pending migrations:

```bash
# Check current migration status
flask db current

# Apply all pending migrations
flask db upgrade
```

If you're using Docker, migrations should run automatically on container startup. If they didn't, you can manually trigger them:

```bash
# Inside the container or with docker exec
docker exec -it timetracker-app flask db upgrade
```

### Option 2: Quick Fix Script

If you cannot run migrations for some reason, you can use the quick fix script:

```bash
# Set your DATABASE_URL environment variable
export DATABASE_URL="postgresql+psycopg2://user:password@host:port/database"

# Run the fix script
python scripts/fix_quotes_template_id.py
```

Or with Docker:

```bash
docker exec -it timetracker-app python /app/scripts/fix_quotes_template_id.py
```

### Option 3: Manual SQL Fix

If you have direct database access, you can run this SQL:

```sql
-- Add the column
ALTER TABLE quotes ADD COLUMN template_id INTEGER;

-- Create index
CREATE INDEX ix_quotes_template_id ON quotes (template_id);

-- Add foreign key (if quote_pdf_templates table exists)
ALTER TABLE quotes 
ADD CONSTRAINT fk_quotes_template_id 
FOREIGN KEY (template_id) 
REFERENCES quote_pdf_templates(id) 
ON DELETE SET NULL;
```

## Verification

After applying the fix, verify the column exists:

```sql
-- PostgreSQL
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'quotes' AND column_name = 'template_id';

-- Or check via Python
python -c "
from app import create_app, db
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('quotes')]
    print('template_id' in columns)
"
```

## Prevention

To prevent this issue in the future:

1. **Always run migrations** after pulling code updates:
   ```bash
   flask db upgrade
   ```

2. **Check migration status** before deploying:
   ```bash
   flask db current
   flask db history
   ```

3. **Use the comprehensive schema verification** script:
   ```bash
   python scripts/verify_and_fix_schema.py
   ```

## Related Files

- Migration: `migrations/versions/102_add_missing_quotes_template_id.py`
- Model: `app/models/quote.py` (line 63)
- Fix Script: `scripts/fix_quotes_template_id.py`
- Schema Verification: `scripts/verify_and_fix_schema.py`

## Additional Notes

- The `template_id` column is nullable, so existing quotes won't be affected
- The column references `quote_pdf_templates.id` for PDF template selection
- Migration 102 is idempotent and safe to run multiple times
