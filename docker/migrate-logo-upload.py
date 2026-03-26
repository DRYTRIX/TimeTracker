#!/usr/bin/env python3
"""
Migration script to update logo system from file paths to file uploads
"""

import os
import sys
from sqlalchemy import create_engine, text, MetaData, Table, Column, String
from sqlalchemy.orm import sessionmaker

def migrate_logo_system():
    """Migrate from company_logo_path to company_logo_filename"""
    
    # Database connection
    database_url = os.getenv('DATABASE_URL', 'sqlite:///timetracker.db')
    
    try:
        engine = create_engine(database_url)
        metadata = MetaData()
        
        # Check if settings table exists
        inspector = engine.inspect(engine)
        if 'settings' not in inspector.get_table_names():
            print("❌ Settings table does not exist. Please run the company branding migration first.")
            return False
        
        # Get current columns
        columns = [col['name'] for col in inspector.get_columns('settings')]
        print(f"Current columns: {columns}")
        
        # Check if migration is needed
        if 'company_logo_filename' in columns and 'company_logo_path' not in columns:
            print("✅ Logo upload system already migrated")
            return True
        
        if 'company_logo_path' not in columns:
            print("❌ company_logo_path column not found. Please run the company branding migration first.")
            return False
        
        # Create the uploads directory structure
        create_uploads_directories()
        
        # Rename column from company_logo_path to company_logo_filename
        with engine.connect() as conn:
            # For SQLite
            if 'sqlite' in database_url:
                # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
                print("🔄 SQLite detected - recreating table structure...")
                
                # Get current data
                result = conn.execute(text("SELECT * FROM settings"))
                rows = result.fetchall()
                column_names = result.keys()
                
                if rows:
                    # Create new table with updated schema
                    conn.execute(text("""
                        CREATE TABLE settings_new (
                            id INTEGER PRIMARY KEY,
                            timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Rome',
                            currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                            rounding_minutes INTEGER NOT NULL DEFAULT 1,
                            single_active_timer BOOLEAN NOT NULL DEFAULT 1,
                            allow_self_register BOOLEAN NOT NULL DEFAULT 1,
                            idle_timeout_minutes INTEGER NOT NULL DEFAULT 30,
                            backup_retention_days INTEGER NOT NULL DEFAULT 30,
                            backup_time VARCHAR(5) NOT NULL DEFAULT '02:00',
                            export_delimiter VARCHAR(1) NOT NULL DEFAULT ',',
                            company_name VARCHAR(200) NOT NULL DEFAULT 'Your Company Name',
                            company_address TEXT NOT NULL DEFAULT 'Your Company Address',
                            company_email VARCHAR(200) NOT NULL DEFAULT 'info@yourcompany.com',
                            company_phone VARCHAR(50) NOT NULL DEFAULT '+1 (555) 123-4567',
                            company_website VARCHAR(200) NOT NULL DEFAULT 'www.yourcompany.com',
                            company_logo_filename VARCHAR(255) DEFAULT '',
                            company_tax_id VARCHAR(100) DEFAULT '',
                            company_bank_info TEXT DEFAULT '',
                            invoice_prefix VARCHAR(50) NOT NULL DEFAULT 'INV',
                            invoice_number_pattern VARCHAR(120) NOT NULL DEFAULT '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}',
                            invoice_start_number INTEGER NOT NULL DEFAULT 1000,
                            invoice_terms TEXT NOT NULL DEFAULT 'Payment is due within 30 days of invoice date.',
                            invoice_notes TEXT NOT NULL DEFAULT 'Thank you for your business!',
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Copy data, converting company_logo_path to company_logo_filename
                    for row in rows:
                        row_dict = dict(zip(column_names, row))
                        
                        # Convert logo path to filename if it exists
                        logo_filename = ''
                        if row_dict.get('company_logo_path'):
                            old_path = row_dict['company_logo_path']
                            if old_path and os.path.exists(old_path):
                                # Extract filename from path
                                logo_filename = os.path.basename(old_path)
                                print(f"📁 Converting logo path: {old_path} -> {logo_filename}")
                            else:
                                print(f"⚠️  Logo path not found: {old_path}")
                        
                        # Insert into new table
                        conn.execute(text("""
                            INSERT INTO settings_new (
                                id, timezone, currency, rounding_minutes, single_active_timer,
                                allow_self_register, idle_timeout_minutes, backup_retention_days,
                                backup_time, export_delimiter, company_name, company_address,
                                company_email, company_phone, company_website, company_logo_filename,
                                company_tax_id, company_bank_info, invoice_prefix, invoice_number_pattern, invoice_start_number,
                                invoice_terms, invoice_notes, created_at, updated_at
                            ) VALUES (
                                :id, :timezone, :currency, :rounding_minutes, :single_active_timer,
                                :allow_self_register, :idle_timeout_minutes, :backup_retention_days,
                                :backup_time, :export_delimiter, :company_name, :company_address,
                                :company_email, :company_phone, :company_website, :company_logo_filename,
                                :company_tax_id, :company_bank_info, :invoice_prefix, :invoice_number_pattern, :invoice_start_number,
                                :invoice_terms, :invoice_notes, :created_at, :updated_at
                            )
                        """), {
                            'id': row_dict.get('id'),
                            'timezone': row_dict.get('timezone', 'Europe/Rome'),
                            'currency': row_dict.get('currency', 'EUR'),
                            'rounding_minutes': row_dict.get('rounding_minutes', 1),
                            'single_active_timer': row_dict.get('single_active_timer', True),
                            'allow_self_register': row_dict.get('allow_self_register', True),
                            'idle_timeout_minutes': row_dict.get('idle_timeout_minutes', 30),
                            'backup_retention_days': row_dict.get('backup_retention_days', 30),
                            'backup_time': row_dict.get('backup_time', '02:00'),
                            'export_delimiter': row_dict.get('export_delimiter', ','),
                            'company_name': row_dict.get('company_name', 'Your Company Name'),
                            'company_address': row_dict.get('company_address', 'Your Company Address'),
                            'company_email': row_dict.get('company_email', 'info@yourcompany.com'),
                            'company_phone': row_dict.get('company_phone', '+1 (555) 123-4567'),
                            'company_website': row_dict.get('company_website', 'www.yourcompany.com'),
                            'company_logo_filename': logo_filename,
                            'company_tax_id': row_dict.get('company_tax_id', ''),
                            'company_bank_info': row_dict.get('company_bank_info', ''),
                            'invoice_prefix': row_dict.get('invoice_prefix', 'INV'),
                            'invoice_number_pattern': row_dict.get(
                                'invoice_number_pattern', '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}'
                            ),
                            'invoice_start_number': row_dict.get('invoice_start_number', 1000),
                            'invoice_terms': row_dict.get('invoice_terms', 'Payment is due within 30 days of invoice date.'),
                            'invoice_notes': row_dict.get('invoice_notes', 'Thank you for your business!'),
                            'created_at': row_dict.get('created_at'),
                            'updated_at': row_dict.get('updated_at')
                        })
                    
                    # Drop old table and rename new one
                    conn.execute(text("DROP TABLE settings"))
                    conn.execute(text("ALTER TABLE settings_new RENAME TO settings"))
                    
                else:
                    # No data to migrate, just update schema
                    conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename"))
                
            else:
                # For other databases (PostgreSQL, MySQL)
                print("🔄 Updating column name...")
                conn.execute(text("ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename"))
            
            conn.commit()
            print("✅ Logo upload system migration completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def create_uploads_directories():
    """Create the uploads directory structure"""
    try:
        # Get the app root directory
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uploads_dir = os.path.join(app_root, 'app', 'static', 'uploads', 'logos')
        
        # Create directories
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Create .gitkeep file to preserve directory in git
        gitkeep_file = os.path.join(uploads_dir, '.gitkeep')
        if not os.path.exists(gitkeep_file):
            with open(gitkeep_file, 'w') as f:
                f.write('# This file ensures the uploads directory is preserved in git\n')
        
        print(f"✅ Created uploads directory: {uploads_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create uploads directories: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting logo upload system migration...")
    
    success = migrate_logo_system()
    
    if success:
        print("🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Go to Admin → Settings")
        print("3. Upload your company logo using the new file upload interface")
        print("4. The logo will automatically appear throughout the application")
    else:
        print("💥 Migration failed. Please check the error messages above.")
        sys.exit(1)
