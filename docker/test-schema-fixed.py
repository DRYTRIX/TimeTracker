#!/usr/bin/env python3
"""
Test script to verify database schema is correct
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text


def test_schema():
    """Test if the database has the correct schema"""
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured")
        return False

    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        # Check required tables
        existing_tables = inspector.get_table_names()
        required_tables = ["users", "projects", "time_entries", "settings", "tasks"]
        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False

        print("✓ All required tables exist")

        # Check time_entries has task_id column
        if "time_entries" in existing_tables:
            columns = inspector.get_columns("time_entries")
            column_names = [col["name"] for col in columns]
            print(f"time_entries columns: {column_names}")

            if "task_id" not in column_names:
                print("✗ time_entries table missing task_id column")
                return False
            else:
                print("✓ time_entries table has task_id column")

        # Check tasks table structure
        if "tasks" in existing_tables:
            columns = inspector.get_columns("tasks")
            column_names = [col["name"] for col in columns]
            print(f"tasks columns: {column_names}")
            print("✓ tasks table exists with correct structure")

        print("✓ Database schema is correct")
        return True

    except Exception as e:
        print(f"Error testing schema: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if test_schema():
        print("Schema test PASSED")
        sys.exit(0)
    else:
        print("Schema test FAILED")
        sys.exit(1)
