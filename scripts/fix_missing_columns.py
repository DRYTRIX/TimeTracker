#!/usr/bin/env python3
"""
Script to manually add missing columns to the users table.
This is a workaround for cases where migrations show as applied but columns are missing.

Usage:
    python scripts/fix_missing_columns.py
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@localhost:5432/timetracker")


def has_column(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def add_column_if_missing(engine, table_name, column_name, column_type, nullable=True, default=None):
    """Add a column to a table if it doesn't exist"""
    if has_column(engine, table_name, column_name):
        print(f"✓ Column '{column_name}' already exists in '{table_name}'")
        return False
    
    try:
        with engine.connect() as conn:
            # Build ALTER TABLE statement
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if not nullable:
                alter_sql += " NOT NULL"
            if default is not None:
                alter_sql += f" DEFAULT {default}"
            
            conn.execute(text(alter_sql))
            conn.commit()
            print(f"✓ Added column '{column_name}' to '{table_name}'")
            return True
    except Exception as e:
        print(f"✗ Failed to add column '{column_name}' to '{table_name}': {e}")
        return False


def main():
    """Main function to add missing columns"""
    print("=" * 60)
    print("TimeTracker - Fix Missing Database Columns")
    print("=" * 60)
    print()
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        print()
        
        # Check if users table exists
        inspector = inspect(engine)
        if 'users' not in inspector.get_table_names():
            print("✗ 'users' table does not exist. Please run migrations first.")
            return 1
        
        print("Checking and adding missing columns to 'users' table...")
        print()
        
        # List of columns that should exist based on the User model
        # These are the columns that are commonly missing after migration issues
        columns_to_add = [
            {
                'name': 'password_hash',
                'type': 'VARCHAR(255)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'password_change_required',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'false'
            },
            {
                'name': 'email',
                'type': 'VARCHAR(200)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'full_name',
                'type': 'VARCHAR(200)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'theme_preference',
                'type': 'VARCHAR(10)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'preferred_language',
                'type': 'VARCHAR(8)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'oidc_sub',
                'type': 'VARCHAR(255)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'oidc_issuer',
                'type': 'VARCHAR(255)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'avatar_filename',
                'type': 'VARCHAR(255)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'email_notifications',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'true'
            },
            {
                'name': 'notification_overdue_invoices',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'true'
            },
            {
                'name': 'notification_task_assigned',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'true'
            },
            {
                'name': 'notification_task_comments',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'true'
            },
            {
                'name': 'notification_weekly_summary',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'false'
            },
            {
                'name': 'timezone',
                'type': 'VARCHAR(50)',
                'nullable': True,
                'default': None
            },
            {
                'name': 'date_format',
                'type': 'VARCHAR(20)',
                'nullable': False,
                'default': "'YYYY-MM-DD'"
            },
            {
                'name': 'time_format',
                'type': 'VARCHAR(10)',
                'nullable': False,
                'default': "'24h'"
            },
            {
                'name': 'week_start_day',
                'type': 'INTEGER',
                'nullable': False,
                'default': '1'
            },
            {
                'name': 'time_rounding_enabled',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'true'
            },
            {
                'name': 'time_rounding_minutes',
                'type': 'INTEGER',
                'nullable': False,
                'default': '1'
            },
            {
                'name': 'time_rounding_method',
                'type': 'VARCHAR(10)',
                'nullable': False,
                'default': "'nearest'"
            },
            {
                'name': 'standard_hours_per_day',
                'type': 'FLOAT',
                'nullable': False,
                'default': '8.0'
            },
            {
                'name': 'client_portal_enabled',
                'type': 'BOOLEAN',
                'nullable': False,
                'default': 'false'
            },
            {
                'name': 'client_id',
                'type': 'INTEGER',
                'nullable': True,
                'default': None
            },
        ]
        
        added_count = 0
        for col in columns_to_add:
            if add_column_if_missing(
                engine,
                'users',
                col['name'],
                col['type'],
                col['nullable'],
                col['default']
            ):
                added_count += 1
        
        print()
        print("=" * 60)
        if added_count > 0:
            print(f"✓ Successfully added {added_count} missing column(s)")
        else:
            print("✓ All columns already exist")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
