#!/bin/bash
# TimeTracker Docker Entrypoint with Automatic Migration Detection
# This script automatically detects database state and chooses the correct migration strategy

# Don't exit on errors - let the script continue and show what's happening
# set -e

echo "=== TimeTracker Docker Container Starting ==="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo "Python version: $(python --version 2>/dev/null || echo 'Python not available')"
echo "Flask version: $(flask --version 2>/dev/null || echo 'Flask CLI not available')"
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for database
wait_for_database() {
    local db_url="$1"
    local max_retries=60  # Increased retries
    local retry_delay=3   # Increased delay
    
    log "Waiting for database to be available..."
    log "Database URL: $db_url"
    
    for attempt in $(seq 1 $max_retries); do
        log "Attempt $attempt/$max_retries to connect to database..."
        
        if [[ "$db_url" == postgresql* ]]; then
            log "Testing PostgreSQL connection..."
            
            # Test 1: Try psql if available
            if command_exists psql; then
                log "Testing with psql..."
                if psql "$db_url" -c "SELECT 1" >/dev/null 2>&1; then
                    log "✓ PostgreSQL database is available (via psql)"
                    return 0
                else
                    log "psql connection failed"
                fi
            else
                log "psql not available, skipping psql test"
            fi
            
            # Test 2: Always try Python connection
            log "Testing with Python psycopg2..."
            if python -c "
import psycopg2
import sys
try:
    # Parse connection string to remove +psycopg2 if present
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    print(f'Attempting connection to: {conn_str}')
    conn = psycopg2.connect(conn_str)
    conn.close()
    print('Connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log "✓ PostgreSQL database is available (via Python)"
                return 0
            else
                log "Python connection failed"
            fi
            
        elif [[ "$db_url" == sqlite://* ]]; then
            log "Testing SQLite connection..."
            local db_file="${db_url#sqlite://}"
            if [[ -f "$db_file" ]] || [[ -w "$(dirname "$db_file")" ]]; then
                log "✓ SQLite database is available"
                return 0
            else
                log "SQLite file not accessible"
            fi
        else
            log "Unknown database URL format: $db_url"
        fi
        
        log "Database not ready (attempt $attempt/$max_retries)"
        if [[ $attempt -lt $max_retries ]]; then
            log "Waiting $retry_delay seconds before next attempt..."
            sleep $retry_delay
        fi
    done
    
    log "✗ Database is not available after maximum retries"
    return 1
}

# Function to detect database state
detect_database_state() {
    local db_url="$1"
    
    if [[ "$db_url" == postgresql* ]]; then
        # Simple direct Python execution without temp files
        python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'alembic_version'
        )
    \"\"\")
    has_alembic = cursor.fetchone()[0]
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    \"\"\")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if has_alembic:
        print('migrated')
    elif existing_tables:
        print('legacy')
    else:
        print('fresh')
except Exception as e:
    print('unknown')
" 2>/dev/null
        
    elif [[ "$db_url" == sqlite://* ]]; then
        local db_file="${db_url#sqlite://}"
        
        if [[ ! -f "$db_file" ]]; then
            echo "fresh"
            return
        fi
        
        python -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"alembic_version\"')
    has_alembic = cursor.fetchone() is not None
    
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if has_alembic:
        print('migrated')
    elif existing_tables:
        print('legacy')
    else:
        print('fresh')
except Exception as e:
    print('unknown')
" 2>/dev/null
    else
        echo "unknown"
    fi
}

# Function to choose migration strategy
choose_migration_strategy() {
    local db_state="$1"
    
    case "$db_state" in
        "fresh")
            echo "fresh_init"
            ;;
        "migrated")
            echo "check_migrations"
            ;;
        "legacy")
            echo "comprehensive_migration"
            ;;
        *)
            echo "comprehensive_migration"
            ;;
    esac
}

# Function to execute migration strategy
execute_migration_strategy() {
    local strategy="$1"
    local db_url="$2"
    
    log "Executing migration strategy: '$strategy'"
    
    case "$strategy" in
        "fresh_init")
            log "Executing fresh_init strategy..."
            execute_fresh_init "$db_url"
            ;;
        "check_migrations")
            log "Executing check_migrations strategy..."
            execute_check_migrations "$db_url"
            ;;
        "comprehensive_migration")
            log "Executing comprehensive_migration strategy..."
            execute_comprehensive_migration "$db_url"
            ;;
        *)
            log "✗ Unknown migration strategy: '$strategy'"
            return 1
            ;;
    esac
}

