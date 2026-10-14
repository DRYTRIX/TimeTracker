"""
One-off cleanup: decode HTML entities that sanitize_input() stored into text
fields. sanitize_input used bleach.clean (tags=[], strip=True), which escapes
surviving text ("&" -> "&amp;") — every web-UI write before the fix stored
double-escaped text. Rows written through the API were never affected.

Idempotent: values without entity patterns are left untouched, so the script
can be run repeatedly (and after the validation.py fix, new writes are clean).

Usage:
    python scripts/fix_double_escaped_entities.py            # dry run
    python scripts/fix_double_escaped_entities.py --apply    # write changes
"""

import argparse
import html
import re
import sys

ENTITY_RE = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]{1,9});")

# Model -> text columns fed by sanitize_input (web-UI write paths)
TARGETS = {
    "Task": ["name", "description"],
    "TimeEntry": ["notes", "tags"],
    "Client": ["name", "description", "contact_person", "phone", "address",
               "street", "postcode", "city", "vat_id"],
    "Project": ["name", "description", "billing_ref", "code"],
    "Issue": ["title", "description"],
    "User": ["full_name"],
    "StockItem": ["name", "description", "category", "notes"],
}


def clean_value(value):
    if not isinstance(value, str) or "&" not in value:
        return value, False
    cleaned = html.unescape(value)
    return (cleaned, True) if ENTITY_RE.search(value) else (value, False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = parser.parse_args()

    from app import create_app, db
    from app import models

    app = create_app()
    with app.app_context():
        total_rows = 0
        total_fields = 0
        report = []

        for model_name, fields in TARGETS.items():
            model = getattr(models, model_name, None)
            if model is None:
                report.append(f"{model_name}: model not found, skipped")
                continue

            existing = [f for f in fields if hasattr(model, f)]
            if not existing:
                report.append(f"{model_name}: no matching columns, skipped")
                continue

            column = next(iter(existing))
            query = model.query.filter(getattr(model, column).like("%&%"))
            rows = query.all()
            rows_changed = 0
            fields_changed = 0

            for row in rows:
                row_touched = False
                for field in existing:
                    value = getattr(row, field)
                    cleaned, changed = clean_value(value)
                    if changed and cleaned != value:
                        setattr(row, field, cleaned)
                        fields_changed += 1
                        row_touched = True
                if row_touched:
                    rows_changed += 1

            if rows_changed:
                report.append(
                    f"{model_name}: {rows_changed} rows, {fields_changed} fields "
                    f"({', '.join(existing)})"
                )
                total_rows += rows_changed
                total_fields += fields_changed
            else:
                report.append(f"{model_name}: clean")

        if args.apply:
            db.session.commit()
            print("APPLIED changes.")
        else:
            db.session.rollback()
            print("DRY RUN — no changes written. Re-run with --apply to fix.")

        print(f"\nTotal: {total_rows} rows, {total_fields} fields")
        for line in report:
            print(f"  {line}")


if __name__ == "__main__":
    sys.exit(main())
