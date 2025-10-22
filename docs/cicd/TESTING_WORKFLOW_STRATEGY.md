# Testing Workflow Strategy

## Overview

This document explains the testing strategy for the TimeTracker project. Tests run on **pull requests** before code is merged, ensuring issues are caught and fixed early.

## Workflow Structure

### 1. Pull Request Testing (`ci-comprehensive.yml`)

**Triggers:** All pull requests to `main` or `develop` branches

**Purpose:** Comprehensive testing before code is merged

**Test Stages:**

```
┌─────────────────┐
│  Smoke Tests    │  ← Fast, critical tests (5 min)
└────────┬────────┘
         │
    ┌────┴────────────────────────────────┐
    │                                     │
┌───▼────────────┐  ┌───────────────────┐
│  Unit Tests    │  │ Integration Tests │
│  (parallel)    │  │    (PostgreSQL)   │
└────────┬───────┘  └─────────┬─────────┘
         │                    │
    ┌────┴────────────┬───────┴─────┬─────────────┐
    │                 │             │             │
┌───▼───────────┐ ┌──▼──────────┐ ┌▼──────────┐ ┌▼────────────┐
│ Security Tests│ │ Code Quality│ │Docker Build│ │ Full Suite  │
└───────────────┘ └─────────────┘ └────────────┘ └─────────────┘
                                                   (main PRs only)
         │
         │
    ┌────▼────────────┐
    │  Test Summary   │
    │  (PR comment)   │
    └─────────────────┘
```

**Test Components:**

- ✅ **Smoke Tests**: Fast, critical tests that must pass
- ✅ **Unit Tests**: Isolated component tests (models, routes, API, utils)
- ✅ **Integration Tests**: Component interaction tests with PostgreSQL
- ✅ **Security Tests**: Security-focused tests and dependency checks
- ✅ **Code Quality**: Linting and code quality checks
- ✅ **Docker Build**: Ensures Docker image builds correctly
- ✅ **Full Test Suite**: Complete test suite with PostgreSQL (PRs to main/master only)

**Output:**
- Coverage reports uploaded to Codecov
- Test results as artifacts
- Summary comment posted on PR

### 2. Release Build (`cd-release.yml`)

**Triggers:**
- Push to `main` or `master` (after PR merge)
- Git tags (`v*.*.*`)
- Release events
- Manual workflow_dispatch

**Purpose:** Build and publish official releases

**Stages:**

```
┌──────────────────┐     ┌──────────────────┐
│ Security Audit   │     │ Determine Version│
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └────────────┬───────────┘
                      │
         ┌────────────▼────────────┐
         │  Build & Push Image     │
         │  - Inject Analytics     │
         │  - Multi-arch Build     │
         │  - Tag & Push           │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │  Create GitHub Release  │
         │  - Changelog            │
         │  - Deployment Files     │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │  Release Summary        │
         └─────────────────────────┘
```

**Key Features:**
- ⚡ **Fast**: No redundant testing (already passed on PR)
- 🔒 **Security audit** still runs for last-minute checks
- 🐳 **Multi-arch builds** (amd64, arm64)
- 🔑 **Analytics injection** from GitHub secrets
- 📦 **Automatic releases** with changelog

## Testing Philosophy

### Shift-Left Testing

We follow a **shift-left** approach: catch issues as early as possible.

```
Traditional:                New Strategy:
┌──────┐  ┌──────┐         ┌──────┐  ┌──────┐
│  PR  │→ │ main │         │  PR  │→ │ main │
└──────┘  └──┬───┘         └──┬───┘  └──────┘
             │                 │
         ┌───▼───┐         ┌───▼───┐
         │ TESTS │         │ TESTS │  ← Tests run HERE
         └───┬───┘         └───────┘
             │
         ┌───▼───┐
         │ BUILD │
         └───────┘
```

**Benefits:**
- ❌ Issues caught in PR, not after merge
- 🔧 Fix issues before they reach main
- ⚡ Faster release process
- ✅ More confidence in main branch

