#!/usr/bin/env python3
"""
Simple script to apply the time rounding preferences migration
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text

def check_columns_exist():
    """Check if the time rounding columns already exist"""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        has_enabled = 'time_rounding_enabled' in columns
        has_minutes = 'time_rounding_minutes' in columns
        has_method = 'time_rounding_method' in columns
        
        return has_enabled, has_minutes, has_method

def apply_migration():
    """Apply the migration to add time rounding columns"""
    app = create_app()
    with app.app_context():
        print("Applying time rounding preferences migration...")
        
        # Check if columns already exist
        has_enabled, has_minutes, has_method = check_columns_exist()
        
        if has_enabled and has_minutes and has_method:
            print("✓ Migration already applied! All columns exist.")
            return True
        
        # Apply the migration
        try:
            if not has_enabled:
                print("Adding time_rounding_enabled column...")
                db.session.execute(text(
                    "ALTER TABLE users ADD COLUMN time_rounding_enabled BOOLEAN DEFAULT 1 NOT NULL"
                ))
            
            if not has_minutes:
                print("Adding time_rounding_minutes column...")
                db.session.execute(text(
                    "ALTER TABLE users ADD COLUMN time_rounding_minutes INTEGER DEFAULT 1 NOT NULL"
                ))
            
            if not has_method:
                print("Adding time_rounding_method column...")
                db.session.execute(text(
                    "ALTER TABLE users ADD COLUMN time_rounding_method VARCHAR(10) DEFAULT 'nearest' NOT NULL"
                ))
            
            db.session.commit()
            print("✓ Migration applied successfully!")
            
            # Verify
            has_enabled, has_minutes, has_method = check_columns_exist()
            if has_enabled and has_minutes and has_method:
                print("✓ Verification passed! All columns exist.")
                return True
            else:
                print("✗ Verification failed! Some columns are missing.")
                return False
                
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=== Time Rounding Preferences Migration ===")
    print()
    
    # Check current state
    try:
        has_enabled, has_minutes, has_method = check_columns_exist()
        print("Current database state:")
        print(f"  - time_rounding_enabled: {'✓ exists' if has_enabled else '✗ missing'}")
        print(f"  - time_rounding_minutes: {'✓ exists' if has_minutes else '✗ missing'}")
        print(f"  - time_rounding_method: {'✓ exists' if has_method else '✗ missing'}")
        print()
    except Exception as e:
        print(f"✗ Could not check database state: {e}")
        sys.exit(1)
    
    # Apply migration if needed
    if has_enabled and has_minutes and has_method:
        print("All columns already exist. No migration needed.")
    else:
        success = apply_migration()
        if success:
            print("\n✓ Migration complete! You can now use the time rounding preferences feature.")
            print("  Please restart your application to load the changes.")
        else:
            print("\n✗ Migration failed. Please check the error messages above.")
            sys.exit(1)

