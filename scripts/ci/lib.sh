# Shared helpers for local CI parity with .github/workflows/ci-comprehensive.yml
# shellcheck shell=bash
# Source from repo scripts: source "$(dirname "$0")/ci/lib.sh"

_ci_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CI_ROOT="$(cd "${_ci_lib_dir}/../.." && pwd)"

POSTGRES_CID="${POSTGRES_CID:-}"
DOCKER_TEST_CID="${DOCKER_TEST_CID:-}"

ci_log() { printf '\n== %s ==\n' "$*"; }

ci_init_env() {
  cd "${CI_ROOT}"
  export PYTHONPATH="${CI_ROOT}"
  export FLASK_APP="${FLASK_APP:-app.py}"
  export FLASK_ENV="${FLASK_ENV:-testing}"
  export INSTALLATION_CONFIG_DIR="${INSTALLATION_CONFIG_DIR:-${CI_ROOT}/.test_installation_config}"
  mkdir -p "${INSTALLATION_CONFIG_DIR}" "${INSTALLATION_CONFIG_DIR}/pytest-cache"
}

ci_cleanup() {
  local ec=$?
  if [[ -n "${DOCKER_TEST_CID}" ]]; then
    docker rm -f "${DOCKER_TEST_CID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${POSTGRES_CID}" ]]; then
    docker rm -f "${POSTGRES_CID}" >/dev/null 2>&1 || true
  fi
  exit "${ec}"
}

ci_enable_exit_cleanup() {
  trap ci_cleanup EXIT
}

ci_install() {
  ci_log "Install dependencies (requirements + editable package)"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  python -m pip install -r requirements-test.txt
  python -m pip install -e .
}

ci_smoke() {
  ci_log "Smoke tests"
  pytest -m smoke -v --tb=short --no-cov -n auto
}

ci_flake8() {
  ci_log "Code quality (flake8)"
  flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
  flake8 app/ --count --max-complexity=10 --max-line-length=120 --statistics
}

ci_black() {
  ci_log "Code quality (black)"
  black --check app/
}

ci_isort() {
  ci_log "Code quality (isort)"
  isort --check-only app/
}

ci_mypy() {
  ci_log "Code quality (mypy; non-fatal, same as CI)"
  mypy app/ || true
}

ci_code_quality() {
  ci_flake8
  ci_black
  ci_isort
  ci_mypy
}

# Exact security test selection (no -m security → no "deselected" noise). When adding a
# security test outside tests/test_security.py or tests/test_oidc_session_cookie_bloat.py,
# append its node id here (see: rg 'pytest.mark.security' tests).
_ci_security_tests=(
  tests/test_security.py
  tests/test_oidc_session_cookie_bloat.py
  tests/test_oidc_logout.py::test_logout_without_post_logout_uri_config
  tests/test_oidc_logout.py::test_logout_with_post_logout_uri_config
  tests/test_oidc_logout.py::test_logout_oidc_provider_has_revocation_endpoint_only
  tests/test_oidc_logout.py::test_logout_local_auth_method
  tests/test_oidc_logout.py::test_logout_clears_oidc_id_token_from_session
  tests/test_oidc_logout.py::test_logout_uses_cached_oidc_id_token_hint_when_present
  tests/test_oidc_logout.py::test_logout_with_both_auth_method_no_post_logout_uri
  tests/test_oidc_logout.py::test_logout_provider_metadata_load_fails_gracefully
  tests/test_time_entry_duplication.py::test_duplicate_own_entry_only
  tests/test_time_entry_duplication.py::test_admin_can_duplicate_any_entry
  tests/test_admin_settings_logo.py::test_logo_upload_requires_admin
  tests/test_admin_settings_logo.py::test_remove_logo_requires_admin
)

ci_security_pytest() {
  ci_log "Security tests (pytest)"
  # Writable cache when repo .pytest_cache is not writable.
  pytest -o "cache_dir=${INSTALLATION_CONFIG_DIR}/pytest-cache" \
    -v --tb=short --no-cov \
    -W "ignore:Can't sort tables for DROP:sqlalchemy.exc.SAWarning" \
    "${_ci_security_tests[@]}"
}

