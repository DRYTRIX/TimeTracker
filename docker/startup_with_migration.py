#!/usr/bin/env python3
"""
Enhanced Startup Script with Automatic Migration Detection
This script automatically detects database state and chooses the correct migration strategy
"""

import os
import sys
import time
import subprocess
import sqlite3
import psycopg2
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
try:
    # Ensure logs directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/logs/timetracker_startup.log')
        ]
    )
except Exception as e:
    # Fallback to console-only logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    print(f"Warning: Could not set up file logging: {e}")
logger = logging.getLogger(__name__)

def wait_for_database(db_url, max_retries=60, retry_delay=3):
    """Wait for database to be available"""
    logger.info(f"Waiting for database to be available: {db_url}")
    
    for attempt in range(max_retries):
        try:
            if db_url.startswith('postgresql'):
                # Handle both postgresql:// and postgresql+psycopg2:// URLs
                clean_url = db_url.replace('+psycopg2://', '://')
                conn = psycopg2.connect(clean_url)
                conn.close()
                logger.info("✓ PostgreSQL database is available")
                return True
            elif db_url.startswith('sqlite'):
                # For SQLite, just check if the file exists or can be created
                db_file = db_url.replace('sqlite:///', '')
                if os.path.exists(db_file) or os.access(os.path.dirname(db_file), os.W_OK):
                    logger.info("✓ SQLite database is available")
                    return True
        except Exception as e:
            logger.info(f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.error("Database is not available after maximum retries")
    return False

def detect_database_state(db_url):
    """Detect the current state of the database"""
    logger.info("Analyzing database state...")
    
    try:
        if db_url.startswith('postgresql'):
            # Handle both postgresql:// and postgresql+psycopg2:// URLs
            clean_url = db_url.replace('+psycopg2://', '://')
            conn = psycopg2.connect(clean_url)
            cursor = conn.cursor()
            
            # Check if alembic_version table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """)
            has_alembic = cursor.fetchone()[0]
            
            # Get list of existing tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check if this is a fresh database
            is_fresh = len(existing_tables) == 0
            
            conn.close()
            
            logger.info(f"Database state: has_alembic={has_alembic}, tables={existing_tables}, is_fresh={is_fresh}")
            
            if has_alembic:
                return 'migrated', existing_tables
            elif existing_tables:
                return 'legacy', existing_tables
            else:
                return 'fresh', []
                
        elif db_url.startswith('sqlite'):
            db_file = db_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_file):
                return 'fresh', []
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check if alembic_version table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
            has_alembic = cursor.fetchone() is not None
            
            # Get list of existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            logger.info(f"Database state: has_alembic={has_alembic}, tables={existing_tables}")
            
            if has_alembic:
                return 'migrated', existing_tables
            elif existing_tables:
                return 'legacy', existing_tables
            else:
                return 'fresh', []
    
    except Exception as e:
        logger.error(f"Error detecting database state: {e}")
        return 'unknown', []
    
    return 'unknown', []

def choose_migration_strategy(db_state, existing_tables):
    """Choose the appropriate migration strategy based on database state"""
    logger.info(f"Choosing migration strategy for state: {db_state}")
    
    if db_state == 'fresh':
        logger.info("Fresh database detected - using standard initialization")
        return 'fresh_init'
    
    elif db_state == 'migrated':
        logger.info("Database already migrated - checking for pending migrations")
        return 'check_migrations'
    
    elif db_state == 'legacy':
        logger.info("Legacy database detected - using comprehensive migration")
        return 'comprehensive_migration'
    
    else:
        logger.warning("Unknown database state - using comprehensive migration as fallback")
        return 'comprehensive_migration'

def execute_migration_strategy(strategy, db_url):
    """Execute the chosen migration strategy"""
    logger.info(f"Executing migration strategy: {strategy}")
    
    try:
        if strategy == 'fresh_init':
            return execute_fresh_init(db_url)
        elif strategy == 'check_migrations':
            return execute_check_migrations(db_url)
        elif strategy == 'comprehensive_migration':
            return execute_comprehensive_migration(db_url)
        else:
            logger.error(f"Unknown migration strategy: {strategy}")
            return False
    except Exception as e:
        logger.error(f"Error executing migration strategy: {e}")
        return False

