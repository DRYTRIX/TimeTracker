#!/usr/bin/env python3
"""
Fix script to resolve column name mismatch in settings table
The database has 'company_logo_path' but the application expects 'company_logo_filename'
"""

import os
import sys
from sqlalchemy import create_engine, text


def main():
    """Fix the column name mismatch in settings table"""
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker")

    print(f"Connecting to database: {url}")

    try:
        engine = create_engine(url, pool_pre_ping=True)

        with engine.connect() as conn:
            print("Checking current table structure...")

            # Check what columns currently exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))

            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")

            # Check if we have the old column name
            if "company_logo_path" in columns and "company_logo_filename" not in columns:
                print("Found 'company_logo_path' column, need to rename it to 'company_logo_filename'")

                # Rename the column
                conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename;"))
                print("✓ Renamed company_logo_path to company_logo_filename")

            elif "company_logo_filename" in columns:
                print("✓ company_logo_filename column already exists")

            else:
                print("Neither column exists, adding company_logo_filename")
                conn.execute(
                    text("ALTER TABLE settings ADD COLUMN company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL;")
                )
                print("✓ Added company_logo_filename column")

            # Verify the fix
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))

            columns_after = [row[0] for row in result]
            print(f"Columns after fix: {columns_after}")

            if "company_logo_filename" in columns_after:
                print("✓ Column name mismatch fixed successfully!")
            else:
                print("✗ Failed to fix column name mismatch")
                sys.exit(1)

            conn.commit()

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
