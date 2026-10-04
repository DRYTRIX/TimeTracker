"""Guard: every raw requests.* call under app/integrations/ must set timeout=.

Calls routed through app.utils.integration_http are fine (that helper applies
DEFAULT_TIMEOUT). This test only flags attribute calls on the name `requests`.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_DIR = REPO_ROOT / "app" / "integrations"
REQUEST_METHODS = frozenset({"get", "post", "put", "patch", "delete", "request"})


def _missing_timeout_calls(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "requests"
            and func.attr in REQUEST_METHODS
        ):
            continue
        if any(kw.arg == "timeout" for kw in node.keywords):
            continue
        rel = path.relative_to(REPO_ROOT)
        missing.append(f"{rel}:{node.lineno}")
    return missing


def test_all_integration_requests_calls_have_timeout():
    """Fail if any requests.get/post/put/patch/delete/request lacks timeout=."""
    assert INTEGRATIONS_DIR.is_dir(), f"Missing integrations dir: {INTEGRATIONS_DIR}"

    violations: list[str] = []
    for path in sorted(INTEGRATIONS_DIR.rglob("*.py")):
        violations.extend(_missing_timeout_calls(path))

    assert not violations, (
        "requests.get/post/put/patch/delete/request calls under app/integrations/ "
        "must pass timeout= (or use app.utils.integration_http). Missing:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