def execute_fresh_init(db_url):
    """Execute fresh database initialization"""
    logger.info("Executing fresh database initialization...")
    
    try:
        # Initialize Flask-Migrate
        result = subprocess.run(['flask', 'db', 'init'], 
                              capture_output=True, text=True, check=True)
        logger.info("✓ Flask-Migrate initialized")
        
        # Create initial migration
        result = subprocess.run(['flask', 'db', 'migrate', '-m', 'Initial database schema'], 
                              capture_output=True, text=True, check=True)
        logger.info("✓ Initial migration created")
        
        # Apply migration
        result = subprocess.run(['flask', 'db', 'upgrade'], 
                              capture_output=True, text=True, check=True)
        logger.info("✓ Initial migration applied")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Fresh init failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def execute_check_migrations(db_url):
    """Check and apply any pending migrations"""
    logger.info("Checking for pending migrations...")
    
    try:
        # Check current migration status
        result = subprocess.run(['flask', 'db', 'current'], 
                              capture_output=True, text=True, check=True)
        current_revision = result.stdout.strip()
        logger.info(f"Current migration revision: {current_revision}")

        # If multiple heads exist and we're already at a head, avoid upgrading to "heads"
        # because Alembic can raise:
        #   Requested revision X overlaps with other requested revisions ...
        heads_result = subprocess.run(['flask', 'db', 'heads'], capture_output=True, text=True)
        heads_output = (heads_result.stdout or "").strip()
        head_lines = [ln for ln in heads_output.splitlines() if ln.strip()]
        head_count = len(head_lines)

        if "(head)" in current_revision and head_count > 1:
            logger.warning(
                f"Multiple migration heads detected ({head_count}), but database is already at a head. "
                "Skipping migration upgrade during startup."
            )
            for ln in head_lines:
                logger.warning(f"[HEAD] {ln}")
            return True
        
        # Check for pending migrations
        upgrade_cmd = ['flask', 'db', 'upgrade']
        if head_count > 1:
            upgrade_cmd = ['flask', 'db', 'upgrade', 'heads']

        result = subprocess.run(upgrade_cmd, capture_output=True, text=True, check=True)
        logger.info("✓ Migrations checked and applied")
        
        return True
        
    except subprocess.CalledProcessError as e:
        # If we're already at a head, tolerate Alembic overlap errors (multi-head history)
        combined = (e.stdout or "") + "\n" + (e.stderr or "")
        if "(head)" in locals().get("current_revision", "") and "overlaps with other requested revisions" in combined:
            logger.warning(
                "Migration upgrade reported overlapping heads, but DB is already at a head. Continuing startup."
            )
            return True
        logger.error(f"Migration check failed: {e}")
        return False

def execute_comprehensive_migration(db_url):
    """Execute comprehensive migration for legacy databases"""
    logger.info("Executing comprehensive migration...")
    
    try:
        # Run the comprehensive migration script
        migration_script = '/app/migrations/migrate_existing_database.py'
        
        if os.path.exists(migration_script):
            result = subprocess.run(['python', migration_script], 
                                  capture_output=True, text=True, check=True)
            logger.info("✓ Comprehensive migration completed")
            return True
        else:
            logger.warning("Comprehensive migration script not found, falling back to manual migration")
            return execute_manual_migration(db_url)
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Comprehensive migration failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def execute_manual_migration(db_url):
    """Execute manual migration as fallback"""
    logger.info("Executing manual migration fallback...")
    
    try:
        # Initialize Flask-Migrate if not already done
        if not os.path.exists('/app/migrations/env.py'):
            result = subprocess.run(['flask', 'db', 'init'], 
                                  capture_output=True, text=True, check=True)
            logger.info("✓ Flask-Migrate initialized")
        
        # Create baseline migration
        result = subprocess.run(['flask', 'db', 'migrate', '-m', 'Baseline from existing database'], 
                              capture_output=True, text=True, check=True)
        logger.info("✓ Baseline migration created")
        
        # Stamp database as current
        result = subprocess.run(['flask', 'db', 'stamp', 'head'], 
                              capture_output=True, text=True, check=True)
        logger.info("✓ Database stamped as current")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Manual migration failed: {e}")
        return False

def verify_database_integrity(db_url):
    """Verify that the database is working correctly after migration"""
    logger.info("Verifying database integrity...")
    
    try:
        # Test basic database operations
        if db_url.startswith('postgresql'):
            # Handle both postgresql:// and postgresql+psycopg2:// URLs
            clean_url = db_url.replace('+psycopg2://', '://')
            conn = psycopg2.connect(clean_url)
            cursor = conn.cursor()
            
            # Check if key tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('users', 'projects', 'time_entries')
                AND table_schema = 'public'
            """)
            key_tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            if len(key_tables) >= 2:  # At least users and projects
                logger.info("✓ Database integrity verified")
                return True
            else:
                logger.error(f"Missing key tables: {key_tables}")
                return False
                
        elif db_url.startswith('sqlite'):
            db_file = db_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_file):
                logger.error("SQLite database file not found")
                return False
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check if key tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'projects', 'time_entries')
            """)
            key_tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            if len(key_tables) >= 2:  # At least users and projects
                logger.info("✓ Database integrity verified")
                return True
            else:
                logger.error(f"Missing key tables: {key_tables}")
                return False
    
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")
        return False
    
    return False

def main():
    """Main startup function"""
    logger.info("=== TimeTracker Enhanced Startup with Migration Detection ===")
    
    # Set environment variables
    os.environ.setdefault('FLASK_APP', '/app/app.py')
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    logger.info(f"Database URL: {db_url}")
    
    # Wait for database to be available
    if not wait_for_database(db_url):
        logger.error("Failed to connect to database")
        sys.exit(1)
    
    # Detect database state
    db_state, existing_tables = detect_database_state(db_url)
    logger.info(f"Detected database state: {db_state} with {len(existing_tables)} tables")
    
    # Choose migration strategy
    strategy = choose_migration_strategy(db_state, existing_tables)
    logger.info(f"Selected migration strategy: {strategy}")
    
    # Execute migration strategy
    if not execute_migration_strategy(strategy, db_url):
        logger.error("Migration strategy execution failed")
        sys.exit(1)
    
    # Verify database integrity
    if not verify_database_integrity(db_url):
        logger.error("Database integrity verification failed")
        sys.exit(1)
    
    logger.info("=== Startup and Migration Complete ===")
    logger.info("Database is ready for use")
    
    # Show final migration status
    try:
        result = subprocess.run(['flask', 'db', 'current'], 
                              capture_output=True, text=True, check=True)
        logger.info(f"Final migration status: {result.stdout.strip()}")
    except:
        logger.info("Could not determine final migration status")

if __name__ == "__main__":
    main()
