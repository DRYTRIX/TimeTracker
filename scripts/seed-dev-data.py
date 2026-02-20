#!/usr/bin/env python3
"""
Development Data Seed Script

Seeds the database with test data for local development. Only runs when
FLASK_ENV=development. Creates users, clients, projects, tasks, time entries,
expenses, comments, inventory (warehouses, stock items, movements), and finance
data (currencies, tax rules, invoices, payments).

Usage (local):
    Set FLASK_ENV=development, then either:
      python scripts/seed-dev-data.py
      flask seed

Usage (Docker):
    docker compose exec app /app/docker/seed-dev-data.sh

    Or pass FLASK_ENV and use flask:
    docker compose exec -e FLASK_ENV=development app flask seed

See docs/development/SEED_DEV_DATA.md for full documentation.
"""

import os
import sys

# Force development environment for this script so seed is allowed
os.environ.setdefault("FLASK_ENV", "development")

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
os.environ.setdefault("FLASK_APP", "app")
os.chdir(project_root)


def main():
    if os.getenv("FLASK_ENV") != "development":
        print("FLASK_ENV must be 'development' to run the seed script.")
        print("Set FLASK_ENV=development and try again.")
        sys.exit(1)

    try:
        from app import create_app
        from app.utils.seed_dev_data import run_seed

        app = create_app()
        with app.app_context():
            counts = run_seed(
                extra_users=4,
                clients_count=20,
                projects_per_client=4,
                tasks_per_project=12,
                time_entries_per_task_approx=8,
                days_back=120,
                expense_categories=True,
                expenses_count=50,
                comments_count=80,
            )
        print("Development seed complete:")
        for key, value in counts.items():
            print(f"  {key}: {value}")
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
