# CSRF Token Configuration for Docker

This document explains how CSRF (Cross-Site Request Forgery) protection is configured in TimeTracker when running in Docker containers.

## Overview

TimeTracker uses Flask-WTF's `CSRFProtect` extension to protect against CSRF attacks. CSRF tokens are cryptographic tokens that ensure forms are submitted by legitimate users from your application, not from malicious third-party sites.

## How CSRF Tokens Work

1. When a user visits a page with a form, the server generates a unique CSRF token
2. This token is embedded in the form (usually as a hidden field)
3. When the form is submitted, the token is sent back to the server
4. The server validates the token matches what was originally generated
5. If the token is invalid or missing, the request is rejected with a 400 error

## Critical: SECRET_KEY Configuration

**CSRF tokens are signed using the Flask `SECRET_KEY`.** This means:

- ✅ The same `SECRET_KEY` must be used across container restarts
- ✅ The same `SECRET_KEY` must be used if you run multiple app replicas
- ⚠️ If `SECRET_KEY` changes, all existing CSRF tokens become invalid
- ⚠️ Users will get CSRF errors on form submissions if the key changes

### Generating a Secure SECRET_KEY

Generate a cryptographically secure random key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Setting SECRET_KEY in Docker

#### Option 1: Environment Variable File

Create a `.env` file (do not commit this to git):

```bash
SECRET_KEY=your-generated-key-here
```

Then run docker-compose:

```bash
docker-compose up -d
```

#### Option 2: Export Environment Variable

```bash
export SECRET_KEY="your-generated-key-here"
docker-compose up -d
```

#### Option 3: Docker Secrets (Production Recommended)

For production deployments with Docker Swarm or Kubernetes, use secrets management:

```yaml
secrets:
  secret_key:
    external: true

services:
  app:
    secrets:
      - secret_key
    environment:
      - SECRET_KEY_FILE=/run/secrets/secret_key
```

## CSRF Configuration Variables

### WTF_CSRF_ENABLED

Controls whether CSRF protection is enabled.

- **Default in Production**: `true`
- **Default in Development**: `false` (for easier testing)
- **Recommended**: Keep enabled in production

Set in docker-compose:

```yaml
environment:
  - WTF_CSRF_ENABLED=true
```

### WTF_CSRF_TIME_LIMIT

Time in seconds before a CSRF token expires.

- **Default**: `3600` (1 hour)
- **Range**: Set to `null` for no expiration, or any positive integer

Set in docker-compose:

```yaml
environment:
  - WTF_CSRF_TIME_LIMIT=3600
```

## Docker Compose Files

### docker-compose.yml (Local Development)

```yaml
environment:
  # CSRF enabled by default for security testing
  - WTF_CSRF_ENABLED=${WTF_CSRF_ENABLED:-true}
  - WTF_CSRF_TIME_LIMIT=${WTF_CSRF_TIME_LIMIT:-3600}
  - SECRET_KEY=${SECRET_KEY:-your-secret-key-change-this}
```

### docker-compose.remote.yml (Production)

```yaml
environment:
  # CSRF always enabled in production
  - WTF_CSRF_ENABLED=${WTF_CSRF_ENABLED:-true}
  - WTF_CSRF_TIME_LIMIT=${WTF_CSRF_TIME_LIMIT:-3600}
  - SECRET_KEY=${SECRET_KEY:-your-secret-key-change-this}
```

**Important**: The app will refuse to start in production mode with the default `SECRET_KEY`.

### docker-compose.local-test.yml (Testing)

```yaml
environment:
  # CSRF can be disabled for local testing
  - WTF_CSRF_ENABLED=${WTF_CSRF_ENABLED:-false}
  - WTF_CSRF_TIME_LIMIT=${WTF_CSRF_TIME_LIMIT:-3600}
  - SECRET_KEY=${SECRET_KEY:-local-test-secret-key}
```

## Verifying CSRF Protection

### Check if CSRF is Enabled

Look at the application logs when starting:

```bash
docker-compose logs app | grep -i csrf
```

### Test CSRF Protection

1. Open your browser's developer tools
2. Navigate to a form in TimeTracker
3. Look for a hidden input field: `<input type="hidden" name="csrf_token" value="...">`
4. Try submitting the form without the token (should fail with 400 error)

### Common Issues

#### Issue: "CSRF token missing or invalid"

**Cause**: One of the following:
- `SECRET_KEY` changed between token generation and validation
- Token expired (check `WTF_CSRF_TIME_LIMIT`)
- Clock skew between server and client
- Browser cookies disabled or blocked

**Solution**:
1. Check `SECRET_KEY` is consistent
2. Verify `WTF_CSRF_ENABLED=true`
3. Ensure cookies are enabled
4. Check system time is synchronized

#### Issue: Forms work in development but not in production Docker

**Cause**: Missing or misconfigured `SECRET_KEY`

**Solution**:
1. Set a proper `SECRET_KEY` in your `.env` file
2. Verify the environment variable is passed to the container:
   ```bash
   docker-compose exec app env | grep SECRET_KEY
   ```

#### Issue: CSRF tokens expire too quickly

**Cause**: `WTF_CSRF_TIME_LIMIT` too short

**Solution**: Increase the time limit or disable expiration:
```yaml
environment:
  - WTF_CSRF_TIME_LIMIT=7200  # 2 hours
```

## API Endpoints

The `/api/*` endpoints are **exempted from CSRF protection** because they use JSON and are designed for programmatic access. They rely on other authentication mechanisms instead.

## Security Best Practices

1. ✅ **Always use a strong SECRET_KEY in production**
2. ✅ **Keep SECRET_KEY secret** - never commit to version control
3. ✅ **Use the same SECRET_KEY across all app replicas**
4. ✅ **Enable CSRF protection in production** (`WTF_CSRF_ENABLED=true`)
5. ✅ **Use HTTPS in production** for secure cookie transmission
6. ✅ **Set appropriate cookie security flags**:
   - `SESSION_COOKIE_SECURE=true` (HTTPS only)
   - `SESSION_COOKIE_HTTPONLY=true` (no JavaScript access)
   - `SESSION_COOKIE_SAMESITE=Lax` (CSRF defense)

## Additional Resources

- [Flask-WTF CSRF Protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/2.3.x/security/)

## Summary

For CSRF tokens to work correctly in Docker:

1. **Set a strong SECRET_KEY** and keep it consistent
2. **Enable CSRF protection** with `WTF_CSRF_ENABLED=true`
3. **Configure timeout** appropriately with `WTF_CSRF_TIME_LIMIT`
4. **Use HTTPS in production** with secure cookie flags
5. **Never change SECRET_KEY** without understanding the impact

All docker-compose files have been updated with these settings and include helpful comments.

