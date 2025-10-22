# Testing Workflow Quick Reference

## TL;DR

✅ **Tests run on PRs, not on releases**  
✅ **All tests must pass before merge**  
✅ **Fix issues in PR, not after merge**  
✅ **Main branch is always deployable**

---

## For Contributors

### Creating a PR

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and test locally
pytest -m smoke  # Quick smoke tests
pytest          # Full test suite

# 3. Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/my-feature

# 4. Create PR on GitHub
# 5. Wait for CI - all tests must pass ✅
# 6. Address any test failures
# 7. Get review approval
# 8. Merge to main
```

### Test Markers

```bash
# Smoke tests (fast, critical)
pytest -m smoke

# Unit tests by component
pytest -m "unit and models"
pytest -m "unit and routes"
pytest -m "unit and api"
pytest -m "unit and utils"

# Integration tests
pytest -m integration

# Security tests
pytest -m security

# Everything
pytest
```

### Local Testing with PostgreSQL

```bash
# Start PostgreSQL
docker-compose up -d db

# Set database URL
export DATABASE_URL=postgresql://timetracker:timetracker@localhost:5432/timetracker

# Run migrations
flask db upgrade

# Run tests
pytest
```

---

## For Maintainers

### Creating a Release

**Quick Method:**

```bash
# 1. Update version in setup.py
version='3.2.4'

# 2. Commit and tag
git add setup.py
git commit -m "Bump version to 3.2.4"
git push origin main
git tag v3.2.4
git push origin v3.2.4

# 3. Release workflow runs automatically ✅
```

**Manual Method:**

1. Go to **Actions** → **CD - Release Build**
2. Click **Run workflow**
3. Enter version: `v3.2.4`
4. Skip tests: `yes` (already ran on PR)
5. Click **Run workflow**

### Release Checklist

- [ ] All PRs merged to main
- [ ] All tests passed on PRs
- [ ] Version updated in `setup.py`
- [ ] Version matches tag (v3.2.4 = version='3.2.4')
- [ ] Tag pushed to GitHub
- [ ] Release workflow completed successfully
- [ ] Docker images published
- [ ] GitHub release created

---

## CI Workflow Overview

### On Pull Request → `main` or `develop`

```
Smoke Tests (5 min) 
    ↓
Parallel:
├─ Unit Tests (10 min)
├─ Integration Tests (15 min)
├─ Security Tests (10 min)
└─ Code Quality (5 min)
    ↓
Docker Build (20 min)
    ↓
Full Test Suite (30 min) [main PRs only]
    ↓
Test Summary (PR comment)
```

**Total time:** ~30-40 minutes

### On Merge to `main`

```
Security Audit (10 min)
    ↓
Determine Version
    ↓
Build & Push Docker Image (30-45 min)
├─ Inject analytics config
├─ Multi-arch build (amd64, arm64)
└─ Push to GHCR
    ↓
Create GitHub Release
├─ Generate changelog
└─ Upload deployment files
    ↓
Release Summary
```

**Total time:** ~40-60 minutes

---

## Required Status Checks

Configure in **Settings → Branches → main → Protection rules**:

Required checks:
- ✅ `smoke-tests`
- ✅ `unit-tests`
- ✅ `integration-tests`
- ✅ `security-tests`
- ✅ `code-quality`
- ✅ `docker-build`
- ✅ `full-test-suite` (for main only)

---

## Test Results Interpretation

### ✅ All Pass

```
## ✅ CI Test Results
**Overall Status:** All tests passed!
**Test Results:** 7/7 passed
```

→ Ready to merge after review

### ❌ Some Fail

```
## ❌ CI Test Results
**Overall Status:** 2 test suite(s) failed
**Test Results:** 5/7 passed
```

→ Fix issues and push new commits

### Common Failures

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Smoke tests fail | Critical path broken | Fix immediately, high priority |
| Unit tests fail | Logic error in code | Review test output, fix logic |
| Integration tests fail | Database compatibility | Check PostgreSQL compatibility |
| Security tests fail | Vulnerable dependency | Update dependency or add exception |
| Code quality fail | Linting errors | Run `flake8 app/` locally and fix |
| Docker build fail | Missing dependency | Update Dockerfile or requirements.txt |
| Full suite fail | Complex interaction issue | Review full test logs |

---

## Troubleshooting Commands

### Check test locally
```bash
# Run specific test file
pytest tests/test_models.py -v

