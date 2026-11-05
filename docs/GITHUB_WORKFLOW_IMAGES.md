# GitHub Workflow Docker Images with Database Initialization

This guide explains how the TimeTracker Docker images built through GitHub workflows automatically handle database initialization and port exposure.

## Overview

The GitHub workflows build Docker images that include:
- **Automatic database connection checking**
- **Database initialization logic**
- **Port 8080 properly exposed**
- **Health checks and monitoring**

## Workflow Images

### 1. External Database Image (`docker-publish-external.yml`)
- **Image**: `ghcr.io/drytrix/timetracker-externaldb`
- **Uses**: `Dockerfile` (copied to `Dockerfile.final`)
- **Purpose**: For deployments with external PostgreSQL databases
- **Features**:
  - Waits for external database to be ready
  - Checks if database is initialized
  - Auto-initializes missing tables
  - Port 8080 exposed

### 2. Internal Database Image (`docker-publish-internal.yml`)
- **Image**: `ghcr.io/drytrix/timetracker-internaldb`
- **Uses**: `Dockerfile.simple` (copied to `Dockerfile.final`)
- **Purpose**: For all-in-one deployments with built-in PostgreSQL
- **Features**:
  - Starts PostgreSQL internally
  - Auto-initializes database
  - Creates tables and default data
  - Port 8080 exposed

### 3. Combined Image (`Dockerfile.combined`)
- **Purpose**: For complex deployments with multiple services
- **Features**:
  - PostgreSQL + Flask app in one container
  - Supervisor for process management
  - Auto-database initialization
  - Ports 8080 and 5432 exposed

## How Database Initialization Works

### Step 1: Database Connection Check
```bash
# Wait for PostgreSQL to be ready
python -c "
import os, time, sys
from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL', '')
if url.startswith('postgresql'):
    for attempt in range(30):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print('Database connection established successfully')
            break
        except Exception as e:
            print(f'Waiting for database... (attempt {attempt+1}/30): {e}')
            time.sleep(2)
    else:
        print('Database not ready after waiting, exiting...')
        sys.exit(1)
"
```

### Step 2: Initialization Check
```bash
# Check if required tables exist
python -c "
import os, sys
from sqlalchemy import create_engine, text, inspect

url = os.getenv('DATABASE_URL', '')
if url.startswith('postgresql'):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        existing_tables = inspector.get_table_names()
        required_tables = ['users', 'projects', 'time_entries', 'settings']

        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f'Database not fully initialized. Missing tables: {missing_tables}')
            sys.exit(1)  # Trigger initialization
        else:
            print('Database is already initialized')
            sys.exit(0)  # Skip initialization
    except Exception as e:
        print(f'Error checking database: {e}')
        sys.exit(1)
"
```

### Step 3: Database Initialization
```bash
if [ $? -eq 1 ]; then
    echo "Initializing database..."
    python /app/docker/init-database.py
    if [ $? -eq 0 ]; then
        echo "Database initialized successfully"
    else
        echo "Database initialization failed, but continuing..."
    fi
else
    echo "Database already initialized, skipping initialization"
fi
```

## Port Exposure

All images properly expose port 8080:

```dockerfile
# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/_health || exit 1
```

## Using the Images

### External Database Deployment
```yaml
# docker-compose.yml
services:
  app:
    image: ghcr.io/drytrix/timetracker-externaldb:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@host:5432/db
    restart: unless-stopped
```

### Internal Database Deployment
```yaml
# docker-compose.yml
services:
  app:
    image: ghcr.io/drytrix/timetracker-internaldb:latest
    ports:
      - "8080:8080"
    restart: unless-stopped
```

### Direct Docker Run
```bash
# External database
docker run -d -p 8080:8080 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  ghcr.io/drytrix/timetracker-externaldb:latest

# Internal database (all-in-one)
docker run -d -p 8080:8080 \
  ghcr.io/drytrix/timetracker-internaldb:latest
```

## Environment Variables

### Required for External Database
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### Optional for All Images
```bash
TZ=Europe/Rome
CURRENCY=EUR
ROUNDING_MINUTES=1
SINGLE_ACTIVE_TIMER=true
ALLOW_SELF_REGISTER=true
IDLE_TIMEOUT_MINUTES=30
ADMIN_USERNAMES=admin
SECRET_KEY=your-secret-key-change-this
```

## What Happens on Startup

1. **Container starts** with the built-in startup script
2. **Database connection check** waits for PostgreSQL to be ready
3. **Initialization check** verifies required tables exist
4. **Auto-initialization** runs if needed using Python script
5. **Flask application** starts normally
6. **Port 8080** is accessible from the host

## Benefits

- **No manual database setup** required
- **Automatic table creation** and default data
- **Port 8080 always available** in Docker Desktop
- **Health checks** ensure application is ready
- **Error handling** continues even if initialization fails
- **Fast startup** for already-initialized databases

## Troubleshooting

### Port Not Visible in Docker Desktop
- Ensure you're using the built images, not building locally
- Check that the container is running: `docker ps`
- Verify port mapping: `docker port <container_id>`

### Database Initialization Issues
```bash
# Check container logs
docker logs <container_id>

# Test database manually
docker exec <container_id> python /app/docker/test-db.py

# Check database status
docker exec <container_id> python /app/docker/init-database.py
```

### Health Check Failures
- Ensure the `/_health` endpoint is accessible
- Check if the app is binding to the correct port
- Verify network connectivity

## Workflow Triggers

The images are automatically built and published on:
- **Push to main branch**: Latest development version
- **Tagged releases**: Versioned releases (v1.0.0, v2.0.0, etc.)
- **Manual dispatch**: Manual workflow triggers
- **Pull requests**: Build verification (not published)

## Image Tags

- **`latest`**: Most recent successful build
- **`main`**: Latest main branch build
- **`v*`**: Versioned releases (v1.0.0, v2.0.0, etc.)
- **`<commit-sha>`**: Specific commit builds

Now when you deploy these images from the GitHub Container Registry, they will automatically handle database initialization and expose port 8080 properly in Docker Desktop!
