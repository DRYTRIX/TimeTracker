#!/usr/bin/env python3
"""
Python entrypoint script for TimeTracker Docker container
This avoids shell script line ending issues and provides better error handling
"""

import os
import sys
import time
import subprocess
import traceback
import psycopg2
from urllib.parse import urlparse

def log(message):
    """Log message with timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def wait_for_database():
    """Wait for database to be ready"""
    log("Waiting for database to be available...")
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        log("✗ DATABASE_URL environment variable not set")
        return False
    
    log(f"Database URL: {db_url}")
    
    max_attempts = 30
    retry_delay = 2
    
    for attempt in range(1, max_attempts + 1):
        log(f"Attempt {attempt}/{max_attempts} to connect to database...")
        
        try:
            if db_url.startswith('postgresql'):
                # Parse connection string
                if db_url.startswith('postgresql+psycopg2://'):
                    db_url = db_url.replace('postgresql+psycopg2://', '')
                
                if '@' in db_url:
                    auth_part, rest = db_url.split('@', 1)
                    user, password = auth_part.split(':', 1)
                    if ':' in rest:
                        host_port, database = rest.rsplit('/', 1)
                        if ':' in host_port:
                            host, port = host_port.split(':', 1)
                        else:
                            host, port = host_port, '5432'
                    else:
                        host, port, database = rest, '5432', 'timetracker'
                else:
                    host, port, database, user, password = 'db', '5432', 'timetracker', 'timetracker', 'timetracker'
                
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    connect_timeout=5
                )
                conn.close()
                log("✓ PostgreSQL database is available")
                return True
                
            elif db_url.startswith('sqlite://'):
                db_file = db_url.replace('sqlite://', '')
                if os.path.exists(db_file) or os.access(os.path.dirname(db_file), os.W_OK):
                    log("✓ SQLite database is available")
                    return True
                else:
                    log("SQLite file not accessible")
            else:
                log(f"Unknown database URL format: {db_url}")
                
        except Exception as e:
            log(f"Database connection failed: {e}")
        
        if attempt < max_attempts:
            log(f"Waiting {retry_delay} seconds before next attempt...")
            time.sleep(retry_delay)
    
    log("✗ Database is not available after maximum retries")
    return False

def run_migrations():
    """Run database migrations"""
    log("Checking migrations...")
    
    try:
        # Check if migrations directory exists
        if os.path.exists("/app/migrations"):
            log("Migrations directory exists, checking status...")
            
            # Try to apply any pending migrations
            result = subprocess.run(['flask', 'db', 'upgrade'], 
                                  capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                log("✓ Migrations applied successfully")
                
                # Verify all columns from models exist and fix if missing
                log("Verifying complete database schema against models...")
                fix_result = subprocess.run(
                    ['python', '/app/scripts/verify_and_fix_schema.py'],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if fix_result.returncode == 0:
                    # Print output to show what was fixed
                    if fix_result.stdout:
                        for line in fix_result.stdout.strip().split('\n'):
                            if line.strip() and not line.startswith('='):
                                log(line)
                    log("✓ Database schema verified and fixed")
                else:
                    log(f"⚠ Schema verification had issues: {fix_result.stderr}")
                    # Fallback to the simpler fix script
                    log("Attempting fallback column fix...")
                    fallback_result = subprocess.run(
                        ['python', '/app/scripts/fix_missing_columns.py'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if fallback_result.returncode == 0:
                        log("✓ Fallback fix completed")
                
                return True
            else:
                log(f"⚠ Migration application failed: {result.stderr}")
                # Try to fix missing columns even if migration failed
                log("Attempting to fix missing columns...")
                fix_result = subprocess.run(
                    ['python', '/app/scripts/verify_and_fix_schema.py'],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if fix_result.returncode == 0:
                    if fix_result.stdout:
                        for line in fix_result.stdout.strip().split('\n'):
                            if line.strip() and not line.startswith('='):
                                log(line)
                    log("✓ Missing columns fixed")
                else:
                    # Fallback to simpler script
                    log("Trying fallback fix...")
                    fallback_result = subprocess.run(
                        ['python', '/app/scripts/fix_missing_columns.py'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if fallback_result.returncode == 0:
                        log("✓ Fallback fix completed")
                return False
        else:
            log("No migrations directory found, initializing...")
            
            # Initialize migrations
            result = subprocess.run(['flask', 'db', 'init'], 
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                log("✓ Migrations initialized")
                
                # Create initial migration
                result = subprocess.run(['flask', 'db', 'migrate', '-m', 'Initial schema'], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    log("✓ Initial migration created")
                    
                    # Apply migration
                    result = subprocess.run(['flask', 'db', 'upgrade'], 
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        log("✓ Initial migration applied")
                        return True
                    else:
                        log(f"⚠ Initial migration application failed: {result.stderr}")
                        return False
                else:
                    log(f"⚠ Initial migration creation failed: {result.stderr}")
                    return False
            else:
                log(f"⚠ Migration initialization failed: {result.stderr}")
                return False
                
    except subprocess.TimeoutExpired:
        log("⚠ Migration operation timed out")
        return False
    except Exception as e:
        log(f"⚠ Migration error: {e}")
        return False

def main():
    """Main entrypoint function"""
    log("=== TimeTracker Docker Entrypoint ===")
    
    # Set environment variables
    os.environ.setdefault('FLASK_APP', '/app/app.py')
    
    # Wait for database
    if not wait_for_database():
        log("✗ Failed to connect to database")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        log("⚠ Migration issues detected, continuing anyway")
    
    log("=== Startup Complete ===")
    log("Starting TimeTracker application...")
    
    # Execute the command passed to the container
    if len(sys.argv) > 1:
        try:
            os.execv(sys.argv[1], sys.argv[1:])
        except Exception as e:
            log(f"✗ Failed to execute command: {e}")
            sys.exit(1)
    else:
        # Default command
        try:
            os.execv('/usr/bin/python', ['python', '/app/start.py'])
        except Exception as e:
            log(f"✗ Failed to execute default command: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
