# User Avatar Storage Migration Guide

## Overview

As of this update, user profile pictures (avatars) are now stored in the persistent `/data` volume instead of the application directory. This ensures that **profile pictures persist between Docker container updates and rebuilds**.

## What Changed?

### Previous Behavior
- **Location:** `app/static/uploads/avatars/`
- **Problem:** This directory is inside the application container, so avatars were lost when updating or rebuilding the Docker image
- **Impact:** Users had to re-upload their profile pictures after each update

### New Behavior
- **Location:** `/data/uploads/avatars/`
- **Solution:** This directory is on the persistent `app_data` Docker volume
- **Benefit:** Profile pictures are preserved across all updates and rebuilds

## Migration Required?

**If you have existing user avatars**, you need to run the migration script to move them to the new location.

**If you're setting up a fresh installation**, no migration is needed - the new location will be used automatically.

## How to Migrate Existing Avatars

### Docker Environment

1. **Stop your TimeTracker containers:**
   ```bash
   docker-compose down
   ```

2. **Run the migration script:**
   ```bash
   docker-compose run --rm app python /app/docker/migrate-avatar-storage.py
   ```

3. **Start your containers:**
   ```bash
   docker-compose up -d
   ```

4. **Verify avatars are working:**
   - Log in to TimeTracker
   - Check that user profile pictures are displayed correctly
   - Try uploading a new avatar to confirm uploads work

5. **Optional - Cleanup old files:**
   After confirming everything works, you can remove the old avatar directory:
   ```bash
   docker-compose exec app rm -rf /app/static/uploads/avatars
   ```

### Bare Metal / Development Environment

1. **Navigate to your TimeTracker directory:**
   ```bash
   cd /path/to/TimeTracker
   ```

2. **Ensure the new directory exists:**
   ```bash
   mkdir -p /data/uploads/avatars
   ```

3. **Run the migration script:**
   ```bash
   python docker/migrate-avatar-storage.py
   ```

4. **Restart your application:**
   ```bash
   # Your normal restart command
   systemctl restart timetracker
   # or
   ./restart.sh
   ```

5. **Verify and cleanup:**
   Follow steps 4-5 from the Docker instructions above.

## Technical Details

### Files Modified

1. **`app/routes/auth.py`**
   - Updated `get_avatar_upload_folder()` to use `/data/uploads/avatars`
   - Comment added explaining the persistence benefit

2. **`app/models/user.py`**
   - Updated `get_avatar_path()` to use `/data/uploads/avatars`
   - Added fallback for development environments

3. **`docker-compose.yml`**
   - Already had `app_data:/data` volume mount (no changes needed)

### Configuration

The avatar location now respects the `UPLOAD_FOLDER` configuration:
- **Default:** `/data/uploads` (avatars go to `/data/uploads/avatars`)
- **Configurable:** Set `UPLOAD_FOLDER` in your environment to change the base path

### URL Structure

The public URL structure **remains unchanged**:
- **URL:** `/uploads/avatars/{filename}`
- **Route:** Handled by `auth.serve_uploaded_avatar()`

This means existing avatar URLs in the database continue to work without modification.

## Troubleshooting

### Avatars not displaying after migration

1. **Check file permissions:**
   ```bash
   docker-compose exec app ls -la /data/uploads/avatars/
   ```
   Files should be readable by the app user.

2. **Verify volume mount:**
   ```bash
   docker inspect timetracker-app | grep -A 5 Mounts
   ```
   Should show `/data` mounted from the `app_data` volume.

3. **Check migration log:**
   Re-run the migration script to see if files were actually copied.

### New avatar uploads failing

1. **Check directory permissions:**
   ```bash
   docker-compose exec app touch /data/uploads/avatars/.test
   ```
   If this fails, fix permissions:
   ```bash
   docker-compose exec app chown -R app:app /data/uploads/avatars
   docker-compose exec app chmod -R 755 /data/uploads/avatars
   ```

2. **Check disk space:**
   ```bash
   docker-compose exec app df -h /data
   ```

### Migration script can't find old directory

This is normal if:
- You're setting up a fresh installation (no avatars to migrate)
- Avatars were already migrated previously
- No users have uploaded avatars yet

The script will create the new directory structure automatically.

## Benefits of This Change

✅ **Persistent Storage:** Profile pictures survive Docker updates and rebuilds  
✅ **Consistent with Logos:** Company logos already use `/data/uploads` (consistency)  
✅ **Better UX:** Users don't lose their profile pictures during updates  
✅ **Production Ready:** Proper separation of persistent data from application code  
✅ **Backup Friendly:** All persistent uploads are in one volume (`app_data`)  

## Backup Recommendations

Since avatars are now on the `app_data` volume, include this volume in your backup strategy:

```bash
# Backup the entire data volume
docker run --rm -v timetracker_app_data:/data -v $(pwd):/backup ubuntu tar czf /backup/app_data_backup.tar.gz -C /data .

# Restore the data volume
docker run --rm -v timetracker_app_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/app_data_backup.tar.gz -C /data
```

## Questions?

If you encounter any issues with the avatar migration:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the Docker logs: `docker-compose logs app`
3. Open an issue on GitHub with migration script output

---

**Last Updated:** October 2025  
**Applies to:** TimeTracker v2.x and later