# Compile translations (.po -> .mo) if needed
compile_translations() {
    log "Compiling translation catalogs (if needed)..."
    # Try pybabel if available
    if command_exists pybabel; then
        # Ensure writable permissions before compiling
        chmod -R u+rwX,g+rwX /app/translations 2>/dev/null || true
        if pybabel compile -d /app/translations >/dev/null 2>&1; then
            log "✓ Translations compiled via pybabel"
            return 0
        else
            log "⚠ pybabel compile failed or no catalogs to compile"
        fi
    else
        log "pybabel not available; trying Python fallback"
    fi
    # Python fallback using app.utils.i18n
    if python - <<'PY'
try:
    import os
    from app.utils.i18n import ensure_translations_compiled
    try:
        import pathlib
        p = pathlib.Path('/app/translations')
        for sub in p.glob('**/LC_MESSAGES'):
            try:
                os.chmod(str(sub), 0o775)
            except Exception:
                pass
    except Exception:
        pass
    ensure_translations_compiled('/app/translations')
    print('Python fallback: ensure_translations_compiled executed')
except Exception as e:
    print(f'Python fallback failed: {e}')
PY
    then
        log "✓ Translations compiled via Python fallback"
        return 0
    else
        log "⚠ Could not compile translations (will fallback to msgid)"
        return 1
    fi
}

# Function to execute fresh database initialization
execute_fresh_init() {
    local db_url="$1"
    log "Executing fresh database initialization..."
    
    # Set FLASK_APP if not already set
    if [[ -z "$FLASK_APP" ]]; then
        log "⚠ FLASK_APP not set, setting it to app.py"
        export FLASK_APP=app.py
    fi
    
    # Check if migrations directory already exists
    if [[ -d "/app/migrations" ]]; then
        log "⚠ Migrations directory already exists, checking if it's properly configured..."
        
        # Check if we have the required files
        if [[ -f "/app/migrations/env.py" && -f "/app/migrations/alembic.ini" ]]; then
            log "✓ Migrations directory is properly configured, skipping init"
            log "Checking if we need to create initial migration..."
            
            # Check if we have any migration versions
            if [[ ! -d "/app/migrations/versions" ]] || [[ -z "$(ls -A /app/migrations/versions 2>/dev/null)" ]]; then
                log "No migration versions found, creating initial migration..."
                if ! flask db migrate -m "Initial database schema"; then
                    log "✗ Initial migration creation failed"
                    log "Error details:"
                    flask db migrate -m "Initial database schema" 2>&1 | head -20
                    return 1
                fi
                log "✓ Initial migration created"
            else
                log "✓ Migration versions already exist"
            fi
            
            # Check current migration status
            log "Checking current migration status..."
            local current_revision=$(flask db current 2>/dev/null | tr -d '\n' || echo "none")
            log "Current migration revision: $current_revision"
            
            if [[ "$current_revision" == "none" ]]; then
                log "Database not stamped, stamping with current revision..."
                local head_revision=$(flask db heads 2>/dev/null | tr -d '\n' || echo "")
                if [[ -n "$head_revision" ]]; then
                    if ! flask db stamp "$head_revision"; then
                        log "✗ Database stamping failed"
                        log "Error details:"
                        flask db stamp "$head_revision" 2>&1 | head -20
                        return 1
                    fi
                    log "✓ Database stamped with revision: $head_revision"
                fi
            fi
            
            # Apply any pending migrations
            log "Applying pending migrations..."
            if ! flask db upgrade; then
                log "✗ Migration application failed"
                log "Error details:"
                flask db upgrade 2>&1 | head -20
                return 1
            fi
            log "✓ Migrations applied"
            
            # Wait a moment for tables to be fully committed
            log "Waiting for tables to be fully committed..."
            sleep 2
            
            return 0
        else
            log "⚠ Migrations directory exists but is incomplete, removing it..."
            rm -rf /app/migrations
        fi
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "/app/app.py" ]]; then
        log "⚠ Not in correct directory, changing to /app"
        cd /app
    fi
    
    # Initialize Flask-Migrate
    log "Initializing Flask-Migrate..."
    if ! flask db init; then
        log "✗ Flask-Migrate initialization failed"
        log "Error details:"
        flask db init 2>&1 | head -20
        return 1
    fi
    log "✓ Flask-Migrate initialized"
    
    # Create initial migration
    log "Creating initial migration..."
    if ! flask db migrate -m "Initial database schema"; then
        log "✗ Initial migration creation failed"
        log "Error details:"
        flask db migrate -m "Initial database schema" 2>&1 | head -20
        return 1
    fi
    log "✓ Initial migration created"
    
    # Apply migration
    log "Applying initial migration..."
    if ! flask db upgrade; then
        log "✗ Initial migration application failed"
        log "Error details:"
        flask db upgrade 2>&1 | head -20
        return 1
    fi
    log "✓ Initial migration applied"
    
    return 0
}

