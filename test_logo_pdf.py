#!/usr/bin/env python3
"""
Debug script to test company logo in PDF generation
Run this to check if logo is properly configured and can be embedded in PDFs
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Settings, Invoice
from app.utils.pdf_generator import InvoicePDFGenerator

def test_logo_setup():
    """Test if logo is properly configured"""
    print("=" * 60)
    print("LOGO CONFIGURATION TEST")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        settings = Settings.get_settings()
        
        print(f"\n1. Logo filename in database: {settings.company_logo_filename or 'NONE'}")
        
        if not settings.company_logo_filename:
            print("   ❌ NO LOGO UPLOADED")
            print("   → Upload a logo in Admin → Settings → Company Branding")
            return False
        
        print(f"   ✓ Logo filename found: {settings.company_logo_filename}")
        
        logo_path = settings.get_logo_path()
        print(f"\n2. Logo file path: {logo_path}")
        
        if not logo_path:
            print("   ❌ Could not determine logo path")
            return False
        
        if not os.path.exists(logo_path):
            print(f"   ❌ LOGO FILE DOES NOT EXIST AT: {logo_path}")
            print(f"   → Check if file exists in app/static/uploads/logos/")
            return False
        
        print(f"   ✓ Logo file exists")
        
        file_size = os.path.getsize(logo_path)
        print(f"\n3. Logo file size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        
        if file_size == 0:
            print("   ❌ Logo file is empty")
            return False
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            print("   ⚠️  Logo file is very large (>5MB). Consider optimizing.")
        
        print(f"   ✓ Logo file has content")
        
        # Test base64 encoding
        print(f"\n4. Testing base64 encoding...")
        try:
            from app.utils.template_filters import get_logo_base64
            data_uri = get_logo_base64(logo_path)
            
            if not data_uri:
                print("   ❌ Base64 encoding failed (returned None)")
                return False
            
            if not data_uri.startswith('data:image/'):
                print(f"   ❌ Invalid data URI: {data_uri[:50]}...")
                return False
            
            encoded_size = len(data_uri)
            print(f"   ✓ Base64 encoding successful")
            print(f"   Data URI size: {encoded_size:,} bytes ({encoded_size/1024:.2f} KB)")
            print(f"   Data URI prefix: {data_uri[:50]}...")
            
        except Exception as e:
            print(f"   ❌ Error encoding logo: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        print("✓ LOGO CONFIGURATION IS CORRECT")
        print("=" * 60)
        return True

def test_pdf_generation():
    """Test PDF generation with logo"""
    print("\n" + "=" * 60)
    print("PDF GENERATION TEST")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # Get the most recent invoice
        invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        
        if not invoice:
            print("\n❌ NO INVOICES FOUND")
            print("   → Create an invoice first to test PDF generation")
            return False
        
        print(f"\n1. Testing with Invoice #{invoice.invoice_number}")
        print(f"   Project: {invoice.project.name}")
        print(f"   Client: {invoice.client_name}")
        
        try:
            print(f"\n2. Generating PDF...")
            generator = InvoicePDFGenerator(invoice)
            pdf_bytes = generator.generate_pdf()
            
            if not pdf_bytes:
                print("   ❌ PDF generation returned no data")
                return False
            
            pdf_size = len(pdf_bytes)
            print(f"   ✓ PDF generated successfully")
            print(f"   PDF size: {pdf_size:,} bytes ({pdf_size/1024:.2f} KB)")
            
            # Save PDF for inspection
            output_file = 'test_invoice.pdf'
            with open(output_file, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"\n3. PDF saved to: {output_file}")
            print(f"   → Open this file to check if logo appears")
            
            print("\n" + "=" * 60)
            print("✓ PDF GENERATION SUCCESSFUL")
            print("=" * 60)
            print(f"\n📄 Check the file: {output_file}")
            print("   Look for the logo in the top-left corner of the invoice")
            
            return True
            
        except Exception as e:
            print(f"\n   ❌ Error generating PDF: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run all tests"""
    print("\n🔍 TimeTracker PDF Logo Diagnostic Tool\n")
    
    logo_ok = test_logo_setup()
    
    if logo_ok:
        pdf_ok = test_pdf_generation()
        
        if pdf_ok:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED")
            print("=" * 60)
            print("\nIf the logo still doesn't appear in the PDF:")
            print("1. Open test_invoice.pdf and check manually")
            print("2. Check server logs for DEBUG messages when generating invoices")
            print("3. Try uploading a different logo (simple PNG <1MB)")
            print("4. Verify the logo works in the web UI first (Admin → Settings)")
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ PDF GENERATION FAILED")
            print("=" * 60)
            return 1
    else:
        print("\n" + "=" * 60)
        print("❌ LOGO CONFIGURATION FAILED")
        print("=" * 60)
        print("\nPlease fix the logo configuration first:")
        print("1. Login as admin")
        print("2. Go to Admin → Settings")
        print("3. Scroll to Company Branding section")
        print("4. Upload a logo (PNG, JPG, GIF, SVG, or WEBP)")
        print("5. Run this script again")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

