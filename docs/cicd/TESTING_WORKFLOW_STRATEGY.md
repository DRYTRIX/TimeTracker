# Testing Workflow Strategy

## Overview

TimeTracker uses a **single CI pipeline** ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) on pull requests and pushes to `develop`. Branch protection should require only the **`ci-pass`** job — an aggregator that treats path-filtered skips as success.

## Triggers

| Event | Branches | What runs |
|-------|----------|-----------|
| `pull_request` | `develop`, `main`, `rc/**` | Full CI (path-filtered) |
| `push` | `develop` | Full CI (warms caches) + CD development image |
| `workflow_dispatch` | any | Manual CI |

## Jobs

```
┌────────────┐
│  changes   │  dorny/paths-filter → python/frontend/migrations/docker/desktop/mobile/deps
└─────┬──────┘
      │
 ┌────┴──────────────────────────────────────────────────────────┐
 │ parallel (skipped when paths don't match)                     │
 │  lint │ security │ tests(×4 shards) │ frontend │ migrations   │
 │  docker+e2e │ desktop │ mobile                                │
 └────┬──────────────────────────────────────────────────────────┘
      │
 ┌────▼────┐
 │ ci-pass │  ← only required status check
 └─────────┘
```

### Path filtering

Docs-only PRs (`**/*.md`, `docs/**`) complete in about a minute: every heavy job is skipped and `ci-pass` still succeeds.

### Tests

- Run **once**, sharded 4 ways with `pytest-split` against Postgres.
- Coverage shards are averaged; gate is **40%** (ratchet upward over time).
- Integration no longer runs as a separate 15-minute job that timed out every release.

### Security

- Bandit (high severity) and security pytest always block when Python code changes.
- **pip-audit / Safety** block only when `requirements*.txt` change.
- A **nightly** workflow ([`deps-audit-nightly.yml`](../../.github/workflows/deps-audit-nightly.yml)) opens an issue if new CVEs appear.

### Docker & E2E

One image is built with GHA layer cache, health-checked, then used for Playwright (CSP / a11y / offline).

### Migrations

When `app/models/**` or `migrations/**` change, CI calls the reusable workflow [`migration-validate.yml`](../../.github/workflows/migration-validate.yml) (single Alembic head, new-drift-vs-base, rollback, sample data).

## Local parity

```bash
make ci-local          # or scripts/run-ci-local.sh
make lint              # flake8 + black --check + isort --check
python scripts/bump_version.py --check
pre-commit run black --all-files
pre-commit run isort --all-files
```

Install hooks: `pre-commit install` (config: [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml)). Flake8 config is **only** in [`.flake8`](../../.flake8).

## What does *not* run on every PR

- Full Windows/macOS/Android installers — those ship from **CD - Release Build**. Desktop/mobile CI jobs run tests (and a Linux desktop build) only when those paths change. Manual rebuilds: `build-desktop.yml` / `build-mobile.yml` (`workflow_dispatch`).
- CodeQL skips docs-only PRs via `paths-ignore`.

## Related docs

- [Release process](../admin/deployment/RELEASE_PROCESS.md)
- [Version management](../admin/deployment/VERSION_MANAGEMENT.md)
