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

def _truthy(v: str) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "y", "on")

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

def detect_corrupted_database_state(app):
    """Detect if database is in a corrupted/inconsistent state.
    
    Returns: (is_corrupted: bool, reason: str)
    """
    try:
        from app import db
        from sqlalchemy import text
        
        with app.app_context():
            # Check PostgreSQL
            if os.getenv("DATABASE_URL", "").startswith("postgresql"):
                # Get all tables
                all_tables_result = db.session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
                )
                all_tables = [row[0] for row in all_tables_result]
                
                # Check for alembic_version
                has_alembic_version = 'alembic_version' in all_tables
                
                # Check for core tables
                core_tables = ['users', 'projects', 'time_entries', 'settings', 'clients']
                has_core_tables = any(t in all_tables for t in core_tables)
                
                # Database is corrupted if:
                # 1. Has tables but no alembic_version (migrations were never applied)
                # 2. Has tables but no core tables (partial/corrupted state)
                # 3. Has alembic_version but no core tables (migrations failed)
                
                if len(all_tables) > 0 and not has_alembic_version and not has_core_tables:
                    # Has tables but they're not our tables - likely test/manual tables
                    return True, f"Database has {len(all_tables)} table(s) but no alembic_version or core tables. Tables: {all_tables}"
                
                if has_alembic_version and not has_core_tables:
                    return True, "alembic_version exists but core tables are missing - migrations may have failed"
                    
                if len(all_tables) > 0 and has_core_tables and not has_alembic_version:
                    return True, "Core tables exist but alembic_version is missing - database state is inconsistent"
                    
            # SQLite
            else:
                all_tables_result = db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                )
                all_tables = [row[0] for row in all_tables_result]
                
                has_alembic_version = 'alembic_version' in all_tables
                core_tables = ['users', 'projects', 'time_entries', 'settings', 'clients']
                has_core_tables = any(t in all_tables for t in core_tables)
                
                if len(all_tables) > 0 and not has_alembic_version and not has_core_tables:
                    return True, f"Database has {len(all_tables)} table(s) but no alembic_version or core tables"
                    
                if has_alembic_version and not has_core_tables:
                    return True, "alembic_version exists but core tables are missing"
                    
                if len(all_tables) > 0 and has_core_tables and not has_alembic_version:
                    return True, "Core tables exist but alembic_version is missing"
                    
            return False, ""
    except Exception as e:
        # Can't determine - assume not corrupted
        return False, f"Could not check database state: {e}"


def cleanup_corrupted_database_state(app):
    """Attempt to clean up corrupted database state by removing unexpected tables.
    
    This is only safe when:
    - Database has tables but NO alembic_version (migrations never ran)
    - Database has tables but NO core tables (corrupted/partial state)
    - User can disable with TT_SKIP_DB_CLEANUP env var
    
    Only removes tables when it's safe (no alembic_version = migrations haven't run yet).
    """
    if os.getenv("TT_SKIP_DB_CLEANUP", "").strip().lower() in ("1", "true", "yes"):
        log("Database cleanup skipped (TT_SKIP_DB_CLEANUP is set)", "INFO")
        return False
        
    try:
        from app import db
        from sqlalchemy import text
        
        with app.app_context():
            # Only cleanup if PostgreSQL (SQLite cleanup is more risky)
            if not os.getenv("DATABASE_URL", "").startswith("postgresql"):
                return False
                
            # Get all tables
            all_tables_result = db.session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
            )
            all_tables = [row[0] for row in all_tables_result]
            
            # Check if alembic_version exists
            has_alembic_version = 'alembic_version' in all_tables
            
            # Only cleanup if alembic_version does NOT exist (migrations haven't run)
            # If alembic_version exists, migrations have run and we shouldn't drop tables
            if has_alembic_version:
                log("alembic_version table exists - skipping cleanup (migrations may have run)", "INFO")
                return False
                
            # Check for core tables
            core_tables = ['users', 'projects', 'time_entries', 'settings', 'clients']
            has_core_tables = any(t in all_tables for t in core_tables)
            
            # Only cleanup if we have tables but no core tables (corrupted state)
            if not all_tables:
                return False  # Empty database, nothing to clean
                
            if has_core_tables:
                log("Core tables exist - skipping cleanup", "INFO")
                return False
                
            # We have tables but no alembic_version and no core tables
            # These are likely test/manual tables that prevent migrations
            log(f"Attempting to clean up {len(all_tables)} unexpected table(s): {all_tables}", "INFO")
            log("These appear to be test/manual tables that prevent migrations from running.", "INFO")
            
            # Drop all unexpected tables
            cleaned = False
            for table in all_tables:
                try:
                    log(f"Dropping unexpected table: {table}", "INFO")
                    db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    db.session.commit()
                    log(f"✓ Dropped table: {table}", "SUCCESS")
                    cleaned = True
                except Exception as e:
                    log(f"Failed to drop table {table}: {e}", "WARNING")
                    db.session.rollback()
                    
            return cleaned
    except Exception as e:
        log(f"Database cleanup failed: {e}", "WARNING")
        import traceback
        traceback.print_exc()
        return False


