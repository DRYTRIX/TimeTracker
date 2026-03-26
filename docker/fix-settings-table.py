#!/usr/bin/env python3
"""
Quick fix script to add missing columns to settings table
Run this to immediately resolve the database schema mismatch
"""

import os
import sys
from sqlalchemy import create_engine, text

def main():
    """Add missing columns to settings table"""
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker")
    
    print(f"Connecting to database: {url}")
    
    try:
        engine = create_engine(url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            print("Adding missing columns to settings table...")
            
            # Add missing columns
            columns_to_add = [
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_name VARCHAR(200) DEFAULT 'Your Company Name' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_address TEXT DEFAULT 'Your Company Address' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_email VARCHAR(200) DEFAULT 'info@yourcompany.com' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_phone VARCHAR(50) DEFAULT '+1 (555) 123-4567' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_website VARCHAR(200) DEFAULT 'www.yourcompany.com' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_tax_id VARCHAR(100) DEFAULT '' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_bank_info TEXT DEFAULT '' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_prefix VARCHAR(50) DEFAULT 'INV' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_number_pattern VARCHAR(120) DEFAULT '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_start_number INTEGER DEFAULT 1000 NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_terms TEXT DEFAULT 'Payment is due within 30 days of invoice date.' NOT NULL;",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_notes TEXT DEFAULT 'Thank you for your business!' NOT NULL;"
            ]
            
            for column_sql in columns_to_add:
                conn.execute(text(column_sql))
                print(f"✓ Added column: {column_sql.split()[-2]}")
            
            conn.commit()
            print("✓ All missing columns added successfully!")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
