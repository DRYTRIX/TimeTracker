#!/usr/bin/env python3
"""
Migration script to rename database fields from start_utc/end_utc to start_time/end_time
This script should be run after updating the application code but before starting the new version.
"""

import os
import sys

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


def check_migration_needed(engine):
    """Check if migration is needed"""
    print("Checking if migration is needed...")

    try:
        inspector = inspect(engine)
        columns = inspector.get_columns("time_entries")
        column_names = [col["name"] for col in columns]

        has_old_fields = "start_utc" in column_names or "end_utc" in column_names
        has_new_fields = "start_time" in column_names or "end_time" in column_names

        if has_old_fields and not has_new_fields:
            print("✓ Migration needed: old field names detected")
            return True
        elif has_new_fields and not has_old_fields:
            print("✓ Migration not needed: new field names already exist")
            return False
        elif has_old_fields and has_new_fields:
            print("⚠ Migration partially done: both old and new field names exist")
            return True
        else:
            print("⚠ Unknown state: neither old nor new field names found")
            return True

    except Exception as e:
        print(f"✗ Error checking migration status: {e}")
        return True


def migrate_database(engine):
    """Perform the migration"""
    print("Starting database migration...")

    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Check if old columns exist
                inspector = inspect(engine)
                columns = inspector.get_columns("time_entries")
                column_names = [col["name"] for col in columns]

                if "start_utc" in column_names:
                    print("Renaming start_utc to start_time...")
                    conn.execute(text("ALTER TABLE time_entries RENAME COLUMN start_utc TO start_time"))

                if "end_utc" in column_names:
                    print("Renaming end_utc to end_time...")
                    conn.execute(text("ALTER TABLE time_entries RENAME COLUMN end_utc TO end_time"))

                # Update indexes
                print("Updating indexes...")

                # Drop old index if it exists
                try:
                    conn.execute(text("DROP INDEX IF EXISTS idx_time_entries_start_utc"))
                except:
                    pass

                # Create new index
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON time_entries(start_time)"))

                # Commit transaction
                trans.commit()
                print("✓ Migration completed successfully")
                return True

            except Exception as e:
                trans.rollback()
                print(f"✗ Migration failed: {e}")
                return False

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        return False


def verify_migration(engine):
    """Verify the migration was successful"""
    print("Verifying migration...")

    try:
        inspector = inspect(engine)
        columns = inspector.get_columns("time_entries")
        column_names = [col["name"] for col in columns]

        has_new_fields = "start_time" in column_names and "end_time" in column_names
        has_old_fields = "start_utc" in column_names or "end_utc" in column_names

        if has_new_fields and not has_old_fields:
            print("✓ Migration verified: new field names are present, old ones are gone")
            return True
        else:
            print(f"✗ Migration verification failed: new fields: {has_new_fields}, old fields: {has_old_fields}")
            return False

    except Exception as e:
        print(f"✗ Error verifying migration: {e}")
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

    # Check if migration is needed
    if not check_migration_needed(engine):
        print("No migration needed, exiting...")
        return

    # Perform migration
    if not migrate_database(engine):
        print("Migration failed, exiting...")
        sys.exit(1)

    # Verify migration
    if not verify_migration(engine):
        print("Migration verification failed, exiting...")
        sys.exit(1)

    print("✓ Database migration completed successfully!")


if __name__ == "__main__":
    import time

    main()
