#!/usr/bin/env python3
"""
Test script to verify invoice routing is working
Run this to check if all invoice endpoints are accessible
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, "/app")


def test_imports():
    """Test if all required modules can be imported"""
    try:
        from app import create_app
        from app.routes.invoices import invoices_bp

        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_blueprint_routes():
    """Test if the blueprint has all required routes"""
    try:
        from app.routes.invoices import invoices_bp

        # Check if the blueprint has the required routes
        required_routes = [
            "list_invoices",
            "create_invoice",
            "view_invoice",
            "edit_invoice",
            "update_invoice_status",
            "delete_invoice",
            "generate_from_time",
            "export_invoice_csv",
            "export_invoice_pdf",
            "duplicate_invoice",
        ]

        print("\nChecking blueprint routes:")
        all_routes_ok = True

        # Get the actual view functions from the blueprint
        view_functions = invoices_bp.view_functions

        for route_name in required_routes:
            if route_name in view_functions:
                print(f"✓ {route_name}")
            else:
                print(f"✗ {route_name}")
                all_routes_ok = False

        return all_routes_ok

    except Exception as e:
        print(f"✗ Route check failed: {e}")
        return False


def test_url_generation():
    """Test if URLs can be generated for all routes"""
    try:
        from app import create_app
        from app.routes.invoices import invoices_bp

        # Create a test app context
        app = create_app()

        with app.app_context():
            from flask import url_for

            # Test URL generation for key routes
            test_urls = [
                ("invoices.list_invoices", {}),
                ("invoices.create_invoice", {}),
                ("invoices.view_invoice", {"invoice_id": 1}),
                ("invoices.edit_invoice", {"invoice_id": 1}),
                ("invoices.update_invoice_status", {"invoice_id": 1}),
                ("invoices.delete_invoice", {"invoice_id": 1}),
                ("invoices.generate_from_time", {"invoice_id": 1}),
                ("invoices.export_invoice_csv", {"invoice_id": 1}),
                ("invoices.export_invoice_pdf", {"invoice_id": 1}),
                ("invoices.duplicate_invoice", {"invoice_id": 1}),
            ]

            print("\nTesting URL generation:")
            all_urls_ok = True

            for endpoint, values in test_urls:
                try:
                    url = url_for(endpoint, **values)
                    print(f"✓ {endpoint}: {url}")
                except Exception as e:
                    print(f"✗ {endpoint}: {e}")
                    all_urls_ok = False

            return all_urls_ok

    except Exception as e:
        print(f"✗ URL generation test failed: {e}")
        return False


def main():
    print("=== Invoice Routing Test ===")

    # Test imports
    if not test_imports():
        print("\n✗ Import test failed - cannot continue")
        return

    # Test blueprint routes
    routes_ok = test_blueprint_routes()

    # Test URL generation
    urls_ok = test_url_generation()

    # Summary
    print("\n=== Summary ===")
    if routes_ok and urls_ok:
        print("✓ All invoice routing tests passed")
        print("✓ Application should work correctly")
    else:
        print("⚠ Some routing tests failed")
        print("⚠ Check the errors above")

    print("\n=== Recommendations ===")
    if not routes_ok:
        print("1. Check blueprint route definitions")
        print("2. Verify function names match route names")

    if not urls_ok:
        print("1. Check URL generation in templates")
        print("2. Verify endpoint names in url_for() calls")
        print("3. Check if all required parameters are provided")


if __name__ == "__main__":
    main()
