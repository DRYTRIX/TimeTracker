# Multi-tenant data model

Design options for hosting **multiple organizations** (tenants) on one TimeTracker deployment—typical SaaS or managed-hosting scenario.

**Recommendation:** start with **row-level tenancy** (`organization_id` on shared tables), strict query scoping in services/repositories, and a path to **schema-per-tenant** only for large isolated customers.

## Terminology

| Term | Meaning |
|------|---------|
| **Tenant / organization** | Billing and data-isolation boundary (company using TimeTracker) |
| **User** | Belongs to one primary org; cross-org access only via explicit membership (future) |
| **Instance** | Single deploy (one database today) |

## Option A: Row-level (`organization_id`)

Every tenant-scoped row carries `organization_id` (FK → `organizations`).

### Pros

- Single migration path from current single-tenant schema.
- One backup, one connection pool, simpler ops.
- Cross-tenant analytics for platform operator (if needed).

### Cons

- **Every query** must filter by org; one missed filter is a data leak.
- Noisy migrations touching many tables.
- Harder to offer “dedicated DB” SLAs without export tooling.

### Core tables

| Table | Notes |
|-------|--------|
| `organizations` | `id`, `name`, `slug`, `plan`, `settings_json`, `created_at` |
| `organization_memberships` | `user_id`, `organization_id`, `role`, `is_default` |

Add `organization_id` (NOT NULL after backfill) to: `users`, `projects`, `clients`, `time_entries`, `invoices`, `tasks`, `settings` (split global vs org settings).

### Request context

- Resolve org from: subdomain (`acme.app.example.com`), header (`X-Organization-Id`), or session after login.
- Middleware sets `g.organization_id`; `BaseRepository` applies default filter.

## Option B: Schema-per-tenant (PostgreSQL)

One PostgreSQL schema per tenant (`tenant_acme.*`), shared `public` for platform metadata.

### Pros

- Strong isolation; easier “delete tenant” (DROP SCHEMA).
- Some compliance narratives prefer separate schemas.

### Cons

- Alembic must run **N migrations** or use shared migration runner per schema.
- Connection pooling and search_path management complexity.
- Cross-tenant queries require federation or ETL.

## Option C: Database-per-tenant

Separate database per customer; app routes by hostname to DSN.

### Pros

- Maximum isolation; common for largest enterprise deals.

### Cons

- Operational cost scales linearly; backup/restore per DB.
- Not aligned with current single-`DATABASE_URL` architecture.

## Migration risks (from current single-tenant)

1. **Implicit global data** — `Settings` singleton becomes org-scoped; seed one org and attach all rows.
2. **User uniqueness** — `username` / `email` unique globally today; may become unique per `(organization_id, username)`.
3. **API tokens & webhooks** — must include `organization_id` in scope validation.
4. **Integrations** — OAuth tokens and Slack/Teams configs are per-org.
5. **Background jobs** — schedulers must iterate orgs or partition queues.
6. **File storage** — uploads prefixed with `org_id/` in object storage paths.
7. **Client portal** — custom domains map to `(organization_id, client_id)` (extend `portal_domain.py`).

## Phased rollout

| Phase | Work |
|-------|------|
| 0 | Document + feature flag `MULTI_TENANT_ENABLED=false` (no behavior change) |
| 1 | Add `organizations`, backfill default org id `1`, add nullable `organization_id` |
| 2 | Enforce NOT NULL + repository scoping + tests |
| 3 | Subdomain / admin org switcher |
| 4 | Billing, quotas, org-level settings UI |

## Recommendation summary

| Criterion | Row-level | Schema-per-tenant |
|-----------|-----------|-------------------|
| Time to first SaaS pilot | **Best** | Slow |
| Leak risk if bug | Higher (mitigate with tests + linters) | Lower |
| Enterprise “dedicated” ask | Export + optional DB-per-tenant tier | **Good middle ground** |
| Fits current codebase | **Yes** | Major infra change |

**Ship row-level first** with mandatory `organization_id` in service layer and a CI check that new models include the column. Offer schema-per-tenant or DB-per-tenant only as premium deployment templates, not as the default refactor.

## Related work

- SCIM/SAML: provision users **into** an organization context.
- OAuth apps: register per organization.
- Audit logs: always record `organization_id`.
