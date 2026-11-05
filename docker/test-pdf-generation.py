#!/usr/bin/env python3
"""
Test script to verify PDF generation works
Run this to test both WeasyPrint and ReportLab fallback
"""

import os
import sys


def test_weasyprint():
    """Test if WeasyPrint is available and working"""
    try:
        from weasyprint import HTML, CSS

        print("✓ WeasyPrint is available")
        return True
    except ImportError as e:
        print(f"✗ WeasyPrint import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ WeasyPrint error: {e}")
        return False


def test_reportlab():
    """Test if ReportLab is available and working"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        print("✓ ReportLab is available")
        return True
    except ImportError as e:
        print(f"✗ ReportLab import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ ReportLab error: {e}")
        return False


def test_system_libraries():
    """Test if required system libraries are available"""
    import ctypes.util

    required_libs = ["gobject-2.0-0", "pango-1.0-0", "cairo", "gdk_pixbuf-2.0"]

    print("\nChecking system libraries:")
    for lib in required_libs:
        lib_path = ctypes.util.find_library(lib)
        if lib_path:
            print(f"✓ {lib}: {lib_path}")
        else:
            print(f"✗ {lib}: Not found")

    return True


def main():
    print("=== PDF Generation Test ===")

    # Test system libraries
    test_system_libraries()

    print("\n=== Python Libraries ===")

    # Test WeasyPrint
    weasyprint_ok = test_weasyprint()

    # Test ReportLab
    reportlab_ok = test_reportlab()

    print("\n=== Summary ===")
    if weasyprint_ok:
        print("✓ WeasyPrint is working - High-quality PDFs available")
    elif reportlab_ok:
        print("⚠ WeasyPrint failed but ReportLab is available - Basic PDFs available")
    else:
        print("✗ Both PDF generators failed - No PDF generation available")

    print("\n=== Recommendations ===")
    if not weasyprint_ok:
        print("1. Install system dependencies: libgdk-pixbuf2.0-0, libpango-1.0-0, libcairo2")
        print("2. Rebuild Docker container with updated Dockerfile")
        print("3. Or use ReportLab fallback (already configured)")

    if not reportlab_ok:
        print("1. Install ReportLab: pip install reportlab==4.0.7")
        print("2. Add to requirements.txt")


if __name__ == "__main__":
    main()