def run_migrations():
    """Apply Alembic migrations once (fast path)."""
    log("Applying database migrations (Flask-Migrate)...", "INFO")

    # Prevent app from starting background jobs / DB-dependent init during migrations
    os.environ["TT_BOOTSTRAP_MODE"] = "migrate"
    os.environ.setdefault("FLASK_APP", "app")
    os.environ.setdefault("FLASK_ENV", os.getenv("FLASK_ENV", "production") or "production")
    os.chdir("/app")

    try:
        from flask_migrate import upgrade
        from app import create_app

        app = create_app()
        # Log the DB URL we're about to use (mask password)
        try:
            raw = os.environ.get("DATABASE_URL", "")
            masked = raw
            if "://" in raw and "@" in raw:
                import re as _re

                masked = _re.sub(r"//([^:]+):[^@]+@", r"//\\1:***@", raw)
            log(f"DATABASE_URL (env): {masked}", "INFO")
        except Exception:
            pass

        with app.app_context():
            # Check for corrupted database state BEFORE migrations
            is_corrupted, reason = detect_corrupted_database_state(app)
            if is_corrupted:
                log(f"⚠ Detected corrupted database state: {reason}", "WARNING")
                log("Attempting automatic cleanup...", "INFO")
                
                if cleanup_corrupted_database_state(app):
                    log("✓ Database cleanup completed", "SUCCESS")
                    log("Retrying migrations after cleanup...", "INFO")
                else:
                    log("Database cleanup was skipped or failed", "WARNING")
                    log("Migrations will still be attempted, but may fail.", "WARNING")
            
            # Sanity: show which DB we're connected to before migrating
            try:
                from app import db as _db
                from sqlalchemy import text as _text

                cur_db = _db.session.execute(_text("select current_database()")).scalar()
                table_count = _db.session.execute(
                    _text("select count(1) from information_schema.tables where table_schema='public'")
                ).scalar()
                log(f"Pre-migration DB: {cur_db} (public tables={table_count})", "INFO")
            except Exception as e:
                log(f"Pre-migration DB probe failed: {e}", "WARNING")

            # Use heads to handle branched histories safely
            upgrade(revision="heads")

            # CRITICAL: Verify migrations actually created tables (detect transaction rollback issues)
            try:
                from app import db as _db
                from sqlalchemy import text as _text

                cur_db = _db.session.execute(_text("select current_database()")).scalar()
                table_count = _db.session.execute(
                    _text("select count(1) from information_schema.tables where table_schema='public'")
                ).scalar()
                log(f"Post-migration DB: {cur_db} (public tables={table_count})", "INFO")
                
                # Check if alembic_version table exists (migrations actually ran)
                alembic_exists = _db.session.execute(
                    _text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version')")
                ).scalar()
                
                if not alembic_exists:
                    log("✗ WARNING: alembic_version table missing after migrations!", "ERROR")
                    log("Migrations reported success but alembic_version table was not created.", "ERROR")
                    log("This indicates migrations did not actually run or were rolled back.", "ERROR")
                    log("The database may be in an inconsistent state.", "ERROR")
                    log("", "ERROR")
                    log("RECOVERY OPTIONS:", "ERROR")
                    log("1. Reset database: docker compose down -v && docker compose up -d", "ERROR")
                    log("2. Or set TT_SKIP_DB_CLEANUP=false and restart to try automatic cleanup", "ERROR")
                    return None
                
                # Check if core tables exist
                core_tables_check = _db.session.execute(
                    _text("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema='public' 
                        AND table_name IN ('users', 'projects', 'time_entries', 'settings', 'clients')
                    """)
                ).scalar()
                
                if core_tables_check < 5:
                    log(f"✗ WARNING: Only {core_tables_check}/5 core tables exist after migrations!", "ERROR")
                    log("Migrations reported success but core tables are missing.", "ERROR")
                    log("This indicates migrations did not complete successfully.", "ERROR")
                    log("", "ERROR")
                    log("RECOVERY OPTIONS:", "ERROR")
                    log("1. Reset database: docker compose down -v && docker compose up -d", "ERROR")
                    log("2. Check migration logs for errors", "ERROR")
                    return None
                    
            except Exception as e:
                log(f"Post-migration verification failed: {e}", "ERROR")
                traceback.print_exc()
                return None

        log("Migrations applied and verified", "SUCCESS")
        return app
    except Exception as e:
        log(f"Migration failed: {e}", "ERROR")
        traceback.print_exc()
        return None
    finally:
        # Important: don't leak migrate bootstrap mode into gunicorn runtime
        os.environ.pop("TT_BOOTSTRAP_MODE", None)


def verify_core_tables(app):
    """Verify core application tables exist after migrations (fail-fast)."""
    log("Verifying core database tables exist...", "INFO")
    try:
        from app import db
        from sqlalchemy import text

        with app.app_context():
            # Core tables required for the app to function
            core_tables = ['users', 'projects', 'time_entries', 'settings', 'clients']
            
            # Check PostgreSQL
            if os.getenv("DATABASE_URL", "").startswith("postgresql"):
                # First, list ALL tables for debugging
                try:
                    all_tables_query = text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
                    all_tables_result = db.session.execute(all_tables_query)
                    all_tables = [row[0] for row in all_tables_result]
                    log(f"All tables in database: {all_tables}", "INFO")
                except Exception as e:
                    log(f"Could not list all tables: {e}", "WARNING")
                
                # Use IN clause with proper parameter binding for PostgreSQL
                placeholders = ",".join([f":table_{i}" for i in range(len(core_tables))])
                query = text(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ({placeholders})
                """)
                params = {f"table_{i}": table for i, table in enumerate(core_tables)}
                result = db.session.execute(query, params)
                found_tables = [row[0] for row in result]
                missing = set(core_tables) - set(found_tables)
                
                if missing:
                    log(f"✗ Core tables missing: {sorted(missing)}", "ERROR")
                    log(f"Found core tables: {sorted(found_tables)}", "ERROR")
                    log("Database migrations may have failed silently.", "ERROR")
                    log("Try: docker compose down -v && docker compose up -d", "ERROR")
                    return False
                
                # Also verify alembic_version exists (migrations were applied)
                alembic_check = db.session.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version')")
                ).scalar()
                if not alembic_check:
                    log("✗ alembic_version table missing - migrations may not have been applied", "ERROR")
                    return False
                
                log(f"✓ Core tables verified: {sorted(found_tables)}", "SUCCESS")
                return True
            
            # SQLite check (simpler)
            else:
                # Build IN clause with placeholders for SQLite
                placeholders = ",".join(["?" for _ in core_tables])
                query = text(f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})")
                result = db.session.execute(query, core_tables)
                found_tables = [row[0] for row in result]
                missing = set(core_tables) - set(found_tables)
                
                if missing:
                    log(f"✗ Core tables missing: {sorted(missing)}", "ERROR")
                    return False
                
                # Check alembic_version
                alembic_check = db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                ).fetchone()
                if not alembic_check:
                    log("✗ alembic_version table missing - migrations may not have been applied", "ERROR")
                    return False
                
                log(f"✓ Core tables verified: {sorted(found_tables)}", "SUCCESS")
                return True
                
    except Exception as e:
        log(f"✗ Core table verification failed: {e}", "ERROR")
        traceback.print_exc()
        return False


