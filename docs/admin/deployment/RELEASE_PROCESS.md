# TimeTracker Release Process Guide

This document outlines the comprehensive release process for TimeTracker, including automated workflows, manual steps, and best practices.

## 🚀 Quick Release Guide

### Automated Release (Recommended)

```bash
# 1. Create a complete release with changelog and GitHub release
./scripts/version-manager.sh release --version v1.2.3 --changelog --github-release

# 2. For pre-releases
./scripts/version-manager.sh release --version v1.2.3-rc.1 --pre-release --changelog --github-release
```

### Manual Release Steps

1. **Prepare Release**
2. **Create Tag**
3. **Generate Changelog**
4. **Create GitHub Release**
5. **Verify Deployment**

## 📋 Detailed Release Process

### 1. Pre-Release Checklist

Before starting any release, ensure:

- [ ] **All tests pass** in CI/CD
- [ ] **Database migrations tested** and documented
- [ ] **Docker images build** successfully
- [ ] **Documentation updated** with new features
- [ ] **Breaking changes documented** (if any)
- [ ] **Security vulnerabilities addressed**
- [ ] **Performance regressions checked**

### 2. Release Preparation

#### Check Current Status
```bash
# Check current version and status
./scripts/version-manager.sh status

# Check for uncommitted changes
git status

# Ensure you're on main branch
git checkout main
git pull origin main
```