ci_safety() {
  ci_log "Safety (requirements.txt)"
  local report="${INSTALLATION_CONFIG_DIR}/safety-report.json"
  echo "Scanning requirements.txt (writes ${report}; may take a few minutes)..." >&2
  local ec=0
  python -m safety check --file requirements.txt --save-json "${report}" >/dev/null || ec=$?
  if [[ -f "${report}" ]]; then
    python "${CI_ROOT}/scripts/ci/sanitize_safety_report.py" "${report}" "${CI_ROOT}"
  fi
  echo "Wrote ${report}"
  if [[ "${ec}" -ne 0 ]]; then
    echo "Safety exited with code ${ec} (non-zero usually means reported vulnerabilities; see the JSON)." >&2
    return "${ec}"
  fi
}

ci_security() {
  ci_security_pytest
  ci_safety
}

ci_unit_models() {
  ci_log "Unit tests (models)"
  pytest -m "unit and models" -v -n auto --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing
}

ci_unit_routes() {
  ci_log "Unit tests (routes; -n 0 per CI)"
  pytest -m "unit and routes" -v -n 0 --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing
}

ci_unit_api() {
  ci_log "Unit tests (api + integration marker)"
  pytest -m "api and integration" -v -n auto --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing
}

ci_unit_utils() {
  ci_log "Unit tests (utils)"
  pytest -m "unit and utils" -v -n auto --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing
}

ci_unit_all() {
  ci_unit_models
  ci_unit_routes
  ci_unit_api
  ci_unit_utils
}

# Args: use_existing_db (1 = require DATABASE_URL, no Docker)
ci_ensure_postgres() {
  local use_existing="${1:-0}"

  if [[ "${use_existing}" -eq 1 ]]; then
    if [[ -z "${DATABASE_URL:-}" ]]; then
      echo "ERROR: DATABASE_URL must be set when using --no-postgres-docker." >&2
      exit 1
    fi
    export DATABASE_URL
    ci_log "Using DATABASE_URL from environment"
    return 0
  fi

  if [[ -n "${DATABASE_URL:-}" ]]; then
    export DATABASE_URL
    ci_log "Using existing DATABASE_URL"
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker not found and DATABASE_URL not set. Install Docker or export DATABASE_URL." >&2
    exit 1
  fi

  ci_log "Starting disposable Postgres (postgres:16-alpine, CI credentials)"
  POSTGRES_CID="$(
    docker run -d --rm \
      -e POSTGRES_PASSWORD=test_password \
      -e POSTGRES_USER=test_user \
      -e POSTGRES_DB=test_db \
      postgres:16-alpine
  )"
  ci_enable_exit_cleanup

  local _
  for _ in $(seq 1 60); do
    if docker exec "${POSTGRES_CID}" pg_isready -U test_user -d test_db >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! docker exec "${POSTGRES_CID}" pg_isready -U test_user -d test_db >/dev/null 2>&1; then
    echo "ERROR: Postgres did not become ready in time." >&2
    exit 1
  fi
  local pg_port
  pg_port="$(docker port "${POSTGRES_CID}" 5432 | head -1 | awk -F: '{print $NF}')"
  export DATABASE_URL="postgresql://test_user:test_password@127.0.0.1:${pg_port}/test_db"
  echo "DATABASE_URL=${DATABASE_URL}"
}

ci_integration() {
  local use_existing="${1:-0}"
  ci_ensure_postgres "${use_existing}"
  ci_log "Integration tests"
  pytest -m integration -v -n auto --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing
}

ci_db_upgrade() {
  local use_existing="${1:-0}"
  ci_ensure_postgres "${use_existing}"
  ci_log "Database migrations (flask db upgrade)"
  flask db upgrade
}

ci_full_suite() {
  local use_existing="${1:-0}"
  ci_ensure_postgres "${use_existing}"
  ci_log "Full test suite with coverage thresholds"
  pytest -v -n auto --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing \
    --cov-fail-under=35 --junitxml=junit.xml --maxfail=5
}

