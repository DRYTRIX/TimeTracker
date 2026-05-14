#!/usr/bin/env bash
# Local mirror of .github/workflows/ci-comprehensive.yml — run: ./scripts/run-ci-local.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ci/lib.sh
source "${SCRIPT_DIR}/ci/lib.sh"

SKIP_INSTALL=0
NO_POSTGRES=0
NO_POSTGRES_DOCKER=0
NO_DOCKER_TEST=0

usage() {
  cat <<'EOF'
Run the same checks as .github/workflows/ci-comprehensive.yml (locally).

Usage:
  ./scripts/run-ci-local.sh [options] [command]

Options (place before command):
  --skip-install         Skip pip install (for any command that installs, or "all")
  --no-postgres          Only for "all": skip integration, db-upgrade, and full suite
  --no-postgres-docker   Use DATABASE_URL from the environment (no disposable Postgres container)
  --no-docker-test       Only for "all": skip Docker image build and /_health check

Commands:
  (default)   Same as "all" if you pass only options or no arguments
  all         Full pipeline (install, smoke, quality, security, units, postgres jobs, docker test)
  install     Install Python dependencies only
  smoke | code-quality | flake8 | black | isort | mypy
  security | security-pytest | safety
  unit-models | unit-routes | unit-api | unit-utils | unit-all
  integration | db-upgrade | full
  docker-test
  list        Print command list (short)
  help        This message

Examples:
  ./scripts/run-ci-local.sh smoke
  ./scripts/run-ci-local.sh --skip-install unit-routes
  ./scripts/run-ci-local.sh --no-postgres-docker integration   # uses $DATABASE_URL
  ./scripts/run-ci-local.sh --no-docker-test all

Shared implementation: scripts/ci/lib.sh
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 && "$1" == -* ]]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    --no-postgres) NO_POSTGRES=1 ;;
    --no-postgres-docker) NO_POSTGRES_DOCKER=1 ;;
    --no-docker-test) NO_DOCKER_TEST=1 ;;
    *)
      echo "Unknown option: $1" >&2
      usage 1
      ;;
  esac
  shift
done

CMD="${1:-all}"
[[ -n "${1:-}" ]] && shift || true

if [[ $# -gt 0 ]]; then
  echo "Unexpected arguments: $*" >&2
  usage 1
fi

ci_init_env

USE_EXISTING_PG=0
[[ "${NO_POSTGRES_DOCKER}" -eq 1 ]] && USE_EXISTING_PG=1

case "${CMD}" in
  help|-h|--help) usage 0 ;;
  list) ci_list_commands ;;

  install)
    if [[ "${SKIP_INSTALL}" -eq 1 ]]; then
      ci_log "Skipping pip install (--skip-install); nothing to do for install."
      exit 0
    fi
    ci_install
    ;;

  smoke) ci_smoke ;;
  code-quality) ci_code_quality ;;
  flake8) ci_flake8 ;;
  black) ci_black ;;
  isort) ci_isort ;;
  mypy) ci_mypy ;;

  security) ci_security ;;
  security-pytest) ci_security_pytest ;;
  safety) ci_safety ;;

  unit-models) ci_unit_models ;;
  unit-routes) ci_unit_routes ;;
  unit-api) ci_unit_api ;;
  unit-utils) ci_unit_utils ;;
  unit-all) ci_unit_all ;;

  integration) ci_integration "${USE_EXISTING_PG}" ;;
  db-upgrade) ci_db_upgrade "${USE_EXISTING_PG}" ;;
  full) ci_full_suite "${USE_EXISTING_PG}" ;;

  docker-test) ci_docker_test ;;

  all)
    ci_all "${SKIP_INSTALL}" "${NO_POSTGRES}" "${NO_POSTGRES_DOCKER}" "${NO_DOCKER_TEST}"
    ;;

  *)
    echo "Unknown command: ${CMD}" >&2
    echo "Run: ./scripts/run-ci-local.sh list" >&2
    exit 1
    ;;
esac
