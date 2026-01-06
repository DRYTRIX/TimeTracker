# Troubleshooting OIDC DNS Resolution Errors

## Problem Description

When configuring OIDC (OpenID Connect) authentication, you may encounter DNS resolution errors during application startup, even though DNS resolution works correctly from the command line (e.g., `curl` or `ping`).

### Common Error Messages

```
Error loading metadata: HTTPSConnectionPool(host='auth.example.com', port=443): 
Max retries exceeded with url: /.well-known/openid-configuration 
(Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object>: 
Failed to resolve 'auth.example.com' ([Errno -2] Name or service not known)"))
```

### Why This Happens

This issue occurs because Python's `urllib3` library (used by Authlib) may use a different DNS resolution mechanism than the system's DNS resolver. Even though:

- System DNS resolution works (curl/ping succeed)
- Docker DNS configuration is correct
- Containers are on the same network

Python's resolver may still fail to resolve the domain name.

## Solutions

### Solution 1: Configure DNS Servers in Docker/Portainer (Recommended)

Explicitly configure DNS servers in your Docker Compose or Portainer stack configuration.

#### For Docker Compose

Add DNS configuration to your service:

```yaml
services:
  app:
    image: ghcr.io/drytrix/timetracker:latest
    dns:
      - 8.8.8.8          # Google DNS
      - 8.8.4.4          # Google DNS secondary
      # OR use your internal DNS server
      - 192.168.1.1      # Your router/internal DNS
    # ... rest of configuration
```

#### For Portainer Stacks

Edit your stack configuration and add DNS settings under the service definition:

```yaml
services:
  app:
    # ... other configuration ...
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

After updating, restart the container/stack.

### Solution 2: Use Docker Internal Networking

If both your OIDC provider (e.g., Authentik) and TimeTracker are running on the same Docker network, you can use Docker's internal DNS resolution by using the container/service name instead of the external domain.

#### Find Your OIDC Provider Container Name

In Portainer, check your OIDC provider stack for the service name, or use:

```bash
docker network inspect <network_name>
```

#### Update OIDC_ISSUER Environment Variable

Instead of:
```
OIDC_ISSUER=https://auth.example.com/application/o/time-tracker/
```

Use:
```
OIDC_ISSUER=https://authentik:9443/application/o/time-tracker/
```

Replace `authentik` with your actual Authentik service/container name and `9443` with the internal port.

**Note:** This only works for internal communication. External redirects (like OIDC callbacks) will still need the public domain.

### Solution 3: Add extra_hosts Mapping

Map the domain to an IP address in your Docker configuration.

#### For Docker Compose

```yaml
services:
  app:
    image: ghcr.io/drytrix/timetracker:latest
    extra_hosts:
      - "auth.example.com:192.168.1.100"  # Replace with actual OIDC provider IP
    # ... rest of configuration
```

#### For Portainer Stacks

```yaml
services:
  app:
    # ... other configuration ...
    extra_hosts:
      - "auth.example.com:192.168.1.100"
```

#### To Find the IP Address

```bash
# From within the TimeTracker container
docker exec -it timetracker-app ping -c 1 auth.example.com

# Or from host
ping auth.example.com
```

### Solution 4: Use Lazy Metadata Loading (Automatic)

TimeTracker now includes automatic lazy loading of OIDC metadata. If DNS resolution fails at startup, the application will:

1. Start successfully (no blocking errors)
2. Store OIDC configuration for lazy loading
3. Attempt to fetch metadata on the first login attempt
4. Retry with exponential backoff if DNS resolution fails

This means your application will start even if DNS isn't ready, and will automatically retry when a user attempts to log in.

#### Configuration Options

You can configure the retry behavior using environment variables:

```bash
# Timeout for each metadata fetch attempt (default: 10 seconds)
OIDC_METADATA_FETCH_TIMEOUT=10

# Number of retry attempts (default: 3)
OIDC_METADATA_RETRY_ATTEMPTS=3

# Delay between retries in seconds (default: 2)
OIDC_METADATA_RETRY_DELAY=2
```

## Verification Steps

### 1. Test DNS Resolution from Container

```bash
# Test DNS resolution using Python
docker exec -it <container> python -c "import socket; print(socket.gethostbyname('auth.example.com'))"

# Test with curl
docker exec -it <container> curl -I https://auth.example.com/.well-known/openid-configuration
```

### 2. Check Application Logs

Look for OIDC-related messages in your application logs:

```bash
# If using Docker
docker logs <container> | grep -i oidc

# Check for lazy loading messages
docker logs <container> | grep -i "lazy\|metadata"
```

### 3. Use the OIDC Debug Dashboard

1. Log in as an administrator
2. Navigate to **Admin → OIDC Settings**
3. Click **Test Configuration** to verify connectivity
4. Review the metadata display to confirm successful connection

### 4. Use the Guided Setup Wizard

TimeTracker includes a guided OIDC setup wizard that:

- Tests DNS resolution before configuration
- Validates metadata endpoint accessibility
- Provides troubleshooting tips if connection fails
- Generates correct configuration automatically

Access it via **Admin → OIDC Setup Wizard** (if available).

## Common Scenarios

### Scenario 1: Both Services on Same Docker Network

**Problem:** Authentik and TimeTracker are on the same Docker network but using external domains.

**Solution:** Use Docker internal service names (Solution 2) or ensure both services can resolve each other's external domains.

### Scenario 2: DNS Not Ready at Startup

**Problem:** DNS resolution works after container starts, but fails during startup.

**Solution:** Use lazy loading (Solution 4) - this is automatic and requires no configuration.

### Scenario 3: Custom DNS Server

**Problem:** Using a custom internal DNS server that Python can't access.

**Solution:** Configure explicit DNS servers (Solution 1) pointing to your DNS server.

### Scenario 4: Reverse Proxy with Different Domain

**Problem:** OIDC provider is behind a reverse proxy with a different domain.

**Solution:** Ensure the reverse proxy domain is resolvable and use that domain in `OIDC_ISSUER`.

## Still Having Issues?

If none of the above solutions work:

1. **Check Network Configuration**: Ensure containers are on the same network and can communicate
2. **Verify Firewall Rules**: Check if firewall is blocking DNS queries
3. **Review Provider Logs**: Check your OIDC provider logs for connection attempts
4. **Test from Host**: Verify DNS resolution works from the Docker host
5. **Check DNS Server**: Ensure your DNS server is responding correctly

## Related Documentation

- [OIDC Setup Guide](admin/configuration/OIDC_SETUP.md) - Complete OIDC configuration guide
- [Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md) - Docker deployment guide

## Technical Details

### How Lazy Loading Works

1. **At Startup**: If metadata fetch fails, TimeTracker stores OIDC configuration in app config
2. **On First Login**: When a user attempts OIDC login, the application:
   - Checks if OIDC client exists
   - If not, attempts to fetch metadata using the `requests` library (better DNS handling)
   - Registers the OAuth client with fetched metadata
   - Proceeds with normal OIDC flow

3. **Retry Logic**: Uses exponential backoff (2s, 4s, 8s delays) with configurable attempts

### Why requests Library Works Better

The `requests` library may use different DNS resolution mechanisms than `urllib3`, and sometimes succeeds where `urllib3` fails. TimeTracker's metadata fetcher uses `requests` for better compatibility.
