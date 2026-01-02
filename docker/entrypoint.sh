#!/bin/bash
set -e

# TimeTracker Docker Entrypoint with Automatic Migration Detection
# This script automatically detects database state and chooses the correct migration strategy

echo "=== TimeTracker Docker Container Starting ==="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo "Python version: $(python --version)"
echo "Flask version: $(flask --version 2>/dev/null || echo 'Flask CLI not available')"

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
    
    for attempt in $(seq 1 $max_retries); do
        if [[ "$db_url" == postgresql://* ]]; then
            # PostgreSQL connection test
            if command_exists psql; then
                if psql "$db_url" -c "SELECT 1" >/dev/null 2>&1; then
                    log "✓ PostgreSQL database is available (via psql)"
                    return 0
                fi
            fi
            
            # Always try Python connection as primary method
            if python -c "
import psycopg2
import sys
try:
    # Parse connection string to remove +psycopg2 if present
    conn_str = '$db_url'.replace('+psycopg2://', 'postgresql://')
    conn = psycopg2.connect(conn_str)
    conn.close()
    print('Connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" >/dev/null 2>&1; then
                log "✓ PostgreSQL database is available (via Python)"
                return 0
            fi
        elif [[ "$db_url" == sqlite://* ]]; then
            # SQLite file check
            local db_file="${db_url#sqlite://}"
            if [[ -f "$db_file" ]] || [[ -w "$(dirname "$db_file")" ]]; then
                log "✓ SQLite database is available"
                return 0
            fi
        fi
        
        log "Database not ready (attempt $attempt/$max_retries)"
        if [[ $attempt -lt $max_retries ]]; then
            sleep $retry_delay
        fi
    done
    
    log "✗ Database is not available after maximum retries"
    return 1
}

# Function to detect database state
detect_database_state() {
    local db_url="$1"
    log "Analyzing database state..."
    
    if [[ "$db_url" == postgresql://* ]]; then
        # PostgreSQL state detection
        if command_exists psql; then
            # Check if alembic_version table exists
            local has_alembic=$(psql "$db_url" -t -c "
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                );
            " 2>/dev/null | tr -d ' ')
            
            # Get list of existing tables
            local existing_tables=$(psql "$db_url" -t -c "
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            " 2>/dev/null | grep -v '^$' | tr '\n' ' ')
            
            log "PostgreSQL state: has_alembic=$has_alembic, tables=[$existing_tables]"
            
            if [[ "$has_alembic" == "t" ]]; then
                echo "migrated"
            elif [[ -n "$existing_tables" ]]; then
                echo "legacy"
            else
                echo "fresh"
            fi
        else
            # Fallback to Python detection
            local state=$(python -c "
import psycopg2
try:
    conn = psycopg2.connect('$db_url')
    cursor = conn.cursor()
    
    # Check if alembic_version table exists
    cursor.execute(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'alembic_version'
        )
    \"\"\")
    has_alembic = cursor.fetchone()[0]
    
    # Get list of existing tables
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
" 2>/dev/null)
            echo "$state"
        fi
    elif [[ "$db_url" == sqlite://* ]]; then
        # SQLite state detection
        local db_file="${db_url#sqlite://}"
        
        if [[ ! -f "$db_file" ]]; then
            echo "fresh"
            return
        fi
        
        local state=$(python -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()
    
    # Check if alembic_version table exists
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"alembic_version\"')
    has_alembic = cursor.fetchone() is not None
    
    # Get list of existing tables
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
" 2>/dev/null)
        echo "$state"
    else
        echo "unknown"
    fi
}

# Function to choose migration strategy
choose_migration_strategy() {
    local db_state="$1"
    log "Choosing migration strategy for state: $db_state"
    
    case "$db_state" in
        "fresh")
            log "Fresh database detected - using standard initialization"
            echo "fresh_init"
            ;;
        "migrated")
            log "Database already migrated - checking for pending migrations"
            echo "check_migrations"
            ;;
        "legacy")
            log "Legacy database detected - using comprehensive migration"
            echo "comprehensive_migration"
            ;;
        *)
            log "Unknown database state - using comprehensive migration as fallback"
            echo "comprehensive_migration"
            ;;
    esac
}

# Function to execute migration strategy
execute_migration_strategy() {
    local strategy="$1"
    local db_url="$2"
    
    log "Executing migration strategy: $strategy"
    
    case "$strategy" in
        "fresh_init")
            execute_fresh_init "$db_url"
            ;;
        "check_migrations")
            execute_check_migrations "$db_url"
            ;;
        "comprehensive_migration")
            execute_comprehensive_migration "$db_url"
            ;;
        *)
            log "✗ Unknown migration strategy: $strategy"
            return 1
            ;;
    esac
}

# Function to execute fresh database initialization
execute_fresh_init() {
    local db_url="$1"
    log "Executing fresh database initialization..."
    
    # Initialize Flask-Migrate
    if ! flask db init >/dev/null 2>&1; then
        log "✗ Flask-Migrate initialization failed"
        return 1
    fi
    log "✓ Flask-Migrate initialized"
    
    # Create initial migration
    if ! flask db migrate -m "Initial database schema" >/dev/null 2>&1; then
        log "✗ Initial migration creation failed"
        return 1
    fi
    log "✓ Initial migration created"
    
    # Apply migration
    if ! flask db upgrade >/dev/null 2>&1; then
        log "✗ Initial migration application failed"
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

    # If Alembic reports multiple heads and the DB is already at a head, attempting to
    # upgrade to all heads can fail with:
    #   "Requested revision X overlaps with other requested revisions ..."
    # In that situation, treat it as "no pending migrations for this database" and continue.
    local heads_output
    heads_output=$(flask db heads 2>/dev/null || echo "")
    local head_count
    head_count=$(echo "$heads_output" | grep -v '^$' | wc -l | tr -d ' ')
    if [[ "$current_revision" == *"(head)"* ]] && [[ "$head_count" -gt 1 ]]; then
        log "⚠ Multiple migration heads detected ($head_count), but database is already at a head."
        log "⚠ Skipping migration upgrade during startup to avoid Alembic overlap error."
        log "Heads:"
        echo "$heads_output" | sed 's/^/[HEAD] /'
        return 0
    fi
    
    # Check for pending migrations
    # If there are multiple heads and we're not at a head, upgrade all heads.
    # Otherwise do the normal single-head upgrade.
    local upgrade_target="upgrade"
    if [[ "$head_count" -gt 1 ]]; then
        upgrade_target="upgrade heads"
    fi
    # shellcheck disable=SC2086
    local upgrade_output
    upgrade_output=$(mktemp)
    set +e
    # shellcheck disable=SC2086
    flask db $upgrade_target >"$upgrade_output" 2>&1
    local rc=$?
    set -e
    if [[ $rc -ne 0 ]]; then
        if [[ "$current_revision" == *"(head)"* ]] && grep -q "overlaps with other requested revisions" "$upgrade_output"; then
            log "⚠ Migration upgrade reported overlapping heads, but DB is already at a head. Continuing startup."
            rm -f "$upgrade_output"
            return 0
        fi
        log "✗ Migration check failed"
        cat "$upgrade_output" 2>/dev/null || true
        rm -f "$upgrade_output"
        return 1
    fi
    rm -f "$upgrade_output"
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
    
    # Initialize Flask-Migrate if not already done
    if [[ ! -f "/app/migrations/env.py" ]]; then
        if ! flask db init >/dev/null 2>&1; then
            log "✗ Flask-Migrate initialization failed"
            return 1
        fi
        log "✓ Flask-Migrate initialized"
    fi
    
    # Create baseline migration
    if ! flask db migrate -m "Baseline from existing database" >/dev/null 2>&1; then
        log "✗ Baseline migration creation failed"
        return 1
    fi
    log "✓ Baseline migration created"
    
    # Stamp database as current
    if ! flask db stamp head >/dev/null 2>&1; then
        log "✗ Database stamping failed"
        return 1
    fi
    log "✓ Database stamped as current"
    
    return 0
}

# Function to verify database integrity
verify_database_integrity() {
    local db_url="$1"
    log "Verifying database integrity..."
    
    # Test basic database operations
    if [[ "$db_url" == postgresql://* ]]; then
        if command_exists psql; then
            # Check if key tables exist
            local key_tables=$(psql "$db_url" -t -c "
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('users', 'projects', 'time_entries')
                AND table_schema = 'public';
            " 2>/dev/null | grep -v '^$' | tr '\n' ' ')
            
            if [[ $(echo "$key_tables" | wc -w) -ge 2 ]]; then
                log "✓ Database integrity verified (PostgreSQL)"
                return 0
            else
                log "✗ Missing key tables: [$key_tables]"
                return 1
            fi
        else
            # Fallback to Python verification
            if python -c "
import psycopg2
try:
    conn = psycopg2.connect('$db_url')
    cursor = conn.cursor()
    
    cursor.execute(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('users', 'projects', 'time_entries')
        AND table_schema = 'public'
    \"\"\")
    key_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if len(key_tables) >= 2:
        exit(0)
    else:
        exit(1)
except:
    exit(1)
" >/dev/null 2>&1; then
                log "✓ Database integrity verified (PostgreSQL via Python)"
                return 0
            else
                log "✗ Database integrity check failed (PostgreSQL)"
                return 1
            fi
        fi
    elif [[ "$db_url" == sqlite://* ]]; then
        local db_file="${db_url#sqlite://}"
        
        if [[ ! -f "$db_file" ]]; then
            log "✗ SQLite database file not found"
            return 1
        fi
        
        if python -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name IN (\"users\", \"projects\", \"time_entries\")')
    key_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if len(key_tables) >= 2:
        exit(0)
    else:
        exit(1)
except:
    exit(1)
" >/dev/null 2>&1; then
            log "✓ Database integrity verified (SQLite)"
            return 0
        else
            log "✗ Database integrity check failed (SQLite)"
            return 1
        fi
    fi
    
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
        exit 1
    fi
    
    log "Database URL: $db_url"
    
    # Wait for database to be available
    if ! wait_for_database "$db_url"; then
        log "✗ Failed to connect to database"
        exit 1
    fi
    
    # Detect database state
    local db_state=$(detect_database_state "$db_url")
    log "Detected database state: $db_state"
    
    # Choose migration strategy
    local strategy=$(choose_migration_strategy "$db_state")
    log "Selected migration strategy: $strategy"
    
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
    log "Starting TimeTracker application..."
    exec "$@"
}

# Run main function with all arguments
main "$@"
