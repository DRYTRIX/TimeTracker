#!/bin/bash
# TimeTracker Test Runner for Linux/Mac
# Quick test execution script

set -e

echo "========================================"
echo "TimeTracker Test Runner"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo -e "${RED}ERROR: pytest not found!${NC}"
    echo "Please install test dependencies:"
    echo "  pip install -r requirements-test.txt"
    exit 1
fi

# Parse command line arguments
case "$1" in
    smoke)
        echo -e "${GREEN}Running smoke tests (quick critical tests)...${NC}"
        python -m pytest -m smoke -v
        ;;
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        python -m pytest -m unit -v
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        python -m pytest -m integration -v
        ;;
    security)
        echo -e "${GREEN}Running security tests...${NC}"
        python -m pytest -m security -v
        ;;
    database)
        echo -e "${GREEN}Running database tests...${NC}"
        python -m pytest -m database -v
        ;;
    all)
        echo -e "${GREEN}Running full test suite in parallel...${NC}"
        python -m pytest -v -n auto
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage...${NC}"
        python -m pytest --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    fast)
        echo -e "${GREEN}Running tests in parallel (fast mode)...${NC}"
        python -m pytest -n auto -v
        ;;
    parallel)
        echo -e "${GREEN}Running tests in parallel with 4 workers...${NC}"
        python -m pytest -n 4 -v
        ;;
    watch)
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        python -m pytest-watch
        ;;
    failed)
        echo -e "${GREEN}Re-running last failed tests...${NC}"
        python -m pytest --lf -v
        ;;
    *)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  smoke        - Run smoke tests (fastest, < 1 min)"
        echo "  unit         - Run unit tests (2-5 min)"
        echo "  integration  - Run integration tests (5-10 min)"
        echo "  security     - Run security tests (3-5 min)"
        echo "  database     - Run database tests (5-10 min)"
        echo "  all          - Run full test suite (15-30 min)"
        echo "  coverage     - Run tests with coverage report"
        echo "  fast         - Run tests in parallel (auto workers)"
        echo "  parallel     - Run tests in parallel (4 workers)"
        echo "  watch        - Run tests in watch mode (pytest-watch)"
        echo "  failed       - Re-run last failed tests"
        echo ""
        echo "Examples:"
        echo "  $0 smoke"
        echo "  $0 coverage"
        echo "  $0 fast"
        exit 1
        ;;
esac

