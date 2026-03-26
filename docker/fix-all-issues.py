#!/usr/bin/env python3
"""
Comprehensive fix script for all TimeTracker issues
This script will:
1. Fix database schema (column name mismatches)
2. Fix file upload permissions
3. Ensure all required directories exist with proper permissions
"""

import os
import sys
import stat
from sqlalchemy import create_engine, text

def fix_database_schema(engine):
    """Fix database schema issues"""
    print("=== Fixing Database Schema ===")
    
    try:
        with engine.connect() as conn:
            # Check current table structure
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'settings' 
                ORDER BY column_name;
            """))
            
            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")
            
            # Fix column name mismatch
            if 'company_logo_path' in columns and 'company_logo_filename' not in columns:
                print("Found 'company_logo_path' column, renaming to 'company_logo_filename'")
                conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename;"))
                print("✓ Renamed company_logo_path to company_logo_filename")
                columns.remove('company_logo_path')
                columns.append('company_logo_filename')
            elif 'company_logo_filename' in columns:
                print("✓ company_logo_filename column already exists")
            else:
                print("Neither column exists, adding company_logo_filename")
                conn.execute(text("ALTER TABLE settings ADD COLUMN company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL;"))
                print("✓ Added company_logo_filename column")
                columns.append('company_logo_filename')
            
            # Add any missing required columns
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
            
            # Update existing settings with default values
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
            
            conn.commit()
            print("✓ Database schema fixed successfully")
            
    except Exception as e:
        print(f"✗ Error fixing database schema: {e}")
        raise

def fix_file_permissions():
    """Fix file upload permissions"""
    print("\n=== Fixing File Upload Permissions ===")
    
    # Define the upload directories that need permissions fixed
    upload_dirs = [
        '/app/app/static/uploads',
        '/app/app/static/uploads/logos',
        '/app/static/uploads',
        '/app/static/uploads/logos'
    ]
    
    try:
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                print(f"Fixing permissions for: {upload_dir}")
                
                # Set directory permissions to 755 (rwxr-xr-x)
                os.chmod(upload_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✓ Set directory permissions for: {upload_dir}")
                
                # Check if we can write to the directory
                test_file = os.path.join(upload_dir, 'test_permissions.tmp')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"✓ Write permission test passed for: {upload_dir}")
                except Exception as e:
                    print(f"⚠ Write permission test failed for: {upload_dir}: {e}")
                    
            else:
                print(f"Creating directory: {upload_dir}")
                try:
                    os.makedirs(upload_dir, mode=0o755, exist_ok=True)
                    print(f"✓ Created directory: {upload_dir}")
                except Exception as e:
                    print(f"✗ Failed to create directory {upload_dir}: {e}")
        
        # Also check the parent static directory
        static_dirs = ['/app/app/static', '/app/static']
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                print(f"Fixing permissions for static directory: {static_dir}")
                os.chmod(static_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✓ Set static directory permissions for: {static_dir}")
        
        print("✓ File permissions fixed successfully")
        
    except Exception as e:
        print(f"✗ Error fixing file permissions: {e}")
        raise

def main():
    """Main function to fix all issues"""
    print("=== Starting comprehensive TimeTracker fix ===")
    
    # Fix file permissions first (this doesn't require database connection)
    try:
        fix_file_permissions()
    except Exception as e:
        print(f"Warning: Could not fix file permissions: {e}")
    
    # Fix database schema
    try:
        url = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker")
        print(f"\nConnecting to database: {url}")
        
        engine = create_engine(url, pool_pre_ping=True)
        fix_database_schema(engine)
        
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        print("Database fixes skipped. Please ensure database is running and accessible.")
        return
    
    print("\n=== All fixes completed successfully! ===")
    print("Your TimeTracker application should now work properly:")
    print("✓ Database schema is correct")
    print("✓ File uploads should work")
    print("✓ Company logo uploads should function")

if __name__ == "__main__":
    main()
