#!/usr/bin/env python
"""Run each test file individually and report results"""
import sys
import os
import subprocess
from pathlib import Path

# Run from project root (parent of scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
sys.path.insert(0, _project_root)
os.chdir(_project_root)

# Get all test files
test_dir = Path("tests")
test_files = sorted(test_dir.glob("test_*.py"))

print("=" * 70)
print("Running TimeTracker Tests Individually")
print("=" * 70)
print()

results = []

for test_file in test_files:
    test_name = test_file.name
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    # Run pytest for this specific file
    cmd = [
        sys.executable,
        "-m", "pytest",
        str(test_file),
        "-v",
        "--tb=line",
        "-x"  # Stop on first failure
    ]
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    status = "✓ PASSED" if result.returncode == 0 else "✗ FAILED"
    results.append((test_name, status, result.returncode))
    print(f"\nResult: {status} (exit code: {result.returncode})")

print("\n\n" + "=" * 70)
print("SUMMARY OF ALL TESTS")
print("=" * 70)
for test_name, status, code in results:
    print(f"{status:12} - {test_name}")

passed = sum(1 for _, s, _ in results if "PASSED" in s)
failed = sum(1 for _, s, _ in results if "FAILED" in s)
print(f"\nTotal: {len(results)} test files | Passed: {passed} | Failed: {failed}")
print("=" * 70)