### PR Requirements

Before a PR can be merged to `main`, it must:

1. ✅ Pass all smoke tests
2. ✅ Pass all unit tests
3. ✅ Pass all integration tests
4. ✅ Pass security tests
5. ✅ Pass code quality checks
6. ✅ Pass Docker build test
7. ✅ Pass full test suite (with PostgreSQL)
8. ✅ Have code review approval

## How to Use

### For Contributors

#### Creating a Pull Request

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "Add new feature"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/my-feature
   ```

4. Create PR on GitHub targeting `main` or `develop`

5. **Wait for CI to complete** - all tests must pass

6. **Review test summary** posted as PR comment

7. **Fix any issues** by pushing new commits

8. Once tests pass and PR is approved, merge to main

#### Interpreting Test Results

The CI will post a comment on your PR with results:

```
## ✅ CI Test Results

**Overall Status:** All tests passed!

**Test Results:** 7/7 passed

### Test Suites:

- ✅ Smoke Tests: **success**
- ✅ Unit Tests: **success**
- ✅ Integration Tests: **success**
- ✅ Security Tests: **success**
- ✅ Code Quality: **success**
- ✅ Docker Build: **success**
- ✅ Full Test Suite: **success**
```

### For Maintainers

#### Creating a Release

**Option 1: Automatic Release (Recommended)**

1. Merge PR to `main` (all tests already passed)

2. Update version in `setup.py`:
   ```python
   version='3.2.4',  # Increment version
   ```

3. Commit version bump:
   ```bash
   git add setup.py
   git commit -m "Bump version to 3.2.4"
   git push origin main
   ```

4. Create and push tag:
   ```bash
   git tag v3.2.4
   git push origin v3.2.4
   ```

5. Release workflow automatically:
   - Runs security audit
   - Builds multi-arch Docker images
   - Creates GitHub release with changelog
   - Publishes to GitHub Container Registry

**Option 2: Manual Release**

1. Go to **Actions** → **CD - Release Build** → **Run workflow**

2. Enter version (e.g., `v3.2.4`)

3. Choose whether to skip tests (default: yes, since tests ran on PR)

4. Click **Run workflow**

#### Verifying Analytics Configuration

The release workflow automatically verifies that PostHog secrets are correctly injected:

```bash
# Pre-injection checks:
✅ Verify POSTHOG_API_KEY secret exists
✅ Verify SENTRY_DSN secret exists (optional)

# Post-injection checks:
✅ Verify placeholders were replaced
✅ Verify key format is correct (starts with 'phc_')
✅ Display partial key for confirmation

# Build fails if:
❌ Secret is not set
❌ Placeholder replacement fails
❌ Key format is incorrect
```

## Troubleshooting

### Tests Failing on PR

**Problem:** Tests pass locally but fail on CI

**Solutions:**
1. Check database compatibility (CI uses PostgreSQL)
2. Ensure migrations are committed
3. Check for environment-specific issues
4. Review CI logs for specific errors

### Full Test Suite Timeout

**Problem:** Full test suite times out (30 min limit)

**Solutions:**
1. Check for hanging tests
2. Optimize slow tests
3. Consider splitting test suite further
4. Check database connection issues

### Release Build Failing

**Problem:** Release build fails even though PR tests passed

**Solutions:**
1. Check security audit results (may have new vulnerabilities)
2. Verify GitHub secrets are set correctly
3. Check version in `setup.py` matches tag
4. Review Docker build logs

### PostHog Key Not Injected

**Problem:** Analytics not working in release

**Solutions:**
1. Verify `POSTHOG_API_KEY` secret is set in GitHub
2. Check workflow logs for injection step
3. Ensure key starts with `phc_`
4. Review `app/config/analytics_defaults.py` in built image

## Configuration Files

### Key Files

- `.github/workflows/ci-comprehensive.yml` - PR testing workflow
- `.github/workflows/cd-release.yml` - Release workflow
- `.github/workflows/cd-development.yml` - Development builds (develop branch)
- `pytest.ini` - Test configuration
- `requirements-test.txt` - Test dependencies

### Branch Protection

Recommended branch protection rules for `main`:

```yaml
Protection Rules:
  - Require pull request reviews: Yes
  - Required approvals: 1
  - Require status checks to pass: Yes
    - smoke-tests
    - unit-tests
    - integration-tests
    - security-tests
    - code-quality
    - docker-build
    - full-test-suite (for main only)
  - Require branches to be up to date: Yes
  - Require linear history: Yes (optional)
  - Include administrators: Yes
