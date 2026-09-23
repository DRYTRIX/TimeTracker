# OAuth 2.0 API applications (authorization server)

Design for turning TimeTracker into an **OAuth 2.0 authorization server** so third-party apps (mobile clients, partner integrations, Zapier custom apps) can obtain scoped access tokens instead of long-lived personal API tokens.

This is **foundational design + model stubs** only. Full Authlib wiring, admin UI, and consent screens are follow-up work.

## Goals

- Register **OAuth applications** (confidential or public) with redirect URIs and allowed scopes.
- Support **authorization code + PKCE** for user-delegated access (primary flow for SPAs and mobile).
- Issue **access tokens** that map to existing REST API auth (`require_api_token` scopes) or dedicated OAuth bearer validation.
- Coexist with **personal API tokens** (`ApiToken`) and **OIDC login** (external IdP); do not conflate “login OIDC” with “API OAuth server.”

## Non-goals (phase 1)

- Client credentials grant for machine-only apps (phase 2; can reuse `OAuthApplication` with `grant_types`).
- Dynamic client registration (RFC 7591).
- OpenID Connect identity layer on top of our authorization server.

## Library

- **[Authlib](https://docs.authlib.org/)** Flask integration (`AuthorizationServer`, `ResourceProtector`, SQLAlchemy mixins where applicable).
- Dependency to add in a later PR: `authlib` (not pinned in this scaffolding pass).

## Data model

Implemented as stubs in `app/models/oauth_app.py` (migration **197**).

| Table | Purpose |
|-------|---------|
| `oauth_applications` | Registered client apps |
| `oauth_authorization_codes` | Short-lived codes exchanged at `/oauth/token` |

### `oauth_applications`

| Column | Type | Notes |
|--------|------|--------|
| `id` | int PK | |
| `client_id` | string(64) unique | Public identifier (`tt_app_…`) |
| `client_secret_hash` | string(128) nullable | SHA-256; null for public clients |
| `name` | string(200) | Display name in consent UI |
| `description` | text | Optional |
| `owner_user_id` | FK → `users.id` | Admin or developer who registered the app |
| `redirect_uris` | JSON array | Exact match enforced |
| `allowed_scopes` | text | Comma-separated subset of API scopes |
| `grant_types` | JSON array | Default `["authorization_code"]` |
| `is_confidential` | bool | True → requires `client_secret` at token endpoint |
| `is_active` | bool | Soft disable |
| `created_at` / `updated_at` | datetime | |

### `oauth_authorization_codes`

| Column | Type | Notes |
|--------|------|--------|
| `id` | int PK | |
| `code_hash` | string(128) unique | Store hash only |
| `application_id` | FK → `oauth_applications.id` | |
| `user_id` | FK → `users.id` | Resource owner |
| `redirect_uri` | string(500) | Must match authorize request |
| `scope` | text | Granted scopes |
| `code_challenge` | string(128) nullable | PKCE |
| `code_challenge_method` | string(10) nullable | `S256` |
| `expires_at` | datetime | ~10 minutes |
| `used_at` | datetime nullable | Single use |

Future tables (document only): `oauth_access_tokens`, `oauth_refresh_tokens` (or reuse `ApiToken` with `source=oauth` + `oauth_application_id`).

## Scopes

Align with existing API token scopes (`read:projects`, `write:time_entries`, `read:ai`, etc.). OAuth apps declare `allowed_scopes`; consent UI shows intersection with requested scopes.

Suggested default for new apps: `read:projects,read:time_entries,write:time_entries`.

## Endpoints (target)

Base path prefix: `/oauth` (browser + token) and admin under `/admin/oauth-apps` (future).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/oauth/authorize` | Session (logged-in user) | Authorization endpoint; query: `client_id`, `redirect_uri`, `response_type=code`, `scope`, `state`, PKCE `code_challenge` |
| POST | `/oauth/authorize` | Session | Consent form submit (approve/deny) |
| POST | `/oauth/token` | Client auth (Basic or body) | Exchange code or refresh token |
| POST | `/oauth/revoke` | Client or token bearer | RFC 7009 revoke |
| GET | `/oauth/.well-known/oauth-authorization-server` | Public | Metadata (issuer, endpoints, PKCE methods) |

### Admin / API management (future)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/oauth/applications` | `admin:all` or `manage:oauth_apps` | List apps |
| POST | `/api/v1/oauth/applications` | same | Create app; return `client_secret` once |
| PATCH | `/api/v1/oauth/applications/<id>` | same | Update redirect URIs, scopes, active flag |
| DELETE | `/api/v1/oauth/applications/<id>` | same | Revoke app |

## Security

- Enforce **exact redirect URI** match; no open redirects.
- **PKCE required** for public clients; recommended for all clients.
- Hash secrets and authorization codes at rest (same pattern as `ApiToken.hash_token`).
- Rate-limit `/oauth/token` and `/oauth/authorize` via existing Flask-Limiter.
- Audit log events: `oauth_app.created`, `oauth.consent_granted`, `oauth.token_issued`.

## Integration with existing auth

1. Token endpoint mints a record compatible with `require_api_token` **or** a parallel `require_oauth_bearer` that resolves to `user_id` + scopes.
2. Personal API tokens remain unchanged.
3. OIDC (`AUTH_METHOD=oidc`) continues to authenticate **humans to the web UI**; OAuth server issues **API access** to registered apps.

## Implementation phases

1. **Scaffolding (this PR):** models + migration + this doc.
2. Authlib `AuthorizationServer`, authorize + token routes, PKCE validation.
3. Admin UI + API CRUD for applications.
4. Refresh tokens + client credentials grant (optional).
5. Public developer documentation in `docs/api/OAUTH2.md`.

## References

- RFC 6749 (OAuth 2.0), RFC 7636 (PKCE), RFC 8414 (authorization server metadata)
- Existing: `app/models/api_token.py`, `app/utils/api_auth.py`, `app/routes/admin_api_tokens.py`
