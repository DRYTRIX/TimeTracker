"""
Legacy migration helpers (task management and issues tables).
Extracted from app/__init__.py. Prefer Flask-Migrate/Alembic for new schema changes.
"""


def migrate_task_management_tables():
    """Check and migrate Task Management tables if they don't exist."""
    from app import db

    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "tasks" not in existing_tables:
            print("Task Management: Creating tasks table...")
            db.create_all()
            print("✓ Tasks table created successfully")
        else:
            print("Task Management: Tasks table already exists")

        if "time_entries" in existing_tables:
            time_entries_columns = [col["name"] for col in inspector.get_columns("time_entries")]
            if "task_id" not in time_entries_columns:
                print("Task Management: Adding task_id column to time_entries table...")
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE time_entries ADD COLUMN task_id INTEGER REFERENCES tasks(id)"))
                    print("✓ task_id column added to time_entries table")
                except Exception as e:
                    print(f"⚠ Warning: Could not add task_id column: {e}")
                    print("  You may need to manually add this column or recreate the database")
            else:
                print("Task Management: task_id column already exists in time_entries table")

        print("Task Management migration check completed")

    except Exception as e:
        print(f"⚠ Warning: Task Management migration check failed: {e}")
        print("  The application will continue, but Task Management features may not work properly")


def migrate_issues_table():
    """Check and migrate Issues table if it doesn't exist."""
    from app import db

    try:
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "issues" not in existing_tables:
            print("Issues: Creating issues table...")
            from app.models import Issue

            Issue.__table__.create(db.engine, checkfirst=True)
            print("✓ Issues table created successfully")
        else:
            print("Issues: Issues table already exists")

        print("Issues migration check completed")

    except Exception as e:
        print(f"⚠ Warning: Issues migration check failed: {e}")
        print("  The application will continue, but Issues features may not work properly")
