#!/usr/bin/env python
"""Verify audit logs setup - check routes, table, and imports"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 70)
print("Audit Logs Setup Verification")
print("=" * 70)

# Test 1: Check if modules can be imported
print("\n1. Testing imports...")
try:
    from app.models.audit_log import AuditLog
    print("   ✓ AuditLog model imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import AuditLog: {e}")
    sys.exit(1)

try:
    from app.utils.audit import check_audit_table_exists, reset_audit_table_cache
    print("   ✓ Audit utility imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import audit utility: {e}")
    sys.exit(1)

try:
    from app.routes.audit_logs import audit_logs_bp
    print("   ✓ Audit logs blueprint imported successfully")
    print(f"   Blueprint name: {audit_logs_bp.name}")
except Exception as e:
    print(f"   ✗ Failed to import audit_logs blueprint: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check routes in blueprint
print("\n2. Checking blueprint routes...")
routes = []
for rule in audit_logs_bp.url_map.iter_rules() if hasattr(audit_logs_bp, 'url_map') else []:
    routes.append(rule.rule)

# Check deferred functions (routes not yet registered)
if hasattr(audit_logs_bp, 'deferred_functions'):
    print(f"   Found {len(audit_logs_bp.deferred_functions)} deferred route functions")
    for func in audit_logs_bp.deferred_functions:
        if hasattr(func, '__name__'):
            print(f"     - {func.__name__}")

# Test 3: Create app and check registered routes
print("\n3. Creating app and checking registered routes...")
try:
    from app import create_app
    app = create_app()
    
    # Find all audit-related routes
    audit_routes = []
    for rule in app.url_map.iter_rules():
        if 'audit' in rule.rule.lower():
            audit_routes.append({
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': sorted([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']])
            })
    
    if audit_routes:
        print(f"   ✓ Found {len(audit_routes)} registered audit log route(s):")
        for route in audit_routes:
            print(f"     {route['rule']} -> {route['endpoint']} [{', '.join(route['methods'])}]")
    else:
        print("   ✗ No audit log routes found in app!")
        print("   This means the blueprint was not registered properly.")
        print("\n   Checking app initialization...")
        
        # Check if blueprint is in the app
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        if 'audit_logs' in blueprint_names:
            print("   ✓ Blueprint is registered in app")
        else:
            print("   ✗ Blueprint 'audit_logs' NOT found in app blueprints")
            print(f"   Available blueprints: {', '.join(sorted(blueprint_names))}")
    
    # Test 4: Check database table
    print("\n4. Checking database table...")
    with app.app_context():
        reset_audit_table_cache()
        table_exists = check_audit_table_exists(force_check=True)
        
        if table_exists:
            print("   ✓ audit_logs table exists")
            try:
                count = AuditLog.query.count()
                print(f"   Current log count: {count}")
            except Exception as e:
                print(f"   ⚠ Could not query table: {e}")
        else:
            print("   ✗ audit_logs table does NOT exist")
            print("   Run migration: flask db upgrade")
            
            # Show available tables
            try:
                from sqlalchemy import inspect as sqlalchemy_inspect
                inspector = sqlalchemy_inspect(app.extensions['sqlalchemy'].db.engine)
                tables = inspector.get_table_names()
                print(f"\n   Available tables ({len(tables)}):")
                for table in sorted(tables)[:20]:  # Show first 20
                    print(f"     - {table}")
                if len(tables) > 20:
                    print(f"     ... and {len(tables) - 20} more")
            except Exception as e:
                print(f"   Could not list tables: {e}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("Verification Complete")
print("=" * 70)
print("\nIf routes are missing, restart your Flask application.")
print("If table is missing, run: flask db upgrade")

