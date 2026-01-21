#!/usr/bin/env python
"""Script to check if audit logging is working"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.audit_log import AuditLog
from app.models import TimeEntry, User
from app.utils.audit import check_audit_table_exists, reset_audit_table_cache
from sqlalchemy import inspect as sqlalchemy_inspect

def check_audit_setup():
    """Check if audit logging is properly set up"""
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("Audit Logging Diagnostic")
        print("=" * 70)
        
        # Check 1: Table exists
        print("\n1. Checking if audit_logs table exists...")
        reset_audit_table_cache()
        table_exists = check_audit_table_exists(force_check=True)
        if table_exists:
            print("   ✓ audit_logs table EXISTS")
            
            # Count existing logs
            try:
                count = AuditLog.query.count()
                print(f"   ✓ Found {count} existing audit log entries")
            except Exception as e:
                print(f"   ✗ Error querying audit logs: {e}")
        else:
            print("   ✗ audit_logs table DOES NOT EXIST")
            print("   → Run migration: flask db upgrade")
            print("   → Or manually run: migrations/versions/044_add_audit_logs_table.py")
            return False
        
        # Check 2: Event listener registration
        print("\n2. Checking event listener registration...")
        from sqlalchemy import event
        from sqlalchemy.orm import Session
        from app.utils import audit
        
        # Check if the event listener is registered
        listeners = event.contains(Session, "after_flush", audit.receive_after_flush)
        if listeners:
            print("   ✓ Event listener is registered")
        else:
            print("   ✗ Event listener is NOT registered")
            print("   → Check app/__init__.py line 913: from app.utils import audit")
        
        # Check 3: Test with a sample operation
        print("\n3. Testing audit logging with a sample operation...")
        try:
            # Get a test user
            test_user = User.query.first()
            if not test_user:
                print("   ✗ No users found in database - cannot test")
                return False
            
            # Get a time entry to test with
            test_entry = TimeEntry.query.filter_by(user_id=test_user.id).first()
            if not test_entry:
                print("   ✗ No time entries found for test user - cannot test deletion")
                print("   → Create a time entry first, then delete it to test audit logging")
                return False
            
            print(f"   → Found test entry: TimeEntry#{test_entry.id}")
            print(f"   → Will test by updating a field (not deleting)")
            
            # Test with an update instead of delete
            original_notes = test_entry.notes
            test_entry.notes = f"Test audit log - {original_notes or ''}"
            db.session.commit()
            
            # Check if audit log was created
            import time
            time.sleep(0.1)  # Small delay to ensure commit completed
            
            recent_logs = AuditLog.query.filter_by(
                entity_type="TimeEntry",
                entity_id=test_entry.id,
                action="updated"
            ).order_by(AuditLog.created_at.desc()).limit(1).all()
            
            if recent_logs:
                print(f"   ✓ Audit log created successfully!")
                print(f"   → Log ID: {recent_logs[0].id}")
                print(f"   → Action: {recent_logs[0].action}")
                print(f"   → Entity: {recent_logs[0].entity_type}#{recent_logs[0].entity_id}")
            else:
                print("   ✗ No audit log was created for the update")
                print("   → Check application logs for errors")
                print("   → Verify event listener is being triggered")
            
            # Restore original notes
            test_entry.notes = original_notes
            db.session.commit()
            
        except Exception as e:
            print(f"   ✗ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 70)
        print("Diagnostic complete!")
        print("=" * 70)
        return True

if __name__ == "__main__":
    success = check_audit_setup()
    sys.exit(0 if success else 1)

