# Running Multiple TimeTracker Instances

TimeTracker is designed as **one company, many users**: a single instance shares one company profile (Settings → Company), one email sender, and one namespace for clients, projects, and invoices.

If you need **fully independent companies** — each with its own branding, invoice letterhead, SMTP identity, and data — run **one TimeTracker instance per company**. Roles and permissions can restrict what users see within a single org, but they cannot split company-level settings or email identity across tenants.

## When to use multiple instances

| Goal | Recommended approach |
|------|---------------------|
| One business, employees see only their assigned clients/projects | Single instance + [Subcontractor role](SUBCONTRACTOR_ROLE.md) or [own-scope permissions](ADVANCED_PERMISSIONS.md) |
| One business, users should not see each other's personal projects/clients | Single instance + RBAC own-scope (see [Advanced Permissions](ADVANCED_PERMISSIONS.md)) |
| **Several independent companies** (own invoice data, email sender, full admin control) | **Separate instance per company** (this guide) |

## Docker Compose pattern

Copy [`docker-compose.example.yml`](../docker-compose.example.yml) once per company and give each stack **unique** values:

| Setting | Instance A | Instance B | Instance C |
|---------|------------|------------|------------|
| Host port | `8080:8080` | `8081:8080` | `8082:8080` |
| `container_name` (app) | `timetracker-app-a` | `timetracker-app-b` | `timetracker-app-c` |
| `container_name` (db) | `timetracker-db-a` | `timetracker-db-b` | `timetracker-db-c` |
| Named volumes | `app_data_a`, `db_data_a`, … | `app_data_b`, … | `app_data_c`, … |
| `SECRET_KEY` | Unique per instance | Unique per instance | Unique per instance |
| `.env` file | `.env.company-a` | `.env.company-b` | `.env.company-c` |

Example for a second instance (`docker-compose.company-b.yml`):

```yaml
services:
  app:
    image: ghcr.io/drytrix/timetracker:latest
    container_name: timetracker-app-b
    env_file:
      - .env.company-b
    ports:
      - "8081:8080"
    volumes:
      - app_data_b:/data
      - app_uploads_b:/app/app/static/uploads
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    container_name: timetracker-db-b
    env_file:
      - .env.company-b
    volumes:
      - db_data_b:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  app_data_b:
  app_uploads_b:
  db_data_b:
```

Start each stack from the project root:

```bash
# Generate a unique SECRET_KEY per instance
python -c "import secrets; print(secrets.token_hex(32))"

docker compose -f docker-compose.example.yml --env-file .env.company-a up -d
docker compose -f docker-compose.company-b.yml --env-file .env.company-b up -d
```

Access:

- Company A: `http://your-server:8080`
- Company B: `http://your-server:8081`

See [Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md) for full environment variable reference.

## Per-instance setup checklist

For each instance:

1. Set a unique **`SECRET_KEY`** in that instance's `.env` (required in production).
2. Log in as admin and configure **Settings → Company** (legal name, address, VAT, logo).
3. Configure **email / SMTP** for that company's sender address ([Email Configuration](admin/configuration/EMAIL_CONFIGURATION.md)).
4. Create users; each person can be the sole admin of their own instance if desired.
5. Optionally set **`TZ`** and **`CURRENCY`** per instance if companies operate in different regions.

Instances do not share databases or uploads. Back up each stack's volumes separately.

## Reverse proxy (optional)

To expose friendly hostnames instead of ports, point subdomains at the correct backend port:

- `tt-a.example.com` → `http://127.0.0.1:8080`
- `tt-b.example.com` → `http://127.0.0.1:8081`

Use your preferred reverse proxy (nginx, Caddy, Traefik). For HTTPS, see [HTTPS setup guides](admin/security/README_HTTPS.md).

## RBAC is not a substitute for multi-company

Within a **single** instance, [Advanced Permissions](ADVANCED_PERMISSIONS.md) and the [Subcontractor role](SUBCONTRACTOR_ROLE.md) can limit which clients, projects, and tasks a user sees. That suits one organization with scoped employees or subcontractors.

It does **not** provide:

- Separate company profiles or invoice letterheads
- Independent SMTP / “from” addresses per company
- Hard isolation of all entity types and settings as separate tenants

For those requirements, use separate instances as described above.

## Related documentation

- [Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md) — Single-instance deployment
- [Advanced Permissions](ADVANCED_PERMISSIONS.md) — Roles within one organization
- [Subcontractor role](SUBCONTRACTOR_ROLE.md) — Client/project assignment within one org
- [Email Configuration](admin/configuration/EMAIL_CONFIGURATION.md) — Per-instance mail settings