ci_docker_test() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "WARN: docker not installed; skipping Docker build test." >&2
    return 0
  fi

  ci_enable_exit_cleanup
  ci_log "Docker build (matches docker-build job)"
  local image_tag="timetracker-ci-local:latest"
  docker build -t "${image_tag}" "${CI_ROOT}"

  ci_log "Docker container startup + /_health (matches docker-build job)"
  local ctest_name="timetracker-ci-local-test-$$"
  local secret_key="test-secret-key-for-ci-only-$(openssl rand -hex 32)"
  DOCKER_TEST_CID="$(
    docker run -d --rm --name "${ctest_name}" \
      -p 0:8080 \
      -e DATABASE_URL="sqlite:////app/test.db" \
      -e SECRET_KEY="${secret_key}" \
      -e FLASK_ENV="development" \
      "${image_tag}"
  )"

  local host_port
  host_port="$(docker port "${DOCKER_TEST_CID}" 8080 | head -1 | awk -F: '{print $NF}')"
  local health_check_passed=false
  local i
  for i in $(seq 1 60); do
    if [[ "$(docker inspect -f '{{.State.Status}}' "${DOCKER_TEST_CID}" 2>/dev/null || echo gone)" != "running" ]]; then
      echo "Container exited unexpectedly. Logs:" >&2
      docker logs "${DOCKER_TEST_CID}" >&2 || true
      exit 1
    fi
    if curl -fsS "http://127.0.0.1:${host_port}/_health" >/dev/null 2>&1; then
      echo "Health check passed (attempt ${i}/60)"
      health_check_passed=true
      break
    fi
    if [[ $((i % 10)) -eq 0 ]]; then
      echo "Still waiting... (${i}/60)"
      docker logs --tail 10 "${DOCKER_TEST_CID}" || true
    fi
    sleep 2
  done
  if [[ "${health_check_passed}" != true ]]; then
    echo "Health check failed after 120s. Logs:" >&2
    docker logs "${DOCKER_TEST_CID}" >&2 || true
    exit 1
  fi
  curl -fsS "http://127.0.0.1:${host_port}/_health" >/dev/null
  docker stop "${DOCKER_TEST_CID}" >/dev/null
  DOCKER_TEST_CID=""
}

ci_all() {
  local skip_install="${1:-0}"
  local no_postgres="${2:-0}"
  local no_postgres_docker="${3:-0}"
  local no_docker_test="${4:-0}"
  local use_existing=0
  [[ "${no_postgres_docker}" -eq 1 ]] && use_existing=1

  if [[ "${skip_install}" -eq 0 ]]; then
    ci_install
  else
    ci_log "Skipping pip install (--skip-install)"
  fi

  ci_smoke
  ci_code_quality
  ci_security
  ci_unit_all

  if [[ "${no_postgres}" -eq 1 ]]; then
    ci_log "Skipping Postgres-backed tests (--no-postgres)"
  else
    ci_integration "${use_existing}"
    ci_db_upgrade "${use_existing}"
    ci_full_suite "${use_existing}"
  fi

  if [[ "${no_docker_test}" -eq 1 ]]; then
    ci_log "Skipping Docker image build / health check (--no-docker-test)"
  else
    ci_docker_test
  fi

  ci_log "All CI-local checks finished successfully."
}

ci_list_commands() {
  cat <<'EOF'
Commands (run one at a time):
  install           pip install requirements + test deps + editable package
  smoke             smoke tests
  code-quality      flake8, black, isort, mypy (mypy non-fatal)
  flake8            flake8 only
  black             black --check only
  isort             isort --check-only only
  mypy              mypy only (non-fatal)
  security          security pytest + safety
  security-pytest   security pytest only (explicit node list; see lib.sh)
  safety            safety check only
  unit-models       unit matrix: models
  unit-routes       unit matrix: routes (-n 0)
  unit-api          unit matrix: api + integration marker
  unit-utils        unit matrix: utils
  unit-all          all four unit groups
  integration       integration tests (starts disposable Postgres if DATABASE_URL unset)
  db-upgrade        flask db upgrade (needs DATABASE_URL or Docker Postgres)
  full              full pytest suite with coverage gates (needs DATABASE_URL or Docker)
  docker-test       docker build + container /_health
  all               full pipeline (same as before)

Postgres: integration / db-upgrade / full start postgres:16-alpine via Docker when
DATABASE_URL is unset. Use --no-postgres-docker and export DATABASE_URL to use your own DB.
EOF
}
