# syntax=docker/dockerfile:1.4

# --- Stage 1: Frontend Build ---
FROM node:18-slim as frontend
WORKDIR /app
COPY package*.json ./
RUN npm install
# Copy files needed for Tailwind build
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY app/static/src ./app/static/src
COPY app/templates ./app/templates
# Create dist directory for output
RUN mkdir -p app/static/dist
# Run the build (creates app/static/dist/output.css)
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
# Support visibility: if donate_hide_public.pem is in project root it is copied to /app; set path so app finds it (override in compose if needed)
ENV DONATE_HIDE_PUBLIC_KEY_FILE=/app/donate_hide_public.pem

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

# Create non-root user early (before copying files)
RUN useradd -m -u 1000 timetracker

# Create all directories before copying files to ensure proper structure
RUN mkdir -p \
    /app/translations \
    /data \
    /data/uploads \
    /app/logs \
    /app/instance \
    /app/app/static/uploads/logos \
    /app/static/uploads/logos \
    /app/app/static/dist

# Copy project files with correct ownership (includes optional donate_hide_public.pem from root when present)
COPY --chown=timetracker:timetracker . .

# Also install certificate generation script to a stable path used by docs/compose
COPY --chown=timetracker:timetracker scripts/generate-certs.sh /scripts/generate-certs.sh

# Set permissions on directories and ensure static files are readable
RUN chmod -R 775 /app/translations \
    && chmod 755 /data /data/uploads /app/logs /app/instance \
    && chmod -R 755 /app/app/static/uploads /app/static/uploads \
    && chmod 755 /app/app/static/dist \
    && chmod -R 755 /app/app/static

# Copy compiled assets from frontend stage (after general COPY to ensure it overwrites any local version)
COPY --chown=timetracker:timetracker --from=frontend /app/app/static/dist/output.css /app/app/static/dist/output.css

# Ensure the CSS file has correct permissions
RUN chmod 644 /app/app/static/dist/output.css

# Copy the startup script
COPY --chown=timetracker:timetracker docker/start-fixed.py /app/start.py

# Precompile translations at build time for faster startup (no runtime pybabel calls).
# If Babel isn't available for some reason, don't fail the image build.
RUN pybabel compile -d /app/translations >/dev/null 2>&1 || true

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
    /app/docker/seed-dev-data.sh \
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


