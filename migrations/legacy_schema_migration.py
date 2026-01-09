#!/usr/bin/env python3
"""
Legacy Schema Migration Script for TimeTracker
This script handles migration from old custom migration system to Flask-Migrate
"""

import os
import sys
from pathlib import Path

def migrate_legacy_schema():
    """Migrate from legacy schema to new Flask-Migrate system"""
    print("=== Legacy Schema Migration ===")
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("Error: Please run this script from the TimeTracker root directory")
        return False
    
    # Set environment variables
    os.environ.setdefault('FLASK_APP', 'app.py')
    
    try:
        from app import create_app, db
        app = create_app()
        
        with app.app_context():
            print("✓ Application context created")
            
            # Check current database state
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print(f"Found {len(existing_tables)} existing tables: {existing_tables}")
            
            # Handle legacy schema issues
            if 'projects' in existing_tables:
                migrate_projects_table(db)
            
            if 'settings' in existing_tables:
                migrate_settings_table(db)
            
            print("✓ Legacy schema migration completed")
            return True
            
    except Exception as e:
        print(f"✗ Error during legacy schema migration: {e}")
        return False

def migrate_projects_table(db):
    """Migrate projects table from legacy schema"""
    print("Migrating projects table...")
    
    try:
        # Check if projects table has old 'client' column
        inspector = db.inspect(db.engine)
        project_columns = [col['name'] for col in inspector.get_columns('projects')]
        
        if 'client' in project_columns and 'client_id' not in project_columns:
            print("  - Converting projects.client to projects.client_id")
            
            # Create clients table if it doesn't exist
            if 'clients' not in inspector.get_table_names():
                print("  - Creating clients table")
                db.session.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(200) UNIQUE NOT NULL,
                        description TEXT,
                        contact_person VARCHAR(200),
                        email VARCHAR(200),
                        phone VARCHAR(50),
                        address TEXT,
                        default_hourly_rate NUMERIC(9, 2),
                        status VARCHAR(20) DEFAULT 'active' NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                """))
            
            # Add client_id column
            db.session.execute(db.text("""
                ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_id INTEGER
            """))
            
            # Migrate existing client names to clients table
            db.session.execute(db.text("""
                INSERT INTO clients (name, status)
                SELECT DISTINCT client, 'active' FROM projects
                WHERE client IS NOT NULL AND client <> ''
                ON CONFLICT (name) DO NOTHING
            """))
            
            # Update projects to reference clients
            db.session.execute(db.text("""
                UPDATE projects p
                SET client_id = c.id
                FROM clients c
                WHERE p.client_id IS NULL AND p.client = c.name
            """))
            
            # Create index
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id)
            """))
            
            print("  - Projects table migration completed")
            
    except Exception as e:
        print(f"  - Warning: Projects table migration failed: {e}")

def migrate_settings_table(db):
    """Migrate settings table from legacy schema"""
    print("Migrating settings table...")
    
    try:
        inspector = db.inspect(db.engine)
        settings_columns = [col['name'] for col in inspector.get_columns('settings')]
        
        # Add missing columns that the new system expects
        missing_columns = [
            ('allow_analytics', 'BOOLEAN DEFAULT TRUE'),
            ('logo_path', 'VARCHAR(500)'),
            ('company_website', 'VARCHAR(200)')
        ]
        
        for col_name, col_def in missing_columns:
            if col_name not in settings_columns:
                print(f"  - Adding missing column: {col_name}")
                db.session.execute(db.text(f"""
                    ALTER TABLE settings ADD COLUMN {col_name} {col_def}
                """))
        
        print("  - Settings table migration completed")
        
    except Exception as e:
        print(f"  - Warning: Settings table migration failed: {e}")

def create_migration_baseline():
    """Create a migration baseline for the current database state"""
    print("Creating migration baseline...")
    
    import subprocess
    import shlex
    
    try:
        # Initialize Flask-Migrate if not already done
        if not Path("migrations/env.py").exists():
            print("  - Initializing Flask-Migrate")
            try:
                subprocess.run(['flask', 'db', 'init'], check=True)
            except subprocess.CalledProcessError as e:
                print(f"  - Failed to initialize Flask-Migrate: {e}")
                return False
        
        # Create initial migration
        print("  - Creating initial migration")
        try:
            subprocess.run(['flask', 'db', 'migrate', '-m', 'Baseline from legacy schema'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"  - Failed to create migration: {e}")
            return False
        
        # Stamp database as being at this revision
        print("  - Stamping database")
        try:
            subprocess.run(['flask', 'db', 'stamp', 'head'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"  - Failed to stamp database: {e}")
            return False
        
        print("✓ Migration baseline created")
        return True
        
    except Exception as e:
        print(f"✗ Error creating migration baseline: {e}")
        return False

def main():
    """Main function"""
    print("=== TimeTracker Legacy Schema Migration ===")
    print("This script migrates from the old custom migration system to Flask-Migrate")
    
    # Step 1: Migrate legacy schema
    if not migrate_legacy_schema():
        print("Legacy schema migration failed")
        sys.exit(1)
    
    # Step 2: Create migration baseline
    if not create_migration_baseline():
        print("Migration baseline creation failed")
        sys.exit(1)
    
    print("\n=== Migration Complete ===")
    print("🎉 Your legacy database has been successfully migrated!")
    
    print("\nNext steps:")
    print("1. Test your application to ensure everything works")
    print("2. Review the generated migration files in migrations/versions/")
    print("3. For future schema changes, use:")
    print("   - flask db migrate -m 'Description of changes'")
    print("   - flask db upgrade")
    print("4. To check status: flask db current")
    print("5. To view history: flask db history")

if __name__ == "__main__":
    main()
