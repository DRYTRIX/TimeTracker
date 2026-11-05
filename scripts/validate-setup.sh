#!/bin/bash
# TimeTracker CI/CD Setup Validation Script for Linux/Mac
# Runs the Python validation script

set -e

echo "========================================"
echo "TimeTracker CI/CD Setup Validation"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "ERROR: Python not found!"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

# Use python3 if available, otherwise python
if command -v python3 &> /dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

# Run the validation script
$PYTHON scripts/validate-setup.py
exit $?
