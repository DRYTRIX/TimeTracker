# NAS Deployment Guide (QNAP, Synology, Portainer)

This guide explains how to install TimeTracker on a NAS or homelab server using Docker — **without cloning the repository**. It uses the self-contained [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) stack, which pulls a prebuilt image and stores all data in Docker volumes.

## Overview

| What you get | Details |
|--------------|---------|
| **Containers** | `app` (TimeTracker) + `db` (PostgreSQL 16) |
| **Image** | `ghcr.io/drytrix/timetracker:latest` (multi-arch: amd64 + arm64) |
| **Access** | `http://<your-nas-ip>:8080` (HTTP, LAN-friendly) |
| **Data** | Named Docker volumes only — no host folder setup required |

**Supported platforms:** QNAP (Container Station), Synology (Container Manager), Portainer (Unraid, TrueNAS, etc.), or any host with Docker Compose.

## Prerequisites

- Docker and Docker Compose available on your NAS (most modern NAS devices include this)
- **2 GB+ RAM** free for the containers
- Port **8080** available (or choose another port — see [Port conflicts](#port-conflicts))
- Outbound internet access so Docker can pull images from GitHub Container Registry

## Before you start: generate a SECRET_KEY

TimeTracker requires a `SECRET_KEY` (32+ characters) for sessions and CSRF protection. You only need to set this once.

**On your computer (any OS with OpenSSL):**

```bash
openssl rand -hex 32
```

**On QNAP or Synology via SSH:**

```bash
openssl rand -hex 32
```

Copy the output — you will paste it as the `SECRET_KEY` environment variable when deploying the stack.

> **Alternative (if you have Python):** `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Option 1: QNAP Container Station

QNAP models with Intel/AMD (x86) or ARM64 processors are supported. The published image includes both architectures.

1. Open **Container Station** on your QNAP.
2. Go to **Applications** (or **Create** → **Application** depending on your QTS version).
3. Choose **Create** and select the **YAML** / **Compose** editor.
4. Copy the full contents of [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) from the [GitHub repository](https://github.com/drytrix/TimeTracker/blob/main/docker-compose.nas.yml) and paste into the editor.
5. Add environment variables (look for **Environment**, **Advanced settings**, or **.env** in Container Station):
   - `SECRET_KEY` = *(paste the value from openssl above)*
   - Optional: `TZ` = your timezone (e.g. `Europe/Brussels`, `America/New_York`)
   - Optional: `HTTP_PORT` = `8080` (change if 8080 is already in use)
6. Click **Create** / **Deploy**.
7. Wait 1–2 minutes for the first start (database migrations run automatically).
8. Open **`http://<qnap-ip>:8080`** in your browser.

**First login:** The first user you create becomes admin (or use `ADMIN_USERNAMES=admin` in environment variables).

---

## Option 2: Synology Container Manager

Works on DSM 7.2+ with Container Manager (formerly Docker package). Supports both x86 and ARM Synology models (e.g. DS920+, DS224+, RS models).

1. Open **Container Manager** on your Synology NAS.
2. Go to **Project** → **Create**.
3. Set a project name (e.g. `timetracker`).
4. Paste the contents of [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) into the **Web editor**.
5. In the environment / `.env` section, add:
   ```bash
   SECRET_KEY=paste-your-generated-key-here
   TZ=Europe/Brussels
   HTTP_PORT=8080
   ```
6. Click **Done** / **Build** (Synology will pull images — no local build is required).
7. Wait until both containers (`timetracker-app`, `timetracker-db`) show as running.
8. Open **`http://<synology-ip>:8080`**.

> **Tip:** If Synology warns about elevated privileges, the default compose file does not require `privileged` mode. You can decline unless your DSM version insists on it for volume access.

---

## Option 3: Portainer (Unraid, TrueNAS, generic Docker host)

Portainer is common on Unraid and other homelab setups. For **web editor** deployments, always use `docker-compose.nas.yml` — do not paste `docker-compose.remote.yml` (it requires local build contexts and host folder mounts).

1. In Portainer, go to **Stacks** → **Add stack**.
2. Name the stack `timetracker`.
3. Choose **Web editor**.
4. Paste the contents of [`docker-compose.nas.yml`](../../../docker-compose.nas.yml).
5. Scroll to **Environment variables** and add:
   - `SECRET_KEY` = your generated key
   - `TZ`, `CURRENCY`, `HTTP_PORT` as needed
6. Click **Deploy the stack**.
7. Open **`http://<host-ip>:8080`**.

For Portainer-specific HTTPS or repository-based deployment, see [Portainer Deployment Guide](PORTAINER_DEPLOYMENT.md).

---

## Option 4: SSH + Docker Compose (no NAS UI)

If you prefer the command line on your NAS or a Linux server:

```bash
# Download the NAS compose file (no git clone needed)
curl -fsSL -o docker-compose.nas.yml \
  https://raw.githubusercontent.com/drytrix/TimeTracker/main/docker-compose.nas.yml

# Create a minimal .env file
cat > .env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
TZ=Europe/Brussels
HTTP_PORT=8080
EOF

# Start TimeTracker
docker compose -f docker-compose.nas.yml up -d
```

Open **`http://<server-ip>:8080`**.

---

## Environment variables reference

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random string, 32+ characters. Generate with `openssl rand -hex 32`. |

### Recommended

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `Europe/Brussels` | Your timezone |
| `CURRENCY` | `EUR` | Default currency |
| `ADMIN_USERNAMES` | `admin` | Username treated as admin on first login |
| `HTTP_PORT` | `8080` | Host port mapped to the app |

### Optional (database)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `timetracker` | Database name |
| `POSTGRES_USER` | `timetracker` | Database user |
| `POSTGRES_PASSWORD` | `timetracker` | Database password — change for shared networks |

---

## Common pitfalls

### First boot takes 1–2 minutes

On first start, TimeTracker waits for PostgreSQL, runs database migrations, and seeds default settings. The health check has a **40-second start period**. The `app` container may briefly show as **unhealthy** — this is normal. Check logs if it stays unhealthy for more than 3 minutes.

### Port conflicts

If port 8080 is already used (common on NAS devices running other apps):

```bash
HTTP_PORT=8180
```

Redeploy the stack and use `http://<nas-ip>:8180`.

### Accessing via LAN IP

The NAS compose file uses **HTTP-safe cookie and CSRF settings** by default, so logging in via `http://192.168.x.x:8080` works without extra configuration. You do **not** need to disable CSRF manually for LAN access.

### HTTPS / reverse proxy

For production or remote access, put TimeTracker behind your NAS reverse proxy instead of exposing plain HTTP:

- **QNAP:** Control Panel → Web Server → Virtual Host, or use the built-in reverse proxy in QuFirewall / QTS apps
- **Synology:** Control Panel → Login Portal → Advanced → Reverse Proxy

Point the proxy to `http://localhost:8080` (or your `HTTP_PORT`). If you terminate HTTPS at the proxy, you may need to set these environment variables on the `app` service:

```bash
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Image pull failures

Ensure your NAS can reach `ghcr.io`. Some networks block GitHub Container Registry. If pull fails, try from SSH:

```bash
docker pull ghcr.io/drytrix/timetracker:latest
```

### ARM vs x86

Official images are built for **linux/amd64** and **linux/arm64**. Most QNAP and Synology models from 2020 onward are supported. Very old 32-bit ARM devices (`arm/v7`) are **not** supported by the published images.

### Updating TimeTracker

1. In your NAS UI or via SSH, pull the latest image:
   ```bash
   docker compose -f docker-compose.nas.yml pull
   docker compose -f docker-compose.nas.yml up -d
   ```
2. Migrations run automatically on startup — no manual steps needed.

### Backing up your data

Data lives in Docker volumes: `app_data`, `app_uploads`, `app_logs`, `db_data`.

**Database backup (via SSH):**

```bash
docker exec timetracker-db pg_dump -U timetracker timetracker > timetracker-backup.sql
```

**Volume backup:** Use your NAS backup tools or Portainer's volume backup feature. See [Backup and Restore](../BACKUP_AND_RESTORE.md) for full procedures.

---

## What this stack does *not* include

To keep NAS installs simple, `docker-compose.nas.yml` intentionally omits:

- **nginx / HTTPS** — use your NAS reverse proxy instead, or deploy the full [Docker Compose setup](../configuration/DOCKER_COMPOSE_SETUP.md) on a server with git clone
- **Peppol bridge** — optional e-invoicing; requires additional services and API keys
- **Ollama / AI helper** — large download (~5 GB); enable separately if needed
- **Redis** — not required; the app runs without it by default

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Stack fails immediately with SECRET_KEY error | Set `SECRET_KEY` in environment variables |
| App stays unhealthy > 3 min | Check logs: `docker logs timetracker-app` |
| Can't log in / CSRF errors | Ensure you're using HTTP (not HTTPS) unless reverse proxy vars are set |
| Port already allocated | Change `HTTP_PORT` to e.g. `8180` |
| Database connection errors | Ensure `timetracker-db` is healthy; wait for Postgres `start_period` |

More help:

- [Docker Startup Troubleshooting](../configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)
- [Portainer Deployment Guide](PORTAINER_DEPLOYMENT.md)
- [GitHub Issues](https://github.com/drytrix/TimeTracker/issues)

---

## Related documentation

- [`docker-compose.nas.yml`](../../../docker-compose.nas.yml) — NAS compose file (copy-paste ready)
- [INSTALLATION.md](../../../INSTALLATION.md) — Full installation guide (git clone + HTTPS)
- [Docker Public Setup](../configuration/DOCKER_PUBLIC_SETUP.md) — Production with published images
- [Backup and Restore](../BACKUP_AND_RESTORE.md) — Data backup procedures
