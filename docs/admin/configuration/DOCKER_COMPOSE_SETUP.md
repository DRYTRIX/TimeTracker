## Docker Compose Setup Guide

This guide shows how to configure TimeTracker with Docker Compose, including all environment variables, a production-friendly example compose file, and quick-start commands.

### Prerequisites
- Docker and Docker Compose installed
- A `.env` file in the project root

### 1) Create and configure your .env file

Start from the example and edit values:

```bash
cp env.example .env
```

Required for production:
- SECRET_KEY: Generate a strong key: `python -c "import secrets; print(secrets.token_hex(32))"`
- TZ: Set your local timezone (preferred over UTC) to ensure correct timestamps based on your locale [[memory:7499916]].

Recommended defaults (safe to keep initially):
- POSTGRES_DB=timetracker
- POSTGRES_USER=timetracker
- POSTGRES_PASSWORD=timetracker

If you use the bundled PostgreSQL container, leave `DATABASE_URL` as:
`postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker`

### 2) Use the example compose file

We provide `docker-compose.example.yml` with sane defaults using the published image `ghcr.io/drytrix/timetracker:latest` [[memory:7499921]]. Copy it as your working compose file or run it directly:

```bash
# Option A: Use example directly
docker-compose -f docker-compose.example.yml up -d

# Option B: Make it your default compose
cp docker-compose.example.yml docker-compose.yml
docker-compose up -d
```

Access the app at `http://localhost:8080`.

For a full stack with HTTPS reverse proxy and monitoring, see the root `docker-compose.yml` and the Monitoring section below.

### 3) Verify
```bash
docker-compose ps
docker-compose logs app --tail=100
```

### 4) Optional services
- Reverse proxy (HTTPS): See `docker-compose.yml` (services `certgen` and `nginx`).
  - **Note**: The `certgen` service is now self-contained and works with Portainer and other container orchestration tools without requiring host filesystem mounts.
- Monitoring stack: Prometheus, Grafana, Loki, Promtail are available in `docker-compose.yml`.

---

## Environment Variables Reference

All environment variables can be provided via `.env` and are consumed by the `app` container unless otherwise noted. Defaults shown are the effective values if not overridden.

### Core
- SECRET_KEY: Secret used for sessions/CSRF. Required in production. No default.
- FLASK_ENV: Flask environment. Default: `production`.
- FLASK_DEBUG: Enable debug. Default: `false`.
- TZ: Local timezone (e.g., `Europe/Brussels`). Default: `Europe/Rome` in env.example; compose defaults may override.

### Database
- DATABASE_URL: SQLAlchemy URL. Default: `postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker`.
- POSTGRES_DB: Database name (db service). Default: `timetracker`.
- POSTGRES_USER: Database user (db service). Default: `timetracker`.
- POSTGRES_PASSWORD: Database password (db service). Default: `timetracker`.
- POSTGRES_HOST: Hostname for external DB (not needed with bundled db). Default: `db`.

### Application behavior
- CURRENCY: ISO currency code. Default: `EUR`.
- ROUNDING_MINUTES: Rounding step for entries. Default: `1`.
- SINGLE_ACTIVE_TIMER: Allow only one active timer per user. Default: `true`.
- IDLE_TIMEOUT_MINUTES: Auto-pause after idle. Default: `30`.
- ALLOW_SELF_REGISTER: Allow new users to self-register by entering any username and password on the login page. Default: `true`. **Security note**: When enabled, anyone can create an app user with whatever credentials they type. The app does not use or import database credentials—users are created with exactly what is entered. Avoid using your database username (e.g. `timetracker`) as an app username; if someone creates an app user with matching DB credentials, it can be confusing or a security risk.
- ADMIN_USERNAMES: Comma-separated admin usernames. Default: `admin`. **Important**: Only the first username in the list is automatically created during database initialization. Additional admin usernames must either:
  - Self-register by logging in (if `ALLOW_SELF_REGISTER=true`), or
  - Be created manually by an existing admin user.
  Example: `ADMIN_USERNAMES=admin,manager` - only "admin" is created automatically; "manager" must self-register or be created manually.

