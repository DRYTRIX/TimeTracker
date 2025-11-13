#!/usr/bin/env python
"""Test script to verify audit log routes are registered"""

import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app import create_app
    
    app = create_app()
    
    print("=" * 60)
    print("Checking Audit Log Routes")
    print("=" * 60)
    
    # Get all routes
    audit_routes = []
    for rule in app.url_map.iter_rules():
        if 'audit' in rule.rule.lower():
            audit_routes.append({
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': list(rule.methods)
            })
    
    if audit_routes:
        print(f"\n✓ Found {len(audit_routes)} audit log route(s):\n")
        for route in audit_routes:
            print(f"  Route: {route['rule']}")
            print(f"  Endpoint: {route['endpoint']}")
            print(f"  Methods: {', '.join(route['methods'])}")
            print()
    else:
        print("\n✗ No audit log routes found!")
        print("\nChecking for import errors...")
        
        # Try to import the blueprint
        try:
            from app.routes.audit_logs import audit_logs_bp
            print("✓ Blueprint imported successfully")
            print(f"  Blueprint name: {audit_logs_bp.name}")
            print(f"  Blueprint routes: {len(audit_logs_bp.deferred_functions)}")
        except Exception as e:
            print(f"✗ Error importing blueprint: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All routes containing 'audit':")
    print("=" * 60)
    for rule in app.url_map.iter_rules():
        if 'audit' in rule.rule.lower():
            print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods)})")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

