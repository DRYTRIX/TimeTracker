# Docker Startup Script Troubleshooting Guide

## Problem
You're getting the error: `exec /app/start.sh: no such file or directory`

## Root Causes
This error typically occurs due to one of these issues:

1. **Line Ending Issues**: Windows CRLF line endings in shell scripts
2. **File Permissions**: Script not executable
3. **File Not Found**: Script not copied correctly during Docker build
4. **Path Issues**: Script path incorrect

## Solutions

### Solution 1: Use the Remote Compose (Recommended)
```bash
# Use the production remote compose with prebuilt image
docker-compose -f docker-compose.remote.yml up -d
```

### Solution 2: Rebuild Locally
The provided `Dockerfile` supports local builds. If you prefer rebuilding:
```bash
docker-compose up --build -d
```

### Solution 3: Manual Fix
If you want to fix it manually:

1. **Check if Docker Desktop is running**
   ```powershell
   Get-Service -Name "*docker*"
   Start-Service -Name "com.docker.service"  # If stopped
   ```

2. **Rebuild the Docker image**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up
   ```

3. **Check the container logs**
   ```bash
   docker-compose logs app
   ```

### Solution 4: Use Simple Startup Script
The `start-simple.sh` script is a minimal version that should work reliably.

## Debugging Steps

### 1. Check if the script exists in the container
```bash
docker exec -it timetracker-app ls -la /app/start.sh
```

### 2. Check script permissions
```bash
docker exec -it timetracker-app file /app/start.sh
```

### 3. Check script content
```bash
docker exec -it timetracker-app cat /app/start.sh
```

### 4. Check Docker build logs
```bash
docker-compose build --no-cache
```

## File Structure
- `Dockerfile` - Container build file
- `docker/start.sh` - Startup wrapper
- `docker/start-simple.sh` - Simple, reliable startup script
- `docker/start-fixed.sh` - Enhanced startup script with schema fixes

## Quick Test
```bash
# Test remote production image
docker-compose -f docker-compose.remote.yml up -d

# Or build locally
docker-compose up --build -d
```

## Common Issues and Fixes

### Issue: "Permission denied"
**Fix**: Ensure script has execute permissions
```dockerfile
RUN chmod +x /app/start.sh
```

### Issue: "No such file or directory"
**Fix**: Check if script was copied correctly
```dockerfile
COPY docker/start-simple.sh /app/start.sh
```

### Issue: "Bad interpreter"
**Fix**: Fix line endings
```dockerfile
RUN sed -i 's/\r$//' /app/start.sh
```

## Next Steps
1. Try the fixed Dockerfile first
2. If that works, the issue was with line endings or permissions
3. If it still fails, check Docker Desktop status and rebuild
4. Check container logs for additional error details

## Support
If the issue persists, check:
- Docker Desktop version and status
- Windows line ending settings
- Antivirus software blocking Docker
- Docker daemon logs

---

## Additional Troubleshooting

### Database Tables Not Created (PostgreSQL)

**Symptoms**: Services start successfully, but database tables are missing when using PostgreSQL. Works fine with SQLite.

**Causes**:
- Flask-Migrate initialization didn't run properly
- Database container wasn't ready when app started
- Migration scripts failed silently

**Solutions**:

1. **Check database initialization logs**:
   ```bash
   docker-compose logs app | grep -i "database\|migration\|initialization\|flask db"
   ```

2. **Verify database container is healthy**:
   ```bash
   docker-compose ps db
   docker-compose logs db
   ```

3. **Manually trigger database initialization**:
   ```bash
   docker-compose exec app flask db upgrade
   ```

4. **For a complete fresh start** (⚠️ **WARNING**: This will delete all data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

5. **Verify tables exist**:
   ```bash
   # PostgreSQL
   docker-compose exec db psql -U timetracker -d timetracker -c "\dt"
   
   # Or check from app container
   docker-compose exec app python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print(db.engine.table_names())"
   ```

**Prevention**: The entrypoint script should automatically handle this. If issues persist, check that:
- The entrypoint script runs properly (check container logs)
- Database container has `healthcheck` configured
- App service has `depends_on` with `condition: service_healthy` for the db service

### Admin User Authentication Issues

**Symptoms**: Cannot login with usernames from `ADMIN_USERNAMES` environment variable (e.g., `ADMIN_USERNAMES=admin,manager`).

**Important Understanding**:
- Only the **first** username in `ADMIN_USERNAMES` is automatically created during database initialization
- Additional admin usernames in the comma-separated list must be created separately before they can login
- If `ADMIN_USERNAMES=admin,manager`, only "admin" is created automatically

**Solutions**:

1. **Login with the first admin user**:
   - Use the first username from `ADMIN_USERNAMES` (default: "admin")
   - If using `AUTH_METHOD=local`, the default admin has no password initially. On first login, enter the username and choose any password (minimum 8 characters)—it will be set and you will be logged in. There is no default password; you define it yourself on first use.
   - If using `AUTH_METHOD=none`, you can login immediately (no password required)

2. **Create additional admin users**:

   **Option A: Self-Registration** (if `ALLOW_SELF_REGISTER=true`):
   - Go to login page
   - Enter the additional admin username (e.g., "manager")
   - Set a password and login
   - The user will automatically get admin role because their username is in `ADMIN_USERNAMES`

   **Option B: Manual Creation** (recommended for production):
   - Login with the first admin user
   - Navigate to **Admin → Users → Create User**
   - Create the additional admin users
   - They will automatically get admin role when they login (if their username is in `ADMIN_USERNAMES`)

3. **Verify admin user exists**:
   ```bash
   # PostgreSQL
   docker-compose exec db psql -U timetracker -d timetracker -c "SELECT username, role, is_active FROM users;"
   ```

4. **Check environment variable is set correctly**:
   ```bash
   docker-compose exec app env | grep ADMIN_USERNAMES
   ```

5. **If the first admin user doesn't exist**, check:
   - Database initialization completed successfully (check logs)
   - `ADMIN_USERNAMES` is set in `.env` file before starting containers
   - Container logs show admin user creation

**Example Configuration**:
```bash
# .env file
ADMIN_USERNAMES=admin,manager
ALLOW_SELF_REGISTER=true  # Allows "manager" to self-register
```

In this example:
- "admin" is created automatically during initialization
- "manager" must self-register by logging in (or be created manually)