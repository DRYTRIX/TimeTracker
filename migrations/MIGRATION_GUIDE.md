# Complete Database Migration Guide

This guide covers **ALL** possible migration scenarios from any previous database state to the new Flask-Migrate system.

## 🎯 Migration Scenarios Covered

### 1. **Fresh Installation** (No existing database)
- New project setup
- First-time deployment

### 2. **Existing Database with Old Custom Migrations**
- Legacy migration scripts
- Custom Python migration files
- Manual schema changes

### 3. **Existing Database with Mixed Schema**
- Some tables exist, some missing
- Incomplete schema
- Partial migrations

### 4. **Existing Database with Data**
- Production databases with user data
- Development databases with test data
- Staging databases

### 5. **Database from Different Versions**
- Old TimeTracker versions
- Different schema versions
- Incompatible table structures

## 🚀 Migration Methods

### **Method 1: Automated Migration (Recommended)**

#### **For Any Existing Database:**
```bash
# Run the comprehensive migration script
python migrations/migrate_existing_database.py
```

This script will:
- ✅ Detect your database type (PostgreSQL/SQLite)
- ✅ Create a complete backup
- ✅ Analyze existing schema
- ✅ Create migration strategy
- ✅ Initialize Flask-Migrate
- ✅ Create baseline migration
- ✅ Preserve all existing data
- ✅ Verify migration success

#### **For Legacy Schema Migration:**
```bash
# Run the legacy schema migration script
python migrations/legacy_schema_migration.py
```

This script handles:
- ✅ Old `projects.client` → `projects.client_id` conversion
- ✅ Missing columns in settings table
- ✅ Legacy table structures
- ✅ Data preservation

### **Method 2: Manual Migration**

#### **Step-by-Step Process:**

