#!/usr/bin/env python3
"""
Migration script to fix invoice currency codes.
Updates all invoices to use the currency from Settings instead of hard-coded EUR.
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Invoice, Settings

def fix_invoice_currencies():
    """Update all invoices to use currency from Settings"""
    app = create_app()
    
    with app.app_context():
        # Get the currency from settings
        settings = Settings.get_settings()
        target_currency = settings.currency if settings else 'USD'
        
        print(f"Target currency from settings: {target_currency}")
        
        # Get all invoices
        invoices = Invoice.query.all()
        
        if not invoices:
            print("No invoices found in database.")
            return
        
        print(f"Found {len(invoices)} invoices to process.")
        
        # Update each invoice that doesn't match the target currency
        updated_count = 0
        for invoice in invoices:
            if invoice.currency_code != target_currency:
                print(f"Updating invoice {invoice.invoice_number}: {invoice.currency_code} -> {target_currency}")
                invoice.currency_code = target_currency
                updated_count += 1
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\nSuccessfully updated {updated_count} invoice(s) to use {target_currency}.")
            except Exception as e:
                db.session.rollback()
                print(f"Error updating invoices: {e}")
                sys.exit(1)
        else:
            print(f"\nAll invoices already using {target_currency}. No updates needed.")

if __name__ == '__main__':
    print("=" * 60)
    print("Invoice Currency Migration")
    print("=" * 60)
    print("\nThis script will update all invoices to use the currency")
    print("configured in Settings instead of the hard-coded default.\n")
    
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        fix_invoice_currencies()
    else:
        print("Migration cancelled.")

