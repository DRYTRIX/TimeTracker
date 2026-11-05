#!/usr/bin/env python3
"""
Immediate fix for missing invoice tables
Run this script to create the missing tables right now
"""

import os
import sys
import subprocess


def main():
    print("=== Fixing Missing Invoice Tables ===")

    # Run the fix script
    try:
        result = subprocess.run(
            [sys.executable, "/app/docker/fix-invoice-tables.py"], capture_output=True, text=True, check=True
        )

        print("✓ Fix script output:")
        print(result.stdout)

        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"✗ Fix script failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)

    print("=== Invoice Tables Fixed ===")
    print("You can now access the invoice functionality!")


if __name__ == "__main__":
    main()
