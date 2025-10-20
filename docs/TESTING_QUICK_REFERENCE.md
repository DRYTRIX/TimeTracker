# Testing Quick Reference

## TL;DR - Fix for Coverage Error

If you're getting:
```
FAIL Required test coverage of 50% not reached. Total coverage: 27.81%
```

**The Fix:**
```bash
# Don't run coverage on route tests alone
pytest -m routes -v

# Instead, run coverage on ALL tests
pytest --cov=app --cov-report=html --cov-fail-under=50
```

Or use the Makefile:
```bash
# Run route tests (no coverage)
make test-routes

# Run full coverage test
make test-coverage
```

## Why?

Route tests only exercise ~28% of your codebase (which is correct!). The other 72% is tested by:
- Model tests
- Utility tests  
- Integration tests
- Business logic tests

Coverage should be measured across ALL tests, not individual test suites.

## Common Commands

### Development Testing
```bash
make test-routes          # Test routes only
make test-models          # Test models only
make test-unit           # Test unit tests only
make test-integration    # Test integration only
make test-api            # Test API endpoints
```

### Coverage Analysis
```bash
make test-coverage        # All tests with 50% requirement
make test-coverage-report # All tests, no requirement
```

### CI/CD Testing
```bash
make test-smoke          # Quick validation (< 1 min)
pytest --cov=app --cov-report=xml --cov-fail-under=50  # Full CI test
```

### View Coverage Report
```bash
make test-coverage-report
# Then open htmlcov/index.html in your browser
```

## Test Markers

Run specific test types:
```bash
pytest -m smoke          # Smoke tests
pytest -m unit           # Unit tests
pytest -m integration    # Integration tests
pytest -m routes         # Route tests
pytest -m api            # API tests
pytest -m models         # Model tests
pytest -m database       # Database tests
pytest -m security       # Security tests
```

## Full Documentation

See `docs/TESTING_COVERAGE_GUIDE.md` for complete guide.

