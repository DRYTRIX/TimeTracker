# Default Data Seeding Fix - Changelog

## Version 3.2.3 - Bug Fix

### Issue

**Problem**: Default client and project ("Default Client" and "General") were being re-created after deletion during updates from version 3.2.2 to 3.2.3.

**Reported By**: User feedback

**Root Cause**: Database initialization scripts were checking if specific default entities existed by name and would recreate them if not found, regardless of whether this was a fresh installation or an existing database where the user had intentionally deleted them.

### Solution

Implemented a persistent flag-based tracking system to ensure default data is only seeded on fresh database installations:

1. **Added Tracking to InstallationConfig** (`app/utils/installation.py`):
   - New method: `is_initial_data_seeded()` - checks if initial data has been created
   - New method: `mark_initial_data_seeded()` - marks that initial data has been created
   - Flag persists in `data/installation.json`

2. **Updated Database Initialization Scripts**:
   - `docker/init-database.py` - Flask-based initialization
   - `docker/init-database-enhanced.py` - Enhanced SQL-based initialization
   - `docker/init-database-sql.py` - SQL script-based initialization

3. **New Behavior**:
   - On fresh installation (no projects exist): Creates default client and project, sets flag
   - On existing database (projects exist): Sets flag without creating defaults
   - On already-seeded database (flag is true): Skips default data creation entirely

### Changes Made

#### Files Modified

1. **app/utils/installation.py**
   - Added `is_initial_data_seeded()` method
   - Added `mark_initial_data_seeded()` method
   - Both methods read/write to `data/installation.json`

2. **docker/init-database.py**
   - Import `InstallationConfig`
   - Check flag before creating default project/client
   - Mark flag after seeding

3. **docker/init-database-enhanced.py**
   - Import `InstallationConfig` with proper path handling
   - Check project count and flag before seeding
   - Mark flag after seeding

4. **docker/init-database-sql.py**
   - Import `InstallationConfig` with proper path handling
   - Separate default data SQL from base SQL
   - Conditional execution based on flag and project count

5. **tests/test_installation_config.py**
   - Added `test_initial_data_seeding_tracking()`
   - Added `test_initial_data_seeding_persistence()`
   - Added `test_initial_data_seeding_default_value()`

6. **docs/DEFAULT_DATA_SEEDING.md** (New)
   - Complete documentation of the new behavior
   - Troubleshooting guide
   - Migration notes
   - Reset instructions

### Testing

#### Unit Tests Added

```bash
pytest tests/test_installation_config.py::TestInstallationConfig::test_initial_data_seeding_tracking -v
pytest tests/test_installation_config.py::TestInstallationConfig::test_initial_data_seeding_persistence -v
pytest tests/test_installation_config.py::TestInstallationConfig::test_initial_data_seeding_default_value -v
```

#### Manual Testing Scenarios

1. **Fresh Installation**:
   - ✅ Default client and project created
   - ✅ Flag set in installation.json

2. **Upgrade from v3.2.2 (with defaults deleted)**:
   - ✅ Defaults NOT recreated
   - ✅ Flag set on first startup

3. **Restart After Deletion**:
   - ✅ Deleted defaults remain deleted
   - ✅ No re-creation on restart

### Backward Compatibility

- **Existing Installations**: Flag is automatically set on first startup after upgrade
- **No Manual Intervention**: System detects existing projects and sets flag appropriately
- **No Breaking Changes**: All existing functionality preserved

### Configuration File

The flag is stored in `data/installation.json`:

```json
{
  "telemetry_salt": "...",
  "installation_id": "...",
  "setup_complete": true,
  "initial_data_seeded": true,
  "initial_data_seeded_at": "2025-10-23 12:34:56.789"
}
```

### Migration Path

#### From v3.2.2 to v3.2.3+

1. User upgrades container to v3.2.3
2. On first startup, initialization script runs
3. Script detects existing projects (if any)
4. Sets `initial_data_seeded = true` in installation.json
5. Skips default data creation
6. User's previously deleted defaults remain deleted

#### Fresh Installation

1. New installation starts
2. No projects exist in database
3. Default client and project created
4. Flag set to `true`
5. User can delete defaults if desired
6. Defaults will never be recreated

### Documentation

- **[DEFAULT_DATA_SEEDING.md](docs/DEFAULT_DATA_SEEDING.md)**: Complete guide to the new behavior
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Updated with migration notes
- **Code Comments**: Added inline documentation in all modified files

### Benefits

1. ✅ **User Control**: Users can delete default entities without them being recreated
2. ✅ **Predictable Behavior**: Once deleted, defaults stay deleted
3. ✅ **Update Safety**: Updates don't re-inject previously deleted data
4. ✅ **Migration Safety**: Database migrations respect user's data choices
5. ✅ **Backward Compatible**: No manual intervention needed during upgrade

### Breaking Changes

**None** - This is a pure bug fix with full backward compatibility.

### Known Limitations

None identified.

### Future Improvements

Potential enhancements for future releases:

1. Admin UI to reset/recreate default data if needed
2. Option to customize default data during initial setup
3. Multiple default project templates

### Support

For issues or questions:
- See documentation: `docs/DEFAULT_DATA_SEEDING.md`
- Check troubleshooting section
- Report bugs via GitHub issues

---

## Summary

This fix ensures that default client and project data respects user preferences and is only created during initial database setup, never to be automatically recreated after deletion. The implementation uses a persistent flag in the installation configuration that tracks whether initial data has been seeded, providing predictable and user-friendly behavior across updates and restarts.

**Status**: ✅ Complete and Ready for Production

**Version**: 3.2.3+

**Date**: October 23, 2025

