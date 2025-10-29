# Uploads Persistence in TimeTracker

## Overview

This document explains how TimeTracker handles persistent file uploads (company logos and user avatars) across container rebuilds and restarts.

## Problem Statement

Prior to this implementation, uploaded files (company logos and user avatars) were stored directly in the container's filesystem at `app/static/uploads/`. When containers were rebuilt or redeployed, these files were lost because they were not stored in a persistent volume.

## Solution

We've implemented Docker volume persistence for the uploads directory, ensuring that all uploaded files persist across:
- Container rebuilds
- Container restarts
- Application updates
- Docker Compose down/up cycles

## Technical Implementation

### Directory Structure

```
app/static/uploads/
├── logos/              # Company logo files
│   ├── .gitkeep
│   └── [uploaded logo files]
└── avatars/            # User avatar files
    ├── .gitkeep
    └── [uploaded avatar files]
```

### Docker Volume Configuration

All Docker Compose files have been updated to include the `app_uploads` volume:

```yaml
services:
  app:
    volumes:
      - app_data:/data
      - app_logs:/app/logs
      - app_uploads:/app/app/static/uploads  # Persistent uploads volume

volumes:
  app_data:
    driver: local
  app_uploads:
    driver: local
```

### Updated Docker Compose Files

The following Docker Compose configurations have been updated:

1. **docker-compose.yml** - Main production configuration
2. **docker-compose.example.yml** - Example configuration for new users
3. **docker-compose.remote.yml** - Remote deployment configuration
4. **docker-compose.local-test.yml** - Local testing with SQLite
5. **docker-compose.remote-dev.yml** - Remote development configuration

Note: Overlay files (`docker-compose.analytics.yml`, `docker-compose.https-*.yml`) don't need changes as they extend the base configuration.

## Migration Guide

### For New Installations

If you're setting up TimeTracker for the first time, the uploads persistence is automatically configured. Simply run:

```bash
docker-compose up -d
```

### For Existing Installations

If you're upgrading from a version without uploads persistence, follow these steps:

#### Step 1: Backup Existing Uploads (if any)

```bash
# Create a backup of existing uploads
docker cp timetracker-app:/app/app/static/uploads ./uploads_backup
```

#### Step 2: Update Docker Compose Configuration

Pull the latest changes:

```bash
git pull origin main
# or
git pull origin develop
```

#### Step 3: Run Migration Script

```bash
python migrations/ensure_uploads_persistence.py
```

The migration script will:
- Create the required directory structure
- Set proper permissions (755)
- Create `.gitkeep` files for git tracking
- Verify Docker volume configuration

#### Step 4: Restart Containers

```bash
# Stop containers
docker-compose down

# Start with new configuration
docker-compose up -d
```

#### Step 5: Restore Backups (if needed)

If you had existing uploads, restore them:

```bash
# Copy logos back
docker cp ./uploads_backup/logos/. timetracker-app:/app/app/static/uploads/logos/

# Copy avatars back (if any)
docker cp ./uploads_backup/avatars/. timetracker-app:/app/app/static/uploads/avatars/

# Fix permissions
docker exec timetracker-app chown -R timetracker:timetracker /app/app/static/uploads
```

#### Step 6: Verify

1. Log in to TimeTracker
2. Go to Admin → Settings
3. Check if your company logo is still displayed
4. Try uploading a new logo to test the functionality

## File Upload Locations

### Company Logo

- **Storage Path**: `/app/app/static/uploads/logos/`
- **URL Path**: `/uploads/logos/{filename}`
- **Database Field**: `settings.company_logo_filename`
- **Max Size**: 5MB
- **Supported Formats**: PNG, JPG, JPEG, GIF, SVG, WEBP

### User Avatars

- **Storage Path**: `/app/app/static/uploads/avatars/`
- **URL Path**: `/uploads/avatars/{filename}`
- **Database Field**: `users.avatar_filename`
- **Max Size**: 2MB (configurable)
- **Supported Formats**: PNG, JPG, JPEG, GIF, WEBP

## Volume Management

### Inspecting the Volume

```bash
# List all volumes
docker volume ls

# Inspect the uploads volume
docker volume inspect timetracker_app_uploads

# View volume contents
docker run --rm -v timetracker_app_uploads:/data alpine ls -lah /data
```

### Backing Up the Volume

```bash
# Create a backup archive
docker run --rm \
  -v timetracker_app_uploads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### Restoring from Backup

```bash
# Restore from backup archive
docker run --rm \
  -v timetracker_app_uploads:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/uploads_backup_YYYYMMDD_HHMMSS.tar.gz"
```

### Removing the Volume (⚠️ Caution)

```bash
# Stop containers first
docker-compose down

# Remove the volume (this will delete all uploaded files!)
docker volume rm timetracker_app_uploads

