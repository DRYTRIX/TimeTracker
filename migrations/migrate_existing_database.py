#!/usr/bin/env python3
"""
Comprehensive Database Migration Script for TimeTracker
This script can migrate ANY existing database to the new Flask-Migrate system
"""

import os
import sys
import subprocess
import sqlite3
import psycopg2
from pathlib import Path
from datetime import datetime
import shutil

def run_command(command, description, capture_output=True):
    """Run a command and handle errors"""
    print(f"\n--- {description} ---")
    print(f"Running: {command}")
    
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"✓ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            subprocess.run(command, shell=True, check=True)
            print(f"✓ {description} completed successfully")
            return True
    except subprocess.CmdProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error code: {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def check_flask_migrate_installed():
    """Check if Flask-Migrate is properly installed"""
    try:
        import flask_migrate
        print("✓ Flask-Migrate is installed")
        return True
    except ImportError:
        print("✗ Flask-Migrate is not installed")
        print("Please install it with: pip install Flask-Migrate")
        return False

def detect_database_type():
    """Detect the type of database being used"""
    db_url = os.getenv('DATABASE_URL', '')
    
    if db_url.startswith('postgresql'):
        return 'postgresql', db_url
    elif db_url.startswith('sqlite'):
        return 'sqlite', db_url
    else:
        # Check for common database files
        if os.path.exists('instance/timetracker.db'):
            return 'sqlite', 'sqlite:///instance/timetracker.db'
        elif os.path.exists('timetracker.db'):
            return 'sqlite', 'sqlite:///timetracker.db'
        else:
            return 'unknown', None

def backup_database(db_type, db_url):
    """Create a comprehensive backup of the current database"""
    print("\n--- Creating Database Backup ---")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.getenv("TT_BACKUP_DIR", "/data/backups")
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        # Fall back to CWD if /data isn't writable
        backup_dir = os.getcwd()
    
    if db_type == 'postgresql':
        backup_file = os.path.join(backup_dir, f"backup_postgresql_{timestamp}.dump")
        backup_cmd = ["pg_dump", "--format=custom", f'--dbname={db_url}', f"--file={backup_file}"]
        print(f"PostgreSQL database detected")
        print(f"Running: {' '.join(backup_cmd)}")
        
        try:
            subprocess.run(backup_cmd, check=True)
            print(f"✓ Database backed up to: {backup_file}")
            return backup_file
        except subprocess.CalledProcessError as e:
            print(f"✗ PostgreSQL backup failed: {e}")
            print("Please ensure pg_dump is available and you have proper permissions")
            return None
            
    elif db_type == 'sqlite':
        # Find the actual database file
        if 'instance/timetracker.db' in db_url:
            db_file = 'instance/timetracker.db'
        elif 'timetracker.db' in db_url:
            db_file = 'timetracker.db'
        else:
            db_file = db_url.replace('sqlite:///', '')
        
        if os.path.exists(db_file):
            backup_file = os.path.join(backup_dir, f"backup_sqlite_{timestamp}.db")
            shutil.copy2(db_file, backup_file)
            print(f"✓ SQLite database backed up to: {backup_file}")
            return backup_file
        else:
            print(f"✗ SQLite database file not found: {db_file}")
            return None
    else:
        print("✗ Unknown database type")
        return None

def analyze_existing_schema(db_type, db_url):
    """Analyze the existing database schema to understand what needs to be migrated"""
    print("\n--- Analyzing Existing Database Schema ---")
    
    if db_type == 'postgresql':
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get list of existing tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Get table schemas
            table_schemas = {}
            for table in existing_tables:
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                table_schemas[table] = columns
            
            conn.close()
            
            print(f"✓ Found {len(existing_tables)} existing tables: {existing_tables}")
            return existing_tables, table_schemas
            
        except Exception as e:
            print(f"✗ Error analyzing PostgreSQL schema: {e}")
            return [], {}
            
    elif db_type == 'sqlite':
        try:
            # Find the actual database file
            if 'instance/timetracker.db' in db_url:
                db_file = 'instance/timetracker.db'
            elif 'timetracker.db' in db_url:
                db_file = 'timetracker.db'
            else:
                db_file = db_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_file):
                print(f"✗ SQLite database file not found: {db_file}")
                return [], {}
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get list of existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Get table schemas
            table_schemas = {}
            for table in existing_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                table_schemas[table] = columns
            
            conn.close()
            
            print(f"✓ Found {len(existing_tables)} existing tables: {existing_tables}")
            return existing_tables, table_schemas
            
        except Exception as e:
            print(f"✗ Error analyzing SQLite schema: {e}")
            return [], {}
    
    return [], {}

def create_migration_strategy(existing_tables, table_schemas):
    """Create a migration strategy based on existing schema"""
    print("\n--- Creating Migration Strategy ---")
    
    # Define expected tables and their priority
    expected_tables = [
        'clients', 'users', 'projects', 'tasks', 'time_entries', 
        'settings', 'invoices', 'invoice_items'
    ]
    
    missing_tables = [table for table in expected_tables if table not in existing_tables]
    existing_but_modified = []
    
    if missing_tables:
        print(f"Tables to create: {missing_tables}")
    
    # Check for schema modifications
    for table in existing_tables:
        if table in expected_tables:
            # This table exists, check if it needs modifications
            print(f"Table '{table}' exists - will preserve data")
    
    return missing_tables, existing_but_modified

