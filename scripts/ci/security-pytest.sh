#!/usr/bin/env bash
# Run the same security pytest set as ci_security_pytest (single entry for CI + Makefile).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"
ci_init_env
ci_security_pytest
