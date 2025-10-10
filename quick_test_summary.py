#!/usr/bin/env python
"""Quick test summary - runs each test file and shows results"""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

test_files = [
    "test_basic.py",
    "test_analytics.py", 
    "test_invoices.py",
    "test_models_comprehensive.py",
    "test_new_features.py",
    "test_routes.py",
    "test_security.py",
    "test_timezone.py"
]

print("=" * 80)
print("TIMETRACKER TEST SUMMARY")
print("=" * 80)

results = []

for test_file in test_files:
    print(f"\nTesting: {test_file}...", end=" ", flush=True)
    
    cmd = [sys.executable, "-m", "pytest", f"tests/{test_file}", "-q", "--tb=no", "--no-header"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    # Parse output for pass/fail counts
    output = result.stdout + result.stderr
    
    if result.returncode == 0:
        status = "✓ ALL PASSED"
    elif result.returncode == 1:
        status = "✗ SOME FAILED"
    else:
        status = "⚠ ERROR"
    
    # Try to extract summary line
    summary_line = ""
    for line in output.split('\n'):
        if 'passed' in line.lower() or 'failed' in line.lower() or 'error' in line.lower():
            summary_line = line.strip()
            if summary_line:
                break
    
    results.append((test_file, status, summary_line))
    print(f"{status}")
    if summary_line:
        print(f"  └─ {summary_line}")

print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

for test_file, status, summary in results:
    print(f"{status:15} {test_file}")

print("=" * 80)

