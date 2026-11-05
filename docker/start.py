#!/usr/bin/env python3
"""
Python startup script for TimeTracker
This avoids any shell script issues and runs everything in Python
"""

import os
import sys
import time
import subprocess


def main():
    print("=== Starting TimeTracker (Python Mode) ===")

    # Set environment
    os.environ["FLASK_APP"] = "app"
    os.chdir("/app")

    print("Waiting for database to be ready...")
    time.sleep(5)  # Simple wait

    print("Running SQL database initialization (for basic tables)...")
    try:
        subprocess.run([sys.executable, "/app/docker/init-database-sql.py"], check=True)
        print("SQL database initialization completed")
    except subprocess.CalledProcessError as e:
        print(f"SQL database initialization failed: {e}")
        sys.exit(1)

    print("Running main database initialization...")
    try:
        subprocess.run([sys.executable, "/app/docker/init-database.py"], check=True)
        print("Database initialization completed")
    except subprocess.CalledProcessError as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

    print("Starting application...")
    # Start gunicorn
    os.execv(
        "/usr/local/bin/gunicorn",
        [
            "gunicorn",
            "--bind",
            "0.0.0.0:8080",
            "--worker-class",
            "eventlet",
            "--workers",
            "1",
            "--timeout",
            "120",
            "app:create_app()",
        ],
    )


if __name__ == "__main__":
    main()
