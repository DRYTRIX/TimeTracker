# Database Migrations with Flask-Migrate

This directory contains the database migration system for TimeTracker, now standardized on Flask-Migrate with proper versioning.

## Overview

The migration system has been updated from custom Python scripts to use Flask-Migrate, which provides:
- **Standardized migrations** using Alembic
- **Version tracking** for all database changes
- **Rollback capabilities** to previous versions
- **Automatic schema detection** from SQLAlchemy models
- **Cross-database compatibility** (PostgreSQL, SQLite)

## Quick Start

### 1. Initialize Migrations (First Time Only)
```bash
flask db init
```

### 2. Create Your First Migration
```bash
flask db migrate -m "Initial database schema"
```

### 3. Apply Migrations
```bash
flask db upgrade
```

## Migration Commands

### Basic Commands
- `flask db init` - Initialize migrations directory
- `flask db migrate -m "Description"` - Create a new migration
- `flask db upgrade` - Apply pending migrations
- `flask db downgrade` - Rollback last migration
- `flask db current` - Show current migration version
- `flask db history` - Show migration history

### Advanced Commands
- `flask db show <revision>` - Show specific migration details
- `flask db stamp <revision>` - Mark database as being at specific revision
- `flask db heads` - Show current heads (for branched migrations)

## Migration Workflow

### 1. Make Model Changes
Edit your SQLAlchemy models in `app/models/`:
```python
# Example: Add a new column
class User(db.Model):
    # ... existing fields ...
    phone_number = db.Column(db.String(20), nullable=True)
```

### 2. Generate Migration
```bash
flask db migrate -m "Add phone number to users"
```

### 3. Review Generated Migration
Check the generated migration file in `migrations/versions/`:
```python
def upgrade():
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))

def downgrade():
    op.drop_column('users', 'phone_number')
```

### 4. Apply Migration
```bash
flask db upgrade
```

### 5. Verify Changes
Check the migration status:
```bash
flask db current
```

## Migration Files Structure

```
migrations/
├── versions/           # Migration files
│   ├── 001_initial_schema.py
│   ├── 002_add_phone_number.py
│   └── ...
├── env.py             # Migration environment
├── script.py.mako     # Migration template
├── alembic.ini        # Alembic configuration
└── README.md          # This file
```

## Transition from Old System

If you're migrating from the old custom migration system:

### 1. Backup Your Database
```bash
# PostgreSQL
pg_dump --format=custom --dbname="$DATABASE_URL" --file=backup_$(date +%Y%m%d_%H%M%S).dump

# SQLite
cp instance/timetracker.db backup_timetracker_$(date +%Y%m%d_%H%M%S).db
```

### 2. Use Migration Management Script
```bash
python migrations/manage_migrations.py
```

### 3. Or Manual Migration
```bash
# Initialize Flask-Migrate
flask db init

# Create initial migration (captures current schema)
flask db migrate -m "Initial schema from existing database"

# Apply migration
flask db upgrade
```

## Best Practices

### 1. Migration Naming
Use descriptive names for migrations:
```bash
flask db migrate -m "Add user profile fields"
flask db migrate -m "Create project categories table"
flask db migrate -m "Add invoice payment tracking"
```

### 2. Testing Migrations
Always test migrations on a copy of your production data:
```bash
# Test upgrade
flask db upgrade

# Test downgrade
flask db downgrade

# Verify data integrity
```

### 3. Backup Before Migrations
```bash
# Always backup before major migrations
flask db backup  # Custom command
# or
pg_dump --format=custom --dbname="$DATABASE_URL" --file=pre_migration_backup.dump
```

### 4. Review Generated Code
Always review auto-generated migrations before applying:
- Check the `upgrade()` function
- Verify the `downgrade()` function
- Ensure data types and constraints are correct

## Troubleshooting

### Common Issues

#### 1. Migration Already Applied
```bash
# Check current status
flask db current

# If migration is already applied, stamp the database
flask db stamp <revision>
```

#### 2. Migration Conflicts
```bash
# Show migration heads
flask db heads

# Merge branches if needed
flask db merge -m "Merge migration branches" <revision1> <revision2>
```

#### 3. Database Out of Sync
```bash
# Check migration history
flask db history

# Reset to specific revision
flask db stamp <revision>
```

#### 4. Model Import Errors
Ensure all models are imported in your application:
```python
# In app/__init__.py or similar
from app.models import User, Project, TimeEntry, Task, Settings, Invoice, Client
```

### Getting Help

1. Check the migration status: `flask db current`
2. Review migration history: `flask db history`
3. Check Alembic logs for detailed error messages
4. Verify database connection and permissions

## Advanced Features

### Custom Migration Operations
You can add custom operations in your migrations:
```python
def upgrade():
    # Custom data migration
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")

    # Custom table operations
    op.create_index('custom_idx', 'table_name', ['column_name'])
```

### Data Migrations
For complex data migrations, use the `op.execute()` method:
```python
def upgrade():
    # Migrate existing data
    op.execute("""
        INSERT INTO new_table (id, name)
        SELECT id, name FROM old_table
    """)
```

### Conditional Migrations
Handle different database types:
```python
def upgrade():
    # PostgreSQL-specific operations
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
```

## Environment Variables

Ensure these environment variables are set:
```bash
export FLASK_APP=app.py
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
# or
export DATABASE_URL="sqlite:///instance/timetracker.db"
```

## CI/CD Integration

For automated deployments, include migration steps:
```yaml
# Example GitHub Actions step
- name: Run database migrations
  run: |
    flask db upgrade
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Support

For migration-related issues:
1. Check this README
2. Review Flask-Migrate documentation: https://flask-migrate.readthedocs.io/
3. Check Alembic documentation: https://alembic.sqlalchemy.org/
4. Review generated migration files for errors
