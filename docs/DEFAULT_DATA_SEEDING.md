# Default Data Seeding Behavior

## Overview

TimeTracker's database initialization has been updated to ensure that default client and project data is only created during a fresh database installation, and never re-injected during subsequent updates or restarts.

## Previous Behavior (Before v3.2.3)

Previously, the database initialization scripts would check if specific default entities existed by name:
- If "Default Client" didn't exist, it would be recreated
- If "General" project didn't exist, it would be recreated

This meant that if a user deleted these default entities, they would be re-created on the next container restart or update.

## New Behavior (v3.2.3+)

The system now tracks whether initial data has been seeded using a flag in `data/installation.json`:

```json
{
  "initial_data_seeded": true,
  "initial_data_seeded_at": "2025-10-23 12:34:56.789"
}
```

### Seeding Logic

1. **Fresh Installation** (no existing projects):
   - Default client "Default Client" is created
   - Default project "General" is created
   - Flag `initial_data_seeded` is set to `true`

2. **Existing Database** (projects already exist):
   - Default data is NOT created
   - Flag `initial_data_seeded` is set to `true` to prevent future attempts

3. **Already Seeded** (flag is `true`):
   - Default data is NEVER created again
   - This persists across updates, restarts, and migrations

## Benefits

1. **User Control**: Users can delete default entities without them being recreated
2. **Clean Updates**: Updates won't re-inject deleted default data
3. **Predictable Behavior**: Once deleted, defaults stay deleted
4. **Migration Safety**: Database migrations don't re-seed data

## Implementation Details

### Configuration Tracking

The `InstallationConfig` class (`app/utils/installation.py`) provides methods to track seeding:

```python
from app.utils.installation import get_installation_config

config = get_installation_config()

# Check if initial data has been seeded
if not config.is_initial_data_seeded():
    # Create default data...
    config.mark_initial_data_seeded()
```

### Affected Scripts

The following database initialization scripts have been updated:

1. **`docker/init-database.py`** - Flask-based initialization
2. **`docker/init-database-enhanced.py`** - Enhanced SQL-based initialization
3. **`docker/init-database-sql.py`** - SQL script-based initialization

All scripts now check the `initial_data_seeded` flag before creating default entities.

## Testing

Unit tests have been added to verify the behavior:

```bash
# Run installation config tests
pytest tests/test_installation_config.py -v

# Specific tests for seeding behavior
pytest tests/test_installation_config.py::TestInstallationConfig::test_initial_data_seeding_tracking -v
pytest tests/test_installation_config.py::TestInstallationConfig::test_initial_data_seeding_persistence -v
```

## Resetting Default Data

If you need to reset the system to create default data again:

### Option 1: Delete the Flag (Recommended)

Edit `data/installation.json` and remove the `initial_data_seeded` flag:

```bash
# Linux/Mac
sed -i '/"initial_data_seeded"/d' data/installation.json

# Windows (PowerShell)
(Get-Content data/installation.json) | Where-Object { $_ -notmatch 'initial_data_seeded' } | Set-Content data/installation.json
```

Then restart the container or application.

### Option 2: Manual Deletion

Delete all projects from the database, then remove the flag:

```sql
-- Connect to your database
DELETE FROM time_entries;  -- Remove time entries first
DELETE FROM projects;       -- Remove all projects
DELETE FROM clients;        -- Remove all clients
```

Then remove the `initial_data_seeded` flag from `data/installation.json` and restart.

### Option 3: Fresh Installation

For a completely fresh start:

```bash
# Stop the application
docker-compose down

# Remove the database volume
docker volume rm timetracker_postgres_data

# Remove installation config
rm data/installation.json

# Start fresh
docker-compose up -d
```

## Troubleshooting

### Default Data Not Being Created

**Symptom**: Fresh installation but no default client/project created

**Possible Causes**:
1. The `initial_data_seeded` flag is already set to `true`
2. Projects already exist in the database

**Solution**:
1. Check `data/installation.json` for the flag
2. Check database for existing projects: `SELECT COUNT(*) FROM projects;`
3. Remove the flag if needed and restart

### Default Data Being Recreated (Shouldn't Happen)

**Symptom**: Deleted default data reappears after restart

**This should NOT happen with v3.2.3+**. If it does:

1. Check your version: The fix is in v3.2.3 and later
2. Verify `data/installation.json` exists and is writable
3. Check container logs for errors writing to installation.json
4. Report as a bug if issue persists

## Migration Notes

### Upgrading from v3.2.2 to v3.2.3

If you already deleted default entities in v3.2.2:

1. Upgrade to v3.2.3
2. The flag will be automatically set on first startup (if projects exist)
3. Your deleted defaults will NOT be recreated
4. No manual intervention needed

### Fresh Installation

On a fresh installation:
1. Default client and project will be created
2. Flag will be set automatically
3. You can safely delete these defaults
4. They won't be recreated

## Related Files

- `app/utils/installation.py` - InstallationConfig class
- `docker/init-database.py` - Flask-based initialization
- `docker/init-database-enhanced.py` - Enhanced initialization
- `docker/init-database-sql.py` - SQL-based initialization
- `tests/test_installation_config.py` - Unit tests

## See Also

- [Database Migration Guide](../migrations/MIGRATION_GUIDE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Quick Start Guide](QUICK_START_GUIDE.md)