1. **Backup Your Database**
   ```bash
   # PostgreSQL
   pg_dump --format=custom --dbname="$DATABASE_URL" --file=backup_$(date +%Y%m%d_%H%M%S).dump

   # SQLite
   cp instance/timetracker.db backup_timetracker_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Initialize Flask-Migrate**
   ```bash
   flask db init
   ```

3. **Create Baseline Migration**
   ```bash
   flask db migrate -m "Baseline from existing database"
   ```

4. **Review Generated Migration**
   ```bash
   # Check the generated file in migrations/versions/
   cat migrations/versions/*.py
   ```

5. **Stamp Database as Current**
   ```bash
   flask db stamp head
   ```

6. **Apply Any Pending Migrations**
   ```bash
   flask db upgrade
   ```

### **Method 3: Setup Scripts**

#### **Windows:**
```bash
scripts\setup-migrations.bat
```

#### **Linux/Mac:**
```bash
scripts/setup-migrations.sh
```

#### **Python (Cross-platform):**
```bash
python migrations/manage_migrations.py
```

## 🔍 Pre-Migration Analysis

### **Check Your Current State:**

```bash
# Check if Flask-Migrate is available
python -c "import flask_migrate; print('✓ Flask-Migrate available')"

# Check database connection
python -c "from app import create_app; app = create_app(); print('✓ Database accessible')"

# Check existing tables (if any)
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'Existing tables: {tables}')
"
```

### **Common Database States:**

| State | Description | Migration Approach |
|-------|-------------|-------------------|
| **No Database** | Fresh installation | `flask db init` → `flask db migrate` → `flask db upgrade` |
| **Empty Database** | Tables exist but no data | `flask db stamp head` → `flask db upgrade` |
| **Partial Schema** | Some tables missing | Run comprehensive migration script |
| **Legacy Schema** | Old table structures | Run legacy schema migration script |
| **Complete Schema** | All tables exist | `flask db stamp head` |

## 🛡️ Safety Measures

### **Automatic Backups:**
- ✅ Database backup before any migration
- ✅ Timestamped backup files
- ✅ Multiple backup formats (dump, copy)
- ✅ Backup verification

### **Migration Verification:**
- ✅ Schema analysis before migration
- ✅ Data integrity checks
- ✅ Rollback capability
- ✅ Migration status verification

### **Error Handling:**
- ✅ Graceful failure handling
- ✅ Detailed error messages
- ✅ Recovery instructions
- ✅ Safe fallback options

## 📋 Migration Checklist

### **Before Migration:**
- [ ] **Backup your database** (automatic with scripts)
- [ ] **Check disk space** (need space for backup + migration)
- [ ] **Stop application** (if running)
- [ ] **Verify dependencies** (Flask-Migrate installed)
- [ ] **Check permissions** (database access)

### **During Migration:**
- [ ] **Run migration script** (automatic or manual)
- [ ] **Review generated files** (check migrations/versions/)
- [ ] **Verify backup creation** (check backup files)
- [ ] **Monitor progress** (watch for errors)

### **After Migration:**
- [ ] **Test application** (start and verify functionality)
- [ ] **Check migration status** (`flask db current`)
- [ ] **Verify data integrity** (check key tables)
- [ ] **Update deployment scripts** (if using CI/CD)

## 🔧 Troubleshooting

### **Common Issues & Solutions:**

#### **1. Migration Already Applied**
```bash
# Check current status
flask db current

# If migration is already applied, stamp the database
flask db stamp head
```

#### **2. Schema Conflicts**
```bash
# Show migration heads
flask db heads

# Merge branches if needed
flask db merge -m "Merge migration branches" <revision1> <revision2>
```

#### **3. Database Out of Sync**
```bash
# Check migration history
flask db history

# Reset to specific revision
flask db stamp <revision>
```

#### **4. Permission Errors**
```bash
# Check database permissions
# Ensure user has CREATE, ALTER, INSERT privileges
# For PostgreSQL: GRANT ALL PRIVILEGES ON DATABASE timetracker TO timetracker;
```

#### **5. Connection Issues**
```bash
# Verify DATABASE_URL environment variable
echo $DATABASE_URL

# Test connection manually
python -c "from app import create_app; app = create_app(); print('Connection OK')"
```

### **Recovery Options:**

#### **If Migration Fails:**
1. **Check backup files** - your data is safe
2. **Review error logs** - identify the issue
3. **Fix the problem** - resolve conflicts/errors
4. **Restart migration** - run script again

#### **If Data is Lost:**
1. **Restore from backup** - use pg_restore or copy SQLite file
2. **Verify restoration** - check data integrity
3. **Contact support** - if issues persist

## 📚 Advanced Migration Scenarios

### **Handling Complex Schema Changes:**

#### **Custom Data Migrations:**
```python
# In your migration file
def upgrade():
    # Custom data transformation
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")

    # Complex table modifications
    op.execute("""
        INSERT INTO new_table (id, name, status)
        SELECT id, name, 'active' FROM old_table
        WHERE status = 'enabled'
    """)
```

#### **Conditional Migrations:**
```python
def upgrade():
    # Handle different database types
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    elif op.get_bind().dialect.name == 'sqlite':
        # SQLite-specific operations
        pass
```

#### **Rollback Strategies:**
```python
def downgrade():
    # Always provide rollback capability
    op.drop_table('new_table')
    op.drop_column('existing_table', 'new_column')
```

## 🚀 Post-Migration

### **Verification Steps:**
```bash
# Check migration status
flask db current

# View migration history
flask db history

# Test database connection
python -c "from app import create_app, db; app = create_app(); print('OK')"

# Verify key tables
python -c "
from app import create_app, db
from app.models import User, Project, TimeEntry
app = create_app()
with app.app_context():
    users = User.query.count()
    projects = Project.query.count()
    entries = TimeEntry.query.count()
    print(f'Users: {users}, Projects: {projects}, Entries: {entries}')
"
```

### **Future Migrations:**
```bash
# Create new migration
flask db migrate -m "Add new feature"

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

## 📞 Support & Help

### **Getting Help:**
1. **Check this guide** - covers most scenarios
2. **Review migration logs** - detailed error information
3. **Check Flask-Migrate docs** - https://flask-migrate.readthedocs.io/
4. **Check Alembic docs** - https://alembic.sqlalchemy.org/

### **Emergency Recovery:**
```bash
# If everything fails, restore from backup
# PostgreSQL:
pg_restore --clean --dbname="$DATABASE_URL" backup_file.dump

# SQLite:
cp backup_file.db instance/timetracker.db
```

## 🎉 Success Indicators

Your migration is successful when:
- ✅ `flask db current` shows a revision number
- ✅ `flask db history` shows migration timeline
- ✅ Application starts without database errors
- ✅ All existing data is accessible
- ✅ New features work correctly
- ✅ Backup files are created and accessible

---

**Remember**: The migration scripts are designed to be **safe** and **reversible**. Your data is automatically backed up, and you can always restore if needed. When in doubt, run the comprehensive migration script - it handles all scenarios automatically!
