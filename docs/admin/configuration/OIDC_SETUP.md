## OpenID Connect (OIDC) Setup Guide

This guide explains how to enable Single Sign-On (SSO) with OpenID Connect for TimeTracker. OIDC is optional; you can run with local login only, OIDC only, both, or combined with LDAP using `AUTH_METHOD=all` (see [LDAP Setup](LDAP_SETUP.md)).

### Quick Summary

- Set `AUTH_METHOD=oidc` (SSO only), `AUTH_METHOD=both` (SSO + local password), or `AUTH_METHOD=all` (local + SSO + LDAP; LDAP is documented separately).
- Configure `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `OIDC_REDIRECT_URI`.
- Optional: Configure admin mapping via `OIDC_ADMIN_GROUP` or `OIDC_ADMIN_EMAILS`.
- Restart the app. The login page will show an “Sign in with SSO” button when enabled.

### Prerequisites

- A running TimeTracker instance (Docker or local).
- An OIDC provider (e.g., Azure AD, Okta, Keycloak, Auth0, Google Workspace).
- A client application registered at your IdP with Authorization Code flow enabled.

### 1) Application URLs

You will need these URLs when creating the OIDC client at your Identity Provider:

- Authorization callback (Redirect URI):
  - `https://<your-app-host>/auth/oidc/callback`
- Post-logout redirect (optional):
  - `https://<your-app-host>/`

Make sure your external URL and protocol (HTTP/HTTPS) match how users access the app. Behind a reverse proxy, ensure the proxy sets `X-Forwarded-Proto` so redirects/cookies work correctly.

### 2) Required Environment Variables

Add these to your environment (e.g., `.env`, Docker Compose, or Kubernetes Secrets):

```
AUTH_METHOD=oidc            # Options: none | local | oidc | ldap | both | all (see section 5; LDAP: LDAP_SETUP.md)

# Core OIDC settings
OIDC_ISSUER=https://idp.example.com/realms/your-realm
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://your-app.example.com/auth/oidc/callback

# Scopes and claims (defaults are usually fine)
OIDC_SCOPES=openid profile email
OIDC_USERNAME_CLAIM=preferred_username
OIDC_FULL_NAME_CLAIM=name
OIDC_EMAIL_CLAIM=email
OIDC_GROUPS_CLAIM=groups

# Optional admin mapping
OIDC_ADMIN_GROUP=timetracker-admins      # If your IdP issues a groups claim
OIDC_ADMIN_EMAILS=alice@company.com,bob@company.com

# Optional: RP-Initiated Logout (set only if your provider supports end_session_endpoint)
# If unset, users will be logged out locally and redirected to TimeTracker's login page.
# If set, TimeTracker will redirect to the provider's logout endpoint after local logout.
OIDC_POST_LOGOUT_REDIRECT_URI=https://your-app.example.com/

# Optional: Advanced DNS resolution and metadata fetch configuration
# DNS resolution strategy: "auto" (try socket then getaddrinfo), "socket", "getaddrinfo", or "both" (default: "auto")
OIDC_DNS_RESOLUTION_STRATEGY=auto
# TTL for IP address cache in seconds (default: 300 = 5 minutes)
OIDC_IP_CACHE_TTL=300
# Use IP address directly if DNS resolution succeeds via socket (default: true)
OIDC_USE_IP_DIRECTLY=true
# Try Docker internal service names if external DNS fails (default: true)
OIDC_USE_DOCKER_INTERNAL=true
# Background metadata refresh interval in seconds (default: 3600 = 1 hour, 0 to disable)
OIDC_METADATA_REFRESH_INTERVAL=3600
# Timeout for each metadata fetch attempt (default: 10 seconds)
OIDC_METADATA_FETCH_TIMEOUT=10
# Number of retry attempts (default: 3)
OIDC_METADATA_RETRY_ATTEMPTS=3
# Delay between retries in seconds (default: 2)
OIDC_METADATA_RETRY_DELAY=2
```

Also ensure the standard app settings are configured (database, secret key, etc.). See `env.example` for a complete template.

### 3) Provider-Specific Notes

- Azure AD (Entra ID)
  - Issuer: `https://login.microsoftonline.com/<tenant-id>/v2.0`
  - Use `openid profile email` scopes.
  - Preferred username commonly available via `preferred_username` or `upn`.
  - Group claims may need to be enabled in App Registration → Token configuration.

- Okta
  - Issuer: `https://<yourOktaDomain>/oauth2/default`
  - Add claims for `groups` if you want role mapping by group.

- Keycloak
  - Issuer: `https://<keycloak>/realms/<realm>`
  - You can map custom claims and groups in the realm client.

