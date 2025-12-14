# Version Management System

This document describes the comprehensive version management system for TimeTracker that provides flexible versioning for both GitHub releases and build numbers.

## Overview

The version management system provides multiple ways to set version tags:

1. **GitHub Releases** - Automatic versioning when creating releases
2. **Git Tags** - Manual version tagging for releases
3. **Build Numbers** - Automatic versioning for branch builds
4. **Manual Workflow Dispatch** - Custom version input through GitHub Actions
5. **Local Version Management** - Command-line tools for version management

## Version Format Support

The system supports various version formats:

### Semantic Versions
- `v1.2.3` - Full semantic version (recommended for releases)
- `1.2.3` - Semantic version without 'v' prefix
- `v1.2` - Major.Minor version
- `v1` - Major version only

### Build Versions
- `build-123` - Build number format
- `main-build-456` - Branch-specific build
- `feature-build-789` - Feature branch build

### Pre-release Versions
- `rc1` - Release candidate
- `beta1` - Beta version
- `alpha1` - Alpha version
- `dev-123` - Development version

## GitHub Actions Workflow

### Automatic Version Detection

The GitHub Actions workflow automatically determines the version based on the trigger:

1. **Manual Workflow Dispatch** - Uses custom input version
2. **GitHub Release** - Uses release tag name
3. **Git Tag** - Uses git tag name
4. **Branch Push** - Uses branch name + build number
5. **Fallback** - Uses commit SHA

### Version Priority

```yaml
# Priority order for version determination:
# 1. Manual workflow dispatch input
# 2. GitHub release tag
# 3. Git tag
# 4. Branch name with build number
# 5. Fallback to commit SHA
```

### Tag Strategy

- **Releases/Tags**: Tagged as both `version` and `latest`
- **Main Branch Builds**: Tagged as both `version` and `main`
- **Feature Branches**: Tagged only as `version`
- **Pull Requests**: Build but don't push (preview only)

## Usage Methods

### 1. GitHub Releases (Recommended)

Create a GitHub release to automatically trigger a build with the release version:

1. Go to GitHub repository → Releases → "Create a new release"
2. Choose a tag (e.g., `v1.2.3`) or create a new one
3. Fill in release title and description
4. Publish the release
5. GitHub Actions automatically builds and pushes the Docker image

**Result**: Image tagged as `ghcr.io/drytrix/timetracker:v1.2.3` and `ghcr.io/drytrix/timetracker:latest`

### 2. Git Tags

Create a git tag locally and push to trigger a build:

```bash
# Create and push a tag
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3
```

**Result**: Image tagged as `ghcr.io/drytrix/timetracker:v1.2.3` and `ghcr.io/drytrix/timetracker:latest`

### 3. Manual Workflow Dispatch

Trigger a build with a custom version through GitHub Actions:

1. Go to GitHub repository → Actions → "Build and Publish TimeTracker Docker Image"
2. Click "Run workflow"
3. Enter custom version (e.g., `custom-build-123`)
4. Click "Run workflow"

**Result**: Image tagged as `ghcr.io/drytrix/timetracker:custom-build-123`

### 4. Branch Builds

Push to any branch to automatically create a build version:

```bash
# Push to main branch
git push origin main
# Results in: main-build-456 (where 456 is the build number)

# Push to feature branch
git push origin feature/new-feature
# Results in: feature-new-feature-build-789
```

## Local Version Management

### Installation

Make the scripts executable:

```bash
# Unix/Linux/macOS
chmod +x scripts/version-manager.sh

# Windows
# No special action needed, .bat files are executable by default
```

### Basic Commands

#### Check Current Status

```bash
# Unix/Linux/macOS
./scripts/version-manager.sh status

# Windows
scripts\version-manager.bat status
```

**Output:**
```
=== Version Status ===
Current branch: main
Latest tag: v1.2.3
Commits since last tag: 5
Current commit: a1b2c3d
Suggested next version: v1.2.4
=====================
```

#### Create a Release Tag

```bash
# Unix/Linux/macOS
./scripts/version-manager.sh tag v1.2.4 "Release 1.2.4 with new features"

# Windows
scripts\version-manager.bat tag v1.2.4 "Release 1.2.4 with new features"
```

#### Create a Build Tag

