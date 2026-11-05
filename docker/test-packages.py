#!/usr/bin/env python3
"""
Test script to verify system packages are available
Run this to check if WeasyPrint dependencies are installed
"""

import os
import subprocess
import sys


def check_package(package_name):
    """Check if a package is installed"""
    try:
        result = subprocess.run(["dpkg", "-l", package_name], capture_output=True, text=True, check=False)
        if result.returncode == 0 and package_name in result.stdout:
            return True
        return False
    except Exception:
        return False


def check_library(library_name):
    """Check if a library is available"""
    try:
        result = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and library_name in result.stdout:
            return True
        return False
    except Exception:
        return False


def main():
    print("=== System Package Test ===")

    # Check required packages
    required_packages = [
        "libgdk-pixbuf2.0-0",
        "libpango-1.0-0",
        "libcairo2",
        "libpangocairo-1.0-0",
        "libffi-dev",
        "shared-mime-info",
        "fonts-liberation",
        "fonts-dejavu-core",
    ]

    print("\nChecking installed packages:")
    all_packages_ok = True
    for package in required_packages:
        if check_package(package):
            print(f"✓ {package}")
        else:
            print(f"✗ {package}")
            all_packages_ok = False

    # Check libraries
    print("\nChecking available libraries:")
    required_libs = ["libgobject-2.0", "libpango-1.0", "libcairo", "libgdk_pixbuf-2.0"]

    all_libs_ok = True
    for lib in required_libs:
        if check_library(lib):
            print(f"✓ {lib}")
        else:
            print(f"✗ {lib}")
            all_libs_ok = False

    # Summary
    print("\n=== Summary ===")
    if all_packages_ok and all_libs_ok:
        print("✓ All WeasyPrint dependencies are available")
        print("✓ High-quality PDF generation should work")
    else:
        print("⚠ Some dependencies are missing")
        print("⚠ PDF generation may fall back to ReportLab")

    # Recommendations
    print("\n=== Recommendations ===")
    if not all_packages_ok:
        print("1. Rebuild Docker container with updated Dockerfile")
        print("2. Use Dockerfile.weasyprint for better compatibility")
        print("3. Or use ReportLab fallback (already configured)")

    if not all_libs_ok:
        print("1. Install missing system libraries")
        print("2. Check package names for your Debian version")
        print("3. Consider using a different base image")


if __name__ == "__main__":
    main()
