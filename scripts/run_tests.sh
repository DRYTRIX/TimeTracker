#!/bin/bash
# Run from project root: bash scripts/run_tests.sh
# In Docker, /app is the project root.
cd "$(dirname "$0")/.." 2>/dev/null || cd /app
echo "====== Running TimeTracker Tests ======"
python -m pytest tests/ -v --tb=short
echo "====== Tests Complete. Exit Code: $? ======"

