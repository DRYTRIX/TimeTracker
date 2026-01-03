#!/usr/bin/env python3
"""
Improved Python startup script for TimeTracker
This script ensures proper database initialization order and handles errors gracefully
"""

import os
import sys
import time
import subprocess
import traceback
import psycopg2
from urllib.parse import urlparse

def wait_for_database():
    """Wait for database to be ready with proper connection testing"""
    # Logging is handled by main()
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker')

    # If using SQLite, ensure the database directory exists and return immediately
    if db_url.startswith('sqlite:'):
        try:
            # Normalize file path from URL
            db_path = None
            prefix_four = 'sqlite:////'
            prefix_three = 'sqlite:///'
            prefix_mem = 'sqlite://'
            if db_url.startswith(prefix_four):
                db_path = '/' + db_url[len(prefix_four):]
            elif db_url.startswith(prefix_three):
                # Relative inside container; keep as-is
                db_path = db_url[len(prefix_three):]
                # If it's a relative path, make sure directory exists
                if not db_path.startswith('/'):
                    db_path = '/' + db_path
            elif db_url.startswith(prefix_mem):
                # Could be sqlite:///:memory:
                if db_url.endswith(':memory:'):
                    return True
                # Fallback: strip scheme
                db_path = db_url[len(prefix_mem):]

            if db_path:
                import os as _os
                import sqlite3 as _sqlite3
                dir_path = _os.path.dirname(db_path)
                if dir_path:
                    _os.makedirs(dir_path, exist_ok=True)
                # Try to open the database to ensure writability
                conn = _sqlite3.connect(db_path)
                conn.close()
            return True
        except Exception as e:
            print(f"SQLite path/setup check failed: {e}")
            return False
    
    # Parse the URL to get connection details (PostgreSQL)
    # Handle both postgresql:// and postgresql+psycopg2:// schemes
    if db_url.startswith('postgresql'):
        if db_url.startswith('postgresql+psycopg2://'):
            parsed_url = urlparse(db_url.replace('postgresql+psycopg2://', 'postgresql://'))
        else:
            parsed_url = urlparse(db_url)
        
        # Extract connection parameters
        user = parsed_url.username or 'timetracker'
        password = parsed_url.password or 'timetracker'
        host = parsed_url.hostname or 'db'
        port = parsed_url.port or 5432
        # Remove leading slash from path to get database name
        database = parsed_url.path.lstrip('/') or 'timetracker'
    else:
        # Fallback for other formats
        host, port, database, user, password = 'db', '5432', 'timetracker', 'timetracker', 'timetracker'
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception as e:
            attempt += 1
            if attempt < max_attempts:
                time.sleep(2)
    
    return False

def run_script(script_path, description):
    """Run a Python script with proper error handling"""
    try:
        result = subprocess.run(
            [sys.executable, script_path], 
            check=True,
            capture_output=False,  # Let the script output directly
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        log(f"{description} failed with exit code {e.returncode}", "ERROR")
        return False
    except Exception as e:
        log(f"Unexpected error running {description}: {e}", "ERROR")
        return False

def display_network_info():
    """Display network information for debugging"""
    print("=== Network Information ===")
    try:
        print(f"Hostname: {os.uname().nodename}")
    except:
        print("Hostname: N/A (Windows)")
    
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Local IP: {local_ip}")
    except:
        print("Local IP: N/A")
    
    print(f"Environment: {os.environ.get('FLASK_APP', 'N/A')}")
    print(f"Working Directory: {os.getcwd()}")
    print("==========================")

def log(message, level="INFO"):
    """Log message with timestamp and level"""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = {
        "INFO": "ℹ",
        "SUCCESS": "✓",
        "WARNING": "⚠",
        "ERROR": "✗"
    }.get(level, "•")
    print(f"[{timestamp}] {prefix} {message}")

def main():
    log("=" * 60, "INFO")
    log("Starting TimeTracker Application", "INFO")
    log("=" * 60, "INFO")
    
    # Set environment
    os.environ['FLASK_APP'] = 'app'
    os.chdir('/app')
    
    # Wait for database
    log("Waiting for database connection...", "INFO")
    if not wait_for_database():
        log("Database is not available, exiting...", "ERROR")
        sys.exit(1)
    
    # Run enhanced database initialization and migration (optional)
    if (os.getenv("SKIP_DB_INIT", "") or "").strip().lower() in ("1", "true", "yes", "y", "on"):
        log("SKIP_DB_INIT=true set; skipping database initialization in container startup.", "WARNING")
    else:
        log("Running database initialization...", "INFO")
        if not run_script('/app/docker/init-database-enhanced.py', 'Database initialization'):
            log("Database initialization failed, exiting...", "ERROR")
            sys.exit(1)
        log("Database initialization completed", "SUCCESS")
    
    # Ensure default settings and admin user exist (idempotent)
    # Note: Database initialization is already handled by the migration system above
    # The flask init_db command is optional and may not be available in all environments
    try:
        result = subprocess.run(
            ['flask', 'init_db'],
            check=False,  # Don't fail if command doesn't exist
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0 and "No such command" not in (result.stderr or ""):
            log("flask init_db returned non-zero exit code (continuing)", "WARNING")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # All errors are non-fatal - database is already initialized
        pass

    log("=" * 60, "INFO")
    log("Starting application server", "INFO")
    log("=" * 60, "INFO")
    # Start gunicorn with access logs
    port = os.getenv("PORT", "8080")
    bind = f"0.0.0.0:{port}"
    os.execv('/usr/local/bin/gunicorn', [
        'gunicorn',
        '--bind', bind,
        '--worker-class', 'eventlet',
        '--workers', '1',
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        'app:create_app()'
    ])

if __name__ == '__main__':
    main()
