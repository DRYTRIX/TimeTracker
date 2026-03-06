# TimeTracker Makefile
# Common development and testing tasks

.PHONY: help install test test-smoke test-unit test-integration test-security test-coverage \
        test-fast test-parallel lint format clean docker-build docker-run setup dev security-scan frontend-a11y

# Default target
help:
	@echo "TimeTracker Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install all dependencies"
	@echo "  make dev            - Setup development environment"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run full test suite"
	@echo "  make test-smoke     - Run smoke tests (< 1 min)"
	@echo "  make test-unit      - Run unit tests (2-5 min)"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-routes    - Run route/endpoint tests"
	@echo "  make test-models    - Run model tests"
	@echo "  make test-api       - Run API tests"
	@echo "  make test-security  - Run security tests"
	@echo "  make test-database  - Run database tests"
	@echo "  make test-coverage  - Run tests with 50% coverage requirement"
	@echo "  make test-coverage-report - Generate coverage report (no minimum)"
	@echo "  make test-fast      - Run tests in parallel"
	@echo "  make test-parallel  - Run tests with 4 workers"
	@echo "  make test-failed    - Re-run last failed tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linters (flake8)"
	@echo "  make format         - Format code (black + isort)"
	@echo "  make format-check   - Check code formatting"
	@echo "  make security-scan  - Run security scanners"
	@echo "  make frontend-a11y  - Run accessibility check on web app (requires app running; set FRONTEND_URL)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container"
	@echo "  make docker-test    - Test Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Clean temporary files"
	@echo "  make clean-all      - Clean everything including deps"

# Setup and installation
install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

setup: dev
	@echo "Development environment ready!"
	@echo "Run 'make test-smoke' to verify setup"

# Testing targets
test:
	pytest -v

test-smoke:
	pytest -m smoke -v

test-unit:
	pytest -m unit -v

test-integration:
	pytest -m integration -v

test-security:
	pytest -m security -v

test-database:
	pytest -m database -v

test-routes:
	pytest -m routes -v

test-models:
	pytest -m models -v

test-api:
	pytest -m api -v

test-coverage:
	pytest --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml --cov-fail-under=50
	@echo "Coverage report: htmlcov/index.html"

test-coverage-report:
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"
	@echo "Note: No minimum coverage threshold enforced"

test-fast:
	pytest -n auto -v

test-parallel:
	pytest -n 4 -v

test-failed:
	pytest --lf -v

test-debug:
	pytest -v --tb=long --pdb

# Code quality targets
lint:
	@echo "Running flake8..."
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 app/ --count --max-complexity=10 --max-line-length=120 --statistics

format:
	@echo "Running black..."
	black app/
	@echo "Running isort..."
	isort app/

format-check:
	@echo "Checking black..."
	black --check app/
	@echo "Checking isort..."
	isort --check-only app/

security-scan:
	@echo "Running bandit..."
	bandit -r app/
	@echo "Running safety..."
	safety check --file requirements.txt

# Frontend quality: accessibility check (requires app running at FRONTEND_URL, default http://localhost:3000)
FRONTEND_URL ?= http://localhost:3000
frontend-a11y:
	@echo "Accessibility check: $(FRONTEND_URL)"
	@command -v npx >/dev/null 2>&1 || { echo "npx not found; install Node.js or run: npx pa11y $(FRONTEND_URL)"; exit 0; }
	npx --yes pa11y "$(FRONTEND_URL)" 2>/dev/null || echo "Run: npx pa11y $(FRONTEND_URL) (start app first). See docs/development/FRONTEND_QUALITY_GATES.md"

# Docker targets
docker-build:
	docker build -t timetracker:latest .

docker-run:
	docker run -d --name timetracker \
		-p 8080:8080 \
		-e DATABASE_URL="sqlite:///test.db" \
		-e SECRET_KEY="dev-secret" \
		timetracker:latest

docker-test:
	docker build -t timetracker:test .
	docker run --rm timetracker:test pytest -m smoke

docker-stop:
	docker stop timetracker || true
	docker rm timetracker || true

# Database targets
db-migrate:
	flask db migrate

db-upgrade:
	flask db upgrade

db-downgrade:
	flask db downgrade

# Cleanup targets
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf *.db
	rm -rf dist/
	rm -rf build/

clean-all: clean
	rm -rf venv/
	rm -rf .venv/
	find . -type f -name '*.log' -delete

# Development server
run:
	python app.py

run-dev:
	FLASK_ENV=development FLASK_DEBUG=1 python app.py

# CI/CD simulation
ci-local:
	@echo "Simulating CI pipeline locally..."
	@echo "1. Running smoke tests..."
	make test-smoke
	@echo "2. Running unit tests..."
	make test-unit
	@echo "3. Running code quality checks..."
	make lint
	make format-check
	@echo "4. Running security scan..."
	make security-scan
	@echo "✓ Local CI checks passed!"

# Install pre-commit hooks
hooks:
	@echo "Installing pre-commit hooks..."
	@which pre-commit > /dev/null || pip install pre-commit
	pre-commit install
	@echo "Pre-commit hooks installed!"

# Documentation
docs:
	@echo "Documentation files:"
	@echo "  - CI_CD_QUICK_START.md"
	@echo "  - CI_CD_DOCUMENTATION.md"
	@echo "  - CI_CD_IMPLEMENTATION_SUMMARY.md"