# Run specific test
pytest tests/test_models.py::test_user_creation -v

# Show print statements
pytest -v -s

# Stop on first failure
pytest -x

# Show locals on failure
pytest -l

# Run last failed tests
pytest --lf
```

### Debug CI failures

1. **Check workflow logs:**
   - Go to PR → Checks → Click failed check
   - Review error messages
   - Download artifacts if needed

2. **Run exact CI command locally:**
   ```bash
   # Same as CI runs
   pytest -v --cov=app --cov-report=xml --cov-report=html --cov-report=term
   ```

3. **Check database migration:**
   ```bash
   flask db upgrade
   flask db current
   ```

4. **Build Docker image locally:**
   ```bash
   docker build -t timetracker-test .
   ```

---

## GitHub Secrets

### Required Secrets

Set in **Settings → Secrets and variables → Actions**:

- `POSTHOG_API_KEY` - PostHog analytics key (starts with `phc_`)
- `SENTRY_DSN` - Sentry error tracking DSN (optional)

### Verify Secrets

```bash
# Using GitHub CLI
gh secret list

# Check in workflow logs
# Look for: "✅ PostHog API key: phc_***XXXX"
```

---

## File Locations

### Workflows
- `.github/workflows/ci-comprehensive.yml` - PR testing
- `.github/workflows/cd-release.yml` - Release builds
- `.github/workflows/cd-development.yml` - Dev builds (develop branch)

### Configuration
- `pytest.ini` - Pytest configuration
- `requirements-test.txt` - Test dependencies
- `setup.py` - Version (SINGLE SOURCE OF TRUTH)

### Documentation
- `docs/cicd/TESTING_WORKFLOW_STRATEGY.md` - Full documentation
- `docs/cicd/QUICK_REFERENCE_TESTING.md` - This file
- `docs/cicd/BUILD_CONFIGURATION_SUMMARY.md` - Build configuration

---

## Key Metrics

### Test Times
- Smoke: ~5 min
- Unit: ~10 min
- Integration: ~15 min
- Security: ~10 min
- Code Quality: ~5 min
- Docker Build: ~20 min
- Full Suite: ~30 min

### Coverage Target
- Minimum: 80%
- Current: Check Codecov badge

---

## Best Practices

### ✅ DO

- Run tests locally before pushing
- Write tests for new features
- Keep PRs small and focused
- Fix test failures immediately
- Use descriptive commit messages
- Update documentation with code

### ❌ DON'T

- Push directly to main (use PR)
- Skip tests (they're required)
- Merge PR with failing tests
- Commit without testing locally
- Create massive PRs (hard to review)
- Ignore flaky tests (fix them)

---

## Quick Commands

```bash
# Local testing
pytest -m smoke                    # Quick smoke tests
pytest --cov=app                   # With coverage
pytest -v -s                       # Verbose with print
pytest -x --pdb                    # Debug on failure
pytest --lf                        # Re-run last failures

# Database
flask db upgrade                   # Apply migrations
flask db current                   # Show current migration
flask db migrate -m "description"  # Create migration

# Docker
docker-compose up -d db            # Start PostgreSQL
docker-compose down                # Stop all services
docker build -t test .             # Test Docker build

# Git
git checkout -b feature/name       # Create feature branch
git rebase main                    # Update from main
git push --force-with-lease        # Force push safely

# Release
git tag v3.2.4                     # Create tag
git push origin v3.2.4             # Push tag
git tag -d v3.2.4                  # Delete local tag
git push origin :refs/tags/v3.2.4  # Delete remote tag
```

---

## Need Help?

1. **Read full docs:** `docs/cicd/TESTING_WORKFLOW_STRATEGY.md`
2. **Check workflow logs** in GitHub Actions
3. **Search existing issues** on GitHub
4. **Ask for help:** Create issue with workflow run link

---

## Change Summary

### What Changed (from previous workflow)

| Aspect | Before | After |
|--------|--------|-------|
| When tests run | On release | On PR |
| Issue detection | After merge | Before merge |
| Fix location | Hotfix PR | Same PR |
| Main branch | May be broken | Always works |
| Release time | Slow (tests + build) | Fast (build only) |

### Benefits

✅ Catch issues earlier  
✅ Fix issues before merge  
✅ Main always deployable  
✅ Faster releases  
✅ Better code quality  
✅ More confidence  

---

**Last Updated:** October 2025  
**Version:** 3.2.x

