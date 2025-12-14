# Quick Start: Local Development with Docker Compose

## TL;DR - Fastest Local Start

```powershell
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker

cp env.example .env
# Edit .env and set a strong SECRET_KEY

docker-compose -f docker-compose.example.yml up -d

# Open http://localhost:8080
```

See the full Docker Compose setup guide: `docs/DOCKER_COMPOSE_SETUP.md`.

## Local Development (Python) Alternative

If you prefer to run locally with Python:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Analytics & Telemetry (Optional)

To test PostHog or Sentry in development, set the respective variables in `.env` and restart the app. For advanced local analytics configuration, see `docs/analytics.md` and `assets/README.md`.

## Troubleshooting

- CSRF token errors: For HTTP (localhost), set `WTF_CSRF_SSL_STRICT=false` and ensure `SESSION_COOKIE_SECURE=false`/`CSRF_COOKIE_SECURE=false`.
- Database not ready: The app waits for Postgres healthcheck; check `docker-compose logs db`.
- Timezone issues: Set `TZ` to your locale.

