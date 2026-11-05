#!/usr/bin/env python3
"""
Fix script for duplicate columns in settings table
This script will remove the old company_logo_path column and keep only company_logo_filename
"""

import os
import sys
from sqlalchemy import create_engine, text


def main():
    """Fix duplicate columns in settings table"""
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker")

    print(f"Connecting to database: {url}")

    try:
        engine = create_engine(url, pool_pre_ping=True)

        with engine.connect() as conn:
            print("=== Fixing duplicate columns in settings table ===")

            # Check current table structure
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))

            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")

            # Check if we have both columns
            has_old_column = "company_logo_path" in columns
            has_new_column = "company_logo_filename" in columns

            if has_old_column and has_new_column:
                print("Found both company_logo_path and company_logo_filename columns")
                print("This will cause confusion. Removing the old company_logo_path column...")

                # Remove the old column
                conn.execute(text("ALTER TABLE settings DROP COLUMN company_logo_path;"))
                print("✓ Removed old company_logo_path column")

            elif has_old_column and not has_new_column:
                print("Found only company_logo_path column, renaming to company_logo_filename")
                conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename;"))
                print("✓ Renamed company_logo_path to company_logo_filename")

            elif has_new_column and not has_old_column:
                print("✓ company_logo_filename column exists, no old column found")

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

            final_columns = [row[0] for row in result]
            print(f"Final columns: {final_columns}")

            if "company_logo_filename" in final_columns and "company_logo_path" not in final_columns:
                print("✓ Duplicate columns issue fixed successfully!")
                print("Only company_logo_filename column remains")
            else:
                print("✗ Failed to fix duplicate columns issue")
                sys.exit(1)

            conn.commit()

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
