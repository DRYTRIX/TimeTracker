#!/bin/bash
# Development Database Reset Script (bash wrapper)
# Resets the database by dropping all tables, re-applying migrations, and seeding default data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Running database reset script..."
echo ""

# Check if running in Docker or locally
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    # Running inside Docker container
    python3 /app/scripts/reset-dev-db.py
else
    # Running locally - check if Docker Compose is available
    if command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1; then
        echo "Running reset script in Docker container..."
        if command -v docker-compose >/dev/null 2>&1; then
            docker-compose exec app python3 /app/scripts/reset-dev-db.py
        else
            docker compose exec app python3 /app/scripts/reset-dev-db.py
        fi
    else
        # Run directly (assumes local Python environment)
        cd "$PROJECT_ROOT"
        python3 scripts/reset-dev-db.py
    fi
fi
