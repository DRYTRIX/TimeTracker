#!/usr/bin/env python3
"""
Migration script to add company branding fields to settings table
Run this to add the new fields for invoice PDF generation
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
        
        if 'settings' not in inspector.get_table_names():
            print("Settings table does not exist, creating it...")
            create_settings_table(engine)
        
        # Check existing columns
        columns = inspector.get_columns("settings")
        column_names = [col['name'] for col in columns]
        print(f"Current columns in settings: {column_names}")
        
        # Add company branding fields
        add_company_branding_fields(engine, column_names)
        
        # Add invoice default fields
        add_invoice_default_fields(engine, column_names)
        
        print("✓ Company branding migration completed successfully")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def create_settings_table(engine):
    """Create settings table if it doesn't exist"""
    create_sql = """
    CREATE TABLE settings (
        id SERIAL PRIMARY KEY,
        timezone VARCHAR(50) DEFAULT 'Europe/Rome' NOT NULL,
        currency VARCHAR(3) DEFAULT 'EUR' NOT NULL,
        rounding_minutes INTEGER DEFAULT 1 NOT NULL,
        single_active_timer BOOLEAN DEFAULT true NOT NULL,
        allow_self_register BOOLEAN DEFAULT true NOT NULL,
        idle_timeout_minutes INTEGER DEFAULT 30 NOT NULL,
        backup_retention_days INTEGER DEFAULT 30 NOT NULL,
        backup_time VARCHAR(5) DEFAULT '02:00' NOT NULL,
        export_delimiter VARCHAR(1) DEFAULT ',' NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()
    print("✓ Settings table created")

def add_company_branding_fields(engine, existing_columns):
    """Add company branding fields to settings table"""
    fields_to_add = [
        ('company_name', 'VARCHAR(200) DEFAULT \'Your Company Name\' NOT NULL'),
        ('company_address', 'TEXT DEFAULT \'Your Company Address\' NOT NULL'),
        ('company_email', 'VARCHAR(200) DEFAULT \'info@yourcompany.com\' NOT NULL'),
        ('company_phone', 'VARCHAR(50) DEFAULT \'+1 (555) 123-4567\' NOT NULL'),
        ('company_website', 'VARCHAR(200) DEFAULT \'www.yourcompany.com\' NOT NULL'),
        ('company_logo_filename', 'VARCHAR(255) DEFAULT \'\' NOT NULL'),
        ('company_tax_id', 'VARCHAR(100) DEFAULT \'\''),
        ('company_bank_info', 'TEXT DEFAULT \'\'')
    ]
    
    for field_name, field_def in fields_to_add:
        if field_name not in existing_columns:
            print(f"Adding {field_name} field...")
            sql = f"ALTER TABLE settings ADD COLUMN {field_name} {field_def};"
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            print(f"✓ Added {field_name}")
        else:
            print(f"✓ {field_name} already exists")

def add_invoice_default_fields(engine, existing_columns):
    """Add invoice default fields to settings table"""
    fields_to_add = [
        ('invoice_prefix', 'VARCHAR(50) DEFAULT \'INV\' NOT NULL'),
        ('invoice_number_pattern', 'VARCHAR(120) DEFAULT \'{PREFIX}-{YYYY}{MM}{DD}-{SEQ}\' NOT NULL'),
        ('invoice_start_number', 'INTEGER DEFAULT 1000 NOT NULL'),
        ('invoice_terms', 'TEXT DEFAULT \'Payment is due within 30 days of invoice date.\' NOT NULL'),
        ('invoice_notes', 'TEXT DEFAULT \'Thank you for your business!\' NOT NULL')
    ]
    
    for field_name, field_def in fields_to_add:
        if field_name not in existing_columns:
            print(f"Adding {field_name} field...")
            sql = f"ALTER TABLE settings ADD COLUMN {field_name} {field_def};"
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            print(f"✓ Added {field_name}")
        else:
            print(f"✓ {field_name} already exists")

if __name__ == '__main__':
    main()
