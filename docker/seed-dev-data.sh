#!/bin/sh
# Run development data seed inside the container.
# Sets FLASK_ENV=development so the seed is allowed (production image defaults to FLASK_ENV=production).
#
# From host:
#   docker compose exec app /app/docker/seed-dev-data.sh
#
# Or with flask CLI (pass env explicitly):
#   docker compose exec -e FLASK_ENV=development app flask seed
set -e
export FLASK_ENV=development
exec python3 /app/scripts/seed-dev-data.py "$@"