```

To configure:
1. Go to **Settings** → **Branches**
2. Add rule for `main` branch
3. Enable required status checks from list above

## Monitoring & Metrics

### Test Coverage

- Coverage reports uploaded to Codecov
- Minimum coverage target: 80%
- View coverage at: `https://codecov.io/gh/YOUR_ORG/TimeTracker`

### Build Times

- **Smoke tests**: ~5 minutes
- **Unit tests**: ~10 minutes (parallel)
- **Integration tests**: ~15 minutes
- **Full test suite**: ~30 minutes
- **Release build**: ~30-45 minutes

### Success Metrics

Track these metrics over time:
- Test pass rate
- Time to detect issues
- Time to fix issues
- Code coverage percentage
- Build success rate

## Best Practices

### For Development

1. ✅ Run tests locally before pushing
2. ✅ Write tests for new features (unit + integration)
3. ✅ Keep PRs small and focused
4. ✅ Update documentation with code changes
5. ✅ Address test failures promptly

### For Testing

1. ✅ Write smoke tests for critical paths
2. ✅ Use markers to categorize tests (@pytest.mark.smoke)
3. ✅ Mock external dependencies
4. ✅ Test with PostgreSQL for database-dependent code
5. ✅ Keep tests fast and focused

### For Releases

1. ✅ Always use PRs, never push directly to main
2. ✅ Ensure all tests pass on PR before merging
3. ✅ Update version in setup.py before tagging
4. ✅ Use semantic versioning (MAJOR.MINOR.PATCH)
5. ✅ Write meaningful commit messages for changelog

## Migration Notes

### What Changed?

**Before:**
- Tests ran only on release (after merge to main)
- Issues discovered after code already in main
- Required hotfix PRs to fix issues

**After:**
- Tests run on every PR before merge
- Issues discovered and fixed in PR
- Main branch always deployable

### Transitioning

If you're working on an old PR:

1. Rebase on latest main:
   ```bash
   git checkout main
   git pull
   git checkout your-branch
   git rebase main
   ```

2. Push and trigger new CI:
   ```bash
   git push --force-with-lease
   ```

3. Ensure all new tests pass

## FAQ

**Q: Why do tests take so long?**
A: We run comprehensive tests including integration tests with PostgreSQL and multi-platform Docker builds. This ensures high quality but takes time.

**Q: Can I skip tests to merge faster?**
A: No. Tests are required for all PRs to main. This prevents breaking changes.

**Q: What if tests fail intermittently?**
A: Flaky tests should be fixed. Use test retries sparingly and investigate root cause.

**Q: Can I test locally with PostgreSQL?**
A: Yes! Use docker-compose to run a local PostgreSQL:
```bash
docker-compose up -d db
export DATABASE_URL=postgresql://timetracker:timetracker@localhost:5432/timetracker
pytest
```

**Q: How do I run only smoke tests locally?**
A: Use pytest markers:
```bash
pytest -m smoke
```

**Q: What if the release workflow fails?**
A: Check the workflow logs. Most common issues:
- Version mismatch (setup.py vs tag)
- Missing GitHub secrets
- Docker build failures

## Further Reading

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [Codecov Documentation](https://docs.codecov.com/)

## Support

If you encounter issues:

1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Check existing GitHub issues
4. Create a new issue with:
   - Workflow run link
   - Error messages
   - Steps to reproduce

