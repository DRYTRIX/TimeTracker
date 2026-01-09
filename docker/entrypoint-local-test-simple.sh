#!/bin/bash
# TimeTracker Local Test Entrypoint - Simple Version
# Runs everything as root to avoid permission issues

echo "=== TimeTracker Local Test Container Starting (Simple Mode) ==="
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

log "Running as root user (simplified mode)..."
# Run the application directly as root
exec "$@"
