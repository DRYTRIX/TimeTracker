#!/usr/bin/env python3
"""
Simple database test script for TimeTracker
This script tests database connectivity and shows initialization status.
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text


def test_database():
    """Test database connectivity and show status"""
    url = os.getenv("DATABASE_URL", "")

    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured")
        return

    print(f"Testing database connection to: {url}")

    try:
        # Test connection
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ Database connection successful")
            print(f"  PostgreSQL version: {version}")

        # Check tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ["users", "projects", "time_entries", "settings"]

        print(f"\nDatabase tables:")
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (missing)")

        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f"\nDatabase is NOT fully initialized")
            print(f"Missing tables: {missing_tables}")
            return False
        else:
            print(f"\n✓ Database is fully initialized")
            return True

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
