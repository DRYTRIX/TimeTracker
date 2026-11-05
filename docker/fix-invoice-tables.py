#!/usr/bin/env python3
"""
Quick fix script to create missing invoice tables
Run this if the database is missing invoice tables
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect


def main():
    url = os.getenv("DATABASE_URL", "")

    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured")
        return

    print(f"Database URL: {url}")

    try:
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)

        # Check if invoice tables exist
        existing_tables = inspector.get_table_names()
        print(f"Existing tables: {existing_tables}")

        if "invoices" in existing_tables and "invoice_items" in existing_tables:
            print("✓ Invoice tables already exist")
            return

        print("Creating missing invoice tables...")

        # Create invoices table
        if "invoices" not in existing_tables:
            print("Creating invoices table...")
            create_invoices_sql = """
            CREATE TABLE invoices (
                id SERIAL PRIMARY KEY,
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                client_name VARCHAR(200) NOT NULL,
                client_email VARCHAR(200),
                client_address TEXT,
                issue_date DATE NOT NULL,
                due_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'draft' NOT NULL,
                subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0,
                tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
                tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
                total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
                notes TEXT,
                terms TEXT,
                created_by INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            with engine.connect() as conn:
                conn.execute(text(create_invoices_sql))
                conn.commit()
            print("✓ invoices table created")

        # Create invoice_items table
        if "invoice_items" not in existing_tables:
            print("Creating invoice_items table...")
            create_invoice_items_sql = """
            CREATE TABLE invoice_items (
                id SERIAL PRIMARY KEY,
                invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
                description VARCHAR(500) NOT NULL,
                quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
                unit_price NUMERIC(10, 2) NOT NULL,
                total_amount NUMERIC(10, 2) NOT NULL,
                time_entry_ids VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            with engine.connect() as conn:
                conn.execute(text(create_invoice_items_sql))
                conn.commit()
            print("✓ invoice_items table created")

        print("✓ All invoice tables created successfully")

    except Exception as e:
        print(f"Error creating invoice tables: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
