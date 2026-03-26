#!/usr/bin/env python3
"""
Migration script to add missing company branding columns to settings table
This script adds the missing columns that are expected by the Settings model
"""

import os
import sys
import time
from sqlalchemy import create_engine, text, inspect

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

def add_missing_columns(engine):
    """Add missing company branding columns to settings table"""
    print("Adding missing company branding columns to settings table...")
    
    # SQL statements to add missing columns
    add_columns_sql = """
    -- Add company branding columns
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_name VARCHAR(200) DEFAULT 'Your Company Name' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_address TEXT DEFAULT 'Your Company Address' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_email VARCHAR(200) DEFAULT 'info@yourcompany.com' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_phone VARCHAR(50) DEFAULT '+1 (555) 123-4567' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_website VARCHAR(200) DEFAULT 'www.yourcompany.com' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_tax_id VARCHAR(100) DEFAULT '' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS company_bank_info TEXT DEFAULT '' NOT NULL;
    
    -- Add invoice default columns
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_prefix VARCHAR(50) DEFAULT 'INV' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_number_pattern VARCHAR(120) DEFAULT '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_start_number INTEGER DEFAULT 1000 NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_terms TEXT DEFAULT 'Payment is due within 30 days of invoice date.' NOT NULL;
    ALTER TABLE settings ADD COLUMN IF NOT EXISTS invoice_notes TEXT DEFAULT 'Thank you for your business!' NOT NULL;
    """
    
    try:
        with engine.connect() as conn:
            # Execute the SQL statements
            conn.execute(text(add_columns_sql))
            conn.commit()
        
        print("✓ Missing columns added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding missing columns: {e}")
        return False

def verify_columns(engine):
    """Verify that all required columns exist in settings table"""
    print("Verifying settings table columns...")
    
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('settings')]
        
        required_columns = [
            'id', 'timezone', 'currency', 'rounding_minutes', 'single_active_timer',
            'allow_self_register', 'idle_timeout_minutes', 'backup_retention_days',
            'backup_time', 'export_delimiter', 'company_name', 'company_address',
            'company_email', 'company_phone', 'company_website', 'company_logo_filename',
            'company_tax_id', 'company_bank_info', 'invoice_prefix', 'invoice_number_pattern', 'invoice_start_number',
            'invoice_terms', 'invoice_notes', 'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"✗ Missing columns: {missing_columns}")
            return False
        else:
            print("✓ All required columns exist")
            return True
            
    except Exception as e:
        print(f"✗ Error verifying columns: {e}")
        return False

def update_existing_settings(engine):
    """Update existing settings with default values if they don't have company branding"""
    print("Updating existing settings with default company branding...")
    
    update_sql = """
    UPDATE settings SET 
        company_name = COALESCE(company_name, 'Your Company Name'),
        company_address = COALESCE(company_address, 'Your Company Address'),
        company_email = COALESCE(company_email, 'info@yourcompany.com'),
        company_phone = COALESCE(company_phone, '+1 (555) 123-4567'),
        company_website = COALESCE(company_website, 'www.yourcompany.com'),
        company_logo_filename = COALESCE(company_logo_filename, ''),
        company_tax_id = COALESCE(company_tax_id, ''),
        company_bank_info = COALESCE(company_bank_info, ''),
        invoice_prefix = COALESCE(invoice_prefix, 'INV'),
        invoice_number_pattern = COALESCE(invoice_number_pattern, '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}'),
        invoice_start_number = COALESCE(invoice_start_number, 1000),
        invoice_terms = COALESCE(invoice_terms, 'Payment is due within 30 days of invoice date.'),
        invoice_notes = COALESCE(invoice_notes, 'Thank you for your business!')
    WHERE id = (SELECT id FROM settings LIMIT 1);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(update_sql))
            conn.commit()
        
        print("✓ Existing settings updated successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error updating existing settings: {e}")
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
    if verify_columns(engine):
        print("All required columns already exist, no migration needed")
        return
    
    print("Migration needed, starting column addition...")
    
    # Add missing columns
    if not add_missing_columns(engine):
        print("Failed to add missing columns")
        sys.exit(1)
    
    # Update existing settings with defaults
    if not update_existing_settings(engine):
        print("Failed to update existing settings")
        sys.exit(1)
    
    # Verify everything was added
    if verify_columns(engine):
        print("✓ Migration completed successfully")
    else:
        print("✗ Migration failed - columns still missing")
        sys.exit(1)

if __name__ == "__main__":
    main()
