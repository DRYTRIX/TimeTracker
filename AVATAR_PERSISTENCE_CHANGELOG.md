# Changelog: Profile Picture Persistence

**Date:** October 22, 2025  
**Version:** Current  
**Type:** Enhancement  
**Breaking Change:** No (backward compatible with migration)

## Summary

Profile pictures (user avatars) now persist between Docker container updates and rebuilds. Previously, avatars were stored in the application directory and would be lost when updating the Docker image.

## Changes

### Modified Files

1. **`app/routes/auth.py`**
   - Updated `get_avatar_upload_folder()` to use `/data/uploads/avatars` instead of `app/static/uploads/avatars`
   - Avatars now stored on persistent volume

2. **`app/models/user.py`**
   - Updated `get_avatar_path()` to reference new storage location
   - Added comments explaining persistence benefit

### New Files

3. **`docker/migrate-avatar-storage.py`**
   - Migration script to move existing avatars to new location
   - Safe to run multiple times
   - Verifies permissions and provides detailed output

4. **`docs/AVATAR_STORAGE_MIGRATION.md`**
   - Complete migration guide
   - Troubleshooting section
   - Backup recommendations

5. **`docs/AVATAR_PERSISTENCE_SUMMARY.md`**
   - Quick reference for the change
   - Migration commands
   - Verification checklist

6. **`docs/TEST_AVATAR_PERSISTENCE.md`**
   - Testing guide with step-by-step instructions
   - Automated test script
   - Troubleshooting commands

## Technical Details

### Storage Location

| Aspect | Before | After |
|--------|--------|-------|
| **Path** | `/app/static/uploads/avatars/` | `/data/uploads/avatars/` |
| **Volume** | Inside container (ephemeral) | `app_data` volume (persistent) |
| **Survives Updates** | ❌ No | ✅ Yes |
| **URL** | `/uploads/avatars/{filename}` | `/uploads/avatars/{filename}` (unchanged) |

### Docker Configuration

- Uses existing `app_data:/data` volume mount
- No docker-compose.yml changes required
- Consistent with company logo storage (`/data/uploads`)

### Backward Compatibility

✅ **Fully backward compatible**
- Existing avatar URLs continue to work
- Database schema unchanged (no migration needed)
- Old avatars can be migrated with provided script
- No code changes required for users

## Migration Required?

### New Installations
✅ **No action needed** — New location used automatically

### Existing Installations with Avatars
⚠️ **Migration recommended** — Run migration script to preserve existing avatars

```bash
docker-compose down
docker-compose run --rm app python /app/docker/migrate-avatar-storage.py
docker-compose up -d
```

### Existing Installations without Avatars
✅ **No action needed** — New location will be used automatically

## Testing

All code changes have been validated:
- ✅ No linter errors
- ✅ Code logic verified
- ✅ Volume mount confirmed in docker-compose.yml
- ✅ URL structure preserved
- ✅ Backward compatible

### Recommended Testing

After deployment:
1. Verify existing avatars display correctly
2. Upload new avatar and verify persistence after restart
3. Rebuild container and verify avatars still exist
4. Check `/data/uploads/avatars/` contains files

See `docs/TEST_AVATAR_PERSISTENCE.md` for detailed testing guide.

## Benefits

1. **🔄 Persistent Storage** — Avatars survive updates and rebuilds
2. **👥 Better UX** — Users don't lose profile pictures during updates
3. **🏗️ Production Ready** — Proper separation of persistent data from code
4. **🔧 Consistent** — Matches company logo storage pattern
5. **💾 Backup Friendly** — All uploads in one volume (`app_data`)

## Related Documentation

- 📖 [Full Migration Guide](docs/AVATAR_STORAGE_MIGRATION.md)
- 📖 [Testing Guide](docs/TEST_AVATAR_PERSISTENCE.md)
- 📖 [Quick Summary](docs/AVATAR_PERSISTENCE_SUMMARY.md)
- 📖 [Logo Upload System](docs/LOGO_UPLOAD_SYSTEM_README.md) (similar pattern)

## Questions or Issues?

If you encounter problems:
1. Review the troubleshooting section in `docs/AVATAR_STORAGE_MIGRATION.md`
2. Check Docker logs: `docker-compose logs app`
3. Verify volume mount: `docker inspect timetracker-app | grep Mounts`
4. Run migration script again with verbose output

---

**Implemented by:** AI Assistant  
**Approved by:** _Pending Review_  
**Deployed:** _Pending_

