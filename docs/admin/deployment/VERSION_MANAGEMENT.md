# Version Management System

How TimeTracker versions are stored, bumped, and published.

**Canonical release how-to:** [Release Process](RELEASE_PROCESS.md) (Prepare Release → merge `rc/v*` → Finalize tag → CD publish).

**Canonical bump tool:** [`scripts/bump_version.py`](../../../scripts/bump_version.py) updates `setup.py`, `VERSION`, client manifests, and promotes `CHANGELOG.md` `[Unreleased]`.

**For contributors:** Application version is defined in **setup.py** (mirrored by the bump script). Do not hand-edit desktop/mobile versions — run the script. Desktop and mobile build tooling is covered in the [Build Guide](../../../scripts/README-BUILD.md).

**OpenAPI (`/api/openapi.json`):** The `info.version` field uses the same resolution as the in-app version helpers: environment variables **`TIMETRACKER_VERSION`** or **`APP_VERSION`** override the value read from **`setup.py`**; see `get_version_from_setup()` in `app/config/analytics_defaults.py` and `openapi_spec()` in `app/routes/api_docs.py`.

## Overview

1. **Prepare Release** (`release-prepare.yml`) — Creates `rc/vX.Y.Z`, runs `bump_version.py`, opens a PR to `main`.
2. **Finalize Release** (`release-finalize.yml`) — On merge of that PR, tags `vX.Y.Z` and back-merges to `develop`.
3. **CD - Release Build** (`cd-release.yml`) — On `v*.*.*` tags (or manual dispatch), publishes Docker images, client artifacts, and the GitHub Release (notes from `CHANGELOG.md`).
4. **CD - Development Build** (`cd-development.yml`) — On image-affecting pushes to `develop`, publishes `:develop` (synthetic `dev-<run>-<sha>` version). See [Release Process → Development image](RELEASE_PROCESS.md#development-image-develop).

Do **not** create production releases via the GitHub “Draft a new release” UI or by running `version-manager.sh` alone — those paths are obsolete for shipping.

## Version format

Production releases use semantic versions with a `v` prefix on git tags:

- Tag: `v5.19.0`
- `setup.py` / `VERSION` / clients: `5.19.0` (mobile may append `+build`)

Development images use synthetic versions such as `dev-123-a1b2c3d4` and registry tags `develop`, `dev-<sha>`.

## Files updated by `bump_version.py`

| File | Role |
|------|------|
| `setup.py` | Primary source of truth |
| `VERSION` | Mirror |
| `README.md` | “Latest release: vX.Y.Z” line |
| `CHANGELOG.md` | Promotes `[Unreleased]` → `## [X.Y.Z] - date` |
| `browser-extension/package.json`, `manifest.json` | Extension version |
| `desktop/package.json` (+ lock) | Electron app version |
| `mobile/pubspec.yaml` | Flutter version (`X.Y.Z+build`) |
| `docs/GAP_ROADMAP.md` | Best-effort mirrors |

```bash
python scripts/bump_version.py 5.19.0
python scripts/bump_version.py --bump patch
python scripts/bump_version.py --check
python scripts/bump_version.py --extract-notes 5.19.0
```

## GitHub Actions (current)

### Release publish (`cd-release.yml`)

Triggered by:

1. Push of tag `v*.*.*` (normal path after Finalize)
2. Manual **workflow_dispatch** with a version that matches `setup.py`

Version must match `setup.py`. Tag commits must be ancestors of `main`. Images are tagged with the semver plus `latest` / `stable`.

### Development publish (`cd-development.yml`)

Triggered by pushes to `develop` that match the image-affecting path allowlist, or by **workflow_dispatch**. Smoke tests must pass before push (unless `force_build`). In-flight publishes are not cancelled mid-run.

### Manual / emergency tag

Only when automation cannot tag (see [Release Process](RELEASE_PROCESS.md)):

```bash
git checkout main && git pull
python scripts/bump_version.py --check
git tag vX.Y.Z && git push origin vX.Y.Z
```

## Docker image labels

Release and development images include OCI labels (version, revision, source) via `docker/metadata-action` in the CD workflows.

## Best practices

- Use **semantic versioning** for releases (`v1.2.3`)
- Keep release notes in **`CHANGELOG.md` `[Unreleased]`** before Prepare Release
- Run **`python scripts/bump_version.py --check`** locally when touching version files
- Prefer **Prepare/Finalize** over hand-tagging
- Tag production releases from **`main`** only (via the rc merge)

## Troubleshooting

### Tag already exists

```bash
# Prefer a new patch/minor instead of moving tags.
# Only delete/recreate in true emergency (coordinate with CD):
git tag -d v1.2.3
git push origin --delete v1.2.3
```

### Release build not triggered after Finalize

- Prefer `RELEASE_PAT` or a GitHub App so the tag push can trigger `cd-release.yml` (`GITHUB_TOKEN` alone often will not)
- Confirm the tag matches `v*.*.*` and the commit is on `main`
- Check that `setup.py` version matches the tag (without `v`)

### Develop image not updated

- Push may not have matched the path filter (docs-only) — use **Actions → CD - Development Build → Run workflow**
- Smoke tests may have failed — check the run or use `force_build`
- Confirm Docker Hub credentials if you expect Hub as well as GHCR

## Obsolete tooling

`scripts/version-manager.sh` (and `.bat` / `.ps1` wrappers) only manage git tags. They do **not** bump `setup.py` / clients / CHANGELOG. Prefer `bump_version.py` + Prepare/Finalize.

## Admin in-app update notification (GitHub releases) {#admin-github-update-notification}

Administrators can be notified in the web UI when a **newer semantic version** exists on GitHub compared to this installation. The feature is server-driven, does not affect non-admin users, and uses caching so routine page loads do not hammer the GitHub API.

### Behavior

- **Source of truth for “latest”:** GitHub’s API for the configured repository (default `DRYTRIX/TimeTracker`), either `releases/latest` or, when pre-releases are enabled, the newest non-draft release from the releases list.
- **Installed version:** `APP_VERSION` / `GITHUB_TAG` from the environment (via Flask config) if it parses as a semantic version; otherwise the version read from **`setup.py`** at runtime (see the note at the top of this document). Non-semver installs (for example `dev-123`) do not show an upgrade prompt.
- **UI:** A small, non-blocking card on authenticated admin pages (templates using `base.html`). **Dismiss** hides until the next load; **Don’t show again for this version** persists per user in the database (migration `148_add_user_dismissed_release_version`) and mirrors to browser `localStorage` as a fallback.
- **API:** `GET /api/version/check` and `POST /api/version/dismiss` on the legacy `/api` JSON routes; session or API token; admin-only. See [REST API — Admin version check](../../api/REST_API.md#admin-version-check-web-json-under-api).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VERSION_CHECK_GITHUB_REPO` | `DRYTRIX/TimeTracker` | `owner/repo` for `api.github.com/repos/{repo}/releases/…` |
| `VERSION_CHECK_GITHUB_CACHE_TTL` | `43200` (12h) | TTL in seconds for the successful GitHub response cache |
| `VERSION_CHECK_GITHUB_STALE_TTL` | `604800` (7d) | TTL for the last successful payload used when GitHub returns errors (for example `403` rate limit) |
| `VERSION_CHECK_HTTP_TIMEOUT` | `10` | HTTP timeout in seconds for GitHub requests |
| `GITHUB_RELEASES_TOKEN` | _(empty)_ | Optional GitHub personal access token (fine-scoped classic token with `public_repo` is enough for public repos); raises authenticated rate limits. **Do not commit tokens;** set only via environment or secrets manager. |
| `ENABLE_PRE_RELEASE_NOTIFICATIONS` | `false` | When `true`, consider the newest non-draft release from the paginated releases list (including pre-releases). When `false`, use `releases/latest` (stable only per GitHub’s definition). |

Optional: set `APP_VERSION` (or `GITHUB_TAG`) at deploy time to a semver string so Docker images and CI builds compare correctly against release tags.