# Function to check and apply pending migrations
execute_check_migrations() {
    local db_url="$1"
    log "Checking for pending migrations..."
    
    # Check current migration status
    local current_revision=$(flask db current 2>/dev/null | tr -d '\n' || echo "unknown")
    log "Current migration revision: $current_revision"
    
    # Check for pending migrations
    if ! flask db upgrade; then
        log "✗ Migration check failed"
        log "Error details:"
        flask db upgrade 2>&1 | head -20
        return 1
    fi
    log "✓ Migrations checked and applied"
    
    return 0
}

# Function to execute comprehensive migration
execute_comprehensive_migration() {
    local db_url="$1"
    log "Executing comprehensive migration..."
    
    # Try to run the enhanced startup script
    if [[ -f "/app/docker/startup_with_migration.py" ]]; then
        log "Running enhanced startup script..."
        if python /app/docker/startup_with_migration.py; then
            log "✓ Enhanced startup script completed successfully"
            return 0
        else
            log "⚠ Enhanced startup script failed, falling back to manual migration"
        fi
    fi
    
    # Fallback to manual migration
    log "Executing manual migration fallback..."
    
    # Check what tables exist in the database
    log "Analyzing existing database structure..."
    if ! python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    \"\"\")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'alembic_version'
        AND table_schema = 'public'
    \"\"\)
    alembic_table = cursor.fetchone()
    
    conn.close()
    
    print(f'Existing tables: {existing_tables}')
    print(f'Alembic version table exists: {bool(alembic_table)}')
    
    if len(existing_tables) == 0:
        print('Database is empty - no baseline migration needed')
        exit(0)
    elif alembic_table:
        print('Database already has alembic_version table - no baseline migration needed')
        exit(0)
    else:
        print('Database has existing tables but no alembic_version - baseline migration needed')
        exit(1)
except Exception as e:
    print(f'Error analyzing database: {e}')
    exit(1)
"; then
        log "Database analysis completed"
    fi
    
    # Initialize Flask-Migrate if not already done
    if [[ ! -f "/app/migrations/env.py" ]]; then
        log "Initializing Flask-Migrate..."
        if ! flask db init; then
            log "✗ Flask-Migrate initialization failed"
            log "Error details:"
            flask db init 2>&1 | head -20
            return 1
        fi
        log "✓ Flask-Migrate initialized"
    fi
    
    # Check if we need to create a baseline migration
    log "Checking if baseline migration is needed..."
    if python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'alembic_version'
        AND table_schema = 'public'
    \"\"\")
    alembic_table = cursor.fetchone()
    
    conn.close()
    
    if alembic_table:
        print('Alembic version table already exists - skipping baseline migration')
        exit(0)
    else:
        print('Alembic version table missing - baseline migration needed')
        exit(1)
except Exception as e:
    print(f'Error checking alembic version: {e}')
    exit(1)
"; then
        log "✓ No baseline migration needed - database already stamped"
        return 0
    fi
    
    # If we get here, we need a baseline migration
    # But first, let's check if there are any conflicting tables
    log "Checking for potential table conflicts..."
    if ! python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    # Check for tables that might conflict with our migration
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name IN ('clients', 'users', 'projects', 'tasks', 'time_entries', 'settings', 'invoices', 'invoice_items')
        ORDER BY table_name
    \"\"\")
    conflicting_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if conflicting_tables:
        print(f'Found potentially conflicting tables: {conflicting_tables}')
        print('These tables might conflict with the migration. Consider backing up data first.')
        exit(1)
    else:
        print('No conflicting tables found - safe to proceed with baseline migration')
        exit(0)
except Exception as e:
    print(f'Error checking for conflicts: {e}')
    exit(1)
"; then
        log "⚠ Potential table conflicts detected - proceeding with caution"
    fi
    
    # Create baseline migration
    log "Creating baseline migration from existing database..."
    if ! flask db migrate -m "Baseline from existing database"; then
        log "✗ Baseline migration creation failed"
        log "Error details:"
        flask db migrate -m "Baseline from existing database" 2>&1 | head -20
        
        # Try to understand why the migration failed
        log "Attempting to understand migration failure..."
        if ! python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    \"\"\")
    columns = cursor.fetchall()
    
    conn.close()
    
    print('Database schema:')
    current_table = None
    for table, column, data_type, nullable in columns:
        if table != current_table:
            print(f'\\nTable: {table}')
            current_table = table
        print(f'  {column}: {data_type} (nullable: {nullable})')
except Exception as e:
    print(f'Error getting schema: {e}')
"; then
            log "Could not analyze database schema"
        fi
        
        log "✗ Baseline migration creation failed - trying alternative approach..."
        
        # Try to stamp the database with the existing migration version
        log "Attempting to stamp database with existing migration version..."
        if python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    # Check if we have any migration files
    import os
    migration_dir = '/app/migrations/versions'
    if os.path.exists(migration_dir):
        migration_files = [f for f in os.listdir(migration_dir) if f.endswith('.py')]
        if migration_files:
            # Get the first migration file (should be 001_initial_schema.py)
            first_migration = sorted(migration_files)[0]
            migration_id = first_migration.split('_')[0]
            print(f'Found migration file: {first_migration} with ID: {migration_id}')
            
            # Try to stamp the database with this migration
            import subprocess
            result = subprocess.run(['flask', 'db', 'stamp', migration_id], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print('Successfully stamped database with existing migration')
                exit(0)
            else:
                print(f'Failed to stamp database: {result.stderr}')
                exit(1)
        else:
            print('No migration files found')
            exit(1)
    else:
        print('Migration directory not found')
        exit(1)
except Exception as e:
    print(f'Error in alternative approach: {e}')
    exit(1)
"; then
            log "✓ Database stamped with existing migration version"
            return 0
        else
            log "✗ Alternative approach also failed"
            return 1
        fi
    fi
    
    log "✓ Baseline migration created"
    
    # Stamp database as current
    log "Stamping database with current migration version..."
    if ! flask db stamp head; then
        log "✗ Database stamping failed"
        log "Error details:"
        flask db stamp head 2>&1 | head -20
        return 1
    fi
    log "✓ Database stamped as current"
    
    return 0
}

# Function to verify database integrity
verify_database_integrity() {
    local db_url="$1"
    log "Verifying database integrity..."
    
    # Try up to 3 times with delays
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Database integrity check attempt $attempt/$max_attempts..."
        
        # Test basic database operations
        if [[ "$db_url" == postgresql* ]]; then
            log "Checking PostgreSQL database integrity..."
            if python -c "
import psycopg2
try:
    # Parse connection string to remove +psycopg2 if present
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    # Check for key tables that should exist after migration
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('clients', 'users', 'projects', 'tasks', 'time_entries', 'settings', 'invoices', 'invoice_items')
        AND table_schema = 'public'
        ORDER BY table_name
    \"\"\")
    key_tables = [row[0] for row in cursor.fetchall()]
    
    # Also check if alembic_version table exists
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'alembic_version'
        AND table_schema = 'public'
    \"\"\")
    alembic_table = cursor.fetchone()
    
    conn.close()
    
    print(f'Found tables: {key_tables}')
    print(f'Alembic version table: {alembic_table[0] if alembic_table else \"missing\"}')
    
    # Require at least the core tables and alembic_version
    if len(key_tables) >= 5 and alembic_table:
        exit(0)
    else:
        print(f'Expected at least 5 core tables, found {len(key_tables)}')
        print(f'Expected alembic_version table: {bool(alembic_table)}')
        exit(1)
except Exception as e:
    print(f'Error during integrity check: {e}')
    exit(1)
"; then
                log "✓ Database integrity verified (PostgreSQL via Python)"
                return 0
            else
                log "✗ Database integrity check failed (PostgreSQL)"
                log "Error details:"
                python -c "
import psycopg2
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    \"\"\")
    all_tables = [row[0] for row in cursor.fetchall()]
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'alembic_version'
        AND table_schema = 'public'
    \"\"\)
    alembic_table = cursor.fetchone()
    
    conn.close()
    
    print(f'All tables in database: {all_tables}')
    print(f'Alembic version table exists: {bool(alembic_table)}')
except Exception as e:
    print(f'Error getting table list: {e}')
" 2>&1 | head -20
                
                if [[ $attempt -lt $max_attempts ]]; then
                    log "Waiting 3 seconds before retry..."
                    sleep 3
                    attempt=$((attempt + 1))
                    continue
                else
                    return 1
                fi
            fi
        elif [[ "$db_url" == sqlite://* ]]; then
            local db_file="${db_url#sqlite://}"
            
            if [[ ! -f "$db_file" ]]; then
                log "✗ SQLite database file not found"
                return 1
            fi
            
            log "Checking SQLite database integrity..."
            if python -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name IN (\"clients\", \"users\", \"projects\", \"tasks\", \"time_entries\", \"settings\", \"invoices\", \"invoice_items\")')
    key_tables = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"alembic_version\"')
    alembic_table = cursor.fetchone()
    
    conn.close()
    
    print(f'Found tables: {key_tables}')
    print(f'Alembic version table: {alembic_table[0] if alembic_table else \"missing\"}')
    
    if len(key_tables) >= 5 and alembic_table:
        exit(0)
    else:
        print(f'Expected at least 5 core tables, found {len(key_tables)}')
        print(f'Expected alembic_version table: {bool(alembic_table)}')
        exit(1)
except Exception as e:
    print(f'Error during integrity check: {e}')
    exit(1)
"; then
                log "✓ Database integrity verified (SQLite)"
                return 0
            else
                log "✗ Database integrity check failed (SQLite)"
                if [[ $attempt -lt $max_attempts ]]; then
                    log "Waiting 3 seconds before retry..."
                    sleep 3
                    attempt=$((attempt + 1))
                    continue
                else
                    return 1
                fi
            fi
        else
            log "✗ Unsupported database type: $db_url"
            return 1
        fi
        
        # If we get here, the check failed
        if [[ $attempt -lt $max_attempts ]]; then
            log "Waiting 3 seconds before retry..."
            sleep 3
            attempt=$((attempt + 1))
        else
            return 1
        fi
    done
    
    return 1
}

# Main execution
main() {
    log "=== TimeTracker Docker Entrypoint with Migration Detection ==="
    
    # Set environment variables
    export FLASK_APP=${FLASK_APP:-/app/app.py}
    
    # Get database URL from environment
    local db_url="${DATABASE_URL}"
    if [[ -z "$db_url" ]]; then
        log "✗ DATABASE_URL environment variable not set"
        log "Available environment variables:"
        env | grep -E "(DATABASE|FLASK|PYTHON)" | sort
        exit 1
    fi
    
    log "Database URL: $db_url"
    
    # Wait for database to be available
    if ! wait_for_database "$db_url"; then
        log "✗ Failed to connect to database"
        log "Trying to run simple test script for debugging..."
        if [[ -f "/app/docker/simple_test.sh" ]]; then
            /app/docker/simple_test.sh
        fi
        exit 1
    fi
    
    # Detect database state
    local db_state=$(detect_database_state "$db_url")
    log "Raw db_state output: '${db_state}'"
    log "Detected database state: '$db_state'"
    
    # Choose migration strategy
    local strategy=$(choose_migration_strategy "$db_state")
    log "Raw strategy output: '${strategy}'"
    log "Selected migration strategy: '$strategy'"
    
    # Log the strategy selection details
    case "$db_state" in
        "fresh")
            log "Fresh database detected - using standard initialization"
            ;;
        "migrated")
            log "Database already migrated - checking for pending migrations"
            ;;
        "legacy")
            log "Legacy database detected - using comprehensive migration"
            ;;
        *)
            log "Unknown database state: '$db_state' - using comprehensive migration as fallback"
            ;;
    esac
    
    # Execute migration strategy
    if ! execute_migration_strategy "$strategy" "$db_url"; then
        log "✗ Migration strategy execution failed"
        exit 1
    fi
    
    # Verify database integrity
    if ! verify_database_integrity "$db_url"; then
        log "✗ Database integrity verification failed"
        exit 1
    fi
    
    log "=== Startup and Migration Complete ==="
    log "Database is ready for use"
    
    # Show final migration status
    local final_status=$(flask db current 2>/dev/null | tr -d '\n' || echo "unknown")
    log "Final migration status: $final_status"
    
    # Start the application
    # Best-effort compile translations before starting
    compile_translations || true
    log "Starting TimeTracker application..."
    exec "$@"
}

# Run main function with all arguments
main "$@"
