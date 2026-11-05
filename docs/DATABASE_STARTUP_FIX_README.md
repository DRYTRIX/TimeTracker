# Database Startup Fix

## Problem Description

The TimeTracker application was experiencing startup failures due to incorrect database initialization order. The main issue was:

1. **Dependency Order Problem**: The `tasks` table has a foreign key reference to `projects(id)`, but the startup scripts were trying to create the `tasks` table before the `projects` table existed.

2. **Script Execution Order**: The startup sequence was running `init-database.py` first (which tried to create tables using Flask models), then `init-database-sql.py` (which created basic tables), but the `tasks` table was missing from the SQL script.

3. **Error Message**:
   ```
   Error creating tasks table: (psycopg2.errors.UndefinedTable) relation "projects" does not exist
   ```

## Root Cause

The `tasks` table creation was embedded in the shell script (`start-new.sh`) but was failing because:
- It referenced `projects(id)` before the `projects` table was created
- The table creation logic was scattered across multiple scripts
- No proper dependency management between table creation steps

## Solution Implemented

### 1. Fixed Database Initialization Order

**Before**:
- `init-database.py` runs first → fails to create tasks table
- `init-database-sql.py` runs second → creates basic tables but missing tasks

**After**:
- `init-database-sql.py` runs first → creates all basic tables including tasks
- `init-database.py` runs second → handles Flask-specific setup

### 2. Added Tasks Table to SQL Script

Updated `docker/init-database-sql.py` to include the `tasks` table creation:

```sql
-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
    assigned_to INTEGER REFERENCES users(id),
    created_by INTEGER REFERENCES users(id) NOT NULL,
    due_date DATE,
    estimated_hours NUMERIC(5,2),
    actual_hours NUMERIC(5,2),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

### 3. Updated Table Verification

- Added `tasks` to the required tables list in `init-database-sql.py`
- Added trigger for automatic `updated_at` column updates
- Updated main init script to not fail if tasks table is missing initially

### 4. Improved Startup Scripts

Created multiple startup options:

- **`docker/start-fixed.py`**: Python-based startup with proper error handling
- **`docker/start-fixed.sh`**: Shell script version with correct execution order
- **`docker/test-database-complete.py`**: Comprehensive database verification script

### 5. Updated Dockerfile

- Changed from `start-new.sh` to `start-fixed.py`
- Updated CMD to use Python script
- Maintained all existing functionality

## Files Modified

1. **`docker/init-database-sql.py`**
   - Added tasks table creation
   - Added tasks to required tables list
   - Added trigger for tasks table

2. **`docker/init-database.py`**
   - Modified to not fail if tasks table missing initially
   - Updated schema checking to skip tasks table validation

3. **`docker/start.py`**
   - Swapped execution order of initialization scripts

4. **`Dockerfile`**
   - Updated to use improved startup script

5. **New Files Created**:
   - `docker/start-fixed.py` - Improved Python startup script
   - `docker/start-fixed.sh` - Fixed shell startup script
   - `docker/test-database-complete.py` - Database verification script

## How to Use

### Option 1: Use Python Startup Script (Recommended)
```bash
# In Dockerfile or docker-compose
CMD ["python", "/app/start.py"]
```

### Option 2: Use Shell Startup Script
```bash
# In Dockerfile or docker-compose
CMD ["/app/start-fixed.sh"]
```

### Option 3: Test Database Setup
```bash
# Run verification script
python docker/test-database-complete.py
```

## Verification

After the fix, the startup sequence should show:

```
=== Starting TimeTracker ===
Waiting for database to be ready...
Database connection established successfully
=== RUNNING DATABASE INITIALIZATION ===
Step 1: Running SQL database initialization...
✓ SQL database initialization completed
Step 2: Running main database initialization...
✓ Main database initialization completed
✓ All database initialization completed successfully
Starting application...
```

## Benefits

1. **Reliable Startup**: Tables are created in the correct dependency order
2. **Better Error Handling**: Clear error messages and proper exit codes
3. **Maintainable Code**: Centralized table creation logic
4. **Flexible Options**: Multiple startup script options for different needs
5. **Comprehensive Testing**: Database verification script for troubleshooting

## Troubleshooting

If you still encounter issues:

1. **Check Database Logs**: Look for specific error messages
2. **Run Verification Script**: Use `test-database-complete.py` to check table status
3. **Verify Environment**: Ensure `DATABASE_URL` is properly set
4. **Check Permissions**: Ensure database user has CREATE TABLE permissions

## Future Improvements

1. **Migration System**: Implement proper database migrations instead of table recreation
2. **Dependency Graph**: Create explicit dependency management for table creation
3. **Rollback Support**: Add ability to rollback failed initialization
4. **Health Checks**: Implement database health checks during startup
