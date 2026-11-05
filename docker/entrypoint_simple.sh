#!/bin/bash
set -e

echo "=== TimeTracker Docker Container Starting ==="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo "Python version: $(python --version 2>/dev/null || echo 'Python not available')"
echo

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for database
wait_for_database() {
    local db_url="$1"
    local max_retries=30
    local retry_delay=2

    log "Waiting for database to be available..."
    log "Database URL: $db_url"

    for attempt in $(seq 1 $max_retries); do
        log "Attempt $attempt/$max_retries to connect to database..."

        if [[ "$db_url" == postgresql* ]]; then
            if python -c "
import psycopg2
import sys
try:
    conn_str = '$db_url'.replace('+psycopg2://', '://')
    conn = psycopg2.connect(conn_str)
    conn.close()
    print('Connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log "✓ PostgreSQL database is available"
                return 0
            fi
        elif [[ "$db_url" == sqlite://* ]]; then
            local db_file="${db_url#sqlite://}"
            if [[ -f "$db_file" ]] || [[ -w "$(dirname "$db_file")" ]]; then
                log "✓ SQLite database is available"
                return 0
            fi
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

# Main execution
main() {
    log "=== TimeTracker Docker Entrypoint ==="

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
        exit 1
    fi

    # Check if migrations directory exists
    if [[ -d "/app/migrations" ]]; then
        log "Migrations directory exists, checking status..."

        # Try to apply any pending migrations
        if command -v flask >/dev/null 2>&1; then
            log "Applying pending migrations..."
            if flask db upgrade; then
                log "✓ Migrations applied successfully"
            else
                log "⚠ Migration application failed, continuing anyway"
            fi
        else
            log "⚠ Flask CLI not available, skipping migrations"
        fi
    else
        log "No migrations directory found, initializing..."

        if command -v flask >/dev/null 2>&1; then
            if flask db init; then
                log "✓ Migrations initialized"
                if flask db migrate -m "Initial schema"; then
                    log "✓ Initial migration created"
                    if flask db upgrade; then
                        log "✓ Initial migration applied"
                    else
                        log "⚠ Initial migration application failed"
                    fi
                else
                    log "⚠ Initial migration creation failed"
                fi
            else
                log "⚠ Migration initialization failed"
            fi
        else
            log "⚠ Flask CLI not available, skipping migration setup"
        fi
    fi

    log "=== Startup Complete ==="
    log "Starting TimeTracker application..."

    # Execute the command passed to the container
    exec "$@"
}

# Run main function with all arguments
main "$@"
