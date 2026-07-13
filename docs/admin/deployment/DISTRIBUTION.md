# TimeTracker Distribution & Download Guide

This is the canonical list of where to get and install TimeTracker. Pick the path that matches your environment.

## Quick links

| I want to… | Go here |
|------------|---------|
| Run on a NAS (QNAP, Synology, Portainer) | [NAS Deployment Guide](NAS_DEPLOYMENT.md) + [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) |
| Pull a Docker image | [Docker Hub](https://hub.docker.com/r/drytrix/timetracker) or `docker pull ghcr.io/drytrix/timetracker:latest` |
| Deploy on a server with Docker Compose | [INSTALLATION.md](../../../INSTALLATION.md) |
| One-click cloud deploy | [Render](#render) · [Railway](#railway) · [Fly.io](#flyio) · [Coolify](#coolify) |
| Install from Unraid Community Apps | [Unraid](#unraid-community-applications) |
| Add to Portainer App Templates | [Portainer](#portainer-app-templates) |
| Download desktop/mobile clients | [GitHub Releases](https://github.com/drytrix/TimeTracker/releases) |

---

## Docker images

Official multi-arch images (`linux/amd64`, `linux/arm64`) are built on every release.

### GitHub Container Registry (primary)

```bash
docker pull ghcr.io/drytrix/timetracker:latest
docker pull ghcr.io/drytrix/timetracker:v5.9.2   # specific version
```

### Docker Hub (mirror)

**Repository:** [hub.docker.com/r/drytrix/timetracker](https://hub.docker.com/r/drytrix/timetracker)

```bash
docker pull drytrix/timetracker:latest
```

> **Note:** The Docker Hub namespace moved from `driesp/timetracker` to **`drytrix/timetracker`**. Update any scripts or bookmarks that used the old URL.

If Docker Hub is unavailable, use GHCR.

### Development image

```bash
docker pull ghcr.io/drytrix/timetracker:develop
```

Use with [`docker/docker-compose.remote-dev.yml`](../../../docker/docker-compose.remote-dev.yml).

---

## Compose files (no build required)

| File | Use case |
|------|----------|
| [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) | NAS, Portainer web editor, simple HTTP (app + Postgres) |
| [`docker/docker-compose.remote.yml`](../../../docker/docker-compose.remote.yml) | Production HTTPS with nginx (requires git clone) |
| [`docker-compose.example.yml`](../../../docker-compose.example.yml) | Simple HTTP from cloned repo |
| GitHub Release `docker-compose.production.yml` | Full production stack artifact |
| GitHub Release `docker-compose.nas.yml` | NAS stack artifact (same as repo file) |

### NAS one-liner (no git clone)

```bash
curl -fsSL -o docker-compose.nas.yml \
  https://raw.githubusercontent.com/drytrix/TimeTracker/main/docker-compose.nas.yml
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
docker compose -f docker-compose.nas.yml up -d
```

Raw compose URL (for pasting into NAS UIs):

```
https://raw.githubusercontent.com/drytrix/TimeTracker/main/docker-compose.nas.yml
```

---

## GitHub Releases

Each release includes:

- `docker-compose.production.yml` — full production stack
- `docker-compose.nas.yml` — NAS-friendly stack
- `k8s-deployment.yml` — basic Kubernetes manifest
- Desktop installers (Windows `.exe`, Linux `.AppImage`/`.deb`, macOS `.dmg`) when CI succeeds
- Mobile builds (Android APK/AAB, iOS simulator zip) when CI succeeds

Download: [github.com/drytrix/TimeTracker/releases](https://github.com/drytrix/TimeTracker/releases)

---

## Portainer App Templates

Add TimeTracker to Portainer's template catalog:

1. In Portainer, go to **Settings → App Templates**
2. Set **App Templates URL** to:
   ```
   https://raw.githubusercontent.com/drytrix/TimeTracker/main/templates/portainer/templates.json
   ```
3. Refresh **App Templates** and deploy **TimeTracker**

Template definition: [`templates/portainer/templates.json`](../../../templates/portainer/templates.json)

See also: [Portainer Deployment Guide](PORTAINER_DEPLOYMENT.md)

---

## Unraid Community Applications

Template XML files live in [`templates/unraid/`](../../../templates/unraid/):

| Template | File |
|----------|------|
| PostgreSQL database | `templates/unraid/timetracker-db.xml` |
| TimeTracker app | `templates/unraid/timetracker-app.xml` |

### Install on Unraid (manual templates)

1. Copy both XML files to `/boot/config/plugins/dockerMan/templates-user/` on your Unraid server
2. In Docker → **Add Container**, pick **TimeTracker-DB** first, deploy
3. Add **TimeTracker** app container on the same custom network (`timetracker`)
4. Set `SECRET_KEY` (generate with `openssl rand -hex 32`)

### Submit to Community Applications

To list TimeTracker in the official Unraid CA catalog:

1. Ensure [`templates/unraid/ca_profile.xml`](../../../templates/unraid/ca_profile.xml) metadata is current
2. Go to [ca.unraid.net/submit](https://ca.unraid.net/submit/new)
3. Point the repository URL at this repo (or a dedicated `unraid-ca-templates` repo containing `templates/unraid/`)
4. Run **Validate**, then **Scan**
5. Wait for moderator review (typically 1–2 weeks)

Checklist before submitting:

- [ ] `Repository` in each XML points to a valid image (`ghcr.io/drytrix/timetracker:latest`, `postgres:16-alpine`)
- [ ] `TemplateURL` in each XML points to the raw GitHub URL for that file
- [ ] `Support`, `Project`, and `Overview` fields are filled in
- [ ] `WebUI` is set to `http://[IP]:[PORT:8080]/` on the app template
- [ ] Tested on a clean Unraid install

---

## Cloud platforms (PaaS)

### Render

One-click Blueprint deploy (PostgreSQL + web service from GHCR image):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/drytrix/TimeTracker)

Blueprint file: [`render.yaml`](../../../render.yaml)

### Railway

1. Create a new project at [railway.app](https://railway.app)
2. Add a **PostgreSQL** plugin
3. Add a **Docker image** service: `ghcr.io/drytrix/timetracker:latest`
4. Set environment variables (see [`railway.toml`](../../../railway.toml))
5. Set `DATABASE_URL` from the Postgres plugin connection string

### Fly.io

```bash
# Requires external Postgres (Fly Postgres, Neon, etc.)
fly launch --no-deploy --image ghcr.io/drytrix/timetracker:latest
fly secrets set SECRET_KEY="$(openssl rand -hex 32)" DATABASE_URL="postgresql://..."
fly deploy
```

Config: [`fly.toml`](../../../fly.toml)

### Coolify

1. In Coolify, create a new **Docker Compose** resource
2. Set **Repository URL** to `https://github.com/drytrix/TimeTracker`
3. Set **Compose file** to `docker-compose.nas.yml`
4. Add environment variable `SECRET_KEY` (generate with `openssl rand -hex 32`)
5. Deploy

Coolify pulls the compose file from Git and uses the prebuilt GHCR image — no local build.

---

## Desktop and mobile clients

Server Docker images do not include desktop or mobile apps. Client binaries are published on [GitHub Releases](https://github.com/drytrix/TimeTracker/releases) when CI builds succeed.

Build from source: see [`desktop/README.md`](../../../desktop/README.md) and [`mobile/README.md`](../../../mobile/README.md).

---

## Official NAS app stores (future)

QNAP App Center and Synology Package Center require native packages (QPKG/SPK), not Docker Compose alone. Until those packages exist, use:

- [NAS Deployment Guide](NAS_DEPLOYMENT.md) — Container Station / Container Manager
- This page — compose file + Docker image

Track demand via GitHub issues labeled `platform:nas` before investing in native packaging.

---

## Maintainer: updating distribution listings

On each release, maintainers should:

1. Verify GHCR and Docker Hub images published (CI: `cd-release.yml`)
2. Update Docker Hub description from [`docker/hub-README.md`](../../../docker/hub-README.md)
3. Confirm GitHub Release includes `docker-compose.nas.yml`
4. Re-test Portainer template URL and Unraid XML if compose changed

See [Release Process](RELEASE_PROCESS.md) for the full checklist.

---

## Related documentation

- [NAS Deployment Guide](NAS_DEPLOYMENT.md)
- [Portainer Deployment Guide](PORTAINER_DEPLOYMENT.md)
- [Docker Public Setup](../configuration/DOCKER_PUBLIC_SETUP.md)
- [Official Builds](OFFICIAL_BUILDS.md)
