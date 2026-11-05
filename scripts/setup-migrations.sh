#!/bin/bash

# TimeTracker Migration Setup Script
# This script helps set up Flask-Migrate for database migrations

set -e

echo "=== TimeTracker Migration Setup ==="
echo "This script will help you set up Flask-Migrate for database migrations"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: Please run this script from the TimeTracker root directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

# Check if Flask is available
if ! python3 -c "import flask" &> /dev/null; then
    echo "Error: Flask is required but not installed"
    echo "Please install dependencies with: pip install -r requirements.txt"
    exit 1
fi

# Check if Flask-Migrate is available
if ! python3 -c "import flask_migrate" &> /dev/null; then
    echo "Error: Flask-Migrate is required but not installed"
    echo "Please install dependencies with: pip install -r requirements.txt"
    exit 1
fi

echo "✓ Prerequisites check passed"
echo ""

# Set environment variables if not already set
if [ -z "$FLASK_APP" ]; then
    export FLASK_APP=app.py
    echo "Set FLASK_APP=app.py"
fi

# Check if migrations directory exists
if [ -d "migrations" ]; then
    echo "✓ Migrations directory already exists"

    # Check if it's properly initialized
    if [ -f "migrations/env.py" ] && [ -f "migrations/alembic.ini" ]; then
        echo "✓ Flask-Migrate is already initialized"

        # Show current status
        echo ""
        echo "Current migration status:"
        flask db current || echo "No migrations applied yet"

        echo ""
        echo "Migration history:"
        flask db history || echo "No migration history"

        echo ""
        echo "To create a new migration:"
        echo "  flask db migrate -m 'Description of changes'"
        echo ""
        echo "To apply pending migrations:"
        echo "  flask db upgrade"

        exit 0
    else
        echo "⚠ Migrations directory exists but appears incomplete"
        echo "Removing and reinitializing..."
        rm -rf migrations
    fi
fi

# Initialize Flask-Migrate
echo "Initializing Flask-Migrate..."
flask db init

if [ $? -eq 0 ]; then
    echo "✓ Flask-Migrate initialized successfully"
else
    echo "✗ Failed to initialize Flask-Migrate"
    exit 1
fi

# Create initial migration
echo ""
echo "Creating initial migration..."
flask db migrate -m "Initial database schema"

if [ $? -eq 0 ]; then
    echo "✓ Initial migration created successfully"
else
    echo "✗ Failed to create initial migration"
    exit 1
fi

# Show the generated migration
echo ""
echo "Generated migration file:"
ls -la migrations/versions/

echo ""
echo "Review the migration file before applying:"
echo "  cat migrations/versions/*.py"

# Ask user if they want to apply the migration
echo ""
read -p "Do you want to apply this migration now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying migration..."
    flask db upgrade

    if [ $? -eq 0 ]; then
        echo "✓ Migration applied successfully"

        echo ""
        echo "Current migration status:"
        flask db current

        echo ""
        echo "Migration history:"
        flask db history
    else
        echo "✗ Failed to apply migration"
        exit 1
    fi
else
    echo "Migration not applied. You can apply it later with:"
    echo "  flask db upgrade"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Your Flask-Migrate system is now set up!"
echo ""
echo "Next steps:"
echo "1. Test your application to ensure everything works"
echo "2. For future schema changes:"
echo "   - Edit your models in app/models/"
echo "   - Run: flask db migrate -m 'Description of changes'"
echo "   - Review the generated migration file"
echo "   - Run: flask db upgrade"
echo ""
echo "Useful commands:"
echo "  flask db current     # Show current migration"
echo "  flask db history     # Show migration history"
echo "  flask db downgrade   # Rollback last migration"
echo ""
echo "For more information, see: migrations/README.md"
