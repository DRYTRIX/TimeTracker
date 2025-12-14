# CSRF Cookie Issues with Remote IP Access

## Problem

When accessing the TimeTracker application:
- ✅ Works fine via `http://localhost:8080`
- ❌ CSRF cookie not created when accessing via IP address (e.g., `http://192.168.1.100:8080`)

## Root Cause

The issue occurs due to browser cookie security policies and Flask's CSRF protection settings:

1. **WTF_CSRF_SSL_STRICT**: When set to `true` (default in production), Flask-WTF rejects cookies from non-HTTPS connections that it considers "insecure"
2. **SESSION_COOKIE_SECURE**: When set to `true`, cookies are only sent over HTTPS, blocking HTTP access via IP
3. **SameSite Policy**: Browsers treat localhost and IP addresses differently for cookie SameSite policies

## Quick Fix

### Option 1: Environment Variables (Recommended)

Add these to your `.env` file:

```bash
# Disable SSL strict mode for HTTP access
WTF_CSRF_SSL_STRICT=false

# Ensure cookies work over HTTP
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false

# Optional: Adjust SameSite if needed
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
```

Then restart the application:

```bash
docker-compose restart app
```

### Option 2: Docker Compose Override

Create or update `docker-compose.override.yml`:

```yaml
services:
  app:
    environment:
      - WTF_CSRF_SSL_STRICT=false
      - SESSION_COOKIE_SECURE=false
      - CSRF_COOKIE_SECURE=false
      - SESSION_COOKIE_SAMESITE=Lax
```

Restart:

```bash
docker-compose up -d
```

## Detailed Explanation

### WTF_CSRF_SSL_STRICT

This Flask-WTF setting controls whether CSRF protection rejects requests it considers insecure:

- **`true`** (default in production): Rejects cookies from HTTP on non-localhost addresses
- **`false`**: Allows cookies over HTTP (needed for IP access without HTTPS)

**When to use `false`:**
- Development/testing environments
- Local network access via IP address
- When HTTPS is not configured

**When to use `true`:**
- Production with HTTPS enabled
- Public-facing applications
- Maximum security requirements

### Cookie Secure Flags

**SESSION_COOKIE_SECURE** and **CSRF_COOKIE_SECURE**:
- **`true`**: Cookies only sent over HTTPS (blocks HTTP access)
- **`false`**: Cookies sent over HTTP and HTTPS

### SameSite Policy

Controls when browsers send cookies:

- **`Strict`**: Cookie only sent for same-site requests (most restrictive)
- **`Lax`** (default): Cookie sent for same-site and top-level navigation
- **`None`**: Cookie sent with all requests (requires Secure flag)

## Testing

### 1. Check Current Settings

```bash
docker-compose exec app env | grep -E "(CSRF|SESSION_COOKIE|WTF)"
```

### 2. Verify Cookie Creation

1. Open browser DevTools (F12)
2. Go to **Application** → **Cookies**
3. Navigate to your app (via IP address)
4. Look for these cookies:
   - `session` - Session cookie
   - `XSRF-TOKEN` - CSRF token cookie

### 3. Test CSRF Token Endpoint

```bash
# Via localhost (should work)
curl -v http://localhost:8080/auth/csrf-token

# Via IP address (should also work after fix)
curl -v http://192.168.1.100:8080/auth/csrf-token
```

Look for `Set-Cookie` headers in the response.

## Security Considerations

### Development vs Production

**Development (HTTP access via IP):**
```bash
WTF_CSRF_SSL_STRICT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

**Production (HTTPS with domain):**
```bash
WTF_CSRF_SSL_STRICT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Risk Assessment

Setting `WTF_CSRF_SSL_STRICT=false`:
- ✅ **Safe for**: Local networks, development, testing
- ⚠️ **Risk for**: Public internet without HTTPS
- ❌ **Never**: Production with sensitive data over HTTP

### Best Practices

1. **Use HTTPS in Production**: Always enable HTTPS for production deployments
2. **Separate Configs**: Use different settings for dev/prod environments
3. **Network Security**: If using HTTP, ensure network is trusted (VPN, local network)
4. **Monitor Logs**: Watch for CSRF failures in application logs

## Alternative Solutions

### Solution 1: Use a Domain Name

Instead of accessing via IP, use a domain name:

```bash
# Add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
192.168.1.100 timetracker.local

# Access via domain
http://timetracker.local:8080
```

### Solution 2: Enable HTTPS

Set up HTTPS with a self-signed certificate for local development:

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=192.168.1.100"

# Update docker-compose to use HTTPS
# Then set:
WTF_CSRF_SSL_STRICT=true
SESSION_COOKIE_SECURE=true
```

### Solution 3: Disable CSRF (Development Only)

⚠️ **Only for isolated development environments:**

```bash
WTF_CSRF_ENABLED=false
```

**Never use this in production or with real data!**

## Troubleshooting

### Issue: Cookie Still Not Created

**Check 1: Verify environment variables are loaded**
```bash
docker-compose exec app env | grep WTF_CSRF_SSL_STRICT
```

**Check 2: Restart the container**
```bash
docker-compose restart app
```

**Check 3: Check application logs**
```bash
docker-compose logs app | tail -50
```

### Issue: CSRF Token Works but Form Fails

This is different from cookie creation. Check:

1. Token in HTML form: View page source and search for `csrf_token`
2. Token in request: Browser DevTools → Network → Form Data
3. Token expiration: Increase `WTF_CSRF_TIME_LIMIT`

### Issue: Works on Chrome but not Firefox/Safari

Different browsers have different cookie policies:

1. Try disabling enhanced tracking protection
2. Check browser console for cookie warnings
3. Use consistent SameSite settings

## Configuration Examples

### Local Development (HTTP, IP Access)

```bash
# .env
FLASK_ENV=development
WTF_CSRF_ENABLED=true
WTF_CSRF_SSL_STRICT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
```

### Production (HTTPS, Domain)

```bash
# .env
FLASK_ENV=production
WTF_CSRF_ENABLED=true
WTF_CSRF_SSL_STRICT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Strict
CSRF_COOKIE_SAMESITE=Strict
```

### Testing (Disable CSRF)

```bash
# .env (isolated test environment only!)
FLASK_ENV=development
WTF_CSRF_ENABLED=false
```

## Related Documentation

- [CSRF Configuration Guide](CSRF_CONFIGURATION.md)
- [CSRF Troubleshooting](../CSRF_TROUBLESHOOTING.md)
- [Docker Setup Guide](DOCKER_PUBLIC_SETUP.md)

## Summary

**The core issue**: `WTF_CSRF_SSL_STRICT=true` (default) blocks cookie creation for HTTP access via IP addresses.

**The solution**: Set `WTF_CSRF_SSL_STRICT=false` when accessing via IP without HTTPS.

**For production**: Always use HTTPS with proper domain names and keep strict settings enabled.

---

**Last Updated:** October 2024  
**Applies To:** TimeTracker v1.0+

