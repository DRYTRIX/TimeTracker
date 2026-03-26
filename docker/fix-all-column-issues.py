#!/usr/bin/env python3
"""
Comprehensive fix script for all settings table column issues
This script will:
1. Rename company_logo_path to company_logo_filename
2. Add any missing columns
3. Ensure all required columns exist with correct names
"""

import os
import sys
from sqlalchemy import create_engine, text

def main():
    """Fix all column issues in settings table"""
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker")
    
    print(f"Connecting to database: {url}")
    
    try:
        engine = create_engine(url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            print("=== Starting comprehensive settings table fix ===")
            
            # Step 1: Check current table structure
            print("\n1. Checking current table structure...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))
            
            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")
            
            # Step 2: Fix column name mismatch
            print("\n2. Fixing column name mismatch...")
            if 'company_logo_path' in columns and 'company_logo_filename' not in columns:
                print("Found 'company_logo_path' column, renaming to 'company_logo_filename'")
                conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename;"))
                print("✓ Renamed company_logo_path to company_logo_filename")
                # Update our columns list
                columns.remove('company_logo_path')
                columns.append('company_logo_filename')
            elif 'company_logo_filename' in columns:
                print("✓ company_logo_filename column already exists")
            else:
                print("Neither column exists, adding company_logo_filename")
                conn.execute(text("ALTER TABLE settings ADD COLUMN company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL;"))
                print("✓ Added company_logo_filename column")
                columns.append('company_logo_filename')
            
            # Step 3: Add any missing required columns
            print("\n3. Adding missing required columns...")
            required_columns = {
                'company_name': 'VARCHAR(200) DEFAULT \'Your Company Name\' NOT NULL',
                'company_address': 'TEXT DEFAULT \'Your Company Address\' NOT NULL',
                'company_email': 'VARCHAR(200) DEFAULT \'info@yourcompany.com\' NOT NULL',
                'company_phone': 'VARCHAR(50) DEFAULT \'+1 (555) 123-4567\' NOT NULL',
                'company_website': 'VARCHAR(200) DEFAULT \'www.yourcompany.com\' NOT NULL',
                'company_tax_id': 'VARCHAR(100) DEFAULT \'\' NOT NULL',
                'company_bank_info': 'TEXT DEFAULT \'\' NOT NULL',
                'invoice_prefix': 'VARCHAR(50) DEFAULT \'INV\' NOT NULL',
                'invoice_number_pattern': 'VARCHAR(120) DEFAULT \'{PREFIX}-{YYYY}{MM}{DD}-{SEQ}\' NOT NULL',
                'invoice_start_number': 'INTEGER DEFAULT 1000 NOT NULL',
                'invoice_terms': 'TEXT DEFAULT \'Payment is due within 30 days of invoice date.\' NOT NULL',
                'invoice_notes': 'TEXT DEFAULT \'Thank you for your business!\' NOT NULL'
            }
            
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    print(f"Adding missing column: {col_name}")
                    sql = f"ALTER TABLE settings ADD COLUMN {col_name} {col_def};"
                    conn.execute(text(sql))
                    print(f"✓ Added {col_name}")
                    columns.append(col_name)
                else:
                    print(f"✓ {col_name} already exists")
            
            # Step 4: Update existing settings with default values
            print("\n4. Updating existing settings with default values...")
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
            
            conn.execute(text(update_sql))
            print("✓ Updated existing settings with default values")
            
            # Step 5: Verify final structure
            print("\n5. Verifying final table structure...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))
            
            final_columns = [row[0] for row in result]
            print(f"Final columns: {final_columns}")
            
            # Check if all required columns exist
            missing_required = [col for col in required_columns.keys() if col not in final_columns]
            if 'company_logo_filename' not in final_columns:
                missing_required.append('company_logo_filename')
            
            if missing_required:
                print(f"✗ Still missing columns: {missing_required}")
                sys.exit(1)
            else:
                print("✓ All required columns are present!")
            
            conn.commit()
            print("\n=== Settings table fix completed successfully! ===")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
