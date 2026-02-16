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


def _sqlite_path_from_url(db_url: str):
    """Resolve SQLite DATABASE_URL to an absolute file path. Returns None for non-file SQLite (e.g. :memory:)."""
    if not (db_url or "").strip().startswith("sqlite"):
        return None
    prefix_four = "sqlite:////"
    prefix_three = "sqlite:///"
    if db_url.startswith("sqlite:////"):
        # sqlite:////absolute/path -> /absolute/path
        rest = db_url[len("sqlite:////"):].lstrip("/")
        return "/" + rest if rest else None
    if db_url.startswith("sqlite:///"):
        raw = db_url[len("sqlite:///"):]
        if raw.startswith("/"):
            return raw
        return os.path.abspath(os.path.join(os.getcwd(), raw))
    if ":memory:" in db_url or db_url.strip() == "sqlite://":
        return None
    return None


def wait_for_database():
    """Wait for database to be ready with proper connection testing"""
    # Logging is handled by main()
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker')

    # If using SQLite, ensure the database directory exists and return immediately.
    # Resolve path the same way the app will: absolute stays absolute, relative is
    # resolved against current working directory (so it matches gunicorn's CWD).
    if db_url.startswith('sqlite:'):
        try:
            import sqlite3 as _sqlite3
            db_path = _sqlite_path_from_url(db_url)
            if db_path is None:
                return True  # :memory: or similar
            dir_path = os.path.dirname(db_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
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
    """Attempt to clean up corrupted database state.

    PostgreSQL: remove unexpected tables when there are tables but no alembic_version/core tables.
    SQLite: remove the DB file when corrupted (alembic_version but no core tables, or tables but
    no alembic/core), so migrations can run on a fresh file.
    """
    if os.getenv("TT_SKIP_DB_CLEANUP", "").strip().lower() in ("1", "true", "yes"):
        log("Database cleanup skipped (TT_SKIP_DB_CLEANUP is set)", "INFO")
        return False

    db_url = os.getenv("DATABASE_URL", "")

    try:
        from app import db
        from sqlalchemy import text

        with app.app_context():
            if db_url.startswith("postgresql"):
                # PostgreSQL: drop unexpected tables only when safe
                all_tables_result = db.session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
                )
                all_tables = [row[0] for row in all_tables_result]
                has_alembic_version = "alembic_version" in all_tables
                core_tables = ["users", "projects", "time_entries", "settings", "clients"]
                has_core_tables = any(t in all_tables for t in core_tables)
                if has_alembic_version:
                    log("alembic_version table exists - skipping cleanup (migrations may have run)", "INFO")
                    return False
                if not all_tables or has_core_tables:
                    return False
                log(f"Attempting to clean up {len(all_tables)} unexpected table(s): {all_tables}", "INFO")
                cleaned = False
                for table in all_tables:
                    try:
                        db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                        db.session.commit()
                        log(f"✓ Dropped table: {table}", "SUCCESS")
                        cleaned = True
                    except Exception as e:
                        log(f"Failed to drop table {table}: {e}", "WARNING")
                        db.session.rollback()
                return cleaned

            if db_url.startswith("sqlite"):
                # SQLite: when corrupted, remove the file so migrations can create a fresh DB
                db_path = _sqlite_path_from_url(db_url)
                if not db_path or not os.path.isfile(db_path):
                    return False
                all_tables_result = db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                )
                all_tables = [row[0] for row in all_tables_result]
                has_alembic_version = "alembic_version" in all_tables
                core_tables = ["users", "projects", "time_entries", "settings", "clients"]
                has_core_tables = any(t in all_tables for t in core_tables)
                is_corrupted = (
                    (has_alembic_version and not has_core_tables)
                    or (len(all_tables) > 0 and not has_alembic_version and not has_core_tables)
                )
                if not is_corrupted:
                    return False
                db.session.close()
                try:
                    db.engine.dispose()
                except Exception:
                    pass
                try:
                    os.remove(db_path)
                    log(f"Removed corrupted SQLite DB at {db_path}; migrations will recreate it.", "INFO")
                    return True
                except Exception as e:
                    log(f"Failed to remove SQLite file {db_path}: {e}", "WARNING")
                    return False

            return False
    except Exception as e:
        log(f"Database cleanup failed: {e}", "WARNING")
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
            _is_pg = os.getenv("DATABASE_URL", "").strip().lower().startswith("postgresql")

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

                if _is_pg:
                    cur_db = _db.session.execute(_text("select current_database()")).scalar()
                    table_count = _db.session.execute(
                        _text("select count(1) from information_schema.tables where table_schema='public'")
                    ).scalar()
                else:
                    cur_db = "sqlite"
                    table_count = _db.session.execute(
                        _text("SELECT count(*) FROM sqlite_master WHERE type='table'")
                    ).scalar() or 0
                log(f"Pre-migration DB: {cur_db} (public tables={table_count})", "INFO")
            except Exception as e:
                log(f"Pre-migration DB probe failed: {e}", "WARNING")

            # Use heads to handle branched histories safely
            upgrade(revision="heads")

            # CRITICAL: Verify migrations actually created tables (detect transaction rollback issues)
            try:
                from app import db as _db
                from sqlalchemy import text as _text

                if _is_pg:
                    cur_db = _db.session.execute(_text("select current_database()")).scalar()
                    table_count = _db.session.execute(
                        _text("select count(1) from information_schema.tables where table_schema='public'")
                    ).scalar()
                    alembic_exists = _db.session.execute(
                        _text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version')")
                    ).scalar()
                    core_tables_check = _db.session.execute(
                        _text("""
                            SELECT COUNT(*)
                            FROM information_schema.tables
                            WHERE table_schema='public'
                            AND table_name IN ('users', 'projects', 'time_entries', 'settings', 'clients')
                        """)
                    ).scalar()
                else:
                    cur_db = "sqlite"
                    table_count = _db.session.execute(
                        _text("SELECT count(*) FROM sqlite_master WHERE type='table'")
                    ).scalar() or 0
                    alembic_exists = (
                        _db.session.execute(
                            _text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                        ).scalar()
                        or 0
                    ) > 0
                    core_tables_check = (
                        _db.session.execute(
                            _text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('users','projects','time_entries','settings','clients')")
                        ).scalar()
                        or 0
                    )
                log(f"Post-migration DB: {cur_db} (public tables={table_count})", "INFO")
                
                # Check if alembic_version table exists (migrations actually ran)
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
            
            # SQLite: same checks as PostgreSQL — list all tables, then verify required core tables exist
            else:
                sqlite_path = _sqlite_path_from_url(os.getenv("DATABASE_URL", ""))
                # List ALL tables for debugging (parity with PostgreSQL)
                try:
                    all_tables_result = db.session.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sqlite_sequence') ORDER BY name")
                    )
                    all_tables = [row[0] for row in all_tables_result]
                    log(f"All tables in database: {all_tables}", "INFO")
                except Exception as e:
                    log(f"Could not list all tables: {e}", "WARNING")
                    all_tables = []

                # Verify each core table exists (explicit check for each so we report accurately)
                found_tables = [t for t in core_tables if t in all_tables]
                missing = set(core_tables) - set(found_tables)

                if missing:
                    log(f"✗ Core tables missing: {sorted(missing)}", "ERROR")
                    log(f"Found core tables: {sorted(found_tables)}", "ERROR")
                    if sqlite_path:
                        log(f"Database file: {sqlite_path}", "ERROR")
                    log("Database migrations may have failed silently.", "ERROR")
                    log("Try removing the database file and restarting, or run: docker compose down -v && docker compose up -d", "ERROR")
                    return False

                if "alembic_version" not in all_tables:
                    log("✗ alembic_version table missing - migrations may not have been applied", "ERROR")
                    if sqlite_path:
                        log(f"Database file: {sqlite_path}", "ERROR")
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

            # Demo user or admin users (same logic as app.initialize_database)
            if app.config.get("DEMO_MODE"):
                from app.models import Role
                demo_username = (app.config.get("DEMO_USERNAME") or "demo").strip().lower()
                existing = User.query.filter_by(username=demo_username).first()
                if not existing:
                    demo_user = User(username=demo_username, role="admin")
                    demo_user.is_active = True
                    demo_user.set_password(app.config.get("DEMO_PASSWORD", "demo"))
                    admin_role = Role.query.filter_by(name="admin").first()
                    if admin_role:
                        demo_user.roles.append(admin_role)
                    db.session.add(demo_user)
                    log(f"Created demo user: {demo_username}", "INFO")
                db.session.commit()
            else:
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
    # Start gunicorn with access logs (bind to PORT when set, e.g. by Render; default 8080 for docker-compose)
    port = os.environ.get('PORT', '8080')
    os.execv('/usr/local/bin/gunicorn', [
        'gunicorn',
        '--bind', '0.0.0.0:%s' % port,
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
