# TimeTracker Installation

This guide walks you through installing and running TimeTracker. For a quick overview, see the [README Quick Start](README.md#-quick-start).

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git**
- **2GB+ RAM** for Docker containers
- **Ports:** 80/443 (HTTPS) or 8080 (HTTP)

Install Docker for your platform: [Docker Installation Guide](https://docs.docker.com/get-docker/).

## Quick Install (Docker with HTTPS)

1. Clone the repository:

   ```bash
   git clone https://github.com/drytrix/TimeTracker.git
   cd TimeTracker
   ```

2. Create your environment file from the template:

   ```bash
   cp env.example .env
   ```

3. Edit `.env` and set at least:
   - **SECRET_KEY** — Required for sessions and CSRF. Generate one:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - **TZ** — Your timezone (e.g. `America/New_York`, `Europe/Brussels`).
   - **CURRENCY** — Default currency (e.g. `USD`, `EUR`).

4. Start the stack:

   ```bash
   docker-compose up -d
   ```

5. Open **https://localhost** in your browser. The first run may show a self-signed certificate warning; proceed to continue.

The **first user who logs in** is created as an admin (or use `ADMIN_USERNAMES` in `.env` to predefine admin usernames).

## First Login and Minimal Config

- Log in with the username you configured (e.g. from `ADMIN_USERNAMES`) or the first account you create.
- In **Admin → Settings** you can adjust timezone, currency, and other options.
- See [Getting Started](docs/GETTING_STARTED.md) for initial setup and core workflows.

## Alternative: SQLite Quick Test

To try TimeTracker without PostgreSQL:

```bash
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
docker-compose -f docker/docker-compose.local-test.yml up --build
```

Then open **http://localhost:8080**. No `.env` is required for this compose file. SQLite is for evaluation only; use PostgreSQL for production.

## Production Deployment

For production:

- Use a strong **SECRET_KEY** and keep `.env` out of version control.
- Prefer **PostgreSQL** (included in the default Docker Compose setup).
- Put the app behind HTTPS (reverse proxy or Docker with HTTPS compose).

Detailed steps and options:

- [Docker Compose Setup](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md) — Full configuration and env reference
- [Docker Public Setup](docs/admin/configuration/DOCKER_PUBLIC_SETUP.md) — Production deployment with published images

## Troubleshooting

| Problem | Documentation |
|--------|----------------|
| Docker won’t start | [Docker Startup Troubleshooting](docs/admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md) |
| Database connection errors | [Database Connection Troubleshooting](docker/TROUBLESHOOTING_DB_CONNECTION.md) |
| CSRF or session errors | [CSRF Troubleshooting](docs/admin/security/CSRF_TROUBLESHOOTING.md) |
| Port already in use | Change ports in your `docker-compose` file or stop the conflicting service |

For more help, see the [Documentation Index](docs/README.md) and [Support](README.md#-support).
