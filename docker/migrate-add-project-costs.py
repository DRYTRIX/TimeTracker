#!/usr/bin/env python3
"""
Migration script to add project_costs table to the database.
This script adds support for tracking project expenses beyond hourly work.

Usage:
    python migrate-add-project-costs.py
"""

import os
import sys

import psycopg2
from psycopg2 import sql


def get_db_connection():
    """Get database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "timetracker"),
        user=os.getenv("DB_USER", "timetracker"),
        password=os.getenv("DB_PASSWORD", "timetracker"),
    )


def table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        );
    """,
        (table_name,),
    )
    return cursor.fetchone()[0]


def migrate():
    """Run the migration"""
    print("Starting project_costs migration...")

    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # Check if table already exists
        if table_exists(cursor, "project_costs"):
            print("✓ Table 'project_costs' already exists. Skipping migration.")
            return True

        print("Creating project_costs table...")

        # Create table
        cursor.execute("""
            CREATE TABLE project_costs (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                description VARCHAR(500) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount NUMERIC(10, 2) NOT NULL,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
                billable BOOLEAN NOT NULL DEFAULT TRUE,
                invoiced BOOLEAN NOT NULL DEFAULT FALSE,
                invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
                cost_date DATE NOT NULL,
                notes TEXT,
                receipt_path VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✓ Created project_costs table")

        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX ix_project_costs_project_id ON project_costs(project_id);")
        cursor.execute("CREATE INDEX ix_project_costs_user_id ON project_costs(user_id);")
        cursor.execute("CREATE INDEX ix_project_costs_cost_date ON project_costs(cost_date);")
        cursor.execute("CREATE INDEX ix_project_costs_invoice_id ON project_costs(invoice_id);")
        print("✓ Created indexes")

        # Add comments
        print("Adding table comments...")
        cursor.execute("""
            COMMENT ON TABLE project_costs IS
            'Tracks project expenses beyond hourly work (travel, materials, services, etc.)';
        """)
        cursor.execute("""
            COMMENT ON COLUMN project_costs.category IS
            'Category of cost: travel, materials, services, equipment, software, other';
        """)
        cursor.execute("""
            COMMENT ON COLUMN project_costs.billable IS
            'Whether this cost should be billed to the client';
        """)
        cursor.execute("""
            COMMENT ON COLUMN project_costs.invoiced IS
            'Whether this cost has been included in an invoice';
        """)
        print("✓ Added comments")

        # Commit the transaction
        conn.commit()
        print("✓ Migration completed successfully!")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        if conn:
            conn.rollback()
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
