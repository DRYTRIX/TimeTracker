# TimeTracker Release Process

## Quick release (recommended)

1. Ensure `develop` is green (`ci-pass` on the latest commit).
2. In GitHub Actions, run **Prepare Release**:
   - `bump`: `patch` | `minor` | `major` (or set an explicit `version`)
   - `base`: `develop` (or `main` for a hotfix)
3. Review the opened PR (`Release vX.Y.Z` from `rc/vX.Y.Z` → `main`).
4. Wait for **`ci-pass`**, then merge.
5. **Finalize Release** (automatic on merge):
   - Tags `vX.Y.Z` (triggers **CD - Release Build**)
   - Back-merges `main` → `develop`
   - Deletes the `rc` branch
6. Watch **CD - Release Build** publish Docker images (GHCR + Docker Hub), desktop/mobile/extension artifacts, and GitHub Release notes from `CHANGELOG.md`.

### Secrets for automation

| Secret | Purpose |
|--------|---------|
| `RELEASE_PAT` | Fine-grained PAT with `contents` + `pull_requests` so tag/PR events trigger other workflows |
| `APP_ID` + `APP_PRIVATE_KEY` | Alternative to `RELEASE_PAT` (GitHub App installation token) |

`GITHUB_TOKEN` alone will create the tag/PR but **will not** trigger `cd-release.yml`. Prefer `RELEASE_PAT` or the App.

## Version bumps

All version locations are updated by one script:

```bash
python scripts/bump_version.py 5.19.0          # apply + promote CHANGELOG Unreleased
python scripts/bump_version.py --bump patch
python scripts/bump_version.py --check         # CI lint job also runs this
python scripts/bump_version.py --extract-notes 5.19.0
```

Updated files: `setup.py`, `VERSION`, `README.md`, `browser-extension/{package,manifest}.json`, `desktop/package.json` (+ lock), `mobile/pubspec.yaml` (build number++), `docs/GAP_ROADMAP.md`, `CHANGELOG.md`.

Do **not** commit `mobile/android/local.properties` (gitignored).

## Branch model

```
feature → develop  (CI required)
             │
    Prepare Release button
             ▼
         rc/vX.Y.Z → main  (CI required)
             │ merge
             ▼
      tag vX.Y.Z + CD release + back-merge to develop
```

Hotfixes: run Prepare Release with `base: main`.

## Manual / emergency tag

```bash
git checkout main && git pull
python scripts/bump_version.py --check
git tag vX.Y.Z && git push origin vX.Y.Z
```

`cd-release` refuses to publish if a `ci-pass` check-run on that commit concluded with failure. Missing `ci-pass` warns but continues (first-rollout / docs edge cases).

## Cleanup stale rc branches

Actions → **Finalize Release** → `workflow_dispatch` with `cleanup_stale_rc=true` deletes remote `rc/*` branches already merged into `main`.

## Development image (`:develop`)

**CD - Development Build** (`cd-development.yml`) publishes `ghcr.io/drytrix/timetracker:develop` (and Docker Hub when credentials are set) on pushes to `develop` that touch image-affecting paths (`app/`, `migrations/`, `translations/`, `peppol_bridge/`, `docker/`, `nginx/`, Dockerfile, requirements, asset build scripts, etc.).

It does **not** run for pure docs-only pushes. Smoke tests must pass before the image is pushed (override with `force_build` on manual dispatch). In-flight publishes are not cancelled when a newer push arrives.

To refresh `:develop` without a matching path change: **Actions → CD - Development Build → Run workflow**.

## Obsolete tooling

`scripts/version-manager.sh` is superseded by `scripts/bump_version.py` + the Prepare/Finalize workflows. Prefer the Actions button flow above.

## Checklist before merging an rc PR

- [ ] `ci-pass` green
- [ ] CHANGELOG section for the version is accurate
- [ ] Migrations reviewed (if the migrations job ran)
- [ ] Breaking changes called out for operators

## Related

- [Testing workflow strategy](../../cicd/TESTING_WORKFLOW_STRATEGY.md)
- [Version management](VERSION_MANAGEMENT.md)
- [Official builds](OFFICIAL_BUILDS.md)
