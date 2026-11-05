# GitHub Actions Status Badges

Add these badges to your README.md to show build status and coverage.

## CI/CD Status Badges

### Main CI Pipeline
```markdown
[![CI Pipeline](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml)
```

[![CI Pipeline](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml)

### Development Build
```markdown
[![Development Build](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml/badge.svg?branch=develop)](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml)
```

[![Development Build](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml/badge.svg?branch=develop)](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml)

### Release Build
```markdown
[![Release Build](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml)
```

[![Release Build](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml)

### Docker Publishing
```markdown
[![Docker Publish](https://github.com/{owner}/{repo}/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/docker-publish.yml)
```

[![Docker Publish](https://github.com/{owner}/{repo}/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/docker-publish.yml)

### Migration Check
```markdown
[![Migration Check](https://github.com/{owner}/{repo}/actions/workflows/migration-check.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/migration-check.yml)
```

[![Migration Check](https://github.com/{owner}/{repo}/actions/workflows/migration-check.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/migration-check.yml)

## Coverage Badges

### Codecov (if configured)
```markdown
[![codecov](https://codecov.io/gh/{owner}/{repo}/branch/main/graph/badge.svg)](https://codecov.io/gh/{owner}/{repo})
```

[![codecov](https://codecov.io/gh/{owner}/{repo}/branch/main/graph/badge.svg)](https://codecov.io/gh/{owner}/{repo})

## Docker Image Badges

### Docker Image Size
```markdown
[![Docker Image Size](https://img.shields.io/docker/image-size/{owner}/{repo}/latest)](https://github.com/{owner}/{repo}/pkgs/container/{repo})
```

[![Docker Image Size](https://img.shields.io/docker/image-size/{owner}/{repo}/latest)](https://github.com/{owner}/{repo}/pkgs/container/{repo})

### Docker Pulls
```markdown
[![Docker Pulls](https://img.shields.io/docker/pulls/{owner}/{repo})](https://github.com/{owner}/{repo}/pkgs/container/{repo})
```

## License and Version Badges

### License
```markdown
[![License](https://img.shields.io/github/license/{owner}/{repo})](LICENSE)
```

[![License](https://img.shields.io/github/license/{owner}/{repo})](LICENSE)

### Latest Release
```markdown
[![Latest Release](https://img.shields.io/github/v/release/{owner}/{repo})](https://github.com/{owner}/{repo}/releases/latest)
```

[![Latest Release](https://img.shields.io/github/v/release/{owner}/{repo})](https://github.com/{owner}/{repo}/releases/latest)

### Python Version
```markdown
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
```

[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)

## Complete Badge Example

Here's a complete set of badges you can add to your README:

```markdown
# TimeTracker

[![CI Pipeline](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/ci-comprehensive.yml)
[![Development Build](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml/badge.svg?branch=develop)](https://github.com/{owner}/{repo}/actions/workflows/cd-development.yml)
[![Release Build](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/cd-release.yml)
[![codecov](https://codecov.io/gh/{owner}/{repo}/branch/main/graph/badge.svg)](https://codecov.io/gh/{owner}/{repo})
[![License](https://img.shields.io/github/license/{owner}/{repo})](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![Latest Release](https://img.shields.io/github/v/release/{owner}/{repo})](https://github.com/{owner}/{repo}/releases/latest)
```

## Instructions

1. Replace `{owner}` with your GitHub username or organization name
2. Replace `{repo}` with your repository name
3. Copy the badge markdown to your README.md
4. Commit and push to see the badges appear

## Custom Badges

You can create custom badges at [shields.io](https://shields.io/).

### Example: Test Coverage Custom Badge
```markdown
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)
```

### Example: Build Status Custom Badge
```markdown
![Status](https://img.shields.io/badge/status-production%20ready-success)
```

### Example: Tests Passing Badge
```markdown
![Tests](https://img.shields.io/badge/tests-100%20passing-success)
```

---

**Note**: Replace `{owner}` and `{repo}` with your actual GitHub username and repository name.