### Authentication

- **AUTH_METHOD**: Controls authentication method. Options:
  - `none`: No password authentication (username only). Use only in trusted environments.
  - `local`: Password authentication required (default). Users must set and use passwords.
  - `oidc`: OIDC/Single Sign-On only. Local login form is hidden.
  - `both`: OIDC + local password authentication. Users can choose either method.
  
  Default: `local`. See [OIDC Setup Guide](OIDC_SETUP.md) for detailed explanations.
- OIDC_ISSUER: OIDC provider issuer URL.
- OIDC_CLIENT_ID: OIDC client id.
- OIDC_CLIENT_SECRET: OIDC client secret.
- OIDC_REDIRECT_URI: App redirect URI for OIDC callback.
- OIDC_SCOPES: Space-separated scopes. Default: `openid profile email`.
- OIDC_USERNAME_CLAIM: Default: `preferred_username`.
- OIDC_FULL_NAME_CLAIM: Default: `name`.
- OIDC_EMAIL_CLAIM: Default: `email`.
- OIDC_GROUPS_CLAIM: Default: `groups`.
- OIDC_ADMIN_GROUP: Optional admin group name.
- OIDC_ADMIN_EMAILS: Optional comma-separated admin emails.
- OIDC_POST_LOGOUT_REDIRECT_URI: Optional RP-initiated logout return URI.

