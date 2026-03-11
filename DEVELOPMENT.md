# TimeTracker Development Guide

Quick reference for running the project locally, running tests, and contributing. For full guidelines, see [Contributing](CONTRIBUTING.md) and the [developer documentation](docs/development/CONTRIBUTING.md).

## Running Locally

### Option A: Python and virtual environment

1. Clone the repo and enter the directory:

   ```bash
   git clone https://github.com/drytrix/TimeTracker.git
   cd TimeTracker
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and set required variables:

   ```bash
   cp env.example .env
   ```

   Edit `.env`: set `SECRET_KEY` (e.g. from `python -c "import secrets; print(secrets.token_hex(32))"`). For a local DB, you can use SQLite (see [Local Testing with SQLite](docs/development/LOCAL_TESTING_WITH_SQLITE.md)).

5. Initialize the database and run the app:

   ```bash
   flask db upgrade
   flask run
   ```

   By default the app is at http://127.0.0.1:5000.

### Option B: Docker (SQLite, no PostgreSQL)

For a quick run without installing Python locally:

```bash
docker-compose -f docker-compose.local-test.yml up --build
```

Then open http://localhost:8080. See [Local Testing with SQLite](docs/development/LOCAL_TESTING_WITH_SQLITE.md) for details.

## Environment Setup

- Copy `env.example` to `.env` and adjust values.
- Key variables: `SECRET_KEY`, `DATABASE_URL` (or leave default for SQLite), `TZ`, `CURRENCY`.
- Full list and descriptions: [Docker Compose Setup](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md) and `env.example`.

## Dependencies

- **Python:** 3.11+
- **Package list:** `requirements.txt`
- **Package install for tests:** `setup.py` is used so the app can be installed as a package (e.g. `pip install -e .`) for testing; core dependencies remain in `requirements.txt`.

## Folder Structure

```
TimeTracker/
├── app/              # Flask app: routes, models, services, templates, utils
├── desktop/          # Electron-style desktop app
├── mobile/           # Flutter mobile app
├── docker/           # Docker config and scripts
├── tests/            # Pytest tests
├── docs/             # Documentation
├── app.py            # Application entry point
├── env.example       # Environment template
└── requirements.txt # Python dependencies
```

For more detail, see [ARCHITECTURE.md](ARCHITECTURE.md) and [Project Structure](docs/development/PROJECT_STRUCTURE.md).

## Coding Conventions

- Follow the [Contributing guidelines](docs/development/CONTRIBUTING.md): PEP 8, Black (line length 88), type hints and docstrings where appropriate.
- Use blueprints for routes; keep business logic in [services](docs/development/SERVICE_LAYER_AND_BASE_CRUD.md).

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Single file
pytest tests/test_timer.py
```

See [Contributing – Testing](docs/development/CONTRIBUTING.md#testing) for more options and conventions.

## Contributing

1. Read [CONTRIBUTING.md](CONTRIBUTING.md).
2. Follow the full [Contributing guidelines](docs/development/CONTRIBUTING.md) (branching, PR process, changelog).
3. For user-facing changes, add an entry under **Unreleased** in [CHANGELOG.md](CHANGELOG.md).

## Releases

How versions and releases are managed is documented in [Version Management](docs/admin/deployment/VERSION_MANAGEMENT.md). The application version is defined in `setup.py` as the single source of truth.
