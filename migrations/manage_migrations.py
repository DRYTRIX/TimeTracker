#!/usr/bin/env python3
"""
Migration Management Script for TimeTracker
This script helps manage the transition from custom migrations to Flask-Migrate
"""

import os
import sys
import subprocess
import shlex
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors
    
    Args:
        command: Command string to run (will be split into list)
        description: Human-readable description of the command
    """
    print(f"\n--- {description} ---")
    print(f"Running: {command}")
    
    # Split command into list to avoid shell injection
    # Handle quoted arguments properly
    import shlex
    try:
        cmd_list = shlex.split(command)
    except ValueError:
        # Fallback to simple split if shlex fails
        cmd_list = command.split()
    
    try:
        result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
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

def initialize_migrations():
    """Initialize Flask-Migrate if not already initialized"""
    migrations_dir = Path("migrations")
    
    if not migrations_dir.exists():
        print("Initializing Flask-Migrate...")
        return run_command("flask db init", "Initialize Flask-Migrate")
    else:
        print("✓ Migrations directory already exists")
        return True

def create_initial_migration():
    """Create the initial migration if it doesn't exist"""
    versions_dir = Path("migrations/versions")
    
    if not versions_dir.exists() or not list(versions_dir.glob("*.py")):
        print("Creating initial migration...")
        return run_command("flask db migrate -m 'Initial database schema'", "Create initial migration")
    else:
        print("✓ Initial migration already exists")
        return True

def apply_migrations():
    """Apply all pending migrations"""
    return run_command("flask db upgrade", "Apply database migrations")

def show_migration_status():
    """Show current migration status"""
    return run_command("flask db current", "Show current migration")

def show_migration_history():
    """Show migration history"""
    return run_command("flask db history", "Show migration history")

def backup_database():
    """Create a backup of the current database"""
    print("\n--- Creating Database Backup ---")
    
    # Check if we're using PostgreSQL or SQLite
    db_url = os.getenv('DATABASE_URL', '')
    
    if db_url.startswith('postgresql'):
        print("PostgreSQL database detected")
        backup_cmd = "pg_dump --format=custom --dbname=\"$DATABASE_URL\" --file=backup_$(date +%Y%m%d_%H%M%S).dump"
        print(f"Please run: {backup_cmd}")
        return True
    else:
        print("SQLite database detected")
        # For SQLite, we'll just copy the file
        if os.path.exists('instance/timetracker.db'):
            import shutil
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_timetracker_{timestamp}.db"
            shutil.copy2('instance/timetracker.db', backup_file)
            print(f"✓ Database backed up to: {backup_file}")
            return True
        else:
            print("SQLite database file not found")
            return False

def main():
    """Main migration management function"""
    print("=== TimeTracker Migration Management ===")
    print("This script will help you transition to Flask-Migrate")
    
    # Check prerequisites
    if not check_flask_migrate_installed():
        sys.exit(1)
    
    # Create backup
    print("\n⚠️  IMPORTANT: Creating database backup before proceeding...")
    if not backup_database():
        print("Failed to create backup. Please create one manually before proceeding.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(1)
    
    # Initialize migrations
    if not initialize_migrations():
        print("Failed to initialize migrations")
        sys.exit(1)
    
    # Create initial migration
    if not create_initial_migration():
        print("Failed to create initial migration")
        sys.exit(1)
    
    # Show current status
    show_migration_status()
    
    # Apply migrations
    print("\n⚠️  About to apply migrations to your database...")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled. You can run 'flask db upgrade' manually later.")
        return
    
    if not apply_migrations():
        print("Failed to apply migrations")
        sys.exit(1)
    
    # Show final status
    print("\n=== Migration Complete ===")
    show_migration_status()
    show_migration_history()
    
    print("\n🎉 Migration to Flask-Migrate completed successfully!")
    print("\nNext steps:")
    print("1. Test your application to ensure everything works")
    print("2. For future schema changes, use:")
    print("   - flask db migrate -m 'Description of changes'")
    print("   - flask db upgrade")
    print("3. To rollback: flask db downgrade")
    print("4. To check status: flask db current")

if __name__ == "__main__":
    main()