- Google Workspace
  - Issuer: `https://accounts.google.com`
  - Groups generally not available by default; prefer admin mapping via emails.

- Authentik
  - TimeTracker does **not** support JWE-encrypted ID tokens. If using Authentik, leave the **Encryption Key** field **empty** on the OAuth2/OpenID provider. If an Encryption Key is set, Authentik sends the ID token as JWE and login will fail with an error about unsupported algorithm or encrypted tokens.

### 4) Behavior and Mapping

- When a user completes SSO:
  - We parse ID token and/or fetch userinfo to get `preferred_username`, `name`, `email` and optional `groups`.
  - We upsert a local user record with `username`, `full_name`, `email`, and store OIDC linkage in `oidc_issuer` + `oidc_sub`.
  - If `ALLOW_SELF_REGISTER=true` (default), unknown users are created on first login; otherwise they’re blocked.
  - Admin role can be granted if user’s groups contains `OIDC_ADMIN_GROUP` or if user’s email is in `OIDC_ADMIN_EMAILS`.

### 5) Authentication Methods

The `AUTH_METHOD` environment variable controls how users authenticate with TimeTracker. It supports these options:

#### Available Options

1. **`none`** - No password authentication (username only)
   - Users log in with just their username, no password required
   - No password field shown on login page
   - Useful for trusted internal networks or development environments
   - Self-registration works (users can create accounts by entering any username)
   - **Note:** This is the least secure option and should only be used in trusted environments

2. **`local`** - Password authentication required (default)
   - Users must set and use a password to log in
   - Password field is shown on login page
   - Users without passwords are prompted to set one in their profile
   - Passwords can be changed in user profile settings
   - Self-registration works (new users must provide a password during registration)
   - Works for both regular login and kiosk mode
   - **Note:** This is the recommended option for most installations

3. **`oidc`** - OIDC/Single Sign-On only
   - Users authenticate via your OIDC provider (e.g., Azure AD, Okta, Keycloak)
   - Local login form is hidden
   - `/login` redirects directly to OIDC login
   - Requires OIDC configuration (see Required Environment Variables above)
   - Self-registration still works if `ALLOW_SELF_REGISTER=true` (users created on first OIDC login)

4. **`both`** - OIDC + Local password authentication (no LDAP)
   - Shows both SSO button and local login form
   - Users can choose to log in with OIDC or use username/password
   - Local authentication requires passwords (same as `local` mode)
   - Best for organizations transitioning to SSO or supporting mixed authentication
   - Requires OIDC configuration to be set up

5. **`ldap`** - LDAP directory authentication only
   - Same username/password form; no OIDC button
   - Users are created or updated from the directory after a successful bind
   - Configure all `LDAP_*` variables; see [LDAP Setup](LDAP_SETUP.md) and `env.example`

6. **`all`** - Local + OIDC + LDAP
   - SSO button plus username/password form; LDAP is tried when appropriate (after local password failure for non-LDAP accounts, or as primary for LDAP-only accounts)
   - Requires OIDC env vars when using SSO, and LDAP env vars for directory login
   - See [LDAP Setup](LDAP_SETUP.md) for LDAP-specific behaviour

#### Summary Table

| Mode | Password field | OIDC | LDAP | Self-register (local) | Typical use |
|------|----------------|------|------|------------------------|-------------|
| `none` | Optional | ❌ | ❌ | ✅ | Trusted / dev |
| `local` | Yes | ❌ | ❌ | ✅ | Default self-hosted |
| `oidc` | N/A (redirect) | ✅ | ❌ | ✅ (first SSO) | SSO only |
| `both` | Yes | ✅ | ❌ | ✅ | SSO + local |
| `ldap` | Yes | ❌ | ✅ | ❌ | Directory only |
| `all` | Yes | ✅ | ✅ | ✅ | Enterprise: all methods |

### 6) Docker Compose Example

```yaml
services:
  app:
    image: ghcr.io/your-org/timetracker:latest
    environment:
      - AUTH_METHOD=oidc
      - OIDC_ISSUER=https://idp.example.com/realms/your-realm
      - OIDC_CLIENT_ID=${OIDC_CLIENT_ID}
      - OIDC_CLIENT_SECRET=${OIDC_CLIENT_SECRET}
      - OIDC_REDIRECT_URI=https://your-app.example.com/auth/oidc/callback
      - OIDC_SCOPES=openid profile email
      - OIDC_ADMIN_GROUP=timetracker-admins
      - OIDC_POST_LOGOUT_REDIRECT_URI=https://your-app.example.com/
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
    # ... other settings like ports/volumes
```

### 7) Security Recommendations

