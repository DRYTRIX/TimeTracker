# TimeTracker Public Docker Image Setup

This guide explains how to set up and use the public Docker image for TimeTracker, which provides faster deployment and consistent builds across different environments.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- GitHub account (for accessing the container registry)
- Basic knowledge of Docker commands

### Step 1: Enable GitHub Container Registry

1. **Push your code to GitHub** (if not already done)
2. **The GitHub Actions workflow will automatically build and publish images** when you:
   - Push to the `main` branch
   - Create a release with a `v*` tag
   - Create a pull request (builds but doesn't publish)

### Step 2: Deploy Using Public Image

#### Option A: Automated Deployment Script

**Linux/macOS:**
```bash
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
# Remote production image (latest)
docker-compose -f docker-compose.remote.yml up -d
```

**Windows:**
```cmd
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
docker-compose -f docker-compose.remote.yml up -d
```

#### Option B: Manual Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/TimeTracker.git
   cd TimeTracker
   ```

2. (Optional) **Use a specific version tag:** set the tag in `docker-compose.remote.yml`.

3. **Create environment file:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Pull and run the image:**
   ```bash
   docker pull ghcr.io/drytrix/timetracker:latest
   docker-compose -f docker-compose.remote.yml up -d
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# Required
SECRET_KEY=your-secure-random-string-here
ADMIN_USERNAMES=admin,manager

# Optional
TZ=Europe/Rome
CURRENCY=EUR
ROUNDING_MINUTES=1
SINGLE_ACTIVE_TIMER=true
ALLOW_SELF_REGISTER=true
IDLE_TIMEOUT_MINUTES=30

# Database (using PostgreSQL from docker-compose)
DATABASE_URL=postgresql+psycopg2://timetracker:timetracker@db:5432/timetracker
```

### Docker Compose Configuration

Use `docker-compose.remote.yml` (production) or `docker-compose.remote-dev.yml` (testing):

- **App**: `ghcr.io/drytrix/timetracker` image
- **PostgreSQL**: Database service with healthcheck
- **Ports**: App exposed on 8080 by default

## 📦 Available Images

### Image Tags

- `latest` - Latest build from main branch
- `v1.0.0` - Specific version releases
- `main-abc123` - Build from specific commit SHA

### Supported Architectures

- `linux/amd64` - Intel/AMD 64-bit processors
- `linux/arm64` - ARM 64-bit (Apple Silicon, ARM servers)
- `linux/arm/v7` - ARM 32-bit (Raspberry Pi 3/4)

## 🔄 Updating

### Automatic Updates

The public image is automatically updated when you push to the main branch. To update your deployment:

```bash
# Pull the latest image
docker pull ghcr.io/drytrix/timetracker:latest

# Restart the containers
docker-compose -f docker-compose.remote.yml up -d
```

### Manual Updates

For specific versions:

```bash
# Pull a specific version
docker pull ghcr.io/drytrix/timetracker:v1.0.0

# Update docker-compose.remote.yml to use the specific tag
# Then restart
docker-compose -f docker-compose.remote.yml up -d
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Image Not Found

**Error:** `manifest for ghcr.io/username/timetracker:latest not found`

**Solution:**
- Ensure the GitHub Actions workflow has run successfully
- Check that your repository name is correct
- Verify the image exists in your GitHub Packages

#### 2. Permission Denied

**Error:** `denied: permission_denied`

**Solution:**
- Ensure your GitHub repository is public, or
- Use a personal access token for private repositories

#### 3. Architecture Mismatch

**Error:** `no matching manifest for linux/arm64`

**Solution:**
- The image supports multiple architectures automatically
- If you're on ARM64, the correct image will be pulled automatically

### Debugging

#### Check Image Details

```bash
# List available images
docker images ghcr.io/drytrix/timetracker

# Inspect image details
docker inspect ghcr.io/drytrix/timetracker:latest
```

#### View Logs

```bash
# Application logs
docker-compose -f docker-compose.remote.yml logs app

# Database logs
docker-compose -f docker-compose.remote.yml logs db

# All logs
docker-compose -f docker-compose.remote.yml logs -f
```

#### Health Check

```bash
# Check if the application is running
curl http://localhost:8080/_health

# Check container status
docker-compose -f docker-compose.remote.yml ps
```

## 🔒 Security Considerations

### Public vs Private Images

- **Public repositories**: Images are publicly accessible
- **Private repositories**: Require authentication to pull images

### Authentication for Private Repositories

If your repository is private, you'll need to authenticate:

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Or use a personal access token
docker login ghcr.io -u USERNAME -p YOUR_TOKEN
```

### Environment Variables

- Never commit sensitive environment variables to version control
- Use `.env` files (already in `.gitignore`)
- Consider using Docker secrets for production deployments

## 📊 Monitoring

### Health Checks

The application includes built-in health checks:

```bash
# Manual health check
curl -f http://localhost:8080/_health

# Docker health check status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Logs

```bash
# Follow application logs
docker-compose -f docker-compose.remote.yml logs -f app

# Export logs for analysis
docker-compose -f docker-compose.remote.yml logs app > timetracker.log
```

## 🚀 Production Deployment

### Recommended Setup

1. **Use specific version tags** instead of `latest`
2. **Set up proper environment variables**
3. **Configure HTTPS** using the Caddy reverse proxy
4. **Set up monitoring** and log aggregation
5. **Regular backups** of the PostgreSQL database

### Example Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    image: ghcr.io/drytrix/timetracker:v1.0.0
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - ADMIN_USERNAMES=${ADMIN_USERNAMES}
      - TZ=${TZ}
    volumes:
      - app_data:/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/_health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 🤝 Contributing

To contribute to the Docker image setup:

1. **Fork the repository**
2. **Make your changes**
3. **Test the Docker build locally**
4. **Submit a pull request**

The GitHub Actions workflow will automatically test your changes and build new images.

## 📚 Additional Resources

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [TimeTracker Main Documentation](README.md)
