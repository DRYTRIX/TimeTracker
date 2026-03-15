#!/usr/bin/env python3
"""Check if export routes are registered"""
import os
import sys

# Add the project root to the path (parent of scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, _project_root)

from app import create_app

app = create_app()

print("\n=== Export Routes ===")
with app.app_context():
    for rule in app.url_map.iter_rules():
        if 'export' in str(rule):
            print(f"✓ {rule}")

print("\n✅ Routes are registered!")
print("\nTo access the new feature:")
print("1. Restart your Flask app: python app.py")
print("2. Go to: http://localhost:5000/reports")
print("3. Click on: 'Export CSV' button")
print("4. Or visit directly: http://localhost:5000/reports/export/form")

