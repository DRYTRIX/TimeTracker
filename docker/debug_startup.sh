#!/bin/bash
set -e

# TimeTracker Startup Debug Script
# This script helps debug startup issues step by step

echo "=== TimeTracker Startup Debug Script ==="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test basic connectivity
test_basic_connectivity() {
    log "=== Testing Basic Connectivity ==="

    # Test if we can resolve the database hostname
    if ping -c 1 db >/dev/null 2>&1; then
        log "✓ Can ping database host 'db'"
    else
        log "✗ Cannot ping database host 'db'"
        return 1
    fi

    # Test if database port is accessible
    if command_exists nc; then
        if nc -zv db 5432 2>/dev/null; then
            log "✓ Database port 5432 is accessible"
        else
            log "✗ Database port 5432 is not accessible"
            return 1
        fi
    else
        log "⚠ netcat not available, skipping port test"
    fi

    return 0
}

# Function to test environment variables
test_environment() {
    log "=== Testing Environment Variables ==="

    # Check if DATABASE_URL is set
    if [[ -n "${DATABASE_URL}" ]]; then
        log "✓ DATABASE_URL is set: ${DATABASE_URL}"

        # Check if it's a valid PostgreSQL URL
        if [[ "${DATABASE_URL}" == postgresql* ]]; then
            log "✓ DATABASE_URL format is valid PostgreSQL"
        else
            log "✗ DATABASE_URL format is not valid PostgreSQL"
            return 1
        fi
    else
        log "✗ DATABASE_URL is not set"
        return 1
    fi

    # Check other important variables
    if [[ -n "${FLASK_APP}" ]]; then
        log "✓ FLASK_APP is set: ${FLASK_APP}"
    else
        log "⚠ FLASK_APP is not set"
    fi

    return 0
}

# Function to test Python dependencies
test_python_dependencies() {
    log "=== Testing Python Dependencies ==="

    # Check if psycopg2 is available
    if python -c "import psycopg2; print('✓ psycopg2 is available')" 2>/dev/null; then
        log "✓ psycopg2 is available"
    else
        log "✗ psycopg2 is not available"
        return 1
    fi

    # Check if Flask is available
    if python -c "import flask; print('✓ Flask is available')" 2>/dev/null; then
        log "✓ Flask is available"
    else
        log "✗ Flask is not available"
        return 1
    fi

    # Check if Flask-Migrate is available
    if python -c "import flask_migrate; print('✓ Flask-Migrate is available')" 2>/dev/null; then
        log "✓ Flask-Migrate is available"
    else
        log "✗ Flask-Migrate is not available"
        return 1
    fi

    return 0
}

# Function to test database connection
test_database_connection() {
    log "=== Testing Database Connection ==="

    # Run the connection test script
    if [[ -f "/app/docker/test_db_connection.py" ]]; then
        log "Running database connection test..."
        if python /app/docker/test_db_connection.py; then
            log "✓ Database connection test successful"
            return 0
        else
            log "✗ Database connection test failed"
            return 1
        fi
    else
        log "⚠ Database connection test script not found"

        # Fallback: test connection manually
        log "Testing connection manually..."
        if python -c "
import psycopg2
import sys
try:
    # Parse connection string to remove +psycopg2 if present
    conn_str = '${DATABASE_URL}'.replace('+psycopg2://', 'postgresql://')
    print(f'Trying to connect to: {conn_str}')
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    print(f'✓ Connection successful, test query result: {result}')
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'✗ Connection failed: {e}')
    sys.exit(1)
"; then
            log "✓ Manual connection test successful"
            return 0
        else
            log "✗ Manual connection test failed"
            return 1
        fi
    fi
}

# Function to test Flask-Migrate commands
test_flask_migrate() {
    log "=== Testing Flask-Migrate Commands ==="

    # Check if flask db command is available
    if flask db --help >/dev/null 2>&1; then
        log "✓ Flask-Migrate commands are available"

        # Test current command
        if flask db current >/dev/null 2>&1; then
            current_revision=$(flask db current 2>/dev/null | tr -d '\n' || echo "unknown")
            log "✓ Current migration revision: $current_revision"
        else
            log "⚠ Could not get current migration revision"
        fi
    else
        log "✗ Flask-Migrate commands are not available"
        return 1
    fi

    return 0
}

# Function to show system information
show_system_info() {
    log "=== System Information ==="

    log "Python version: $(python --version)"
    log "Flask version: $(flask --version 2>/dev/null || echo 'Flask CLI not available')"
    log "Working directory: $(pwd)"
    log "Current user: $(whoami)"
    log "Environment: $(env | grep -E '(FLASK|DATABASE|PYTHON)' | sort)"

    # Check if we're in a container
    if [[ -f /.dockerenv ]]; then
        log "✓ Running in Docker container"
    else
        log "⚠ Not running in Docker container"
    fi

    # Check if we can access the app directory
    if [[ -d "/app" ]]; then
        log "✓ /app directory is accessible"
        log "  Contents: $(ls -la /app | head -5)"
    else
        log "✗ /app directory is not accessible"
    fi
}

# Main execution
main() {
    log "Starting TimeTracker startup debug..."

    # Show system information
    show_system_info
    echo

    # Test basic connectivity
    if ! test_basic_connectivity; then
        log "❌ Basic connectivity test failed"
        echo
        log "Troubleshooting connectivity issues:"
        log "1. Check if database container is running: docker-compose ps db"
        log "2. Check database logs: docker-compose logs db"
        log "3. Check network: docker network ls"
        echo
        return 1
    fi
    echo

    # Test environment variables
    if ! test_environment; then
        log "❌ Environment test failed"
        echo
        log "Troubleshooting environment issues:"
        log "1. Check .env file exists and has correct values"
        log "2. Verify DATABASE_URL format"
        log "3. Check docker-compose environment section"
        echo
        return 1
    fi
    echo

    # Test Python dependencies
    if ! test_python_dependencies; then
        log "❌ Python dependencies test failed"
        echo
        log "Troubleshooting dependency issues:"
        log "1. Check requirements.txt is installed"
        log "2. Verify Python packages are available"
        log "3. Check container build process"
        echo
        return 1
    fi
    echo

    # Test database connection
    if ! test_database_connection; then
        log "❌ Database connection test failed"
        echo
        log "Troubleshooting connection issues:"
        log "1. Check database container health: docker-compose ps db"
        log "2. Verify database credentials"
        log "3. Check database initialization"
        log "4. See: docker/TROUBLESHOOTING_DB_CONNECTION.md"
        echo
        return 1
    fi
    echo

    # Test Flask-Migrate
    if ! test_flask_migrate; then
        log "❌ Flask-Migrate test failed"
        echo
        log "Troubleshooting Flask-Migrate issues:"
        log "1. Check if migrations directory exists"
        log "2. Verify Flask-Migrate is properly installed"
        log "3. Check application configuration"
        echo
        return 1
    fi
    echo

    log "🎉 All tests passed! System appears to be ready."
    log "You can now try starting the application normally."

    return 0
}

# Run main function
main "$@"
