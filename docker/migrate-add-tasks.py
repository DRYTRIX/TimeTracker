#!/usr/bin/env python3
"""
Database migration script to add Task Management feature
"""

import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Task


def migrate_database():
    """Run the database migration"""
    app = create_app()

    with app.app_context():
        print("Starting Task Management migration...")

        try:
            # Use the app's built-in migration function
            from app import migrate_task_management_tables

            migrate_task_management_tables()

            print("\nMigration completed successfully!")
            print("Task Management feature is now available.")
            return True

        except Exception as e:
            print(f"✗ Migration failed: {e}")
            return False


if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