### CSRF and Cookies
- WTF_CSRF_ENABLED: Enable CSRF protection. Default: `true` (example) or `false` in dev.
- WTF_CSRF_TIME_LIMIT: Token lifetime (seconds). Default: `3600`.
- WTF_CSRF_SSL_STRICT: Require HTTPS for CSRF referer checks. Default: `true` for production via compose; set `false` for HTTP.
- WTF_CSRF_TRUSTED_ORIGINS: Comma-separated allowed origins (scheme://host). Default: `https://localhost`.
- PREFERRED_URL_SCHEME: `http` or `https`. Default: `https` in production setups; set `http` for local.
- SESSION_COOKIE_SECURE: Send cookies only over HTTPS. Default: `true` (prod) / `false` (local test).
- SESSION_COOKIE_HTTPONLY: Default: `true`.
- SESSION_COOKIE_SAMESITE: `Lax` | `Strict` | `None`. Default: `Lax`.
- REMEMBER_COOKIE_SECURE: Default: `true` (prod) / `false` (local test).
- CSRF_COOKIE_SECURE: Default: `true` (prod) / `false` (local test).
- CSRF_COOKIE_HTTPONLY: Default: `false`.
- CSRF_COOKIE_SAMESITE: Default: `Lax`.
- CSRF_COOKIE_NAME: Default: `XSRF-TOKEN`.
- CSRF_COOKIE_DOMAIN: Optional cookie domain for subdomains (unset by default).
- PERMANENT_SESSION_LIFETIME: Session lifetime seconds. Default: `86400`.

### File uploads and backups
- MAX_CONTENT_LENGTH: Max upload size in bytes. Default: `16777216` (16MB).
- UPLOAD_FOLDER: Upload path inside container. Default: `/data/uploads`.
- BACKUP_FOLDER: Optional override for where backup archives are stored. Default: `<UPLOAD_FOLDER>/backups` (e.g. `/data/uploads/backups`).
- BACKUP_RETENTION_DAYS: Retain DB backups (if enabled). Default: `30`.
- BACKUP_TIME: Backup time (HH:MM). Default: `02:00`.

### Logging
- LOG_LEVEL: Default: `INFO`.
- LOG_FILE: Default: `/data/logs/timetracker.log` or `/app/logs/timetracker.log` based on compose.

### Analytics & Telemetry (optional)
- SENTRY_DSN: Sentry DSN (empty by default).
- SENTRY_TRACES_RATE: 0.0–1.0 sampling rate. Default: `0.0`.
- POSTHOG_API_KEY: PostHog API key (empty by default).
- POSTHOG_HOST: PostHog host. Default: `https://app.posthog.com`.
- ENABLE_TELEMETRY: Anonymous install telemetry toggle. Default: `false`.
- TELE_SALT: Unique salt for anonymous fingerprinting (optional).
- APP_VERSION: Optional override; usually auto-detected.

### Reverse proxy & monitoring (compose-only variables)
- HOST_IP: Used by `certgen` (in `docker-compose.remote.yml`) to embed SANs in self-signed certs. Default: `192.168.1.100`.
- Grafana variables (service `grafana` in `docker-compose.yml`):
  - GF_SECURITY_ADMIN_PASSWORD: Default: `admin` (set your own in prod).
  - GF_USERS_ALLOW_SIGN_UP: Default: `false`.
  - GF_SERVER_ROOT_URL: Default: `http://localhost:3000`.

---

## Monitoring stack (optional)

The root `docker-compose.yml` includes Prometheus, Grafana, Loki and Promtail. Start them together with the app:

```bash
docker-compose up -d  # uses the root compose with monitoring
```

Open:
- App: `http://localhost` (or `https://localhost` if certificates are present)
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

For CSRF and cookie issues behind proxies, see `docs/CSRF_CONFIGURATION.md`.

---

## Troubleshooting

- CSRF token errors: Ensure `SECRET_KEY` is stable and set correct CSRF/cookie flags for HTTP vs HTTPS.
- Database connection: Confirm `db` service is healthy and `DATABASE_URL` points to it.
- Timezone issues: Set `TZ` to your local timezone [[memory:7499916]].

### Database Tables Not Created (PostgreSQL)

**Symptoms**: Services start successfully, but database tables are missing when using PostgreSQL (works fine with SQLite).

**Solution**:
1. Ensure the database container is healthy and the `app` service waits for it:
   ```bash
   docker-compose ps
   docker-compose logs app | grep -i "database\|migration\|initialization"
   ```

2. Check that Flask-Migrate runs properly during startup. The entrypoint script should automatically:
   - Initialize Flask-Migrate if needed
   - Create and apply migrations
   - Verify tables exist

3. If tables are still missing, manually trigger database initialization:
   ```bash
   docker-compose exec app flask db upgrade
   ```

4. For a fresh start with clean volumes:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

5. Verify tables were created:
   ```bash
   docker-compose exec db psql -U timetracker -d timetracker -c "\dt"
   ```

### Admin User Authentication Issues

**Symptoms**: Cannot login with usernames from `ADMIN_USERNAMES` (e.g., `ADMIN_USERNAMES=admin,manager`).

**Important Notes**:
- Only the **first** username in `ADMIN_USERNAMES` is automatically created during database initialization
- Additional admin usernames in the list must be created separately before they can login

**Solutions**:

1. **If using multiple admin usernames**, create them using one of these methods:

   **Option A: Self-Registration** (if `ALLOW_SELF_REGISTER=true`):
   - Go to the login page
   - Enter the username (e.g., "manager")
   - Set a password and login
   - The user will automatically get admin role if their username is in `ADMIN_USERNAMES`

   **Option B: Manual Creation** (recommended for production):
   - Login with the first admin user (e.g., "admin")
   - Go to **Admin → Users → Create User**
   - Create the additional admin users manually
   - They will automatically get admin role when they login (if their username is in `ADMIN_USERNAMES`)

2. **If you cannot login with the first admin user**:
   - Verify the user was created: `docker-compose exec db psql -U timetracker -d timetracker -c "SELECT username, role FROM users;"`
   - If the user doesn't exist, check container logs for initialization errors
   - The default admin username is "admin" (or the first value in `ADMIN_USERNAMES`)

3. **For fresh installations**, ensure:
   - `ADMIN_USERNAMES` is set in your `.env` file before starting containers
   - Database initialization completed successfully (check logs)
   - If using `AUTH_METHOD=local`, the default admin user has no password initially. On first login, enter the admin username and choose any password (minimum 8 characters)—it will be set and you will be logged in. There is no default password documented because you define it yourself on first use.


