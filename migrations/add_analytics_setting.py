"""
Migration script to add allow_analytics field to settings table
Run this script to add the new privacy setting field
"""

import sqlite3
import os
from datetime import datetime


def migrate_sqlite():
    """Migrate SQLite database"""
    db_path = "instance/timetracker.db"
    if not os.path.exists(db_path):
        print(f"SQLite database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(settings)")
        columns = [column[1] for column in cursor.fetchall()]

        if "allow_analytics" not in columns:
            # Add the new column
            cursor.execute("ALTER TABLE settings ADD COLUMN allow_analytics BOOLEAN DEFAULT 1")
            conn.commit()
            print("✓ Added allow_analytics column to SQLite settings table")
        else:
            print("✓ allow_analytics column already exists in SQLite settings table")

        conn.close()
        return True

    except Exception as e:
        print(f"Error migrating SQLite database: {e}")
        return False


def migrate_postgres():
    """Migrate PostgreSQL database"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Get database URL from environment or use default
        db_url = os.getenv("DATABASE_URL", "postgresql://timetracker:timetracker@localhost:5432/timetracker")

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'settings' AND column_name = 'allow_analytics'
        """)

        if not cursor.fetchone():
            # Add the new column
            cursor.execute("ALTER TABLE settings ADD COLUMN allow_analytics BOOLEAN DEFAULT TRUE")
            conn.commit()
            print("✓ Added allow_analytics column to PostgreSQL settings table")
        else:
            print("✓ allow_analytics column already exists in PostgreSQL settings table")

        conn.close()
        return True

    except ImportError:
        print("PostgreSQL driver not available - skipping PostgreSQL migration")
        return False
    except Exception as e:
        print(f"Error migrating PostgreSQL database: {e}")
        return False


def main():
    """Run the migration"""
    print("Starting migration: Adding allow_analytics field to settings table")
    print("=" * 60)

    # Try SQLite first
    sqlite_success = migrate_sqlite()

    # Try PostgreSQL
    postgres_success = migrate_postgres()

    if sqlite_success or postgres_success:
        print("\n✓ Migration completed successfully!")
        print("\nThe new 'allow_analytics' setting has been added to your settings table.")
        print("Users can now control whether system information is shared for analytics.")
    else:
        print("\n✗ Migration failed for all database types.")
        print("Please check your database connection and try again.")


if __name__ == "__main__":
    main()
