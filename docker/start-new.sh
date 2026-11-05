#!/bin/bash
set -e
cd /app
export FLASK_APP=app

echo "=== Starting TimeTracker ==="

echo "Waiting for database to be ready..."
# Wait for Postgres to be ready
python - <<"PY"
import os
import time
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

url = os.getenv("DATABASE_URL", "")
if url.startswith("postgresql"):
    for attempt in range(30):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection established successfully")
            break
        except Exception as e:
            print(f"Waiting for database... (attempt {attempt+1}/30): {e}")
            time.sleep(2)
    else:
        print("Database not ready after waiting, exiting...")
        sys.exit(1)
else:
    print("No PostgreSQL database configured, skipping connection check")
PY

echo "=== FIXING DATABASE SCHEMA ==="

# Step 1: Create tasks table if it doesn't exist
echo "Step 1: Ensuring tasks table exists..."
python - <<"PY"
import os
import sys
from sqlalchemy import create_engine, text, inspect

url = os.getenv("DATABASE_URL", "")
if url.startswith("postgresql"):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        if 'tasks' not in inspector.get_table_names():
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
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
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

    except Exception as e:
        print(f"Error creating tasks table: {e}")
        sys.exit(1)
else:
    print("No PostgreSQL database configured")
    sys.exit(0)
PY

# Step 2: Add task_id column to time_entries if it doesn't exist
echo "Step 2: Ensuring task_id column exists in time_entries..."
python - <<"PY"
import os
import sys
from sqlalchemy import create_engine, text, inspect

url = os.getenv("DATABASE_URL", "")
if url.startswith("postgresql"):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        if 'time_entries' in inspector.get_table_names():
            columns = inspector.get_columns("time_entries")
            column_names = [col['name'] for col in columns]
            print(f"Current columns in time_entries: {column_names}")

            if 'task_id' not in column_names:
                print("Adding task_id column...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE time_entries ADD COLUMN task_id INTEGER;"))
                    conn.commit()
                print("✓ task_id column added successfully")
            else:
                print("✓ task_id column already exists")
        else:
            print("⚠ Warning: time_entries table does not exist")

    except Exception as e:
        print(f"Error adding task_id column: {e}")
        sys.exit(1)
else:
    print("No PostgreSQL database configured")
    sys.exit(0)
PY

# Step 2.5: Add missing columns to tasks table if it exists
echo "Step 2.5: Ensuring tasks table has all required columns..."
python - <<"PY"
import os
import sys
from sqlalchemy import create_engine, text, inspect

url = os.getenv("DATABASE_URL", "")
if url.startswith("postgresql"):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        if 'tasks' in inspector.get_table_names():
            columns = inspector.get_columns("tasks")
            column_names = [col['name'] for col in columns]
            print(f"Current columns in tasks: {column_names}")

            # Check for missing columns
            missing_columns = []
            required_columns = ['started_at', 'completed_at']

            for col in required_columns:
                if col not in column_names:
                    missing_columns.append(col)

            if missing_columns:
                print(f"Adding missing columns to tasks table: {missing_columns}")
                with engine.connect() as conn:
                    for col in missing_columns:
                        if col == 'started_at':
                            conn.execute(text("ALTER TABLE tasks ADD COLUMN started_at TIMESTAMP;"))
                        elif col == 'completed_at':
                            conn.execute(text("ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMP;"))
                    conn.commit()
                print("✓ Missing columns added to tasks table successfully")
            else:
                print("✓ tasks table has all required columns")
        else:
            print("⚠ Warning: tasks table does not exist")

    except Exception as e:
        print(f"Error adding missing columns to tasks: {e}")
        sys.exit(1)
else:
    print("No PostgreSQL database configured")
    sys.exit(0)
PY

# Step 3: Run the main database initialization
echo "Step 3: Running main database initialization..."
python /app/docker/init-database.py
if [ $? -ne 0 ]; then
    echo "Database initialization failed. Exiting."
    exit 1
fi

# Step 4: Run the SQL database initialization (for invoice tables)
echo "Step 4: Running SQL database initialization..."
python /app/docker/init-database-sql.py
if [ $? -ne 0 ]; then
    echo "SQL database initialization failed. Exiting."
    exit 1
fi

# Step 5: Run company branding migration
echo "Step 5: Running company branding migration..."
python /app/docker/migrate-add-company-branding.py
if [ $? -ne 0 ]; then
    echo "Company branding migration failed. Exiting."
    exit 1
fi

# Step 6: Test system packages
echo "Step 6: Testing system packages..."
python /app/docker/test-packages.py
echo "Package test completed"

# Step 7: Test PDF generation capabilities
echo "Step 7: Testing PDF generation..."
python /app/docker/test-pdf-generation.py
echo "PDF generation test completed (warnings are normal if WeasyPrint dependencies missing)"

# Step 8: Test invoice routing
echo "Step 8: Testing invoice routing..."
python /app/docker/test-routing.py
echo "Routing test completed"

echo "=== DATABASE SCHEMA FIXED SUCCESSFULLY ==="

echo "Starting application..."
exec gunicorn --bind 0.0.0.0:8080 --worker-class eventlet --workers 1 --timeout 120 "app:create_app()"