def ensure_default_data(app):
    """Ensure Settings row + admin users exist (idempotent, no create_all)."""
    log("Ensuring default data exists...", "INFO")
    try:
        from app import db
        from app.models import Settings, User
        with app.app_context():
            # Settings
            try:
                Settings.get_settings()
            except Exception:
                # Fallback: create row if model supports it
                if not Settings.query.first():
                    db.session.add(Settings())
                    db.session.commit()

            # Admin users
            admin_usernames = [u.strip().lower() for u in os.getenv("ADMIN_USERNAMES", "admin").split(",") if u.strip()]
            for username in admin_usernames[:5]:  # safety cap
                existing = User.query.filter_by(username=username).first()
                if not existing:
                    u = User(username=username, role="admin")
                    try:
                        u.is_active = True
                    except Exception:
                        pass
                    db.session.add(u)
                else:
                    changed = False
                    if getattr(existing, "role", None) != "admin":
                        existing.role = "admin"
                        changed = True
                    if hasattr(existing, "is_active") and not getattr(existing, "is_active", True):
                        existing.is_active = True
                        changed = True
                    if changed:
                        db.session.add(existing)
            db.session.commit()

        log("Default data ensured", "SUCCESS")
        return True
    except Exception as e:
        log(f"Default data initialization failed (continuing): {e}", "WARNING")
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
    
    # Migrations (single source of truth)
    migration_app = run_migrations()
    if not migration_app:
        log("Migrations failed, exiting...", "ERROR")
        sys.exit(1)

    # Fail-fast: verify core tables exist (don't start app with broken DB)
    if not verify_core_tables(migration_app):
        log("Core database tables are missing. Startup aborted.", "ERROR")
        log("If this is a fresh install, migrations may have failed.", "ERROR")
        log("If this persists, check migration logs and consider resetting the database.", "ERROR")
        sys.exit(1)

    # Seed minimal default rows (fast, idempotent)
    ensure_default_data(migration_app)

    log("=" * 60, "INFO")
    log("Starting application server", "INFO")
    log("=" * 60, "INFO")
    # Start gunicorn with access logs
    os.execv('/usr/local/bin/gunicorn', [
        'gunicorn',
        '--bind', '0.0.0.0:8080',
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
