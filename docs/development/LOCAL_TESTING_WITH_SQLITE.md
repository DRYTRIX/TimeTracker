# Local Testing with SQLite

This document explains how to run TimeTracker locally for testing using SQLite instead of PostgreSQL.

## Overview

The local test environment uses:
- **SQLite database** instead of PostgreSQL (no separate database container needed)
- **Development mode** with debug logging enabled
- **Local data persistence** through Docker volumes
- **Simplified setup** for quick testing and development

## Quick Start

### Option 1: Using Scripts (Recommended)

**Windows:**
```cmd
scripts\start-local-test.bat
```

**Linux/macOS:**
```bash
./scripts/start-local-test.sh
```

**PowerShell:**
```powershell
.\scripts\start-local-test.ps1
```

### Option 2: Manual Docker Compose

```bash
docker-compose -f docker-compose.local-test.yml up --build
```

## Configuration

The local test environment uses these key settings:

- **Database**: SQLite at `/data/timetracker.db` (persisted in Docker volume)
- **Port**: 8080 (same as production)
- **Environment**: Development mode with debug enabled
- **Security**: Secure cookies disabled for local testing
- **Logs**: Available in `./logs/` directory

## Environment Variables

You can override default settings using environment variables:

```bash
# Timezone
export TZ=Europe/Brussels

# Currency
export CURRENCY=EUR

# Admin users (comma-separated)
export ADMIN_USERNAMES=admin,testuser

# Secret key (change for security)
export SECRET_KEY=your-local-test-secret-key

# Start with custom settings
docker-compose -f docker-compose.local-test.yml up --build
```

## Data Persistence

- **SQLite database**: Stored in Docker volume `app_data_local_test`
- **Uploads**: Stored in `/data/uploads` (persisted in Docker volume)
- **Logs**: Stored in `./logs/` directory (mounted from host)

## Stopping the Environment

```bash
# Stop containers
docker-compose -f docker-compose.local-test.yml down

# Stop and remove volumes (WARNING: This will delete all data)
docker-compose -f docker-compose.local-test.yml down -v
```

## Accessing the Application

Once started, the application will be available at:
- **URL**: http://localhost:8080
- **Health Check**: http://localhost:8080/_health

## Database Management

### Viewing SQLite Database

You can access the SQLite database directly:

```bash
# Copy database from container to host
docker cp timetracker-app-local-test:/data/timetracker.db ./local-db.sqlite

# Use sqlite3 command line tool
sqlite3 local-db.sqlite

# Or use any SQLite browser tool
```

### Resetting Database

To start with a fresh database:

```bash
# Stop and remove volumes
docker-compose -f docker-compose.local-test.yml down -v

# Start again
docker-compose -f docker-compose.local-test.yml up --build
```

## Troubleshooting

### Container Won't Start

1. **Check Docker is running**:
   ```bash
   docker info
   ```

2. **Check port 8080 is available**:
   ```bash
   netstat -an | grep 8080
   ```

3. **View container logs**:
   ```bash
   docker-compose -f docker-compose.local-test.yml logs app
   ```

### Database Issues

1. **Check database file exists**:
   ```bash
   docker exec timetracker-app-local-test ls -la /data/
   ```

2. **Reset database**:
   ```bash
   docker-compose -f docker-compose.local-test.yml down -v
   docker-compose -f docker-compose.local-test.yml up --build
   ```

### Permission Issues

The local test setup includes a custom entrypoint that automatically handles permissions. If you still encounter issues:

```bash
# Check container logs for permission errors
docker-compose -f docker-compose.local-test.yml logs app

# If needed, fix permissions manually
docker exec timetracker-app-local-test chown -R timetracker:timetracker /data
```

### Entrypoint Issues

If you encounter issues with the entrypoint script (like `su-exec: not found`), you can use the simplified entrypoint:

1. **Edit docker-compose.local-test.yml** and change the entrypoint line:
   ```yaml
   # Change this line:
   entrypoint: ["/app/docker/entrypoint-local-test.sh"]
   
   # To this:
   entrypoint: ["/app/docker/entrypoint-local-test-simple.sh"]
   ```

2. **Restart the container**:
   ```bash
   docker-compose -f docker-compose.local-test.yml down
   docker-compose -f docker-compose.local-test.yml up --build
   ```

The simplified entrypoint runs everything as root, which avoids user switching issues but is less secure (fine for local testing).

## Differences from Production

| Feature | Local Test | Production |
|---------|------------|------------|
| Database | SQLite | PostgreSQL |
| Debug Mode | Enabled | Disabled |
| Secure Cookies | Disabled | Enabled |
| Data Volume | `app_data_local_test` | `app_data` |
| Container Name | `timetracker-app-local-test` | `timetracker-app` |

## Development Tips

1. **Hot Reload**: The development environment supports hot reloading for Python changes
2. **Logs**: Check `./logs/timetracker.log` for detailed application logs
3. **Database**: Use SQLite browser tools for easier database inspection
4. **Testing**: This environment is perfect for testing new features before production deployment

## Security Note

⚠️ **Important**: This local test environment is configured for development only:
- Secure cookies are disabled
- Debug mode is enabled
- Uses a default secret key

**Never use these settings in production!**
