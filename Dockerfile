# syntax=docker/dockerfile:1.4

# --- Stage 1: Frontend Build ---
FROM node:18-slim as frontend
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build:docker

# --- Stage 2: Python Application ---
# Use bookworm for newer packages and more stable mirrors.
FROM python:3.11-slim-bookworm

# Build-time version argument with safe default
ARG APP_VERSION=dev-0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV APP_VERSION=${APP_VERSION}
ENV TZ=Europe/Rome

# Install system dependencies (with retries for flaky networks on CI/Render).
# Keep this list lean to reduce apt downloads and improve build reliability.
ARG APT_RETRIES=5
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -eux; \
    export DEBIAN_FRONTEND=noninteractive; \
    for i in $(seq 1 "$APT_RETRIES"); do \
      apt-get update -o Acquire::Retries=3 && break || (echo "apt-get update failed (attempt $i/$APT_RETRIES)"; sleep 3); \
    done; \
    for i in $(seq 1 "$APT_RETRIES"); do \
      apt-get install -y --no-install-recommends \
        curl \
        tzdata \
        bash \
        dos2unix \
        gosu \
        # WeasyPrint runtime deps
        libgdk-pixbuf-2.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        libpangocairo-1.0-0 \
        libffi-dev \
        shared-mime-info \
        # Fonts
        fonts-liberation \
        fonts-dejavu-core \
        # Postgres client tools (pg_dump/psql for backups/debug)
        postgresql-client \
      && break || (echo "apt-get install failed (attempt $i/$APT_RETRIES)"; sleep 5); \
    done; \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies with cache mount for pip
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user early (before copying files)
RUN useradd -m -u 1000 timetracker

# Copy project files with correct ownership
COPY --chown=timetracker:timetracker . .

# Also install certificate generation script to a stable path used by docs/compose
COPY --chown=timetracker:timetracker scripts/generate-certs.sh /scripts/generate-certs.sh

# Copy compiled assets from frontend stage (overwriting the stale one from COPY .)
COPY --chown=timetracker:timetracker --from=frontend /app/app/static/dist/output.css /app/app/static/dist/output.css

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
COPY --chown=timetracker:timetracker docker/start-fixed.py /app/start.py

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

# Set ownership only for directories that need write access
# (Most files already have correct ownership from COPY --chown)
RUN chown -R timetracker:timetracker \
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


