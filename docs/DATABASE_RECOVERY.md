# Database Recovery & Automatic Cleanup

## Overview

TimeTracker includes automatic detection and recovery for corrupted database states. This prevents users from needing to manually reset their database in most cases.

## Automatic Cleanup

If the startup process detects a corrupted database state (tables exist but migrations haven't run), it will automatically:

1. **Detect** the corrupted state
2. **Clean up** unexpected tables (test/manual tables that prevent migrations)
3. **Retry** migrations on a clean database

### When Cleanup Runs

Cleanup only runs when:
- Database has tables but **no** `alembic_version` table (migrations never ran)
- Database has tables but **no** core tables (`users`, `projects`, etc.)
- Database is PostgreSQL (SQLite cleanup is skipped for safety)

Cleanup will **NOT** run if:
- `alembic_version` table exists (migrations have run)
- Core tables exist (database is properly initialized)
- `TT_SKIP_DB_CLEANUP=true` environment variable is set

### Disabling Automatic Cleanup

To disable automatic cleanup, set:

```bash
TT_SKIP_DB_CLEANUP=true
```

This can be set in your `.env` file or `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      - TT_SKIP_DB_CLEANUP=true
```

## Manual Recovery

If automatic cleanup doesn't resolve the issue, you can manually reset the database:

### Option 1: Reset Database Volume (Complete Reset)

**WARNING: This will DELETE ALL DATA in the database!**

```bash
# Stop containers
docker compose down

# Remove the database volume (THIS DELETES ALL DATA)
docker volume rm timetracker_db_data

# Start containers (will create fresh database)
docker compose up -d
```

### Option 2: Use the Dev Reset Script

If the database is working but you want to reset it:

```bash
# From host
scripts\reset-dev-db.bat   # Windows
scripts/reset-dev-db.sh    # Linux/Mac

# Or directly in container
docker compose exec app python3 /app/scripts/reset-dev-db.py
```

### Seeding development data (after reset or for a fresh DB)

To fill the database with test data for local development (only when `FLASK_ENV=development`):

```bash
# From host (Docker): use the wrapper script so FLASK_ENV=development is set in the container
docker compose exec app /app/docker/seed-dev-data.sh

# Or with flask seed (pass env explicitly)
docker compose exec -e FLASK_ENV=development app flask seed
```

For non-Docker usage, set `FLASK_ENV=development` and run `flask seed` or `python scripts/seed-dev-data.py`.

The seed creates users, clients, projects, tasks, time entries, expenses, comments, **inventory** (warehouses, stock items, movements), and **finance** data (currencies, tax rules, invoices, payments). See [Development Data Seeding](development/SEED_DEV_DATA.md) for details and options.

## Detection Logic

The system detects corrupted states by checking:

1. **Fresh database**: No tables → Normal, migrations will run
2. **Properly migrated**: Has `alembic_version` + core tables → Normal, app starts
3. **Corrupted state**: Has tables but no `alembic_version` + no core tables → Cleanup triggered
4. **Partial migration**: Has `alembic_version` but no core tables → Error (migrations failed)

## Error Messages

If migrations fail after cleanup, you'll see clear error messages:

```
✗ WARNING: alembic_version table missing after migrations!
Migrations reported success but alembic_version table was not created.
This indicates migrations did not actually run or were rolled back.

RECOVERY OPTIONS:
1. Reset database: docker compose down -v && docker compose up -d
2. Or set TT_SKIP_DB_CLEANUP=false and restart to try automatic cleanup
```

## Troubleshooting

### Cleanup Doesn't Run

If cleanup doesn't run when expected:

1. Check if `TT_SKIP_DB_CLEANUP` is set
2. Verify database state: Check if `alembic_version` exists
3. Check logs: Look for "Detected corrupted database state" messages

### Cleanup Runs But Migrations Still Fail

If cleanup runs but migrations still fail:

1. Check migration logs for errors
2. Verify database connection (check `DATABASE_URL`)
3. Check database permissions
4. Consider manual reset (Option 1 above)

### Database Has Data You Want to Keep

If your database has important data:

1. **Backup first**: `docker compose exec db pg_dump -U timetracker timetracker > backup.sql`
2. Try cleanup (it only removes non-core tables)
3. If cleanup doesn't work, restore from backup and investigate manually
