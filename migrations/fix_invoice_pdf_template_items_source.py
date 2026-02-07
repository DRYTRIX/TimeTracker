#!/usr/bin/env python3
"""
Migration script to fix invoice PDF template table data source.
Updates table elements from invoice.items to invoice.all_line_items so that
extra goods and expenses are included in PDF exports (fixes Issue #503).
"""

import sys
import os
import json

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import InvoicePDFTemplate


OLD_DATA_SOURCE = "{{ invoice.items }}"
NEW_DATA_SOURCE = "{{ invoice.all_line_items }}"


def fix_invoice_pdf_templates():
    """Update invoice PDF templates to use all_line_items instead of items"""
    app = create_app()

    with app.app_context():
        templates = InvoicePDFTemplate.query.all()

        if not templates:
            print("No invoice PDF templates found in database.")
            return

        print(f"Found {len(templates)} invoice PDF template(s) to process.")

        updated_count = 0
        for template in templates:
            if not template.template_json or not template.template_json.strip():
                continue

            try:
                data = json.loads(template.template_json)
            except json.JSONDecodeError as e:
                print(f"  Skipping template {template.page_size} (id={template.id}): invalid JSON - {e}")
                continue

            elements = data.get("elements", [])
            modified = False

            for element in elements:
                if element.get("type") == "table":
                    data_src = element.get("data", "")
                    # Handle exact match and variations with extra whitespace
                    if data_src.strip() == OLD_DATA_SOURCE.strip():
                        element["data"] = NEW_DATA_SOURCE
                        modified = True
                        print(f"  Updating template {template.page_size}: table data source")

            if modified:
                template.template_json = json.dumps(data)
                updated_count += 1

        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\nSuccessfully updated {updated_count} invoice PDF template(s).")
                print("PDF exports will now include items, extra goods, and expenses.")
            except Exception as e:
                db.session.rollback()
                print(f"Error updating templates: {e}")
                sys.exit(1)
        else:
            print("\nNo templates required updates. All templates already use the new data source.")


if __name__ == "__main__":
    print("=" * 60)
    print("Invoice PDF Template Migration (Issue #503)")
    print("=" * 60)
    print("\nThis migration updates invoice PDF templates to include")
    print("extra goods and expenses in the items table.")
    print("\nChange: invoice.items -> invoice.all_line_items")
    print()

    fix_invoice_pdf_templates()
