# Development Data Seeding

The application can be seeded with rich test data for local development. Seeding **only runs when `FLASK_ENV=development`** and is disabled in production and testing.

## What Gets Seeded

| Category | Data | Default counts |
|----------|------|----------------|
| **Users** | Admin (if missing), dev users `devuser1`–`devuser4` (password: `dev`) | 4 extra users |
| **Clients** | Named clients with contact details and hourly rates | 20 |
| **Projects** | Projects per client (e.g. Website, Mobile App, API) | 4 per client |
| **Tasks** | Tasks per project (todo / in progress / review / done) | 12 per project |
| **Time entries** | Closed entries over the last 120 days, linked to tasks | Up to 1500 |
| **Expenses** | Expense categories (Travel, Meals, etc.), expenses on projects | 7 categories, 50 expenses |
| **Comments** | Internal comments on tasks | 80 |
| **Inventory** | Warehouses, stock items, warehouse stock levels, stock movements | 3 warehouses, 15 items, ~40 movements |
| **Finance** | Currencies (EUR, USD), tax rules (VAT), invoices with line items, payments | 2 currencies, 2 tax rules, 25 invoices, payments on up to 20 invoices |

## How to Run

### Local (no Docker)

Set the environment to development, then run the seed:

```bash
# Required: development only
export FLASK_ENV=development   # Linux/macOS
# or: set FLASK_ENV=development   (Windows CMD)
# or: $env:FLASK_ENV="development" (PowerShell)

# Option A: Flask CLI
flask seed

# Option B: Standalone script (sets FLASK_ENV=development by default when unset)
python scripts/seed-dev-data.py
```

### Docker

From the host, run the seed inside the app container. The image defaults to `FLASK_ENV=production`, so use the wrapper script or pass the env explicitly:

```bash
# Option A: Wrapper script (recommended)
docker compose exec app /app/docker/seed-dev-data.sh

# Option B: Flask CLI with env
docker compose exec -e FLASK_ENV=development app flask seed
```

### Flask seed options

You can tune some counts via CLI options:

```bash
flask seed --users 2 --clients 10 --projects-per-client 3 --tasks-per-project 8 --days-back 60
```

Inventory and finance counts use defaults; to change them, call `run_seed()` from code or extend the CLI (see `app/utils/seed_dev_data.py` and `app/utils/cli.py`).

## When to Use

- After a **database reset** (e.g. `scripts/reset-dev-db.py` or `docker compose exec app python3 /app/scripts/reset-dev-db.py`) to get a full dataset.
- On a **fresh database** (after migrations) to avoid entering data by hand.
- To test **reports, dashboards, and filters** with realistic volume.

## Safety

- The seed **refuses to run** unless `FLASK_ENV=development`. In production it raises an error.
- Running the seed multiple times is **additive**: it skips entities that already exist (e.g. clients by name, invoices by number) and adds new ones where applicable (e.g. more time entries, tasks).

## Files

| File | Purpose |
|------|--------|
| `app/utils/seed_dev_data.py` | Core logic: `run_seed()` and data constants |
| `app/utils/cli.py` | `flask seed` command registration |
| `scripts/seed-dev-data.py` | Standalone script for local or CI |
| `docker/seed-dev-data.sh` | Docker wrapper that sets `FLASK_ENV=development` and runs the Python script |

## Related

- [Database Recovery](../DATABASE_RECOVERY.md) – reset and seed from Docker
- [Docker Compose Setup](../admin/configuration/DOCKER_COMPOSE_SETUP.md) – development seed step in troubleshooting
