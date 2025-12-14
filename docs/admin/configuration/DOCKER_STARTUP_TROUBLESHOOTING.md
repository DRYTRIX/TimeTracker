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
