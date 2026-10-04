#!/usr/bin/env bash
# Blocking pip-audit against requirements.txt.
# Respects scripts/ci/pip-audit-ignore.txt for currently unfixable findings.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IGNORE_FILE="${ROOT}/scripts/ci/pip-audit-ignore.txt"

IGNORE_ARGS=()
if [[ -f "${IGNORE_FILE}" ]]; then
  while IFS= read -r line || [[ -n "${line}" ]]; do
    # Strip comments and blank lines
    line="${line%%#*}"
    line="$(echo "${line}" | tr -d '[:space:]')"
    [[ -z "${line}" ]] && continue
    IGNORE_ARGS+=(--ignore-vuln "${line}")
  done < "${IGNORE_FILE}"
fi

echo "🔍 pip-audit: requirements.txt"
python -m pip_audit -r "${ROOT}/requirements.txt" --progress-spinner off "${IGNORE_ARGS[@]+"${IGNORE_ARGS[@]}"}"
