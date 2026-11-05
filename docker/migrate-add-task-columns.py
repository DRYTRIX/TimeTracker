#!/usr/bin/env python3
"""
Migration script to add Task Management columns and tables
This script adds the missing task_id column to time_entries table
and creates the tasks table if they don't exist.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect


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


def migrate_task_management(engine):
    """Migrate database to add Task Management features"""
    print("Starting Task Management migration...")

    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Check if tasks table exists
        if "tasks" not in existing_tables:
            print("Creating tasks table...")
            create_tasks_table_sql = """
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
            
            CREATE INDEX ix_tasks_project_id ON tasks (project_id);
            CREATE INDEX ix_tasks_status ON tasks (status);
            CREATE INDEX ix_tasks_priority ON tasks (priority);
            CREATE INDEX ix_tasks_assigned_to ON tasks (assigned_to);
            CREATE INDEX ix_tasks_created_by ON tasks (created_by);
            """

            with engine.connect() as conn:
                conn.execute(text(create_tasks_table_sql))
                conn.commit()
            print("✓ Tasks table created successfully")
        else:
            print("✓ Tasks table already exists")

        # Check if task_id column exists in time_entries table
        if "time_entries" in existing_tables:
            time_entries_columns = [col["name"] for col in inspector.get_columns("time_entries")]

            if "task_id" not in time_entries_columns:
                print("Adding task_id column to time_entries table...")

                # Add task_id column
                add_column_sql = """
                ALTER TABLE time_entries 
                ADD COLUMN task_id INTEGER;
                """

                # Create index for performance
                create_index_sql = """
                CREATE INDEX ix_time_entries_task_id ON time_entries (task_id);
                """

                with engine.connect() as conn:
                    conn.execute(text(add_column_sql))
                    conn.execute(text(create_index_sql))
                    conn.commit()
                print("✓ task_id column added to time_entries table")
            else:
                print("✓ task_id column already exists in time_entries table")

            # Add foreign key constraint if it doesn't exist
            try:
                # Check if foreign key constraint exists
                constraints_sql = """
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'time_entries' 
                AND constraint_type = 'FOREIGN KEY' 
                AND constraint_name LIKE '%task_id%';
                """

                with engine.connect() as conn:
                    result = conn.execute(text(constraints_sql))
                    constraints = [row[0] for row in result]

                    if not constraints:
                        print("Adding foreign key constraint for task_id...")
                        add_fk_sql = """
                        ALTER TABLE time_entries 
                        ADD CONSTRAINT fk_time_entries_task_id 
                        FOREIGN KEY (task_id) REFERENCES tasks(id);
                        """

                        with engine.connect() as conn:
                            conn.execute(text(add_fk_sql))
                            conn.commit()
                        print("✓ Foreign key constraint added for task_id")
                    else:
                        print("✓ Foreign key constraint already exists for task_id")

            except Exception as e:
                print(f"Warning: Could not add foreign key constraint: {e}")
                print("This is not critical, continuing...")
        else:
            print("⚠ Warning: time_entries table does not exist")

        print("Task Management migration completed successfully!")
        return True

    except Exception as e:
        print(f"✗ Task Management migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function"""
    url = os.getenv("DATABASE_URL", "")

    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping migration")
        return

    print(f"Database URL: {url}")

    # Wait for database to be ready
    engine = wait_for_database(url)

    # Run migration
    if migrate_task_management(engine):
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
