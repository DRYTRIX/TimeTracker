# Database Connection Troubleshooting Guide

This guide helps resolve database connection issues during TimeTracker container startup.

## 🚨 **Common Error: Database Connection Failed**

### **Error Symptoms:**
```
[2025-09-01 19:02:16] Database not ready (attempt 1/30)
[2025-09-01 19:02:18] Database not ready (attempt 2/30)
...
[2025-09-01 19:02:46] Database not ready (attempt 17/30)
```

### **Root Causes:**
1. **PostgreSQL service not fully initialized**
2. **Database container not ready**
3. **Network connectivity issues**
4. **Authentication problems**
5. **Connection string format issues**

## 🔧 **Immediate Solutions**

### **1. Check Database Service Status**
```bash
# Check if database container is running
docker-compose ps db

# Check database container logs
docker-compose logs db

# Check if database is accepting connections
docker-compose exec db pg_isready -U timetracker
```

### **2. Test Database Connection Manually**
```bash
# Test connection from host
docker-compose exec app python /app/docker/test_db_connection.py

# Or test from outside container
docker exec <container_name> python /app/docker/test_db_connection.py
```

### **3. Check Environment Variables**
```bash
# Verify DATABASE_URL is set correctly
docker-compose exec app env | grep DATABASE_URL

# Check if the URL format is correct
echo $DATABASE_URL
```

## 🔍 **Diagnostic Steps**

### **Step 1: Verify Database Container**
```bash
# Check if PostgreSQL container is healthy
docker-compose ps

# Look for these indicators:
# - Status: Up (healthy)
# - Health: healthy
```

### **Step 2: Check Database Logs**
```bash
# View PostgreSQL startup logs
docker-compose logs db | tail -50

# Look for these success indicators:
# - "database system is ready to accept connections"
# - "PostgreSQL init process complete"
# - "database system is ready to accept connections"
```

### **Step 3: Test Network Connectivity**
```bash
# Test if app container can reach database
docker-compose exec app ping db

# Test if database port is accessible
docker-compose exec app nc -zv db 5432
```

### **Step 4: Verify Database Credentials**
```bash
# Check if database user exists
docker-compose exec db psql -U postgres -c "\du"

# Verify database exists
docker-compose exec db psql -U postgres -c "\l"
```

## 🛠️ **Common Fixes**

### **Fix 1: Wait for Database to be Ready**
```bash
# Stop all services
docker-compose down

# Start database first and wait
docker-compose up -d db

# Wait for database to be healthy
docker-compose ps db

# Then start app
docker-compose up -d app
```

### **Fix 2: Check Connection String Format**
```bash
# Correct format for PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database

# If using psycopg2 (automatic)
DATABASE_URL=postgresql+psycopg2://user:password@host:port/database

# Common issues:
# - Missing password
# - Wrong port number
# - Database name doesn't exist
```

### **Fix 3: Verify Database Initialization**
```bash
# Check if database was initialized
docker-compose exec db psql -U timetracker -d timetracker -c "\dt"

# If no tables exist, database might not be initialized
# Check docker/init-database.py or similar scripts
```

### **Fix 4: Check Docker Compose Configuration**
```yaml
# Ensure proper service dependencies
services:
  app:
    depends_on:
      db:
        condition: service_healthy
    # ... other config

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U timetracker"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## 📋 **Troubleshooting Checklist**

### **Before Starting Container:**
- [ ] Database container is running and healthy
- [ ] DATABASE_URL environment variable is set correctly
- [ ] Database user has proper permissions
- [ ] Database exists and is accessible
- [ ] Network connectivity between containers works

### **During Startup:**
- [ ] Container waits for database to be ready
- [ ] Connection string is parsed correctly
- [ ] Authentication succeeds
- [ ] Basic queries can be executed
- [ ] Migration system can access database

### **After Startup:**
- [ ] Database tables are accessible
- [ ] Migration system works correctly
- [ ] Application can read/write data
- [ ] Health checks pass

## 🔧 **Advanced Debugging**

### **Enable Verbose Logging**
```bash
# Set environment variable for verbose logging
export FLASK_DEBUG=1
export PYTHONVERBOSE=1

# Restart container with verbose logging
docker-compose up -d app
```

### **Test Connection Step by Step**
```bash
# 1. Test basic connectivity
docker-compose exec app ping db

# 2. Test port accessibility
docker-compose exec app nc -zv db 5432

# 3. Test PostgreSQL connection
docker-compose exec app python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://timetracker:timetracker@db:5432/timetracker')
    print('Connection successful')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
"

# 4. Test with psycopg2 URL
docker-compose exec app python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker')
    print('Connection successful')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
"
```

### **Check Container Resources**
```bash
# Check if containers have enough resources
docker stats

# Check container logs for resource issues
docker-compose logs app | grep -i "memory\|cpu\|disk"
```

## 🚀 **Prevention Strategies**

### **1. Use Health Checks**
```yaml
# In docker-compose.yml
services:
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U timetracker"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    depends_on:
      db:
        condition: service_healthy
```

### **2. Proper Service Dependencies**
```yaml
# Ensure app waits for database
services:
  app:
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
```

### **3. Connection Retry Logic**
```bash
# The entrypoint script already includes:
# - 60 retry attempts
# - 3-second delays
# - Multiple connection methods
# - Fallback strategies
```

## 📞 **Getting Help**

### **If Problems Persist:**
1. **Check all logs**: `docker-compose logs`
2. **Verify environment**: `docker-compose config`
3. **Test manually**: Use the test script
4. **Check documentation**: See `docker/STARTUP_MIGRATION_CONFIG.md`

### **Useful Commands:**
```bash
# Comprehensive debugging
docker-compose logs -f
docker-compose exec app python /app/docker/test_db_connection.py
docker-compose exec db pg_isready -U timetracker
docker-compose ps
docker network ls
```

---

**Remember**: Most database connection issues are resolved by ensuring the PostgreSQL service is fully initialized before the application container tries to connect. The enhanced entrypoint script includes multiple fallback methods and increased retry logic to handle this automatically.
