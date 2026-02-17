# TimeTracker CI/CD Pipeline Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Test Strategy](#test-strategy)
4. [Workflow Details](#workflow-details)
5. [Docker Registry](#docker-registry)
6. [Deployment](#deployment)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The TimeTracker project implements a comprehensive CI/CD pipeline using GitHub Actions. The pipeline automates:

- **Continuous Integration (CI)**: Automated testing on every pull request
- **Continuous Deployment (CD)**: Automated builds and deployments to container registry
- **Quality Assurance**: Code quality checks, security scanning, and comprehensive testing
- **Multi-platform Support**: Builds for AMD64 and ARM64 architectures

### Key Features

✅ **Multi-level Testing**: Smoke, unit, integration, security, and database tests  
✅ **Parallel Execution**: Fast feedback with parallel test jobs  
✅ **Multi-platform Builds**: Support for x86_64 and ARM64  
✅ **Automated Releases**: Automatic versioning and release creation  
✅ **Security Scanning**: Bandit and Safety security checks  
✅ **Code Quality**: Black, Flake8, and isort validation  
✅ **Coverage Reporting**: Integrated Codecov support  

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Pull Request / Push                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │    Smoke Tests (5m)   │ ◄── Fastest critical tests
           └───────────┬───────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  ┌─────────┐   ┌────────────┐  ┌──────────┐
  │  Unit   │   │Integration │  │ Security │
  │ Tests   │   │   Tests    │  │  Tests   │
  └────┬────┘   └─────┬──────┘  └────┬─────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ Docker Build │
              └──────┬───────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌─────────┐            ┌──────────────┐
   │  develop│            │ main/master  │
   │  Branch │            │   Branch     │
   └────┬────┘            └──────┬───────┘
        │                        │
        ▼                        ▼
   ┌─────────┐            ┌─────────────┐
   │   Dev   │            │   Release   │
   │  Image  │            │   Image     │
   └─────────┘            └─────────────┘
```

---

## Test Strategy

### Test Levels

The CI pipeline uses pytest markers to organize tests into different levels:

#### 1. **Smoke Tests** (`@pytest.mark.smoke`)
- **Duration**: < 1 minute
- **Purpose**: Quick sanity checks
- **When**: Every commit, fastest feedback
- **Examples**:
  - Health check endpoint
  - Basic model creation
  - Login page accessibility

#### 2. **Unit Tests** (`@pytest.mark.unit`)
- **Duration**: 2-5 minutes
- **Purpose**: Test individual components in isolation
- **When**: Every PR, parallel execution
- **Examples**:
  - Model methods
  - Utility functions
  - Business logic

#### 3. **Integration Tests** (`@pytest.mark.integration`)
- **Duration**: 5-10 minutes
- **Purpose**: Test component interactions
- **When**: Every PR
- **Examples**:
  - API endpoints
  - Database operations
  - Route handlers

#### 4. **Security Tests** (`@pytest.mark.security`)
- **Duration**: 3-5 minutes
- **Purpose**: Security vulnerability testing
- **When**: Every PR
- **Examples**:
  - SQL injection
  - XSS protection
  - Authorization checks

#### 5. **Database Tests** (`@pytest.mark.database`)
- **Duration**: 5-10 minutes
- **Purpose**: Database-specific testing
- **When**: Every PR (PostgreSQL & SQLite)
- **Examples**:
  - Migrations
  - Relationships
  - Cascade operations

### Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run all tests
pytest

# Run specific test levels
pytest -m smoke          # Smoke tests only
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m security       # Security tests only

# Run tests in parallel
pytest -n auto

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_routes.py

# Run specific test
pytest tests/test_routes.py::test_health_check
```

---

## Workflow Details

### 1. CI - Comprehensive Pipeline (`ci-comprehensive.yml`)

**Triggers**:
- Pull requests to `main` or `develop`
- Pushes to `develop`

**Jobs**:

#### Smoke Tests (5 min)
```yaml
- Fast critical tests
- No database required
- Fails fast on critical issues
```

#### Unit Tests (10 min, parallel)
```yaml
- Runs in parallel for different components
- Models, routes, API, utils
- SQLite in-memory database
```

#### Integration Tests (15 min)
```yaml
- PostgreSQL service
- Full database interactions
- API endpoint testing
```

#### Security Tests (10 min)
```yaml
- Pytest security markers
- Bandit security linting
- Safety dependency scanning
```

#### Database Tests (15 min each)
```yaml
- PostgreSQL 16
- SQLite
- Migration testing
```

#### Code Quality (10 min)
```yaml
- Flake8 linting
- Black formatting check
- isort import sorting
```

#### Docker Build (20 min)
```yaml
- Multi-platform build test
- Container startup verification
- Health check validation
```

### 2. CD - Development Builds (`cd-development.yml`)

**Triggers**:
- Pushes to `develop` branch
- Manual workflow dispatch

**Process**:
1. Quick test suite (smoke + unit + critical integration)
2. Build multi-platform Docker image (AMD64, ARM64)
3. Push to `ghcr.io` with tags:
   - `develop` (latest development)
   - `dev-{date}-{time}`
   - `dev-{sha}`
4. Create development release
5. Generate deployment manifest

**Tags**:
```
ghcr.io/{owner}/{repo}:develop
ghcr.io/{owner}/{repo}:dev-20240109-143022
ghcr.io/{owner}/{repo}:dev-abc1234
```

### 3. CD - Release Builds (`cd-release.yml`)

**Triggers**:
- Pushes to `main`/`master` branch
- Git tags matching `v*.*.*`
- GitHub releases
- Manual workflow dispatch

**Process**:
1. **Full test suite** (all tests, ~30 minutes)
2. **Security audit** (Bandit + Safety)
3. **Version determination**
4. **Multi-platform build** (AMD64, ARM64)
5. **Push to registry** with tags:
   - Semantic version tags
   - `latest`
   - `stable`
6. **Trigger demo deploy** (optional): if the `TimeTrackerDemoRender` organization secret is set to a Render deploy hook URL, the workflow POSTs to it so the demo site redeploys with the new image.
7. **Create GitHub release** with:
   - Changelog
   - Deployment manifests
   - Docker compose files
   - Kubernetes YAML

**Tags**:
```
ghcr.io/{owner}/{repo}:v1.2.3
ghcr.io/{owner}/{repo}:1.2
ghcr.io/{owner}/{repo}:1
ghcr.io/{owner}/{repo}:latest
ghcr.io/{owner}/{repo}:stable
```

### 4. Additional Workflows

#### Migration Check (`migration-check.yml`)
- Validates database migrations
- Checks for schema drift
- Tests rollback safety
- Runs on model/migration changes

#### Static Analysis (`static.yml`)
- CodeQL security scanning
- Dependency graph updates

---

## Docker Registry

### GitHub Container Registry (GHCR)

Images are published to GitHub Container Registry at:
```
ghcr.io/{owner}/{repo}
```

### Authentication

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull an image
docker pull ghcr.io/{owner}/{repo}:latest

# For private repositories
docker pull ghcr.io/{owner}/{repo}:develop
```

### Image Tags

| Tag | Purpose | Updated | Platforms |
|-----|---------|---------|-----------|
| `latest` | Latest stable release | On release | AMD64, ARM64 |
| `stable` | Last non-prerelease | On release | AMD64, ARM64 |
| `develop` | Latest development | On develop push | AMD64, ARM64 |
| `v1.2.3` | Specific version | On release | AMD64, ARM64 |
| `1.2` | Minor version | On release | AMD64, ARM64 |
| `1` | Major version | On release | AMD64, ARM64 |

### Image Size Optimization

The Docker image includes:
- Python 3.11 slim base
- System dependencies (WeasyPrint, PostgreSQL client)
- Multi-stage builds (future enhancement)
- Layer caching for faster builds

---

## Deployment

### Development Environment

```bash
# Pull development image
docker pull ghcr.io/{owner}/{repo}:develop

# Run with docker-compose
docker-compose -f docker-compose.yml up -d

# Or use the generated deployment manifest
docker-compose -f deployment-dev.yml up -d
```

### Production Environment

#### Docker Compose

```bash
# Download production compose file
wget https://github.com/{owner}/{repo}/releases/latest/download/docker-compose.production.yml

# Configure environment
cat > .env << EOF
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=your-db-password
POSTGRES_USER=timetracker
POSTGRES_DB=timetracker
TZ=Europe/Brussels
CURRENCY=EUR
EOF

# Deploy
docker-compose -f docker-compose.production.yml up -d
```

#### Kubernetes

```bash
# Download K8s manifest
wget https://github.com/{owner}/{repo}/releases/latest/download/k8s-deployment.yml

# Create secrets
kubectl create secret generic timetracker-secrets \
  --from-literal=database-url='postgresql://user:pass@host:5432/db' \
  --from-literal=secret-key='your-secret-key'

# Deploy
kubectl apply -f k8s-deployment.yml

# Check status
kubectl get pods -l app=timetracker
kubectl get svc timetracker
```

#### Manual Docker Run

```bash
docker run -d \
  --name timetracker \
  -p 8080:8080 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e SECRET_KEY="your-secret-key" \
  -e TZ="Europe/Brussels" \
  --restart unless-stopped \
  ghcr.io/{owner}/{repo}:latest
```

---

## Configuration

### GitHub Secrets

Required secrets (already configured via GITHUB_TOKEN):
- ✅ `GITHUB_TOKEN` - Automatic, used for GHCR authentication

Optional secrets:
- `CODECOV_TOKEN` - For Codecov integration
- `SLACK_WEBHOOK` - For Slack notifications
- `DOCKER_HUB_USERNAME` - If publishing to Docker Hub
- `DOCKER_HUB_TOKEN` - If publishing to Docker Hub
- `TimeTrackerDemoRender` - (Organization secret) Render deploy hook URL; when set, the release workflow triggers a redeploy of the demo site after pushing the new container

### Environment Variables

#### Build-time (Docker)
```dockerfile
ARG APP_VERSION=dev-0
ENV APP_VERSION=${APP_VERSION}
```

#### Runtime
```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=your-secret-key-here

# Optional
TZ=Europe/Brussels
CURRENCY=EUR
FLASK_ENV=production
LOG_LEVEL=INFO
```

### Pytest Configuration

Configured in `pytest.ini`:
- Test discovery patterns
- Coverage settings
- Test markers
- Output options

### Test Requirements

Specified in `requirements-test.txt`:
- pytest and plugins
- Code quality tools
- Security scanners
- Test utilities

---

## Troubleshooting

### Common Issues

#### 1. Tests Failing Locally But Passing in CI

**Cause**: Database state, environment differences  
**Solution**:
```bash
# Clean test database
rm -f test.db

# Use same Python version
pyenv install 3.11
pyenv local 3.11

# Reinstall dependencies
pip install -r requirements.txt -r requirements-test.txt
```

#### 2. Docker Build Fails

**Cause**: Missing dependencies, network issues  
**Solution**:
```bash
# Clear Docker cache
docker builder prune -a

# Build with no cache
docker build --no-cache -t timetracker:test .

# Check logs
docker logs <container-id>
```

#### 3. Coverage Below Threshold

**Cause**: New code not tested  
**Solution**:
```bash
# Run coverage locally
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html

# Add tests for uncovered code
```

#### 4. Security Vulnerabilities Detected

**Cause**: Outdated dependencies  
**Solution**:
```bash
# Check vulnerabilities
safety check --file requirements.txt

# Update dependencies
pip install --upgrade <package>

# Update requirements.txt
pip freeze > requirements.txt
```

#### 5. Migration Tests Failing

**Cause**: Schema drift, missing migrations  
**Solution**:
```bash
# Check current migration
flask db current

# Create new migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Test rollback
flask db downgrade -1
flask db upgrade
```

### Debug Workflow Runs

#### View Logs
```bash
# Via GitHub CLI
gh run list
gh run view <run-id>
gh run view <run-id> --log

# Download artifacts
gh run download <run-id>
```

#### Re-run Failed Jobs
1. Go to Actions tab in GitHub
2. Select failed workflow run
3. Click "Re-run failed jobs"

#### Cancel Running Workflow
```bash
gh run cancel <run-id>
```

### Performance Optimization

#### Speed Up Tests
```bash
# Run tests in parallel
pytest -n auto

# Skip slow tests
pytest -m "not slow"

# Run only failed tests
pytest --lf
```

#### Speed Up Builds
- Enable Docker layer caching
- Use build cache
- Parallelize test jobs
- Use smaller base images

---

## Best Practices

### For Developers

1. **Run Tests Locally**: Before pushing, run at least smoke and unit tests
   ```bash
   pytest -m "smoke or unit"
   ```

2. **Write Tests**: Add tests for new features using appropriate markers
   ```python
   @pytest.mark.unit
   @pytest.mark.models
   def test_new_feature():
       pass
   ```

3. **Keep PRs Small**: Smaller PRs = faster CI, easier review

4. **Fix Failures Quickly**: Don't let broken tests sit

5. **Check Coverage**: Aim for >80% coverage on new code

### For Maintainers

1. **Review Test Reports**: Check test results and coverage before merging

2. **Monitor Build Times**: Keep CI under 15 minutes for PRs

3. **Update Dependencies**: Regular security updates

4. **Version Properly**: Use semantic versioning

5. **Document Changes**: Update CHANGELOG.md

---

## Metrics and Monitoring

### CI/CD Metrics

Track these metrics for health:
- ✅ **Test Success Rate**: > 95%
- ✅ **Build Time**: < 15 minutes (PR), < 30 minutes (release)
- ✅ **Coverage**: > 80%
- ✅ **Deployment Frequency**: Multiple times per day (develop)
- ✅ **Mean Time to Recovery**: < 1 hour

### Dashboard

View metrics at:
- GitHub Actions tab
- Codecov dashboard (if configured)
- Docker Hub / GHCR for image stats

---

## Future Enhancements

Planned improvements:
- [ ] Automated performance testing
- [ ] E2E testing with Playwright/Selenium
- [ ] Automated security scanning (Dependabot)
- [ ] Blue-green deployments
- [ ] Canary releases
- [ ] Automated rollback on failures
- [ ] Multi-environment deployments (staging, production)
- [ ] Integration with monitoring (Datadog, Sentry)

---

## Support

For issues or questions:
1. Check this documentation
2. Review GitHub Actions logs
3. Open an issue on GitHub
4. Contact the maintainers

---

**Last Updated**: 2025-01-09  
**Version**: 1.0  
**Maintained by**: TimeTracker Team

