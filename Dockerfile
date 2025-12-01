# syntax=docker/dockerfile:1.4

# --- Stage 1: Frontend Build ---
FROM node:18-slim as frontend
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build:docker

# --- Stage 2: Python Application ---
FROM python:3.11-slim-bullseye

# Build-time version argument with safe default
ARG APP_VERSION=dev-0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV APP_VERSION=${APP_VERSION}
ENV TZ=Europe/Rome

# Install all system dependencies in a single layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    # Core utilities
    curl \
    tzdata \
    bash \
    dos2unix \
    gosu \
    # Network tools for debugging
    iproute2 \
    net-tools \
    iputils-ping \
    dnsutils \
    # WeasyPrint dependencies
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libpangocairo-1.0-0 \
    libffi-dev \
    shared-mime-info \
    # Fonts
    fonts-liberation \
    fonts-dejavu-core \
    # PostgreSQL client dependencies
    gnupg \
    wget \
    lsb-release \
    && sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies with cache mount for pip
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Also install certificate generation script to a stable path used by docs/compose
COPY scripts/generate-certs.sh /scripts/generate-certs.sh

# Copy compiled assets from frontend stage (overwriting the stale one from COPY .)
COPY --from=frontend /app/app/static/dist/output.css /app/app/static/dist/output.css

# Create all directories and set permissions in a single layer
RUN mkdir -p \
    /app/translations \
    /data \
    /data/uploads \
    /app/logs \
    /app/instance \
    /app/app/static/uploads/logos \
    /app/static/uploads/logos \
    && chmod -R 775 /app/translations \
    && chmod 755 /data /data/uploads /app/logs /app/instance \
    && chmod -R 755 /app/app/static/uploads /app/static/uploads

# Copy the startup script
COPY docker/start-fixed.py /app/start.py

# Fix line endings and set permissions in a single layer
RUN find /app/docker -name "*.sh" -o -name "*.py" | xargs dos2unix 2>/dev/null || true \
    && dos2unix /app/start.py /scripts/generate-certs.sh 2>/dev/null || true \
    && chmod +x \
    /app/start.py \
    /app/docker/init-database.py \
    /app/docker/init-database-sql.py \
    /app/docker/init-database-enhanced.py \
    /app/docker/verify-database.py \
    /app/docker/test-db.py \
    /app/docker/test-routing.py \
    /app/docker/entrypoint.sh \
    /app/docker/entrypoint_fixed.sh \
    /app/docker/entrypoint_simple.sh \
    /app/docker/entrypoint-local-test.sh \
    /app/docker/entrypoint-local-test-simple.sh \
    /app/docker/entrypoint.py \
    /app/docker/startup_with_migration.py \
    /app/docker/test_db_connection.py \
    /app/docker/debug_startup.sh \
    /app/docker/simple_test.sh \
    /scripts/generate-certs.sh

# Create non-root user and set ownership
RUN useradd -m -u 1000 timetracker \
    && chown -R timetracker:timetracker \
    /app \
    /data \
    /app/logs \
    /app/instance \
    /app/app/static/uploads \
    /app/static/uploads \
    /app/translations \
    /scripts

USER timetracker

# Expose port
EXPOSE 8080

# Note: Health check is configured in docker-compose.yml
# This allows different healthcheck settings per environment

# Set the entrypoint
ENTRYPOINT ["/app/docker/entrypoint_fixed.sh"]

# Run the application
CMD ["python", "/app/start.py"]