- Always use HTTPS in production.
- Set secure cookies: `SESSION_COOKIE_SECURE=true` in production.
- Keep the client secret in a secret store (not committed to git).
- Restrict `ADMIN_*` variables to trusted values only.
- Ensure your reverse proxy forwards `X-Forwarded-Proto` so redirects use HTTPS URLs.

### 8) Troubleshooting

- “SSO button doesn’t appear”
  - Check `AUTH_METHOD`. Must be `oidc`, `both`, or `all` (SSO is not shown for `local`, `ldap`, or `none`).

- “Redirect URI mismatch”
  - The `OIDC_REDIRECT_URI` must exactly match the value registered at your IdP.

- “Invalid token / missing claims”
  - Confirm scopes and claim names. Override with `OIDC_*_CLAIM` envs if your IdP uses different names.

- “User is not admin”
  - Verify `OIDC_ADMIN_GROUP` matches the group claim value, or add the user’s email to `OIDC_ADMIN_EMAILS`.

- **“SSO failed” with “unsupported algorithm” or “encrypted ID token” in logs**
  - The IdP is sending an encrypted ID token (JWE). TimeTracker does not support JWE-encrypted ID tokens. Disable ID token encryption at the provider. For Authentik, clear the **Encryption Key** on the OAuth2/OpenID provider so it returns a signed (e.g. RS256) JWT instead.

- "Logout keeps me signed in" or "Logout redirects to provider error page"
  - Not all IdPs support RP-Initiated Logout (end-session). If your provider doesn't support it (e.g., Authelia), **do not set** `OIDC_POST_LOGOUT_REDIRECT_URI`. TimeTracker will then perform local logout only and redirect to the login page.
  - If your provider supports end-session and you want to log out from the IdP too, set `OIDC_POST_LOGOUT_REDIRECT_URI` to your desired post-logout landing page.

- **Redirect loop / callback returns to login**
  - The same session cookie must be sent on the callback request (when the IdP redirects the user back to TimeTracker). If the session is missing or different, token exchange fails and the user is sent back to login in a loop.
  - **Cookie size**: Flask uses cookie-based session by default. If the session cookie is too large (e.g. over ~4KB), the browser may drop or truncate it. Consider reducing session data or using server-side session storage (e.g. Flask-Session with Redis) if you already use Redis for cache. TimeTracker does not set `SESSION_TYPE` by default (sessions are cookie-based).
  - **Cookie attributes**: Ensure `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`, and domain match how users access the app (e.g. HTTPS, same domain).
  - **Proxy headers**: Behind a reverse proxy, ensure `X-Forwarded-Proto` and `X-Forwarded-Host` are set correctly so redirect URLs and cookies use the same host/scheme the user sees.
  - **Callback URL**: The callback URL must match exactly (no trailing slash, same scheme and host) between TimeTracker (`OIDC_REDIRECT_URI`) and the IdP client configuration.
  - **Logs**: TimeTracker logs a line like `OIDC callback redirect to login: reason=...` before each redirect to login. Use this to see the exact cause (e.g. `reason=token_exchange_failed` for session/state issues, `reason=unsupported_algorithm_or_jwe` for encrypted/unsupported ID tokens, `reason=missing_issuer_sub` for claim issues).

### 9) Routes Reference

- Local login page: `GET /login` (POST for username form when enabled)
- Start OIDC login: `GET /login/oidc`
- OIDC callback: `GET /auth/oidc/callback`
- Logout: `GET /logout` (tries provider end-session if available)

### 10) Database Changes

Relevant columns on `users` for SSO and account linking include:

- `email` (nullable)
- `oidc_issuer`, `oidc_sub` (nullable), with a unique constraint on `(oidc_issuer, oidc_sub)` where applicable
- `auth_provider` (`local`, `oidc`, or `ldap`) — set automatically from the login path; used to avoid local password login for LDAP-managed users when `AUTH_METHOD=all`

If your DB was not migrated automatically, run your usual migration flow (e.g. `flask db upgrade` / Alembic).

#### Advanced: DNS resolution (OIDC metadata)

If you're experiencing DNS resolution issues (especially in Docker environments), TimeTracker includes enhanced DNS resolution for OIDC metadata:

- **Multiple DNS strategies**: Automatically tries different resolution methods
- **IP address caching**: Reduces lookup overhead
- **Docker network detection**: Tries internal service names when external DNS fails
- **Background refresh**: Keeps metadata current

See [TROUBLESHOOTING_OIDC_DNS.md](../../TROUBLESHOOTING_OIDC_DNS.md) for detailed steps.

### 11) Support

If you run into issues, capture the application logs (including the IdP error page if any) and verify your env vars. Most problems are due to a mismatch in redirect URI, missing scopes/claims, or proxy/HTTPS configuration.
