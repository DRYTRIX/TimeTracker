#!/usr/bin/env python
"""Script to check and verify audit_logs table setup"""

import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.audit_log import AuditLog
from sqlalchemy import inspect as sqlalchemy_inspect

def check_audit_table():
    """Check if audit_logs table exists and show status"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Audit Logs Table Check")
        print("=" * 60)
        
        # Check if table exists
        try:
            inspector = sqlalchemy_inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'audit_logs' in tables:
                print("✓ audit_logs table EXISTS")
                
                # Check table structure
                columns = inspector.get_columns('audit_logs')
                print(f"\nTable has {len(columns)} columns:")
                for col in columns:
                    print(f"  - {col['name']} ({col['type']})")
                
                # Check indexes
                indexes = inspector.get_indexes('audit_logs')
                print(f"\nTable has {len(indexes)} indexes:")
                for idx in indexes:
                    print(f"  - {idx['name']}: {', '.join(idx['column_names'])}")
                
                # Count existing audit logs
                try:
                    count = AuditLog.query.count()
                    print(f"\n✓ Current audit log entries: {count}")
                    
                    if count > 0:
                        # Show recent entries
                        recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()
                        print("\nRecent audit log entries:")
                        for log in recent:
                            print(f"  - {log.created_at}: {log.action} {log.entity_type}#{log.entity_id} by user#{log.user_id}")
                except Exception as e:
                    print(f"\n⚠ Could not query audit logs: {e}")
                    print("   This might indicate a schema mismatch.")
                
            else:
                print("✗ audit_logs table DOES NOT EXIST")
                print("\nTo create the table, run:")
                print("  flask db upgrade")
                print("\nOr manually apply migration:")
                print("  migrations/versions/044_add_audit_logs_table.py")
                
        except Exception as e:
            print(f"✗ Error checking table: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    success = check_audit_table()
    sys.exit(0 if success else 1)

