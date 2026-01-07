# Portainer Deployment Guide

This guide explains how to deploy TimeTracker using Portainer, addressing common issues and providing step-by-step instructions.

## Overview

TimeTracker can be deployed using Portainer's Docker Compose stack feature. The compose files have been optimized to work seamlessly with Portainer, eliminating dependencies on host filesystem mounts for critical components.

## Prerequisites

- Portainer installed and running
- Docker and Docker Compose available on the host
- Access to the TimeTracker repository or compose files
- Basic understanding of Docker Compose

## Quick Start

### Option 1: Using Git Repository (Recommended)

1. **In Portainer, go to Stacks → Add Stack**
2. **Choose "Repository"**
3. **Enter repository details:**
   - Repository URL: `https://github.com/DRYTRIX/TimeTracker.git`
   - Repository reference: `main` (or your preferred branch/tag)
   - Compose path: `docker-compose.remote.yml`
4. **Configure environment variables** (see Environment Variables section below)
5. **Click "Deploy the stack"**

### Option 2: Using Web Editor

1. **In Portainer, go to Stacks → Add Stack**
2. **Choose "Web editor"**
3. **Copy the contents of `docker-compose.remote.yml`** from the repository
4. **Paste into the editor**
5. **Configure environment variables** (see Environment Variables section below)
6. **Click "Deploy the stack"**

## Environment Variables

Create a `.env` file or configure environment variables in Portainer:

### Required Variables

```bash
SECRET_KEY=your-secure-random-string-here  # Generate: python -c "import secrets; print(secrets.token_hex(32))"
ADMIN_USERNAMES=admin
```

### Recommended Variables

```bash
TZ=Europe/Brussels
CURRENCY=EUR
ROUNDING_MINUTES=1
SINGLE_ACTIVE_TIMER=true
ALLOW_SELF_REGISTER=true
IDLE_TIMEOUT_MINUTES=30

# Database credentials (if using bundled PostgreSQL)
POSTGRES_DB=timetracker
POSTGRES_USER=timetracker
POSTGRES_PASSWORD=change-this-password

# HTTPS Configuration (for certificate generation)
HOST_IP=192.168.1.100  # Your server's IP address
```

### Configuring Variables in Portainer

1. In the stack editor, scroll to "Environment variables"
2. Click "Add environment variable" for each variable
3. Or use the "Environment" tab to bulk configure

## Understanding the Services

### certgen Service

The `certgen` service automatically generates SSL certificates for HTTPS:

- **Self-contained**: Uses a dedicated Dockerfile with scripts baked in
- **No host mounts required**: Works without repository files on the host
- **Automatic**: Generates certificates if they don't exist
- **Persistent**: Certificates are stored in the `nginx/ssl` volume

**Note**: This service has been optimized to work with Portainer. It no longer requires the `scripts` directory to be mounted from the host, eliminating the error:
```
sh: can't open '/scripts/generate-certs.sh': No such file or directory
```

### nginx Service

The nginx reverse proxy:
- Terminates SSL/TLS connections
- Proxies requests to the app service
- Waits for certgen to complete successfully

### app Service

The main TimeTracker application:
- Uses the published image: `ghcr.io/drytrix/timetracker:latest`
- Connects to the PostgreSQL database
- Exposes port 8080 internally (not publicly)

### db Service

PostgreSQL database:
- Stores all application data
- Health checks ensure proper initialization
- Data persists in Docker volumes

## Troubleshooting

### Issue: certgen Service Fails

**Symptoms:**
```
service "certgen" didn't complete successfully: exit 2
sh: can't open '/scripts/generate-certs.sh': No such file or directory
```

**Solution:**
This issue has been resolved in the latest version. Ensure you're using:
- `docker-compose.remote.yml` from the latest repository version
- The compose file includes the `build` section for certgen instead of volume mounts