```bash
# Unix/Linux/macOS
./scripts/version-manager.sh build 123

# Windows
scripts\version-manager.bat build 123
```

#### List All Tags

```bash
# Unix/Linux/macOS
./scripts/version-manager.sh list

# Windows
scripts\version-manager.bat list
```

#### Get Version Suggestions

```bash
# Unix/Linux/macOS
./scripts/version-manager.sh suggest

# Windows
scripts\version-manager.bat suggest
```

### Advanced Usage

#### Create Tag Without Pushing

```bash
./scripts/version-manager.sh tag v1.2.4 --no-push
```

#### Custom Build Number

```bash
./scripts/version-manager.sh build --build-number 999
```

#### Show Tag Information

```bash
# Show latest tag info
./scripts/version-manager.sh info

# Show specific tag info
./scripts/version-manager.sh info v1.2.3
```

## Docker Image Labels

All Docker images include comprehensive metadata labels:

```dockerfile
--label "org.opencontainers.image.version=$VERSION"
--label "org.opencontainers.image.revision=${{ github.sha }}"
--label "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
--label "org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}"
```

## Workflow Examples

### Release Workflow

1. **Develop features** on feature branches
2. **Merge to main** when ready
3. **Create release tag**:
   ```bash
   ./scripts/version-manager.sh tag v1.3.0 "Major feature release"
   ```
4. **Push tag** to trigger GitHub Actions
5. **Create GitHub release** for the tag
6. **Docker image** automatically built and pushed

### Development Workflow

1. **Work on feature branch**:
   ```bash
   git checkout -b feature/new-feature
   # ... make changes ...
   git push origin feature/new-feature
   ```
2. **Automatic build** with version like `feature-new-feature-build-123`
3. **Test the image** before merging
4. **Merge to main** when ready
5. **Create release tag** for production

### Hotfix Workflow

1. **Create hotfix branch**:
   ```bash
   git checkout -b hotfix/critical-fix
   # ... fix the issue ...
   git push origin hotfix/critical-fix
   ```
2. **Test the build** with version like `hotfix-critical-fix-build-456`
3. **Create hotfix release**:
   ```bash
   ./scripts/version-manager.sh tag v1.2.4 "Critical security fix"
   ```

## Best Practices

### Version Naming

- **Use semantic versioning** for releases (`v1.2.3`)
- **Use descriptive names** for feature branches
- **Include build numbers** for development builds
- **Be consistent** with naming conventions

### Tag Management

- **Create tags locally** before pushing
- **Use meaningful commit messages** for tags
- **Push tags immediately** after creation
- **Clean up old tags** periodically

### Release Process

- **Test thoroughly** before creating releases
- **Use release candidates** for major versions
- **Document changes** in release notes
- **Tag from main branch** only

## Troubleshooting

### Common Issues

#### Tag Already Exists

```bash
# Delete local tag
git tag -d v1.2.3

# Delete remote tag
git push origin --delete v1.2.3

# Recreate tag
./scripts/version-manager.sh tag v1.2.3
```

#### Build Not Triggered

- Check if the tag was pushed to remote
- Verify GitHub Actions permissions
- Check workflow file syntax
- Ensure tag format is valid

#### Version Format Invalid

The system validates version formats. Common valid formats:

```bash
# Valid
v1.2.3, 1.2.3, build-123, rc1, beta1

# Invalid
1.2.3.4, v1.2.3.4, build_123, release-1
```

### Debug Commands

```bash
# Check git status
git status

# Check remote tags
git ls-remote --tags origin

# Check local tags
git tag -l

# Check GitHub Actions
# Go to Actions tab in GitHub repository
```

## Integration with CI/CD

### GitHub Actions

The version management system integrates seamlessly with GitHub Actions:

- **Automatic triggers** on tags and releases
- **Build number tracking** for continuous builds
- **Docker image publishing** to GitHub Container Registry
- **Pull request previews** without publishing

### External CI/CD

For external CI/CD systems, use the version manager scripts:

```bash
# In CI/CD pipeline
./scripts/version-manager.sh build $BUILD_NUMBER
git push origin --tags
```

## Future Enhancements

- **Version database** for tracking all versions
- **Release notes generation** from commits
- **Dependency version tracking** for security updates
- **Automated changelog** generation
- **Version compatibility** checking
- **Rollback support** for failed releases
