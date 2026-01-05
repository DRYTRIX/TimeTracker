#!/usr/bin/env python3
"""
Quick fix script for missing quotes.template_id column.

This script adds the missing template_id column to the quotes table.
This is a workaround for cases where migration 102 hasn't been applied yet.

Usage:
    python scripts/fix_quotes_template_id.py
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@localhost:5432/timetracker")


def has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def has_index(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists"""
    try:
        indexes = inspector.get_indexes(table_name)
        return any((idx.get("name") or "") == index_name for idx in indexes)
    except Exception:
        return False


def has_foreign_key(inspector, table_name: str, fk_name: str) -> bool:
    """Check if a foreign key constraint exists"""
    try:
        fks = inspector.get_foreign_keys(table_name)
        return any((fk.get("name") or "") == fk_name for fk in fks)
    except Exception:
        return False


def main():
    """Main function to fix missing template_id column"""
    print("=" * 60)
    print("TimeTracker - Fix Missing quotes.template_id Column")
    print("=" * 60)
    print()
    
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        print()
        
        # Check if quotes table exists
        if not has_table(inspector, 'quotes'):
            print("✗ 'quotes' table does not exist. Please run migrations first.")
            return 1
        
        # Check if column already exists
        if has_column(inspector, 'quotes', 'template_id'):
            print("✓ Column 'template_id' already exists in 'quotes' table")
            
            # Verify index exists
            if not has_index(inspector, 'quotes', 'ix_quotes_template_id'):
                print("Creating missing index ix_quotes_template_id...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("CREATE INDEX ix_quotes_template_id ON quotes (template_id)"))
                        conn.commit()
                    print("✓ Index created")
                except Exception as e:
                    print(f"⚠ Warning: Could not create index: {e}")
            
            # Verify foreign key exists (only if quote_pdf_templates table exists)
            if has_table(inspector, 'quote_pdf_templates'):
                if not has_foreign_key(inspector, 'quotes', 'fk_quotes_template_id'):
                    print("Creating missing foreign key fk_quotes_template_id...")
                    try:
                        with engine.connect() as conn:
                            conn.execute(text(
                                "ALTER TABLE quotes "
                                "ADD CONSTRAINT fk_quotes_template_id "
                                "FOREIGN KEY (template_id) "
                                "REFERENCES quote_pdf_templates(id) "
                                "ON DELETE SET NULL"
                            ))
                            conn.commit()
                        print("✓ Foreign key created")
                    except Exception as e:
                        print(f"⚠ Warning: Could not create foreign key: {e}")
            
            print()
            print("=" * 60)
            print("✓ All required columns and constraints already exist")
            print("=" * 60)
            return 0
        
        # Column doesn't exist, add it
        print("Adding template_id column to quotes table...")
        try:
            with engine.connect() as conn:
                # Add column
                conn.execute(text("ALTER TABLE quotes ADD COLUMN template_id INTEGER"))
                conn.commit()
            print("✓ Column added")
        except Exception as e:
            print(f"✗ Failed to add column: {e}")
            return 1
        
        # Create index
        print("Creating index ix_quotes_template_id...")
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE INDEX ix_quotes_template_id ON quotes (template_id)"))
                conn.commit()
            print("✓ Index created")
        except Exception as e:
            print(f"⚠ Warning: Could not create index: {e}")
        
        # Create foreign key if quote_pdf_templates table exists
        if has_table(inspector, 'quote_pdf_templates'):
            print("Creating foreign key fk_quotes_template_id...")
            try:
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE quotes "
                        "ADD CONSTRAINT fk_quotes_template_id "
                        "FOREIGN KEY (template_id) "
                        "REFERENCES quote_pdf_templates(id) "
                        "ON DELETE SET NULL"
                    ))
                    conn.commit()
                print("✓ Foreign key created")
            except Exception as e:
                print(f"⚠ Warning: Could not create foreign key: {e}")
        else:
            print("⚠ quote_pdf_templates table does not exist, skipping foreign key")
        
        print()
        print("=" * 60)
        print("✓ Successfully fixed quotes.template_id column")
        print("=" * 60)
        print()
        print("Note: This is a quick fix. For proper migration management,")
        print("      you should run: flask db upgrade")
        print()
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
