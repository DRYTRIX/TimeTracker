#!/usr/bin/env python
"""Simple script to run tests and display results"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

if __name__ == "__main__":
    print("=" * 70)
    print("Running TimeTracker Tests")
    print("=" * 70)
    print()
    
    # Run pytest with arguments
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "-ra",
        "--color=no"
    ])
    
    print()
    print("=" * 70)
    print(f"Tests completed with exit code: {exit_code}")
    print("=" * 70)
    
    sys.exit(exit_code)

