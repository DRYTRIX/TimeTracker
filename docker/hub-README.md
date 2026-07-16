<!-- Published automatically by cd-release.yml — edit this file in the repo, not on Docker Hub. -->

# TimeTracker

Self-hosted time tracking and project management for freelancers, teams, and businesses.

**Docker Hub:** [hub.docker.com/r/drytrix/timetracker](https://hub.docker.com/r/drytrix/timetracker)

> The Docker Hub repository moved from `driesp/timetracker` to **`drytrix/timetracker`**.

## Quick start

```bash
# Pull from Docker Hub
docker pull drytrix/timetracker:latest

# Or use GitHub Container Registry (primary)
docker pull ghcr.io/drytrix/timetracker:latest
```

### NAS / homelab (recommended for QNAP, Synology, Unraid, Portainer)

Download the NAS-friendly compose file — no git clone required:

```bash
curl -fsSL -o docker-compose.nas.yml \
  https://raw.githubusercontent.com/drytrix/TimeTracker/main/docker-compose.nas.yml
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
docker compose -f docker-compose.nas.yml up -d
```

Open `http://<your-server-ip>:8080`

### One-command install script

```bash
curl -fsSL https://raw.githubusercontent.com/drytrix/TimeTracker/main/scripts/deploy-public.sh | bash
```

## Documentation

- **Distribution guide:** https://github.com/drytrix/TimeTracker/blob/main/docs/admin/deployment/DISTRIBUTION.md
- **NAS install:** https://github.com/drytrix/TimeTracker/blob/main/docs/admin/deployment/NAS_DEPLOYMENT.md
- **Full installation:** https://github.com/drytrix/TimeTracker/blob/main/INSTALLATION.md

## Image tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `stable` | Same as latest (non-prerelease) |
| `{{VERSION}}` | Specific version (current release) |
| `develop` | Development build |

## Platforms

- **Architectures:** `linux/amd64`, `linux/arm64`
- **Database:** PostgreSQL 16 (bundled in compose) or external
- **Ports:** 8080 (HTTP) by default

## Links

- **Source:** https://github.com/drytrix/TimeTracker
- **Issues:** https://github.com/drytrix/TimeTracker/issues
- **Website:** https://timetracker.drytrix.com

## License

See the [GitHub repository](https://github.com/drytrix/TimeTracker) for license details.
