# CI/CD Quick Start Guide

This guide will help you get started with the TimeTracker CI/CD pipeline in 5 minutes.

## 🚀 Quick Start

### For Developers

#### 1. Install Test Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

#### 2. Run Tests Locally

```bash
# Quick smoke tests (< 1 minute)
pytest -m smoke

# All unit tests (2-5 minutes)
pytest -m unit

# Full test suite (10-15 minutes)
pytest
```

#### 3. Check Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Check style
flake8 app/
```

#### 4. Create a Pull Request

Once you create a PR, the CI pipeline will automatically:
- ✅ Run smoke tests
- ✅ Run unit tests (parallel)
- ✅ Run integration tests
- ✅ Run security tests
- ✅ Check code quality
- ✅ Test Docker build
- ✅ Comment on PR with results

### For Maintainers

#### Development Releases (develop branch)

Every push to `develop` automatically:
1. Runs quick test suite
2. Builds Docker image for AMD64 and ARM64
3. Publishes to `ghcr.io/{owner}/{repo}:develop`
4. Creates development release

```bash
# Pull and test development build
docker pull ghcr.io/{owner}/{repo}:develop
docker run -p 8080:8080 ghcr.io/{owner}/{repo}:develop
```

#### Production Releases (main branch)

Every push to `main` or tag `v*.*.*` automatically:
1. Runs full test suite (~30 min)
2. Performs security audit
3. Builds multi-platform images
4. Publishes with version tags
5. Creates GitHub release
6. Generates deployment manifests

```bash
# Create a release
git tag v1.2.3
git push origin v1.2.3

# Or merge to main
git checkout main
git merge develop
git push
```

## 📋 Test Organization

Tests are organized using pytest markers:

| Marker | Purpose | Speed | When to Run |
|--------|---------|-------|-------------|
| `smoke` | Critical tests | < 1 min | Every commit |
| `unit` | Isolated tests | 2-5 min | Every PR |
| `integration` | Component tests | 5-10 min | Every PR |
| `security` | Security tests | 3-5 min | Every PR |
| `database` | DB tests | 5-10 min | Every PR |

### Writing Tests

```python
import pytest

# Smoke test - fast, critical
@pytest.mark.smoke
def test_health_check(client):
    response = client.get('/_health')
    assert response.status_code == 200

# Unit test - isolated
@pytest.mark.unit
@pytest.mark.models
def test_user_creation(app, user):
    assert user.id is not None
    assert user.username == 'testuser'

# Integration test - components interact
@pytest.mark.integration
@pytest.mark.api
def test_create_project(authenticated_client, test_client):
    response = authenticated_client.post('/api/projects', json={
        'name': 'New Project',
        'client_id': test_client.id
    })
    assert response.status_code in [200, 201]

# Security test
@pytest.mark.security
def test_sql_injection_protection(authenticated_client):
    response = authenticated_client.get('/api/search?q=\'; DROP TABLE users; --')
    assert response.status_code in [200, 400, 404]
```

## 🐳 Docker Images

### Development

```bash
# Pull latest development
docker pull ghcr.io/{owner}/{repo}:develop

# Run locally
docker run -d \
  --name timetracker-dev \
  -p 8080:8080 \
  -e DATABASE_URL="sqlite:///test.db" \
  -e SECRET_KEY="dev-secret" \
  ghcr.io/{owner}/{repo}:develop

# Check health
curl http://localhost:8080/_health
```

### Production

```bash
# Pull specific version
docker pull ghcr.io/{owner}/{repo}:v1.2.3

# Or latest stable
docker pull ghcr.io/{owner}/{repo}:latest

# Run with docker-compose
wget https://github.com/{owner}/{repo}/releases/latest/download/docker-compose.production.yml
docker-compose -f docker-compose.production.yml up -d
```

## 🔍 Monitoring Builds

### Via GitHub Web Interface

1. Go to repository → Actions tab
2. View running/completed workflows
3. Click on workflow for detailed logs
4. Download artifacts (test results, coverage)

### Via GitHub CLI

```bash
# Install GitHub CLI
brew install gh  # macOS
# or download from https://cli.github.com/

# List recent runs
gh run list

# View specific run
gh run view <run-id>

# View logs
gh run view <run-id> --log

# Download artifacts
gh run download <run-id>

# Re-run failed jobs
gh run rerun <run-id>
```

## 🔧 Common Tasks

### Test a Specific File

```bash
pytest tests/test_routes.py -v
```

### Test a Specific Function

```bash
pytest tests/test_routes.py::test_health_check -v
```

### Run Tests with Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Run Tests in Parallel

```bash
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 cores
```

### Debug Failing Tests

```bash
# Show full traceback
pytest -v --tb=long

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Run only last failed tests
pytest --lf

# Run all except last failed
pytest --ff
```

### Update Test Dependencies

```bash
# Check for updates
pip list --outdated

# Update a package
pip install --upgrade pytest

# Update requirements file
pip freeze > requirements-test.txt
```

## 🚨 Troubleshooting

### Tests Pass Locally But Fail in CI

**Common causes:**
- Database state differences
- Timezone differences
- Environment variable missing

**Solutions:**
```bash
# Clean test database
rm -f test.db *.db

# Match CI environment
export FLASK_ENV=testing
export DATABASE_URL=postgresql://test_user:test_password@localhost:5432/test_db

# Run with same Python version
python --version  # Should be 3.11
```

### Docker Build Fails

```bash
# Clear Docker cache
docker builder prune -a

# Build without cache
docker build --no-cache -t test .

# Check build logs
docker build -t test . 2>&1 | tee build.log
```

### Tests Are Slow

```bash
# Profile slow tests
pytest --durations=10

# Skip slow tests
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

## 📊 Coverage Goals

Maintain these coverage levels:

- **Overall**: > 80%
- **Critical modules** (models, routes): > 90%
- **New code**: > 85%

Check coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

## 🎯 Best Practices

### Before Creating PR

```bash
# 1. Run smoke tests
pytest -m smoke

# 2. Run affected tests
pytest tests/test_routes.py

# 3. Format code
black app/
isort app/

# 4. Check for issues
flake8 app/

# 5. Run full test suite (optional)
pytest
```

### During Development

- Write tests as you code
- Run relevant tests frequently
- Use markers appropriately
- Keep tests fast and focused
- Mock external dependencies

### PR Review Checklist

- [ ] All CI checks pass
- [ ] Tests added for new features
- [ ] Coverage maintained or increased
- [ ] No security vulnerabilities
- [ ] Code quality checks pass
- [ ] Docker build succeeds

## 📚 Learn More

- [Full CI/CD Documentation](CI_CD_DOCUMENTATION.md)
- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)

## 🆘 Getting Help

1. Check [CI_CD_DOCUMENTATION.md](CI_CD_DOCUMENTATION.md)
2. Review GitHub Actions logs
3. Search existing issues
4. Open a new issue with:
   - Workflow run URL
   - Error message
   - Steps to reproduce

---

**Ready to contribute?** Start by running `pytest -m smoke` and create your first PR! 🎉