#### Version Selection
Follow [Semantic Versioning](https://semver.org/):

- **Major** (v2.0.0): Breaking changes, major new features
- **Minor** (v1.1.0): New features, backward compatible
- **Patch** (v1.0.1): Bug fixes, backward compatible
- **Pre-release** (v1.0.0-rc.1): Release candidates, beta versions

#### Suggested Version
```bash
# Get version suggestion
./scripts/version-manager.sh suggest
```

### 3. Release Types

#### 3.1 Standard Release

```bash
# Create standard release
./scripts/version-manager.sh release \
  --version v1.2.3 \
  --message "Release 1.2.3 with new features and bug fixes" \
  --changelog \
  --github-release
```

**What this does:**
1. Creates and pushes git tag
2. Generates changelog from commits
3. Creates GitHub release with changelog
4. Triggers Docker image build via GitHub Actions

#### 3.2 Pre-Release

```bash
# Create pre-release (RC, beta, alpha)
./scripts/version-manager.sh release \
  --version v1.2.3-rc.1 \
  --message "Release candidate for 1.2.3" \
  --pre-release \
  --changelog \
  --github-release
```

#### 3.3 Hotfix Release

```bash
# Create hotfix from main branch
git checkout main
git pull origin main

# Apply hotfix
git cherry-pick <hotfix-commit>

# Create hotfix release
./scripts/version-manager.sh release \
  --version v1.2.4 \
  --message "Hotfix: Critical security update" \
  --changelog \
  --github-release
```

### 4. Manual Release Steps

If you prefer manual control over the release process:

#### Step 1: Create Tag
```bash
# Create annotated tag
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3
```

#### Step 2: Generate Changelog
```bash
# Generate changelog
python scripts/generate-changelog.py v1.2.3 --output CHANGELOG.md

# Review and edit changelog if needed
nano CHANGELOG.md
```

#### Step 3: Create GitHub Release
```bash
# Using GitHub CLI
gh release create v1.2.3 \
  --title "TimeTracker v1.2.3" \
  --notes-file CHANGELOG.md

# Or via GitHub web interface
# Go to: https://github.com/your-repo/releases/new
```

### 5. Post-Release Verification

#### 5.1 Verify GitHub Actions
- Check that Docker build workflow completed successfully
- Verify Docker images are published to GHCR
- Confirm all CI/CD checks passed

#### 5.2 Test Docker Images
```bash
# Test the released image
docker run -d --name test-release -p 8080:8080 \
  ghcr.io/drytrix/timetracker:v1.2.3

# Verify health
curl -f http://localhost:8080/_health

# Clean up
docker stop test-release && docker rm test-release
```

#### 5.3 Update Documentation
- [ ] Update README.md version references
- [ ] Update deployment documentation
- [ ] Update Docker Compose examples
- [ ] Notify users of new release

### 6. Release Workflow Automation

The release process triggers several automated workflows:

#### 6.1 Release Workflow (`release.yml`)
**Triggered by:** GitHub release creation or manual dispatch

**Steps:**
1. **Validate Release** - Ensures version format is correct
2. **Run Tests** - Full test suite with database migrations
3. **Build & Push Docker** - Multi-architecture Docker images
4. **Generate Changelog** - Automated changelog generation
5. **Update Documentation** - Version references in docs
6. **Notify Deployment** - Summary and deployment instructions

#### 6.2 CI Workflow (`ci.yml`)
**Triggered by:** Push to main/develop, pull requests

**Steps:**
1. **Lint & Format** - Code quality checks
2. **Test Database Migrations** - PostgreSQL & SQLite testing
3. **Test Docker Build** - Container build and startup verification
4. **Security Scan** - Dependency and code security scanning
5. **Version Management Validation** - Version manager script testing

#### 6.3 Migration Check Workflow (`migration-check.yml`)
**Triggered by:** Changes to models or migrations

**Steps:**
1. **Validate Migrations** - Schema consistency and rollback safety
2. **Test with Sample Data** - Data integrity verification
3. **Generate Migration Report** - Detailed migration analysis

### 7. Emergency Procedures

#### 7.1 Rollback Release
```bash
# Delete tag locally and remotely
git tag -d v1.2.3
git push origin --delete v1.2.3

# Delete GitHub release
gh release delete v1.2.3

# Revert commits if needed
git revert <commit-hash>
```

#### 7.2 Fix Broken Release
```bash
# Create hotfix
git checkout v1.2.3
git cherry-pick <fix-commit>

# Create new patch release
./scripts/version-manager.sh release \
  --version v1.2.4 \
  --message "Hotfix for v1.2.3 issues" \
  --changelog \
  --github-release
```

### 8. Release Schedule

#### Recommended Schedule
- **Major releases**: Every 6-12 months
- **Minor releases**: Every 1-2 months
- **Patch releases**: As needed for critical fixes
- **Pre-releases**: 1-2 weeks before major/minor releases

#### Release Windows
- **Regular releases**: Tuesday-Thursday (better for issue resolution)
- **Hotfixes**: Any day (emergency only)
- **Pre-releases**: Friday (allows weekend testing)

### 9. Communication

#### Internal Team
- [ ] Notify team before release
- [ ] Share release notes
- [ ] Coordinate deployment timing
- [ ] Plan post-release monitoring

#### External Users
- [ ] Update release notes on GitHub
- [ ] Update documentation website
- [ ] Notify via social media/newsletters
- [ ] Update Docker Hub descriptions

### 10. Quality Gates

Every release must pass:

- [ ] **All automated tests** (unit, integration, E2E)
- [ ] **Database migration tests** (up and down)
- [ ] **Docker build verification** (multi-architecture)
- [ ] **Security scans** (dependencies and code)
- [ ] **Performance benchmarks** (no significant regression)
- [ ] **Documentation review** (accuracy and completeness)

### 11. Troubleshooting

#### Common Issues

**Issue**: Docker build fails
```bash
# Check Docker build locally
docker build -t test-build .

# Check workflow logs in GitHub Actions
```

**Issue**: Migration validation fails
```bash
# Test migrations locally
flask db upgrade
flask db downgrade
flask db upgrade
```

**Issue**: Version tag already exists
```bash
# Check existing tags
git tag -l

# Delete if needed
git tag -d v1.2.3
git push origin --delete v1.2.3
```

### 12. Tools and Dependencies

#### Required Tools
- **Git** - Version control
- **GitHub CLI** (`gh`) - GitHub release management
- **Docker** - Container testing
- **Python 3.11+** - Script execution
- **Flask** - Database migration testing

#### Installation
```bash
# Install GitHub CLI
# macOS: brew install gh
# Ubuntu: sudo apt install gh
# Windows: winget install GitHub.CLI

# Authenticate
gh auth login

# Install Python dependencies
pip install -r requirements.txt
```

### 13. Metrics and Monitoring

Track release metrics:
- **Release frequency** - How often releases are made
- **Lead time** - Time from commit to release
- **Failure rate** - Percentage of failed releases
- **Recovery time** - Time to fix broken releases
- **User adoption** - Docker pull statistics

### 14. Continuous Improvement

Regular review of:
- [ ] Release process efficiency
- [ ] Automation opportunities
- [ ] Quality gate effectiveness
- [ ] User feedback incorporation
- [ ] Tool and workflow updates

---

## 🔗 Related Documentation

- [Version Management System](VERSION_MANAGEMENT.md)
- [Database Migrations](../migrations/README.md)
- [Docker Setup](DOCKER_PUBLIC_SETUP.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🆘 Support

For release process issues:
1. Check this documentation
2. Review GitHub Actions logs
3. Test locally with provided commands
4. Create issue with detailed error information
