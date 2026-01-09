#!/bin/bash
# TimeTracker Local Test Entrypoint
# Simplified entrypoint for local testing with SQLite

echo "=== TimeTracker Local Test Container Starting ==="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo "Python version: $(python --version 2>/dev/null || echo 'Python not available')"
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure data directory exists and has proper permissions
log "Setting up data directory..."
mkdir -p /data /data/uploads /data/uploads/receipts /app/logs
chmod 755 /data /data/uploads /data/uploads/receipts /app/logs

# If no command was passed from CMD, default to python /app/start.py
if [ $# -eq 0 ]; then
    set -- python /app/start.py
fi

# Set proper ownership for the timetracker user (if it exists)
if id "timetracker" &>/dev/null; then
    log "Setting ownership to timetracker user..."
    chown -R timetracker:timetracker /data /app/logs || true
    log "Switching to timetracker user with gosu..."
    cd /app
    # Delegate to the standard entrypoint that handles migrations for both Postgres and SQLite
    exec gosu timetracker:timetracker /app/docker/entrypoint_fixed.sh "$@"
else
    log "timetracker user not found, running as root..."
    exec /app/docker/entrypoint_fixed.sh "$@"
fi
