# TimeTracker — Unraid Community Applications templates

Clean template-only branch for [Unraid CA](https://ca.unraid.net/) submission.

Submit this repository with branch **`unraid-ca`** (not `main`/`develop`). Those branches contain Android and other XML that CA flags as `not_unraid_application`.

## Apps

1. **TimeTracker-DB** — PostgreSQL 16 (`postgres:16-alpine`) on network `timetracker`
2. **TimeTracker** — `ghcr.io/drytrix/timetracker:latest` (deploy after DB; set `SECRET_KEY`)

Application source: https://github.com/DRYTRIX/TimeTracker

## Note on “duplicate Docker apps”

The DB template uses the official `postgres:16-alpine` image, which already exists in CA. That triggers a duplicate warning for moderator review; it is intentional so TimeTracker ships a matching DB + custom network.
