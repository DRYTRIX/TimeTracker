# Deploy TimeTracker on Railway

Railway’s real one-click path is a **published template** (app image + Postgres + variable references), not [`railway.toml`](../../railway.toml) alone.

## One-click (after template is published)

When a marketplace template exists, add this README button (replace `TEMPLATE_CODE`):

```md
[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/TEMPLATE_CODE?utm_medium=integration&utm_source=button&utm_campaign=timetracker)
```

Until then, use **manual deploy** below or publish the template once (maintainer steps).

## Manual deploy (works today)

1. Create a project at [railway.app](https://railway.app).
2. Add **PostgreSQL**.
3. Add a service from Docker image: `ghcr.io/drytrix/timetracker:latest` (or `drytrix/timetracker:latest`).
4. Set variables on the app service:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Reference Postgres `${{Postgres.DATABASE_URL}}` (or the plugin’s `DATABASE_URL`) |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `FLASK_ENV` | `production` |
| `AUTH_METHOD` | `local` |
| `REDIS_ENABLED` | `false` |

5. Healthcheck path: `/_ready` (see [`railway.toml`](../../railway.toml)).
6. Public HTTP networking on port **8080** (Railway sets `PORT`; the image honors it).

## Maintainer: publish a Railway template

Do this once in the Railway dashboard so the Deploy button can point at a stable template URL.

1. **New project** → add PostgreSQL → add Docker image service `ghcr.io/drytrix/timetracker:latest`.
2. Wire variables as in the table above (`SECRET_KEY` = `${{secret(64, "abcdef0123456789")}}` in the template composer).
3. Settings → **Generate Template from Project** (or Workspace → Templates → New Template with the same services).
4. Fill name **TimeTracker**, description: self-hosted time tracking + Peppol invoicing, link demo + GitHub.
5. **Publish** to the marketplace.
6. Copy the template share URL / code and update:
   - [README.md](../../README.md) Install options (Deploy on Railway button)
   - [DISTRIBUTION.md](../admin/deployment/DISTRIBUTION.md) Railway section
   - Replace `TEMPLATE_CODE` in this file’s one-click section
7. Optional: add a live demo project on the template overview.

### Template composer checklist

- [ ] App source: Docker image `ghcr.io/drytrix/timetracker:latest`
- [ ] Postgres plugin included
- [ ] `DATABASE_URL` → Postgres connection reference
- [ ] `SECRET_KEY` → `${{secret(64, "abcdef0123456789")}}`
- [ ] `FLASK_ENV=production`, `AUTH_METHOD=local`, `REDIS_ENABLED=false`
- [ ] Healthcheck `/_ready`, timeout ≥ 300s
- [ ] Public HTTP enabled
- [ ] Published + README button updated

## Related

- [Distribution Guide](../admin/deployment/DISTRIBUTION.md)
- [DigitalOcean one-click](DIGITALOCEAN.md)
- [Render Blueprint](RENDER.md)