**Verification:**
Check that the certgen service in your compose file looks like:
```yaml
certgen:
  build:
    context: .
    dockerfile: docker/Dockerfile.certgen
  # ... not using volume mount for scripts
```

### Issue: Certificates Not Generated

**Check certgen logs:**
1. In Portainer, go to Containers
2. Find `timetracker-certgen-remote`
3. View logs

**Common causes:**
- Insufficient permissions on `nginx/ssl` volume
- HOST_IP not set correctly
- Container resource limits

**Solution:**
1. Ensure the `nginx/ssl` volume is writable
2. Set `HOST_IP` environment variable to your server's IP
3. Check container resource limits in Portainer

### Issue: nginx Won't Start

**Check dependencies:**
1. Verify certgen completed successfully
2. Check nginx logs in Portainer
3. Ensure certificates exist in the `nginx/ssl` volume

**Solution:**
1. Restart the certgen service
2. Verify `cert.pem` and `key.pem` exist
3. Check nginx configuration in `nginx/conf.d`

### Issue: Can't Access Application

**Check ports:**
1. Verify ports 80 and 443 are exposed
2. Check firewall settings on the host
3. Verify the stack is running

**Solution:**
1. In Portainer, check the stack status
2. View container logs for errors
3. Test internal connectivity: `docker exec -it timetracker-app-remote curl http://localhost:8080/_health`

## Advanced Configuration

### Custom Domain

To use a custom domain:

1. **Update HOST_IP** to match your domain's IP
2. **Update nginx configuration** in `nginx/conf.d/https.conf`
3. **Use Let's Encrypt** instead of self-signed certificates (see HTTPS guides)

### SSL Certificate Options

The certgen service generates self-signed certificates by default. For production:

1. **Use Let's Encrypt** with certbot
2. **Import existing certificates** into the `nginx/ssl` volume
3. **Update nginx configuration** to use your certificates

### Resource Limits

Configure resource limits in Portainer:

1. Go to Stack → Editor
2. Add resource limits to services:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Maintenance

### Updating TimeTracker

1. **Pull latest image:**
   - In Portainer, go to Images
   - Pull `ghcr.io/drytrix/timetracker:latest`

2. **Redeploy stack:**
   - Go to Stacks
   - Select your TimeTracker stack
   - Click "Editor"
   - Click "Update the stack"

### Backing Up Data

1. **Database backup:**
   - Use Portainer's volume backup feature
   - Or export directly: `docker exec timetracker-db-remote pg_dump -U timetracker timetracker > backup.sql`

2. **Application data:**
   - Back up the `app_data_remote` volume
   - Back up the `app_uploads_remote` volume

### Monitoring

- Check container logs in Portainer
- Monitor resource usage in the Containers view
- Set up alerts in Portainer for container failures

## Best Practices

1. **Use secrets for sensitive data:**
   - Store `SECRET_KEY` and database passwords in Portainer secrets
   - Reference secrets in compose file environment variables

2. **Regular backups:**
   - Schedule automatic database backups
   - Backup volumes regularly

3. **Keep updated:**
   - Regularly pull latest images
   - Update compose files when new versions are released

4. **Security:**
   - Change default passwords
   - Use strong SECRET_KEY
   - Enable firewall rules
   - Consider using HTTPS with trusted certificates

## Related Documentation

- [Docker Compose Setup](../configuration/DOCKER_COMPOSE_SETUP.md) - General Docker Compose guide
- [Docker Public Setup](../configuration/DOCKER_PUBLIC_SETUP.md) - Public image deployment
- [Automatic HTTPS Setup](../security/README_HTTPS_AUTO.md) - HTTPS configuration
- [Troubleshooting](../configuration/DOCKER_STARTUP_TROUBLESHOOTING.md) - Common issues

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review container logs in Portainer
3. Check the [GitHub Issues](https://github.com/DRYTRIX/TimeTracker/issues)
4. Review the [main troubleshooting guide](../../../docs/admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)
