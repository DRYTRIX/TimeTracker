#!/bin/bash
set -e

# Initialize PostgreSQL database
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    echo "Initializing PostgreSQL database..."
    su - postgres -c "initdb -D /var/lib/postgresql/data"
    su - postgres -c "pg_ctl -D /var/lib/postgresql/data -l logfile start"

    # Create database and user
    su - postgres -c "createdb timetracker"
    su - postgres -c "createuser -s timetracker"

    # Run initialization SQL
    su - postgres -c "psql -d timetracker -f /app/docker/init.sql"

    su - postgres -c "pg_ctl -D /var/lib/postgresql/data stop"
    echo "PostgreSQL database initialized successfully"
else
    echo "PostgreSQL database already exists"
fi
