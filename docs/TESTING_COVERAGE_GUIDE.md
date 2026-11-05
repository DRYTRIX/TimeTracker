# Testing Coverage Guide

## Understanding the Coverage Issue

### The Problem

When running route tests with coverage requirements:
```bash
pytest -m routes --cov=app --cov-fail-under=50
```

You may see:
```
FAIL Required test coverage of 50% not reached. Total coverage: 27.81%
```

### Why This Happens

The issue occurs because:

1. **Route tests only exercise route handlers** - They test the endpoints in `app/routes/`
2. **Coverage measures the entire `app` module** - Including models, utils, config, etc.
3. **Most code isn't executed by routes alone** - Models, utilities, and business logic require comprehensive testing across all test types

This is **conceptually correct behavior**. Route tests shouldn't execute 50% of your entire codebase - they should test routes. Other code is tested by model tests, integration tests, etc.

## Solutions

### Option 1: Run Tests Without Marker-Specific Coverage (Recommended)

**For development and debugging specific test categories:**
```bash
# Run route tests without coverage requirements
make test-routes

# Or directly:
pytest -m routes -v
```

**For comprehensive coverage analysis:**
```bash
# Run ALL tests with coverage requirement
make test-coverage

# Or directly:
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=50
```

### Option 2: Measure Coverage Only for Routes

If you specifically want to measure route coverage:
```bash
# Measure coverage only for the routes module
pytest -m routes --cov=app/routes --cov-report=term-missing
```

This will show you what percentage of your routes are tested, not the entire app.

### Option 3: Run Coverage on All Tests Together

The standard approach in most projects:
```bash
# Run all tests together with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=50
```

This gives you the true coverage across your entire test suite.

## Test Organization Strategy

### Test Markers

The project uses pytest markers to organize tests:

- `@pytest.mark.smoke` - Critical functionality (health checks, basic routes)
- `@pytest.mark.unit` - Unit tests (isolated, fast)
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.routes` - Route/endpoint tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.models` - Model tests
- `@pytest.mark.database` - Database tests
- `@pytest.mark.security` - Security tests

### Running Different Test Suites

```bash
# Quick smoke test (fastest, for CI)
make test-smoke

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Route tests (no coverage requirement)
make test-routes

# Model tests
make test-models

# API tests
make test-api

# Full test suite with 50% coverage requirement
make test-coverage

# Generate coverage report without failing on threshold
make test-coverage-report
```

## Coverage Targets by Test Type

Different test types have different coverage expectations:

| Test Type | Expected Coverage | Scope |
|-----------|------------------|-------|
| Smoke tests | Low (~10-20%) | Critical paths only |
| Route tests | Low (~20-30%) | Routes + directly called utilities |
| Model tests | Medium (~30-40%) | Models + database operations |
| Unit tests | Medium (~40-60%) | Specific modules being tested |
| Integration tests | High (~60-80%) | Multiple components together |
| **Full suite** | **High (50%+)** | **Entire codebase** |

## Best Practices

### 1. Don't Enforce Coverage on Marker-Specific Tests

❌ **Wrong:**
```bash
pytest -m routes --cov=app --cov-fail-under=50
```

✅ **Correct:**
```bash
# For debugging/development
pytest -m routes -v

# For coverage analysis
pytest --cov=app --cov-fail-under=50
```

### 2. Use Coverage to Find Gaps, Not as a Goal

Coverage percentage is a tool to find untested code, not a target to hit. Focus on:
- Testing critical functionality
- Testing edge cases
- Testing error conditions
- Testing user workflows

### 3. Combine Test Types for Complete Coverage

```bash
# This is how to get meaningful coverage
pytest tests/ --cov=app --cov-report=html --cov-fail-under=50
```

Individual test types complement each other:
- **Route tests**: Ensure endpoints work
- **Model tests**: Ensure data integrity
- **Integration tests**: Ensure components work together
- **Unit tests**: Ensure individual functions work

### 4. Review Coverage Reports

After running tests with coverage:
```bash
# Generate HTML report
pytest --cov=app --cov-report=html

# Open the report
# The report is in htmlcov/index.html
```

Look for:
- Untested critical paths
- Error handling code
- Edge cases
- Business logic

## CI/CD Coverage Strategy

### Development (develop branch)
- Runs smoke tests only (fast feedback)
- No coverage requirements
- Focus on catching obvious breaks

### Pull Requests
- Runs full test suite
- No strict coverage requirement yet
- Migration validation for model changes

### Release (main/master branch)
- Runs full test suite
- Enforces 50% coverage requirement
- Security audit
- Integration tests

## Current Test Coverage

To see current coverage:
```bash
# Run tests with coverage
make test-coverage-report

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Adding More Route Tests

If you want to improve route test coverage, add tests for:

### Missing Route Tests
- Task routes (`/tasks/*`)
- Comment routes (`/comments/*`)
- More comprehensive API tests
- Form submission tests
- File upload tests
- Pagination tests

### Example: Adding Task Route Tests

```python
# tests/test_routes.py

@pytest.mark.integration
@pytest.mark.routes
def test_tasks_list_page(authenticated_client):
    """Test tasks list page."""
    response = authenticated_client.get('/tasks')
    assert response.status_code == 200

@pytest.mark.integration
@pytest.mark.routes
def test_task_create_page(authenticated_client, project):
    """Test task creation page."""
    response = authenticated_client.get(f'/tasks/new?project_id={project.id}')
    assert response.status_code == 200

@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_create_task_api(authenticated_client, project, user, app):
    """Test creating a task via API."""
    with app.app_context():
        response = authenticated_client.post('/api/tasks', json={
            'name': 'Test Task',
            'project_id': project.id,
            'description': 'Test task description',
            'priority': 'medium'
        })
        assert response.status_code in [200, 201]
```

## Troubleshooting

### "pytest: error: unrecognized arguments: --cov=app"

This means `pytest-cov` is not installed:
```bash
pip install -r requirements-test.txt
```

### Coverage too low even with all tests

This is normal if you have:
- Large utility modules
- Configuration code
- Error handling code
- Admin-only features
- Legacy code

Focus on:
1. Test critical user paths
2. Test error conditions
3. Test business logic
4. Don't worry about 100% coverage

### Tests pass individually but fail in suite

This usually indicates:
- Test pollution (tests affecting each other)
- Shared state issues
- Database not being cleaned between tests

Fix by using proper fixtures and isolation.

## Summary

✅ **Do:**
- Run full test suite for coverage analysis
- Use markers to organize and run specific test types
- Focus on testing critical functionality
- Use coverage reports to find gaps

❌ **Don't:**
- Enforce coverage thresholds on marker-specific tests
- Chase 100% coverage
- Write tests just to increase coverage percentage
- Mix coverage analysis with debugging/development testing

## Quick Reference

```bash
# Development workflow
make test-routes          # Debug route tests
make test-models          # Debug model tests
make test-unit           # Debug unit tests

# CI/CD workflow
make test-smoke          # Quick validation
make test-coverage       # Full coverage with 50% threshold

# Coverage analysis
make test-coverage-report  # Generate report without failing
open htmlcov/index.html    # Review coverage
```
