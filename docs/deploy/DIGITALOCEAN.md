# Deploy TimeTracker on DigitalOcean App Platform

One-click deploy uses the Deploy to DigitalOcean button and [`.do/deploy.template.yaml`](../../.do/deploy.template.yaml).

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/DRYTRIX/TimeTracker/tree/develop)

The Deploy button points at the `develop` branch (repo default) so the template is available as soon as it lands. After the file is on `main`, you can switch the button URL to `/tree/main` for release-only deploys.

## What you get

- Web service from Docker Hub image `drytrix/timetracker:latest`
- **Dev Database** (PostgreSQL) — suitable for trials and small demos
- Env: `SECRET_KEY` (change at create time), `DATABASE_URL` bound from the Dev DB, `REDIS_ENABLED=false`

## After deploy

1. Open the App Platform URL.
2. Create the admin account on first visit (or follow the setup wizard).
3. For real production: migrate to a **managed Postgres** cluster, attach persistent storage for uploads, and set a strong `SECRET_KEY`. Dev Databases are not for durable production data.

## Manual deploy (same image)

1. Create an App Platform app from the Docker Hub image `drytrix/timetracker:latest` (or `ghcr.io/drytrix/timetracker:latest`).
2. Add a Postgres database and bind `DATABASE_URL`.
3. Set `SECRET_KEY`, `FLASK_ENV=production`, `AUTH_METHOD=local`, `REDIS_ENABLED=false`.
4. HTTP port **8080**, health check **`/_health`**.

## Related

- [Distribution Guide](../admin/deployment/DISTRIBUTION.md)
- [Render Blueprint](RENDER.md) (managed Postgres Blueprint alternative)
