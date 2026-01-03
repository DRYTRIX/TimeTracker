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

def _env_truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")

def run_flask_migrate_upgrade(timeout: int = 180) -> None:
    """
    Run Flask-Migrate upgrade to ensure schema exists.

    This is intentionally lightweight compared to the legacy startup scripts.
    It prevents "relation ... does not exist" errors on fresh databases,
    especially on platforms where preDeployCommand may be skipped or misconfigured.
    """
    log("Running Flask-Migrate: flask db upgrade", "INFO")
    try:
        # Use "python -m flask" (more reliable than relying on PATH) and point
        # explicitly to app.py so the CLI loads the app instance.
        result = subprocess.run(
            [sys.executable, "-m", "flask", "--app", "app.py", "db", "upgrade"],
            check=True,
            capture_output=False,
            text=True,
            timeout=timeout,
        )
        _ = result  # silence linter/linters that flag unused
        log("Flask-Migrate upgrade completed", "SUCCESS")
    except subprocess.TimeoutExpired:
        log("Flask-Migrate upgrade timed out", "ERROR")
        raise
    except subprocess.CalledProcessError as e:
        log(f"Flask-Migrate upgrade failed with exit code {e.returncode}", "ERROR")
        raise

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

def bootstrap_system_admin():
    """
    Ensure a global/system admin user exists (not tied to any tenant).

    This is important for SaaS multi-tenant deployments where we may skip the
    legacy init scripts and rely on migrations only.
    """
    if not _env_truthy("BOOTSTRAP_SYSTEM_ADMIN", default=True):
        return

    admin_username = (os.getenv("ADMIN_USERNAMES", "admin").split(",")[0] or "admin").strip().lower()
    if not admin_username:
        admin_username = "admin"

    admin_password = (os.getenv("SYSTEM_ADMIN_PASSWORD", "") or "").strip()

    try:
        from app import create_app, db
        from app.models import User, Role

        flask_app = create_app()
        with flask_app.app_context():
            existing = User.query.filter_by(username=admin_username).first()
            if existing:
                return

            user = User(username=admin_username, role="admin")
            # Optionally set an initial password; otherwise user can set it on first login.
            if admin_password:
                user.set_password(admin_password)
                user.password_change_required = False

            role_obj = Role.query.filter_by(name="admin").first()
            if role_obj:
                user.roles.append(role_obj)

            db.session.add(user)
            db.session.commit()
            log(f"Bootstrapped system admin user '{admin_username}'", "SUCCESS")
    except Exception as e:
        # Best-effort: never block startup if bootstrap fails.
        try:
            log(f"Could not bootstrap system admin user: {type(e).__name__}", "WARNING")
        except Exception:
            pass

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

    # Ensure schema exists (very important on fresh databases).
    # If the user disables the container init scripts (SKIP_DB_INIT=true),
    # we still must ensure migrations are applied.
    if _env_truthy("RUN_MIGRATIONS_ON_START", default=False) or _env_truthy("SKIP_DB_INIT", default=False):
        try:
            run_flask_migrate_upgrade(timeout=int(os.getenv("MIGRATIONS_TIMEOUT_SECONDS", "180")))
        except Exception:
            log("Database migrations failed, exiting...", "ERROR")
            sys.exit(1)
    
    # Run enhanced database initialization and migration (optional)
    if _env_truthy("SKIP_DB_INIT", default=False):
        log("SKIP_DB_INIT=true set; skipping database initialization in container startup.", "WARNING")
    else:
        log("Running database initialization...", "INFO")
        if not run_script('/app/docker/init-database-enhanced.py', 'Database initialization'):
            log("Database initialization failed, exiting...", "ERROR")
            sys.exit(1)
        log("Database initialization completed", "SUCCESS")

    # Ensure a system admin exists (global, not tenant-scoped).
    bootstrap_system_admin()

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