# Recreate with new containers
docker-compose up -d
```

## Permissions

The uploads directory uses the following permissions:

- **Directory Permission**: `755` (rwxr-xr-x)
  - Owner (timetracker): Read, Write, Execute
  - Group: Read, Execute
  - Others: Read, Execute

- **File Permission**: `644` (rw-r--r--)
  - Owner (timetracker): Read, Write
  - Group: Read
  - Others: Read

## Security Considerations

### File Type Validation

All uploaded files are validated to ensure they match allowed file types:

- **Logos**: PNG, JPG, JPEG, GIF, SVG, WEBP
- **Avatars**: PNG, JPG, JPEG, GIF, WEBP

### File Size Limits

- **Company Logo**: 5MB maximum
- **User Avatar**: 2MB maximum (configurable)

### Filename Sanitization

All uploaded files are renamed with UUID-based filenames to:
- Prevent path traversal attacks
- Avoid filename collisions
- Remove potentially malicious filenames

### Access Control

- Logo uploads: Admin users only (or users with `manage_settings` permission)
- Avatar uploads: Authenticated users (their own avatar only)

## Troubleshooting

### Uploaded Files Disappear After Restart

**Symptom**: Files uploaded before the persistence update are lost after container restart.

**Solution**:
1. Verify the uploads volume is properly mounted:
   ```bash
   docker inspect timetracker-app | grep -A 10 Mounts
   ```
2. Ensure the volume exists:
   ```bash
   docker volume ls | grep uploads
   ```
3. Check if files are in the volume:
   ```bash
   docker exec timetracker-app ls -lah /app/app/static/uploads/logos/
   ```

### Permission Denied Errors

**Symptom**: "Permission denied" when uploading files.

**Solution**:
1. Check directory permissions:
   ```bash
   docker exec timetracker-app ls -ld /app/app/static/uploads/
   ```
2. Fix permissions if needed:
   ```bash
   docker exec timetracker-app chown -R timetracker:timetracker /app/app/static/uploads
   docker exec timetracker-app chmod -R 755 /app/app/static/uploads
   ```

### Files Not Accessible via Web

**Symptom**: Uploaded files return 404 errors when accessed via browser.

**Solution**:
1. Verify Flask is serving static files correctly
2. Check if files exist:
   ```bash
   docker exec timetracker-app ls /app/app/static/uploads/logos/
   ```
3. Check file permissions allow reading:
   ```bash
   docker exec timetracker-app ls -l /app/app/static/uploads/logos/
   ```

### Volume Not Created

**Symptom**: Volume doesn't exist after `docker-compose up`.

**Solution**:
1. Stop all containers:
   ```bash
   docker-compose down
   ```
2. Verify your docker-compose.yml has the uploads volume defined
3. Start containers again:
   ```bash
   docker-compose up -d
   ```
4. Check if volume was created:
   ```bash
   docker volume ls | grep uploads
   ```

## Testing

### Manual Testing

1. **Upload a logo**:
   - Log in as admin
   - Go to Admin → Settings
   - Upload a company logo
   - Note the logo filename from the database

2. **Restart container**:
   ```bash
   docker-compose restart app
   ```

3. **Verify persistence**:
   - Refresh the Settings page
   - Verify the logo is still displayed

4. **Rebuild container**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

5. **Verify persistence after rebuild**:
   - Log in again
   - Verify the logo is still displayed

### Automated Testing

Run the persistence tests:

```bash
# Run all tests
pytest tests/test_uploads_persistence.py -v

# Run specific test
pytest tests/test_uploads_persistence.py::test_logo_upload_creates_file -v
```

## Best Practices

1. **Regular Backups**: Schedule regular backups of the uploads volume
2. **Volume Naming**: Use consistent volume names across environments
3. **Monitoring**: Monitor volume disk usage to prevent out-of-space issues
4. **Documentation**: Keep documentation updated when modifying upload behavior
5. **Testing**: Test file uploads after any infrastructure changes

## Related Documentation

- [Company Logo Upload System](./LOGO_UPLOAD_SYSTEM_README.md)
- [Logo Upload Implementation Summary](./LOGO_UPLOAD_IMPLEMENTATION_SUMMARY.md)
- [Docker Deployment Guide](../DEPLOYMENT_GUIDE.md)

## Version History

- **v1.0.0** (2024): Initial implementation of uploads persistence
  - Added Docker volume support for uploads directory
  - Updated all Docker Compose configurations
  - Created migration scripts and documentation
  - Added automated tests for persistence verification

## Support

If you encounter issues with uploads persistence:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the logs: `docker-compose logs app`
3. Check volume status: `docker volume inspect timetracker_app_uploads`
4. Open an issue on GitHub with:
   - Docker version
   - Docker Compose version
   - Relevant log output
   - Steps to reproduce the issue

