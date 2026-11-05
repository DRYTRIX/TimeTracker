#!/usr/bin/env python3
"""
Simple database initialization script for TimeTracker
This script ensures the database has the correct schema
"""

import os
import sys
import time

from sqlalchemy import create_engine, inspect, text


def wait_for_database(url, max_attempts=30, delay=2):
    """Wait for database to be ready"""
    print(f"Waiting for database to be ready...")

    for attempt in range(max_attempts):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection established successfully")
            return engine
        except Exception as e:
            print(f"Waiting for database... (attempt {attempt+1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                print("Database not ready after waiting, exiting...")
                sys.exit(1)

    return None


def ensure_correct_schema(engine):
    """Ensure the database has the correct schema"""
    print("Ensuring correct database schema...")

    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Check if tasks table exists
        if "tasks" not in existing_tables:
            print("Creating tasks table...")
            create_tasks_sql = """
            CREATE TABLE tasks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
                assigned_to INTEGER REFERENCES users(id),
                created_by INTEGER REFERENCES users(id) NOT NULL,
                due_date DATE,
                estimated_hours NUMERIC(5,2),
                actual_hours NUMERIC(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
            """

            with engine.connect() as conn:
                conn.execute(text(create_tasks_sql))
                conn.commit()
            print("✓ Tasks table created successfully")
        else:
            print("✓ Tasks table already exists")

        # Check if time_entries table exists and has task_id column
        if "time_entries" in existing_tables:
            time_entries_columns = [col["name"] for col in inspector.get_columns("time_entries")]

            if "task_id" not in time_entries_columns:
                print("Adding task_id column to time_entries table...")
                add_column_sql = """
                ALTER TABLE time_entries 
                ADD COLUMN task_id INTEGER;
                """

                with engine.connect() as conn:
                    conn.execute(text(add_column_sql))
                    conn.commit()
                print("✓ task_id column added to time_entries table")
            else:
                print("✓ task_id column already exists in time_entries table")
        else:
            print("⚠ Warning: time_entries table does not exist")

        print("✓ Database schema is correct")
        return True

    except Exception as e:
        print(f"✗ Error ensuring correct schema: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function"""
    url = os.getenv("DATABASE_URL", "")

    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping initialization")
        return

    print(f"Database URL: {url}")

    # Wait for database to be ready
    engine = wait_for_database(url)

    # Ensure correct schema
    if ensure_correct_schema(engine):
        print("Database schema verification completed successfully")
        sys.exit(0)
    else:
        print("Database schema verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
