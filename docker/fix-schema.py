#!/usr/bin/env python3
"""
Simple script to fix the missing task_id column
"""

import os
import sys
import time
from sqlalchemy import create_engine, text, inspect


def fix_schema():
    """Fix the missing task_id column"""
    url = os.getenv("DATABASE_URL", "")

    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured")
        return False

    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        # Check if time_entries table exists
        if "time_entries" not in inspector.get_table_names():
            print("time_entries table not found")
            return False

        # Check if task_id column exists
        columns = inspector.get_columns("time_entries")
        column_names = [col["name"] for col in columns]
        print(f"Current columns in time_entries: {column_names}")

        if "task_id" in column_names:
            print("task_id column already exists")
            return True

        # Add the missing column
        print("Adding task_id column...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE time_entries ADD COLUMN task_id INTEGER;"))
            conn.commit()

        print("✓ task_id column added successfully")
        return True

    except Exception as e:
        print(f"Error fixing schema: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if fix_schema():
        print("Schema fix completed successfully")
        sys.exit(0)
    else:
        print("Schema fix failed")
        sys.exit(1)
