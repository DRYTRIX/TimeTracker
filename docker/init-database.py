#!/usr/bin/env python3
"""
Database initialization script for TimeTracker
This script checks if the database is connected and initialized,
and initializes it if needed.
"""

import os
import sys
import time
import traceback
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

def wait_for_database(url, max_attempts=30, delay=2):
    """Wait for database to be ready"""
    print(f"Waiting for database to be ready...")
    
    for attempt in range(max_attempts):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection established successfully")
            return engine
        except Exception as e:
            print(f"Waiting for database... (attempt {attempt+1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                print("Database not ready after waiting, exiting...")
                sys.exit(1)
    
    return None

def check_database_initialization(engine):
    """Check if database is initialized by looking for required tables and correct schema"""
    print("Checking if database is initialized...")
    
    try:
        inspector = inspect(engine)
        
        # Check if our main tables exist
        existing_tables = inspector.get_table_names()
        required_tables = ['users', 'projects', 'time_entries', 'settings']
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"Database not fully initialized. Missing tables: {missing_tables}")
            return False
        else:
            print("✓ All required tables exist")
            
            # Check if tables have the correct schema
            print("Checking table schemas...")
            
            # Check if time_entries has task_id column
            if 'time_entries' in existing_tables:
                time_entries_columns = [col['name'] for col in inspector.get_columns('time_entries')]
                print(f"Debug: time_entries columns found: {time_entries_columns}")
                if 'task_id' not in time_entries_columns:
                    print(f"✗ time_entries table missing task_id column. Available columns: {time_entries_columns}")
                    return False
                else:
                    print("✓ time_entries table has correct schema")
            
            # Check if tasks table exists
            if 'tasks' not in existing_tables:
                print("⚠ tasks table missing - will be created by SQL script")
                # Don't return False here, let the SQL script handle it
            else:
                print("✓ tasks table exists")
            
            print("✓ Database is already initialized with all required tables and correct schema")
            return True
            
    except Exception as e:
        print(f"Error checking database initialization: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def check_table_schema(engine, table_name, required_columns):
    """Check if a table has the required columns"""
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return False
        
        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"Table {table_name} missing columns: {missing_columns}")
            return False
        
        return True
    except Exception as e:
        print(f"Error checking schema for {table_name}: {e}")
        return False

def ensure_correct_schema(engine):
    """Ensure all tables have the correct schema"""
    print("Checking table schemas...")
    
    # Define required columns for each table
    required_columns = {
        'time_entries': ['id', 'user_id', 'project_id', 'task_id', 'start_time', 'end_time', 
                        'duration_seconds', 'notes', 'tags', 'source', 'billable', 'created_at', 'updated_at']
        # Note: tasks table is created by SQL script, not checked here
    }
    
    needs_recreation = False
    
    for table_name, columns in required_columns.items():
        if not check_table_schema(engine, table_name, columns):
            print(f"Table {table_name} needs recreation")
            needs_recreation = True
    
    return needs_recreation



def initialize_database(engine):
    """Initialize database using Flask CLI command"""
    print("Initializing database...")
    
    try:
        # Set environment variables for Flask
        os.environ['FLASK_APP'] = 'app'
        os.environ['FLASK_ENV'] = 'production'
        
        print("Importing Flask app...")
        
        # Import Flask app and initialize database
        from app import create_app, db
        from app.models import User, Project, TimeEntry, Settings
        
        print("Creating Flask app...")
        app = create_app()
        
        print("Setting up app context...")
        with app.app_context():
            # Check if we need to recreate tables due to schema mismatch
            if ensure_correct_schema(engine):
                print("Schema mismatch detected, dropping and recreating tables...")
                db.drop_all()
                print("All tables dropped")
            
            print("Creating all tables...")
            # Create all tables
            db.create_all()
            
            print("Verifying tables were created...")
            # Verify tables were created
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            print(f"Tables after creation: {existing_tables}")
            
            # Create default admin user if it doesn't exist
            admin_username = os.getenv('ADMIN_USERNAMES', 'admin').split(',')[0]
            print(f"Checking for admin user: {admin_username}")
            
            if not User.query.filter_by(username=admin_username).first():
                print("Creating admin user...")
                admin_user = User(
                    username=admin_username,
                    role='admin'
                )
                admin_user.is_active = True
                db.session.add(admin_user)
                db.session.commit()
                print(f"Created default admin user: {admin_username}")
            else:
                print(f"Admin user {admin_username} already exists")
            
            # Create default settings if they don't exist
            print("Checking for default settings...")
            if not Settings.query.first():
                print("Creating default settings...")
                settings = Settings()
                db.session.add(settings)
                db.session.commit()
                print("Created default settings")
            else:
                print("Default settings already exist")
            
            # Import installation config to check if initial data has been seeded
            from app.utils.installation import get_installation_config
            installation_config = get_installation_config()
            
            # Only create default project/client on fresh installations
            # Check if initial data has already been seeded
            if not installation_config.is_initial_data_seeded():
                print("Checking for default project...")
                if not Project.query.first():
                    print("Creating default project and client (fresh installation)...")
                    project = Project(
                        name='General',
                        client='Default Client',
                        description='Default project for general tasks',
                        billable=True,
                        status='active'
                    )
                    db.session.add(project)
                    db.session.commit()
                    print("Created default project and client")
                    
                    # Mark that initial data has been seeded
                    installation_config.mark_initial_data_seeded()
                    print("Marked initial data as seeded")
                else:
                    print("Projects already exist, marking initial data as seeded")
                    installation_config.mark_initial_data_seeded()
            else:
                print("Initial data already seeded previously, skipping default project/client creation")
            
            print("Database initialized successfully")
            return True
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    url = os.getenv("DATABASE_URL", "")
    
    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping initialization")
        return
    
    print(f"Database URL: {url}")
    
    # Wait for database to be ready
    engine = wait_for_database(url)
    
    # Check if database is initialized
    print("=== Starting database initialization check ===")
    if not check_database_initialization(engine):
        print("=== Database not initialized, starting initialization ===")
        # Initialize database
        if initialize_database(engine):
            print("Database initialization completed successfully")
            
            # Verify initialization worked
            if check_database_initialization(engine):
                print("Database verification successful")
            else:
                print("Database verification failed - tables still missing")
                sys.exit(1)
        else:
            print("Database initialization failed")
            sys.exit(1)
    else:
        print("=== Database already initialized, checking if reinitialization is needed ===")
        
        # Even if database is initialized, double-check schema and reinitialize if needed
        print("Double-checking schema for existing database...")
        if ensure_correct_schema(engine):
            print("Schema mismatch detected in existing database, reinitializing...")
            if initialize_database(engine):
                print("Database reinitialization completed successfully")
                
                # Verify reinitialization worked
                if check_database_initialization(engine):
                    print("Database verification successful after reinitialization")
                else:
                    print("Database verification failed after reinitialization")
                    sys.exit(1)
            else:
                print("Database reinitialization failed")
                sys.exit(1)
        else:
            print("Schema is correct, no reinitialization needed")

if __name__ == "__main__":
    main()