def initialize_flask_migrate():
    """Initialize Flask-Migrate if not already initialized"""
    migrations_dir = Path("migrations")
    
    if not migrations_dir.exists():
        print("Initializing Flask-Migrate...")
        return run_command("flask db init", "Initialize Flask-Migrate")
    else:
        print("✓ Migrations directory already exists")
        return True

def create_initial_migration():
    """Create the initial migration that captures the current state"""
    versions_dir = Path("migrations/versions")
    
    if not versions_dir.exists() or not list(versions_dir.glob("*.py")):
        print("Creating initial migration...")
        return run_command("flask db migrate -m 'Initial schema from existing database'", "Create initial migration")
    else:
        print("✓ Initial migration already exists")
        return True

def stamp_database_with_current_revision():
    """Mark the database as being at the current migration revision"""
    print("Stamping database with current migration revision...")
    return run_command("flask db stamp head", "Stamp database with current revision")

def apply_migrations():
    """Apply any pending migrations"""
    return run_command("flask db upgrade", "Apply database migrations")

def verify_migration_success():
    """Verify that the migration was successful"""
    print("\n--- Verifying Migration Success ---")
    
    # Check migration status
    print("Current migration status:")
    run_command("flask db current", "Show current migration", capture_output=False)
    
    # Check migration history
    print("\nMigration history:")
    run_command("flask db history", "Show migration history", capture_output=False)
    
    # Test database connection
    try:
        from app import create_app, db
        app = create_app()
        with app.app_context():
            # Try to query the database
            result = db.session.execute(db.text("SELECT 1"))
            print("✓ Database connection test successful")
            return True
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def create_data_migration_script(existing_tables, table_schemas):
    """Create a data migration script for any existing data"""
    print("\n--- Creating Data Migration Script ---")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Data Migration Script for Existing Database
This script handles data migration from old schema to new schema
\"\"\"

from app import create_app, db
from app.models import User, Project, TimeEntry, Task, Settings, Invoice, Client

def migrate_existing_data():
    \"\"\"Migrate existing data to new schema\"\"\"
    app = create_app()
    
    with app.app_context():
        print("Starting data migration...")
        
        # Add your data migration logic here
        # Example: Migrate old client names to new client table
        
        print("Data migration completed")

if __name__ == "__main__":
    migrate_existing_data()
"""
    
    script_path = "migrations/migrate_existing_data.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"✓ Data migration script created: {script_path}")
    return script_path

def main():
    """Main migration function"""
    print("=== TimeTracker Comprehensive Database Migration ===")
    print("This script will migrate ANY existing database to the new Flask-Migrate system")
    
    # Check prerequisites
    if not check_flask_migrate_installed():
        sys.exit(1)
    
    # Detect database type
    db_type, db_url = detect_database_type()
    if not db_url:
        print("✗ Could not detect database configuration")
        print("Please set DATABASE_URL environment variable or ensure database files exist")
        sys.exit(1)
    
    print(f"✓ Detected {db_type} database")
    
    # Create backup
    print("\n⚠️  IMPORTANT: Creating database backup before proceeding...")
    backup_file = backup_database(db_type, db_url)
    if not backup_file:
        # Never block in non-interactive environments (like Docker startup).
        continue_on_fail = os.getenv("TT_MIGRATE_CONTINUE_ON_BACKUP_FAILURE", "false").strip().lower() in ("1", "true", "yes")
        if sys.stdin.isatty() and not continue_on_fail:
            response = input("Failed to create backup. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                sys.exit(1)
        elif continue_on_fail:
            print("⚠ Continuing without backup (TT_MIGRATE_CONTINUE_ON_BACKUP_FAILURE enabled).")
        else:
            print("✗ Backup failed and input is not interactive. Aborting migration.")
            print("  To force continue, set TT_MIGRATE_CONTINUE_ON_BACKUP_FAILURE=true")
            sys.exit(1)
    
    # Analyze existing schema
    existing_tables, table_schemas = analyze_existing_schema(db_type, db_url)
    
    # Create migration strategy
    missing_tables, modified_tables = create_migration_strategy(existing_tables, table_schemas)
    
    # Initialize Flask-Migrate
    if not initialize_flask_migrate():
        print("Failed to initialize Flask-Migrate")
        sys.exit(1)
    
    # Create initial migration
    if not create_initial_migration():
        print("Failed to create initial migration")
        sys.exit(1)
    
    # Create data migration script if needed
    if existing_tables:
        create_data_migration_script(existing_tables, table_schemas)
    
    # Stamp database with current revision
    if not stamp_database_with_current_revision():
        print("Failed to stamp database")
        sys.exit(1)
    
    # Apply any pending migrations
    if not apply_migrations():
        print("Failed to apply migrations")
        sys.exit(1)
    
    # Verify migration success
    if not verify_migration_success():
        print("Migration verification failed")
        sys.exit(1)
    
    # Show final status
    print("\n=== Migration Complete ===")
    print("🎉 Your database has been successfully migrated to Flask-Migrate!")
    
    print("\nNext steps:")
    print("1. Test your application to ensure everything works")
    print("2. Review the generated migration files in migrations/versions/")
    print("3. If you have existing data, run the data migration script:")
    print("   python migrations/migrate_existing_data.py")
    print("4. For future schema changes, use:")
    print("   - flask db migrate -m 'Description of changes'")
    print("   - flask db upgrade")
    
    print("\nBackup created at:", backup_file)
    print("For more information, see: migrations/README.md")

if __name__ == "__main__":
    main()
